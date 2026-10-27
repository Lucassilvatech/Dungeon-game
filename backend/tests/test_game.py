import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select, func
from app.main import app
from app.database import Session
from app.models import Character, Treasury, Ledger, WorldEvent, RoomConnection
from app.seed import seed
from app.config import settings
from app.world import WALLS, NPC, MONSTERS, distance


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setattr(settings, "wander_interval", 100000)
    monkeypatch.setattr(settings, "rate_limits_enabled", False)
    assert (
        os.environ.get("TOWER_TEST_DATABASE") == "1"
    ), "Use disposable PostgreSQL only"
    with Session.begin() as db:
        db.execute(
            text(
                "TRUNCATE lunar_cutovers, lunar_debts, rate_limit_buckets, admin_login_attempts, central_bank, monster_definitions, game_settings, accounts, sessions, link_codes, characters, items, item_definitions, battles, treasury, ledger, world_events RESTART IDENTITY CASCADE"
            )
        )
    seed()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def player(c, name="alice"):
    r = c.post("/auth/register", json={"username": name, "password": "safe-pass-123"})
    assert r.status_code == 201, r.text
    h = {"Authorization": "Bearer " + r.json()["token"]}
    r = c.post("/character", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    navigate(c, h, "common_a")
    return h


def state(c, h):
    return c.get("/state", headers=h).json()


def walk_tiles(c, h, target):
    data = state(c, h)
    m = data["map"]
    s = data["character"]
    start = (s["x"], s["y"])
    queue = [(start, [])]
    seen = {start}
    blocked = {tuple(p) for p in m["walls"]} | {
        tuple(p) for p in m["monsters"].values()
    }
    if m.get("npc"):
        blocked.add(tuple(m["npc"]))
    while queue:
        p, path = queue.pop(0)
        if distance(p, target) <= 1:
            for dx, dy in path:
                r = c.post("/move", json={"dx": dx, "dy": dy}, headers=h)
                assert r.status_code == 200, r.text
            return
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            q = p[0] + dx, p[1] + dy
            if (
                q in seen
                or q in blocked
                or not (0 < q[0] < m["width"] - 1 and 0 < q[1] < m["height"] - 1)
            ):
                continue
            seen.add(q)
            queue.append((q, path + [(dx, dy)]))
    raise AssertionError("No path")


def navigate(c, h, target):
    current = state(c, h)["character"]["room_id"]
    queue = [(current, [])]
    seen = {current}
    with Session() as db:
        while queue:
            src, path = queue.pop(0)
            if src == target:
                for edge_id, x, y in path:
                    walk_tiles(c, h, (x, y))
                    r = c.post(f"/rooms/exits/{edge_id}", json={}, headers=h)
                    assert r.status_code == 200, r.text
                return
            for e in db.scalars(
                select(RoomConnection).where(RoomConnection.source == src)
            ):
                if e.target not in seen:
                    seen.add(e.target)
                    queue.append((e.target, path + [(e.id, e.x, e.y)]))
    raise AssertionError("No room path")


def walk(c, h, target):
    if target == MONSTERS["boss"]:
        navigate(c, h, "boss")
    elif target == NPC:
        navigate(c, h, "guild")
        target = tuple(state(c, h)["map"]["npc"])
    elif target == (13, 2):
        navigate(c, h, "city1")
        target = tuple(state(c, h)["map"]["portal"])
    walk_tiles(c, h, target)


def win(c, h, monster="slime"):
    if monster == "boss":
        with Session.begin() as db:
            char = db.scalar(
                select(Character).where(Character.id == state(c, h)["character"]["id"])
            )
            char.level = 7
            char.hp = 60
            char.strength = 11
            char.defense = 2
    item = state(c, h)["inventory"][0]["id"]
    assert c.post(f"/inventory/{item}/equip", json={}, headers=h).status_code == 200
    walk(c, h, MONSTERS[monster])
    b = c.post("/battles", json={"monster": monster}, headers=h).json()
    while b["status"] == "active":
        turn = b["turn"]
        r = c.post(
            f'/battles/{b["id"]}/action',
            json={
                "turn": turn,
                "action": (
                    "skill"
                    if monster == "boss" and state(c, h)["character"]["energy"] >= 2
                    else "attack"
                ),
            },
            headers=h,
        )
        assert r.status_code == 200, r.text
        b = r.json()
        assert (
            c.post(
                f'/battles/{b["id"]}/action',
                json={"turn": turn, "action": "attack"},
                headers=h,
            ).status_code
            == 409
        )
    assert b["status"] == "won"
    return b


def test_persistence_and_unique_character(client):
    h = player(client)
    assert (
        client.post("/character", json={"name": "another"}, headers=h).status_code
        == 409
    )
    r = client.post(
        "/auth/login", json={"username": "alice", "password": "safe-pass-123"}
    )
    assert r.status_code == 200
    assert (
        state(client, {"Authorization": "Bearer " + r.json()["token"]})["character"][
            "name"
        ]
        == "alice"
    )
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Character)) == 1


def test_movement_and_collision(client):
    h = player(client)
    assert client.post("/move", json={"dx": 1, "dy": 0}, headers=h).status_code == 200
    before = state(client, h)["character"]
    for body, code in [
        ({"dx": 0, "dy": 1}, 409),
        ({"dx": 1, "dy": 1}, 422),
        ({"dx": 50, "dy": 0}, 422),
    ]:
        assert client.post("/move", json=body, headers=h).status_code == code
    assert state(client, h)["character"] == before
    assert client.get("/state").status_code == 403


