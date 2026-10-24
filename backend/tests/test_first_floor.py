"""First-floor invariants, real transactions and deterministic room geometry."""

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from app.main import app
from app.models import (
    Item,
    ItemDefinition,
    Character,
    EnemyInstance,
    Battle,
    WorldEvent,
    Treasury,
)
from app.database import Session
from app.inventory import add_item
from app.layouts import generate, reachable
from app.enemies import EnemyState
from test_game import clean, client, player, state, navigate, walk_tiles, win


def test_stack_fills_existing_then_overflows(client):
    h = player(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.scalar(select(Character).where(Character.id == cid).with_for_update())
        add_item(db, c, "crystal", 90, "test:90")
        add_item(db, c, "crystal", 20, "test:20")
        add_item(db, c, "crystal", 20, "test:20")  # same operation must not duplicate
    stacks = [
        i["quantity"] for i in state(client, h)["inventory"] if i["kind"] == "material"
    ]
    assert stacks == [99, 11]
    with Session() as db:
        assert (
            db.scalar(
                select(func.sum(Item.quantity)).where(
                    Item.owner == cid, Item.definition == "crystal"
                )
            )
            == 110
        )


def test_equipment_instances_stay_distinct(client):
    h = player(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.scalar(select(Character).where(Character.id == cid).with_for_update())
        add_item(db, c, "sword", 2, "test:swords")
    weapons = [i for i in state(client, h)["inventory"] if i["kind"] == "weapon"]
    assert len(weapons) == 3 and len({i["id"] for i in weapons}) == 3
    assert all(i["quantity"] == 1 and not i["stackable"] for i in weapons)


def test_configurable_stack_limit(client):
    h = player(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.get(ItemDefinition, "crystal").max_stack_size = 7
        add_item(db, db.get(Character, cid), "crystal", 16, "test:small")
    assert [
        i["quantity"] for i in state(client, h)["inventory"] if i["kind"] == "material"
    ] == [7, 7, 2]


def test_dead_enemy_rejects_combat_and_duplicate_rewards(client):
    h = player(client)
    b = win(client, h)
    before = state(client, h)
    e = next(e for e in before["map"]["enemies"] if e["id"] == b["enemy_id"])
    assert (
        e["state"] == "DEAD"
        and e["hp"] == 0
        and e["spawn_key"] not in before["map"]["monsters"]
    )
    for target in (str(e["id"]), e["spawn_key"]):
        assert (
            client.post("/battles", json={"monster": target}, headers=h).status_code
            == 409
        )
    after = state(client, h)
    assert (
        after["inventory"] == before["inventory"]
        and after["character"]["xp"] == before["character"]["xp"]
    )
    assert len(client.get("/rewards", headers=h).json()) == 1
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "ENEMY_DIED")
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "GUILD_REWARD_REGISTERED")
            )
            == 1
        )


def test_final_attack_concurrency_commits_death_once(client):
    h = player(client)
    walk_tiles(client, h, (5, 6))
    b = client.post("/battles", json={"monster": "slime"}, headers=h).json()
    with Session.begin() as db:
        db.get(EnemyInstance, b["enemy_id"]).hp = 1
        db.get(Battle, b["id"]).hp = 1

    def hit(_):
        with TestClient(app) as c:
            return c.post(
                f'/battles/{b["id"]}/action',
                json={"turn": 0, "action": "attack"},
                headers=h,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(hit, range(2))) == [200, 409]
    s = state(client, h)
    assert s["character"]["xp"] == 30
    assert sum(i["quantity"] for i in s["inventory"] if i["kind"] == "material") == 1
    assert len(client.get("/rewards", headers=h).json()) == 1


def test_guild_batch_claim_only_at_reception(client):
    h = player(client)
    win(client, h)
    s = state(client, h)
    second = next(e for e in s["map"]["enemies"] if e["state"] == "ALIVE")
    # Two independent, valid kills; prepare HP for the second encounter, not the outcome.
    with Session.begin() as db:
        db.get(Character, s["character"]["id"]).hp = 100
    walk_tiles(client, h, (second["x"], second["y"]))
    b = client.post("/battles", json={"monster": str(second["id"])}, headers=h).json()
    while b["status"] == "active":
        b = client.post(
            f'/battles/{b["id"]}/action',
            json={"turn": b["turn"], "action": "attack"},
            headers=h,
        ).json()
    assert b["status"] == "won"
    summary = client.get("/guild/rewards", headers=h).json()
    assert (
        summary["count"] == 2
        and summary["total"] == 20
        and state(client, h)["character"]["coins"] == 0
    )
    assert client.post("/guild/claim", json={}, headers=h).status_code == 409
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    assert client.post("/interact", json={}, headers=h).json()["rewards"]["count"] == 2
    assert client.post("/guild/claim", json={}, headers=h).json()["paid"] == 20
    assert client.post("/guild/claim", json={}, headers=h).status_code == 409
    with Session() as db:
        assert db.get(Treasury, 1).balance + 20 == 100000


