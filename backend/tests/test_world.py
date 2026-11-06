from uuid import uuid4
from sqlalchemy import select, func
from test_game import clean, client, player, state, navigate, walk_tiles
from app.database import Session
from app.models import RoomState, Character, WorldEvent, Treasury
from app.rooms import template
from app.config import settings


def adventure(c, h):
    return c.post("/adventure", json={"request_id": str(uuid4())}, headers=h)


def secret(c, h, mp):
    mp.setattr(settings, "secret_chance", 1)
    assert adventure(c, h).status_code == 200
    assert c.post("/dungeons/secret/enter", json={}, headers=h).status_code == 200


def battle(c, h, monster):
    walk_tiles(c, h, state(c, h)["map"]["monsters"][monster])
    r = c.post("/battles", json={"monster": monster}, headers=h)
    assert r.status_code == 200, r.text
    b = r.json()
    while b["status"] == "active":
        r = c.post(
            f'/battles/{b["id"]}/action',
            json={"turn": b["turn"], "action": "attack"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        b = r.json()
    return b


def test_city_guild_training(client):
    h = player(client)
    navigate(client, h, "city1")
    s = state(client, h)
    assert s["room"]["safe"] and s["map"]["width"] > 16 and not s["map"]["monsters"]
    assert (
        client.post("/battles", json={"monster": "slime"}, headers=h).status_code == 409
    )
    edge = s["room"]["exits"][0]
    assert (
        client.post("/rooms/exits/" + str(edge["id"]), json={}, headers=h).status_code
        == 409
    )
    assert client.post("/rooms/exits/99999", json={}, headers=h).status_code == 404
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    assert client.post("/interact", json={}, headers=h).status_code == 200
    navigate(client, h, "training")
    before = state(client, h)
    b = battle(client, h, "dummy")
    after = state(client, h)
    assert (
        b["claimed"]
        and b["reward_amount"] == 0
        and before["inventory"] == after["inventory"]
    )
    for key in ("hp", "xp", "level", "coins"):
        assert before["character"][key] == after["character"][key]
    assert not client.get("/rewards", headers=h).json()


def test_deterministic_generation():
    assert template(1729) == template(1729)
    assert len({str(template(i)) for i in range(20)}) >= 2
    assert all(template(i)["monsters"] for i in range(20))


def test_procedural_persistence_and_replay(client, monkeypatch):
    monkeypatch.setattr(settings, "secret_chance", 0)
    h = player(client)
    body = {"request_id": str(uuid4())}
    assert client.post("/adventure", json=body, headers=h).status_code == 200
    s = state(client, h)
    assert s["room"]["kind"] == "PROCEDURAL"
    expected = __import__("json").loads(
        __import__("json").dumps(template(s["room"]["seed"]))
    )
    assert {key: s["map"][key] for key in expected if key != "spawns"} == {
        key: value for key, value in expected.items() if key != "spawns"
    }
    assert set(s["map"]["spawns"]) == set(expected["spawns"])
    assert client.post("/adventure", json=body, headers=h).status_code == 200
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "ADVENTURE_STARTED")
            )
            == 1
        )
    assert adventure(client, h).status_code == 409
    exp = s["expedition"]["id"]
    preview = client.get(f"/expeditions/{exp}/flee-preview", headers=h).json()
    assert (
        client.post(
            f"/expeditions/{exp}/flee",
            json={
                "confirmed": True,
                "confirmation_token": preview["confirmation_token"],
            },
            headers=h,
        ).status_code
        == 200
    )
    assert adventure(client, h).status_code == 200
    fresh = state(client, h)
    assert fresh["room"]["id"] != s["room"]["id"]
    assert fresh["map"]["theme"] != s["map"]["theme"]


def test_secrets_no_spoilers_and_ownership(client, monkeypatch):
    h = player(client)
    s = state(client, h)
    assert (
        s["atlas"]["secrets"] == {"found": 0, "total": 1}
        and "Cripta" not in str(s)
        and "warden" not in str(s)
    )
    assert client.post("/dungeons/secret/enter", json={}, headers=h).status_code == 404
    monkeypatch.setattr(settings, "secret_chance", 1)
    assert adventure(client, h).status_code == 200
    s = state(client, h)
    r = next(r for r in s["atlas"]["rooms"] if r["kind"] == "SECRET_DUNGEON")
    assert (
        r["codex"] == {}
        and "warden" not in str(s)
        and s["atlas"]["secrets"]["found"] == 1
    )
    other = player(client, "bob")
    assert "Cripta" not in str(state(client, other))
    assert (
        client.post("/dungeons/secret/enter", json={}, headers=other).status_code == 404
    )
    assert client.post("/dungeons/secret/enter", json={}, headers=h).status_code == 200
    assert state(client, h)["map"]["recommended_level"] == 8