def test_combat_inventory_and_conserved_rewards(client):
    h = player(client)
    b = win(client, h)
    assert any(
        i["name"] == "Cristal da clareira" for i in state(client, h)["inventory"]
    )
    assert (
        client.post(f'/battles/{b["id"]}/claim', json={}, headers=h).status_code == 409
    )
    walk(client, h, NPC)
    assert client.post("/interact", json={}, headers=h).status_code == 200
    assert (
        client.post(f'/battles/{b["id"]}/claim', json={}, headers=h).json()["paid"]
        == settings.monster_reward
    )
    assert (
        client.post(f'/battles/{b["id"]}/claim', json={}, headers=h).status_code == 409
    )
    with Session() as db:
        assert (
            db.get(Treasury, 1).balance + db.scalar(select(Character.coins))
            == settings.initial_treasury
        )
        assert db.scalar(select(func.count()).select_from(Ledger)) >= 2


def test_ownership(client):
    h = player(client)
    other = player(client, "bob")
    b = win(client, h)
    item = state(client, h)["inventory"][0]["id"]
    assert (
        client.post(f"/inventory/{item}/equip", json={}, headers=other).status_code
        == 404
    )
    assert (
        client.post(
            f'/battles/{b["id"]}/action',
            json={"turn": 0, "action": "attack"},
            headers=other,
        ).status_code
        == 404
    )


def test_concurrent_claim(client):
    h = player(client)
    b = win(client, h)
    walk(client, h, NPC)

    def claim(_):
        with TestClient(app) as c:
            return c.post(f'/battles/{b["id"]}/claim', json={}, headers=h).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, range(2))) == [200, 409]
    assert state(client, h)["character"]["coins"] == settings.monster_reward


def test_insufficient_funds_rollback(client):
    h = player(client)
    b = win(client, h)
    walk(client, h, NPC)
    with Session.begin() as db:
        db.get(Treasury, 1).balance = 0
    assert (
        client.post(f'/battles/{b["id"]}/claim', json={}, headers=h).status_code == 409
    )
    assert state(client, h)["character"]["coins"] == 0
    assert len(client.get("/rewards", headers=h).json()) == 1


def test_boss_defeat_persists(client):
    h = player(client)
    win(client, h, "boss")
    assert state(client, h)["character"]["level"] == 7
    assert state(client, h)["room"]["completed"]
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "FLOOR_BOSS_DEFEATED")
            )
            == 1
        )


def test_discord_link_real_data_and_replay(client, monkeypatch):
    monkeypatch.setattr(settings, "discord_service_key", "test-key")
    h = player(client)
    code = client.post("/discord/code", json={}, headers=h).json()["code"]
    bot = {"X-Bot-Key": "test-key"}
    body = {"code": code, "discord_id": "123"}
    assert client.post("/discord/link", json=body, headers=bot).status_code == 200
    assert (
        client.get("/discord/123/state", headers=bot).json()["character"]
        == state(client, h)["character"]
    )
    assert client.post("/discord/link", json=body, headers=bot).status_code == 400
    assert client.get("/discord/123/state").status_code == 403


def test_concurrent_turn(client):
    h = player(client)
    walk(client, h, MONSTERS["slime"])
    b = client.post("/battles", json={"monster": "slime"}, headers=h).json()
    assert client.post("/move", json={"dx": 1, "dy": 0}, headers=h).status_code == 409

    def attack(_):
        with TestClient(app) as c:
            return c.post(
                f'/battles/{b["id"]}/action',
                json={"turn": 0, "action": "attack"},
                headers=h,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attack, range(2))) == [200, 409]
    assert state(client, h)["battle"]["turn"] == 1


def test_locked_floor_and_remote_actions(client):
    h = player(client)
    assert (
        client.post("/battles", json={"monster": "boss"}, headers=h).status_code == 404
    )
    assert client.post("/interact", json={}, headers=h).status_code == 409
    assert client.post("/travel", json={"floor": 2}, headers=h).status_code == 409


def test_skill_energy_defense_and_defeat(client):
    h = player(client)
    walk(client, h, MONSTERS["boss"])
    b = client.post("/battles", json={"monster": "boss"}, headers=h).json()
    with Session.begin() as db:
        db.scalar(select(Character)).energy = 0
    url = f'/battles/{b["id"]}/action'
    assert (
        client.post(url, json={"turn": 0, "action": "skill"}, headers=h).status_code
        == 409
    )
    assert state(client, h)["battle"]["turn"] == 0
    r = client.post(url, json={"turn": 0, "action": "defend"}, headers=h)
    assert r.status_code == 200 and r.json()["hp"] == 84
    assert state(client, h)["character"]["hp"] == 21
    with Session.begin() as db:
        db.scalar(select(Character)).hp = 1
    assert (
        client.post(url, json={"turn": 1, "action": "defend"}, headers=h).json()[
            "status"
        ]
        == "lost"
    )
    s = state(client, h)
    assert (
        s["battle"] is None and s["character"]["x"] == 2 and s["character"]["hp"] == 30
    )
    assert client.get("/rewards", headers=h).json() == []