def test_healer_removed_and_safe_rest(client):
    h = player(client)
    assert state(client, h)["map"]["npc"] is None
    assert client.post("/interact", json={}, headers=h).status_code == 409
    assert client.post("/rest", json={}, headers=h).status_code == 409
    navigate(client, h, "city1")
    assert state(client, h)["map"]["npc"] is None
    assert client.post("/rest", json={}, headers=h).status_code == 200


def test_room_seed_variation_and_accessible_spawns():
    fingerprints = set()
    themes = set()
    for seed in range(40):
        d = generate("PROCEDURAL", seed)
        assert d == generate("PROCEDURAL", seed)
        reach = reachable(d)
        assert (2, 9) in reach
        assert d["width"] >= 32 and len(d["monsters"]) >= 5
        for p in d["monsters"].values():
            assert tuple(p) in reach
        fingerprints.add(str((d["walls"], d["decorations"], d["width"], d["monsters"])))
        themes.add(d["theme"])
    assert len(fingerprints) > 30 and len(themes) == 4


def test_common_enemy_takes_several_turns(client):
    h = player(client)
    b = win(client, h)
    assert b["turn"] == 4
    assert state(client, h)["character"]["hp"] == 18


def test_wander_respects_home_and_lifecycle(client, monkeypatch):
    from datetime import timedelta
    from app.clock import utc_now
    from app.config import settings

    monkeypatch.setattr(settings, "wander_interval", 1)
    h = player(client)
    s = state(client, h)
    cid = s["character"]["id"]
    with Session.begin() as db:
        e = db.scalar(select(EnemyInstance).where(EnemyInstance.character_id == cid))
        e.state = "DEAD"
        e.hp = 0
    for _ in range(10):
        with Session.begin() as db:
            for e in db.scalars(
                select(EnemyInstance).where(EnemyInstance.character_id == cid)
            ):
                e.moved_at = utc_now() - timedelta(seconds=2)
        s = state(client, h)
        walls = {tuple(p) for p in s["map"]["walls"]}
        with Session() as db:
            for e in db.scalars(
                select(EnemyInstance).where(EnemyInstance.character_id == cid)
            ):
                assert (e.x, e.y) not in walls and abs(e.x - e.home_x) + abs(
                    e.y - e.home_y
                ) <= 2
                if e.state == "DEAD":
                    assert e.hp == 0 and e.x == e.home_x


def test_no_respawn_after_new_session(client):
    h = player(client)
    b = win(client, h)
    with TestClient(app) as other:
        s = state(other, h)
        e = next(e for e in s["map"]["enemies"] if e["id"] == b["enemy_id"])
        assert e["state"] == "DEAD"
        assert (
            other.post(
                "/battles", json={"monster": str(e["id"])}, headers=h
            ).status_code
            == 409
        )


def test_legacy_victory_is_backfilled_as_dead(client):
    h = player(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        # Simulate a retained v2 victory before any durable enemy existed.
        db.query(EnemyInstance).filter(EnemyInstance.character_id == cid).delete()
        db.add(
            Battle(
                character_id=cid,
                monster="slime",
                hp=0,
                turn=2,
                status="won",
                claimed=False,
                room_id="common_a",
            )
        )
    with Session.begin() as db:
        db.add(
            Battle(
                character_id=cid,
                monster="slime",
                hp=3,
                turn=5,
                status="lost",
                claimed=False,
                room_id="common_a",
            )
        )
    s = state(client, h)
    e = next(e for e in s["map"]["enemies"] if e["spawn_key"] == "slime")
    assert e["state"] == "DEAD"
    assert (
        client.post("/battles", json={"monster": str(e["id"])}, headers=h).status_code
        == 409
    )
    assert len(client.get("/rewards", headers=h).json()) == 1


def test_guild_batch_rolls_back_when_budget_insufficient(client):
    h = player(client)
    win(client, h)
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    with Session.begin() as db:
        db.get(Treasury, 1).balance = 0
    assert client.post("/guild/claim", json={}, headers=h).status_code == 409
    assert client.get("/guild/rewards", headers=h).json()["count"] == 1
    assert state(client, h)["character"]["coins"] == 0


def test_legacy_active_battle_is_resumed_without_reset(client):
    h = player(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.query(EnemyInstance).filter(EnemyInstance.character_id == cid).delete()
        db.add(
            Battle(
                character_id=cid,
                monster="slime",
                hp=6,
                turn=2,
                status="active",
                claimed=False,
                room_id="common_a",
            )
        )
    s = state(client, h)
    b = s["battle"]
    assert b["hp"] == 6 and b["turn"] == 2 and b["enemy_id"]
    response = client.post(
        f'/battles/{b["id"]}/action', json={"turn": 2, "action": "attack"}, headers=h
    )
    assert (
        response.status_code == 200
        and response.json()["turn"] == 3
        and response.json()["hp"] == 3
    )