def test_secret_death_no_loss(client, monkeypatch):
    h = player(client)
    secret(client, h, monkeypatch)
    before = state(client, h)
    with Session.begin() as db:
        c = db.scalar(select(Character))
        c.hp = 1
        c.coins = 123
        c.xp = 17
    assert battle(client, h, "warden")["status"] == "lost"
    s = state(client, h)
    assert s["room"]["id"] == "city1" and s["inventory"] == before["inventory"]
    assert (
        s["character"]["coins"] == 123
        and s["character"]["xp"] == 17
        and s["atlas"]["secrets"]["found"] == 1
    )
    assert client.post("/dungeons/secret/enter", json={}, headers=h).status_code == 200


def test_secret_completion_and_repeat_reward(client, monkeypatch):
    h = player(client)
    secret(client, h, monkeypatch)
    with Session.begin() as db:
        db.scalar(select(Character)).strength = 100
    first = battle(client, h, "warden")
    assert first["reward_amount"] == settings.secret_first_reward
    s = state(client, h)
    assert s["room"]["completed"] and s["room"]["codex"]["warden"]["defeated"]
    assert client.post("/dungeons/leave", json={}, headers=h).status_code == 200
    assert client.post("/dungeons/secret/enter", json={}, headers=h).status_code == 200
    before = state(client, h)
    second = battle(client, h, "warden")
    after = state(client, h)
    assert (
        second["reward_amount"]
        == settings.secret_repeat_reward
        < first["reward_amount"] / 10
    )
    assert (
        after["inventory"] == before["inventory"]
        and after["character"]["xp"] == before["character"]["xp"]
    )
    assert client.post("/dungeons/leave", json={}, headers=h).status_code == 200
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    for b in (first, second):
        assert (
            client.post(f'/battles/{b["id"]}/claim', json={}, headers=h).status_code
            == 200
        )
    s = state(client, h)
    assert (
        s["character"]["coins"]
        == settings.secret_first_reward + settings.secret_repeat_reward
    )
    with Session() as db:
        assert (
            db.get(Treasury, 1).balance + s["character"]["coins"]
            == settings.initial_treasury
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "SECRET_DUNGEON_COMPLETED")
            )
            == 1
        )


def test_raid_membership_persists(client):
    h = player(client)
    assert client.post("/raids", json={}, headers=h).status_code == 409
    navigate(client, h, "boss")
    s = state(client, h)
    assert not s["battle"] and s["map"]["recommended_group"] == 4
    r = client.post("/raids", json={}, headers=h)
    assert r.status_code == 200
    raid = r.json()
    other = player(client, "bob")
    body = {"invite": raid["invite"]}
    assert client.post("/raids/join", json=body, headers=other).status_code == 200
    assert (
        len(state(client, h)["raid"]["participants"]) == 2
        and len(state(client, other)["raid"]["participants"]) == 2
    )
    assert client.post("/raids/join", json=body, headers=other).status_code == 409
    assert (
        client.post("/raids/leave", json={}, headers=h).status_code == 200
        and state(client, other)["raid"] is None
    )


def test_room_presence_scope_and_auth(client):
    from starlette.websockets import WebSocketDisconnect
    import pytest

    h = player(client)
    other = player(client, "bob")
    with client.websocket_connect("/ws/rooms") as invalid:
        invalid.send_json({"token": "invalid"})
        with pytest.raises(WebSocketDisconnect):
            invalid.receive_json()
    with client.websocket_connect("/ws/rooms") as a:
        a.send_json({"token": h["Authorization"].split()[1]})
        assert not a.receive_json()["players"]
        with client.websocket_connect("/ws/rooms") as b:
            b.send_json({"token": other["Authorization"].split()[1]})
            assert b.receive_json()["players"][0]["name"] == "alice"
            assert a.receive_json()["players"][0]["name"] == "bob"
            navigate(client, other, "city1")
            # Movement can queue several legitimate earlier positions while HTTP
            # navigation is running. Observe the eventual authoritative room change.
            for _ in range(100):
                update = a.receive_json()
                assert update["room_id"] == "common_a"
                if not update["players"]:
                    break
            else:
                raise AssertionError(
                    "Presence did not remove peer after room departure"
                )
