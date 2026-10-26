from uuid import uuid4
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import asyncio, importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
from sqlalchemy import select, func
from test_game import clean, client, player, state
from app.database import Session
from app.config import settings
from app import models as m
from app.clock import utc_now


def link(client, h, monkeypatch, id="123"):
    monkeypatch.setattr(settings, "discord_service_key", "test-service-key")
    headers = {"X-Bot-Key": "test-service-key"}
    code = client.post("/discord/code", headers=h, json={}).json()["code"]
    r = client.post(
        "/discord/link", headers=headers, json={"code": code, "discord_id": id}
    )
    assert r.status_code == 200, r.text
    return headers, code


def test_private_linked_queries_same_state_and_invalid_service(client, monkeypatch):
    h = player(client)
    bh, code = link(client, h, monkeypatch)
    assert client.get("/discord/123/state", headers=h).status_code == 403
    assert (
        client.post(
            "/discord/link", headers=bh, json={"code": code, "discord_id": "123"}
        ).status_code
        == 400
    )
    for section in [
        "character",
        "attributes",
        "inventory",
        "equipment",
        "location",
        "expedition",
        "rewards",
        "debt",
        "auctions",
        "contracts",
    ]:
        r = client.get("/discord/123/queries/" + section, headers=bh)
        assert r.status_code == 200, r.text
        assert not any(
            k in r.text
            for k in ["confirmation_hash", "password", "test-service-key", "Bearer"]
        )
    assert (
        client.get("/discord/123/queries/character", headers=bh).json()["coins_exact"]
        == state(client, h)["coins_exact"]
    )
    assert client.get("/discord/999/state", headers=bh).status_code == 404
    other = player(client, "other")
    code = client.post("/discord/code", headers=other, json={}).json()["code"]
    assert (
        client.post(
            "/discord/link", headers=bh, json={"code": code, "discord_id": "123"}
        ).status_code
        == 409
    )
    assert client.post("/discord/unlink", headers=h, json={}).status_code == 200
    assert client.get("/discord/123/state", headers=bh).status_code == 404


def test_equipment_confirmation_identity_expiry_stale_and_replay(client, monkeypatch):
    h = player(client)
    bh, _ = link(client, h, monkeypatch)
    item = state(client, h)["inventory"][0]["id"]
    path = "/discord/123/equipment/preview"
    r = client.post(path, headers=bh, json={"item_id": item, "equipped": False})
    assert r.status_code == 200, r.text
    p = r.json()
    body = {"confirmation_token": p["confirmation_token"]}
    endpoint = f"/discord/123/operations/{p['id']}/confirm"
    other = player(client, "other")
    link(client, other, monkeypatch, "456")
    assert (
        client.post(
            endpoint.replace("/123/", "/456/"), headers=bh, json=body
        ).status_code
        == 404
    )
    assert (
        client.post(
            endpoint, headers=bh, json={"confirmation_token": "x" * 30}
        ).status_code
        == 403
    )
    with ThreadPoolExecutor(3) as pool:
        rs = list(
            pool.map(lambda _: client.post(endpoint, headers=bh, json=body), range(3))
        )
    assert all(r.status_code == 200 for r in rs), [r.text for r in rs]
    assert not state(client, h)["inventory"][0]["equipped"]
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.WorldEvent)
                .where(m.WorldEvent.kind == "DISCORD_EQUIPMENT_CHANGED")
            )
            == 1
        )
    p = client.post(path, headers=bh, json={"item_id": item, "equipped": True}).json()
    with Session.begin() as db:
        db.get(m.DiscordOperation, p["id"]).expires_at = utc_now() - timedelta(
            seconds=1
        )
    assert (
        client.post(
            f"/discord/123/operations/{p['id']}/confirm",
            headers=bh,
            json={"confirmation_token": p["confirmation_token"]},
        ).status_code
        == 409
    )
    p = client.post(path, headers=bh, json={"item_id": item, "equipped": True}).json()
    assert (
        client.post(f"/inventory/{item}/equip", headers=h, json={}).status_code == 200
    )
    assert (
        client.post(
            f"/discord/123/operations/{p['id']}/confirm",
            headers=bh,
            json={"confirmation_token": p["confirmation_token"]},
        ).status_code
        == 409
    )
    foreign = state(client, other)["inventory"][0]["id"]
    assert (
        client.post(
            path, headers=bh, json={"item_id": foreign, "equipped": True}
        ).status_code
        == 404
    )


def test_bot_commands_are_private_handle_api_errors_and_do_not_show_tokens():
    spec = importlib.util.spec_from_file_location(
        "tower_discord_bot", Path(__file__).resolve().parents[2] / "discord-bot/bot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def run():
        async def transport(request):
            return httpx.Response(401, json={"detail": "Sessão inválida"})

        api = httpx.AsyncClient(
            base_url="http://api", transport=httpx.MockTransport(transport)
        )
        bot = module.TowerBot(api)
        names = [c.name for c in bot.tree.get_commands()]
        assert len(names) == len(set(names)) and len(names) == 14
        i = SimpleNamespace(
            user=SimpleNamespace(id=123),
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await bot.show(i, "inventory")
        i.response.defer.assert_awaited_once_with(ephemeral=True)
        i.followup.send.assert_awaited_once_with("Sessão inválida", ephemeral=True)
        view = module.EquipmentConfirmation(
            bot, 123, {"id": str(uuid4()), "confirmation_token": "secret-value"}
        )
        foreign = SimpleNamespace(
            user=SimpleNamespace(id=999),
            response=SimpleNamespace(send_message=AsyncMock()),
        )
        assert not await view.interaction_check(foreign)
        foreign.response.send_message.assert_awaited_once()
        for cmd in bot.tree.get_commands():
            assert cmd.default_permissions is None
        await bot.close()

    asyncio.run(run())


def test_bot_success_network_failure_and_repeated_confirmation_are_private():
    spec = importlib.util.spec_from_file_location(
        "tower_bot_safe", Path(__file__).resolve().parents[2] / "discord-bot/bot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def run():
        count = 0

        async def transport(request):
            nonlocal count
            if request.url.path.endswith("/queries/inventory"):
                return httpx.Response(
                    200,
                    json={
                        "inventory": [
                            {
                                "id": 1,
                                "name": "@everyone",
                                "quantity": 1,
                                "equipped": True,
                            }
                        ]
                    },
                )
            count += 1
            return httpx.Response(200, json={"message": "Equipamento atualizado"})

        bot = module.TowerBot(
            httpx.AsyncClient(
                base_url="http://api", transport=httpx.MockTransport(transport)
            )
        )
        i = SimpleNamespace(
            user=SimpleNamespace(id=123),
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await bot.show(i, "inventory")
        sent = i.followup.send.await_args.kwargs
        assert (
            sent["ephemeral"] is True and "@everyone" not in sent["embed"].description
        )
        view = module.EquipmentConfirmation(
            bot, 123, {"id": str(uuid4()), "confirmation_token": "never-visible-token"}
        )
        await view.confirm.callback(i)
        await view.confirm.callback(i)
        assert count == 1 and "never-visible-token" not in str(
            i.followup.send.await_args_list
        )

        async def offline(request):
            raise httpx.ConnectError("offline")

        await bot.api.aclose()
        bot.api = httpx.AsyncClient(
            base_url="http://api", transport=httpx.MockTransport(offline)
        )
        await bot.show(i, "inventory")
        assert i.followup.send.await_args.kwargs["ephemeral"] is True
        assert "indisponível" in i.followup.send.await_args.args[0]
        await bot.close()

    asyncio.run(run())
