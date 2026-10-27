"""0.8 linking retained; 0.9 replaces gameplay commands with strict observation."""

from uuid import uuid4
import asyncio, importlib.util, json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import timedelta
import httpx, pytest
from sqlalchemy import select, text, inspect
from test_game import clean, client, player, state
from app.database import Session, engine
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


def snapshot():
    # Rate counters are security metadata, not gameplay; tests disable them via fixture.
    with engine.connect() as db:
        return {
            t: db.execute(
                text(
                    'SELECT row_to_json(r)::text FROM "'
                    + t
                    + '" r ORDER BY row_to_json(r)::text'
                )
            )
            .scalars()
            .all()
            for t in inspect(engine).get_table_names()
            if t != "rate_limit_buckets"
        }


def test_private_link_queries_are_side_effect_free_including_expired_auction(
    client, monkeypatch
):
    h = player(client)
    bh, code = link(client, h, monkeypatch)
    other = player(client, "other")
    s = state(client, h)
    cid = s["character"]["id"]
    # An expired listing must stay expired OPEN: observation may never settle it.
    with Session.begin() as db:
        item = m.Item(owner=None, definition="crystal", quantity=1, location="auction")
        db.add(item)
        db.flush()
        db.add(
            m.Auction(
                item_id=item.id,
                quantity=1,
                former_owner_id=cid,
                opening_price=1,
                ends_at=utc_now() - timedelta(minutes=1),
            )
        )
    before = snapshot()
    for section in [
        "state",
        "character",
        "attributes",
        "inventory",
        "equipment",
        "location",
        "map",
        "expedition",
        "rewards",
        "debt",
        "auctions",
        "contracts",
        "wallet",
        "mineral",
        "recovery",
    ]:
        url = (
            "/discord/123/state"
            if section == "state"
            else "/discord/123/queries/" + section
        )
        r = client.get(url, headers=bh)
        assert r.status_code == 200, r.text
        assert not any(
            k in r.text
            for k in [
                "confirmation_hash",
                "password",
                "test-service-key",
                "Bearer",
                "confirmation_token",
            ]
        )
        assert snapshot() == before, section
    inv = client.get("/discord/123/queries/inventory", headers=bh).json()["inventory"]
    assert all(i["id"] in {x["id"] for x in s["inventory"]} for i in inv)
    assert client.get("/discord/123/state", headers=h).status_code == 403
    assert client.get("/discord/999/state", headers=bh).status_code == 404
    assert client.get("/discord/123/queries/admin", headers=bh).status_code == 404
    assert (
        client.post(
            "/discord/link", headers=bh, json={"code": code, "discord_id": "123"}
        ).status_code
        == 400
    )
    assert client.post("/discord/unlink", headers=h, json={}).status_code == 200
    assert client.get("/discord/123/state", headers=bh).status_code == 404


@pytest.mark.parametrize(
    "route",
    [
        "equipment/preview",
        "operations/00000000-0000-0000-0000-000000000001/confirm",
        "move",
        "battles",
        "buy",
        "sell",
        "contracts/1/accept",
        "auctions/1/bids",
        "lunar/nuggets/split",
        "attack",
        "target",
        "resources/1/collect",
        "rituals",
    ],
)
def test_discord_has_no_gameplay_capability(client, monkeypatch, route):
    h = player(client)
    bh, _ = link(client, h, monkeypatch)
    before = snapshot()
    r = client.post(
        "/discord/123/" + route,
        headers=bh,
        json={"item_id": 1, "equipped": False, "confirmation_token": "x" * 64},
    )
    assert r.status_code == (
        410 if route.startswith(("equipment/", "operations/")) else 404
    )
    # Service key never substitutes for player or admin credentials on normal APIs.
    for path in [
        "/move",
        "/inventory/1/equip",
        "/contracts/1/accept",
        "/lunar/nuggets/split",
        "/admin/operations/preview",
    ]:
        assert client.post(path, headers=bh, json={}).status_code in (401, 403)
    assert snapshot() == before


def test_old_receipts_preserved_but_never_applied(client, monkeypatch):
    h = player(client)
    bh, _ = link(client, h, monkeypatch)
    s = state(client, h)
    with Session.begin() as db:
        c = db.get(m.Character, s["character"]["id"])
        id = str(uuid4())
        db.add(
            m.DiscordOperation(
                id=id,
                account_id=c.account_id,
                character_id=c.id,
                discord_id="123",
                item_id=s["inventory"][0]["id"],
                equipped=False,
                before={},
                confirmation_hash="a" * 64,
                expires_at=utc_now() + timedelta(minutes=5),
            )
        )
    before = snapshot()
    assert (
        client.post(
            f"/discord/123/operations/{id}/confirm",
            headers=bh,
            json={"confirmation_token": "b" * 64},
        ).status_code
        == 410
    )
    assert snapshot() == before


def test_bot_private_queries_commands_and_no_mutation_buttons():
    spec = importlib.util.spec_from_file_location(
        "tower_readonly_bot", Path(__file__).resolve().parents[2] / "discord-bot/bot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def run():
        async def transport(request):
            if request.url.path.endswith("/inventory"):
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
            return httpx.Response(401, json={"detail": "Sessão inválida"})

        bot = module.TowerBot(
            httpx.AsyncClient(
                base_url="http://api", transport=httpx.MockTransport(transport)
            )
        )
        names = [c.name for c in bot.tree.get_commands()]
        assert len(names) == len(set(names)) == 16 and "equipar" not in names
        assert {"carteira", "minerio", "mapa", "vincular", "recuperacao"} <= set(names)
        assert not hasattr(module, "EquipmentConfirmation")
        i = SimpleNamespace(
            user=SimpleNamespace(id=123),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await bot.show(i, "inventory")
        sent = i.followup.send.await_args.kwargs
        assert (
            sent["ephemeral"]
            and "view" not in sent
            and "@everyone" not in sent["embed"].description
        )
        await bot.show(i, "character")
        assert i.followup.send.await_args.kwargs["ephemeral"]
        with pytest.raises(ValueError):
            await bot.request(i, "/discord/123/equipment/preview", {})

        async def offline(request):
            raise httpx.ConnectError("offline")

        await bot.api.aclose()
        bot.api = httpx.AsyncClient(
            base_url="http://api", transport=httpx.MockTransport(offline)
        )
        await bot.show(i, "inventory")
        assert "indisponível" in i.followup.send.await_args.args[0]
        await bot.close()

    asyncio.run(run())


def test_database_read_only_guard_rolls_back_accidental_future_write(
    client, monkeypatch
):
    from sqlalchemy.exc import DBAPIError
    from app import game

    h = player(client)
    bh, _ = link(client, h, monkeypatch)
    before = snapshot()

    def accidental_write(db, c):
        db.execute(text("UPDATE characters SET hp=0 WHERE id=:id"), {"id": c.id})
        return []

    monkeypatch.setattr(game, "inventory", accidental_write)
    with pytest.raises(DBAPIError):
        client.get("/discord/123/queries/inventory", headers=bh)
    assert snapshot() == before
