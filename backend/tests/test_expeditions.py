from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from test_game import clean, client, player, state, navigate, walk_tiles
from app.main import app
from app.database import Session
from app.models import (
    Character,
    Battle,
    Expedition,
    WorldEvent,
    Room,
    EnemyInstance,
    Treasury,
)
from app.config import settings


def begin(c, h, mp):
    mp.setattr(settings, "secret_chance", 0)
    r = c.post("/adventure", json={"request_id": str(uuid4())}, headers=h)
    assert r.status_code == 200, r.text
    s = state(c, h)
    assert (
        s["expedition"]["status"] == "ACTIVE" and s["expedition"]["alive_enemies"] > 0
    )
    return s


def preview(c, h, eid):
    r = c.get(f"/expeditions/{eid}/flee-preview", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def flee(c, h, eid, token=None):
    token = token or preview(c, h, eid)["confirmation_token"]
    return c.post(
        f"/expeditions/{eid}/flee",
        json={"confirmed": True, "confirmation_token": token},
        headers=h,
    )


def pending_records(h, c, amounts):
    s = state(c, h)
    with Session.begin() as db:
        for amount in amounts:
            db.add(
                Battle(
                    character_id=s["character"]["id"],
                    monster="slime",
                    hp=0,
                    turn=4,
                    status="won",
                    claimed=False,
                    reward_amount=amount,
                    room_id="common_a",
                )
            )


def kill(c, h, eid):
    e = next(e for e in state(c, h)["map"]["enemies"] if e["id"] == eid)
    walk_tiles(c, h, (e["x"], e["y"]))
    b = c.post("/battles", json={"monster": str(eid)}, headers=h).json()
    while b["status"] == "active":
        r = c.post(
            f'/battles/{b["id"]}/action',
            json={"turn": b["turn"], "action": "attack"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        b = r.json()
    assert b["status"] == "won"


def test_active_blocks_new_adventure_exit_and_other_travel(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    eid = s["expedition"]["id"]
    assert (
        client.post(
            "/adventure", json={"request_id": str(uuid4())}, headers=h
        ).status_code
        == 409
    )
    walk_tiles(client, h, (s["room"]["exits"][0]["x"], s["room"]["exits"][0]["y"]))
    assert (
        client.post(
            "/rooms/exits/" + str(s["room"]["exits"][0]["id"]), json={}, headers=h
        ).status_code
        == 409
    )
    assert client.post("/travel", json={"floor": 1}, headers=h).status_code == 409
    assert client.post("/dungeons/secret/enter", json={}, headers=h).status_code == 409
    assert state(client, h)["expedition"]["id"] == eid
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Expedition)) == 1


def test_partial_clear_still_blocks_and_full_clear_completes(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    cid = s["character"]["id"]
    eid = s["expedition"]["id"]
    with Session.begin() as db:
        db.get(Character, cid).strength = 100
    kill(client, h, s["map"]["enemies"][0]["id"])
    assert (
        client.post(
            "/adventure", json={"request_id": str(uuid4())}, headers=h
        ).status_code
        == 409
    )
    for e in state(client, h)["map"]["enemies"]:
        if e["state"] == "ALIVE":
            kill(client, h, e["id"])
    done = state(client, h)
    assert (
        done["expedition"]["status"] == "COMPLETED"
        and done["expedition"]["alive_enemies"] == 0
        and done["room"]["completed"]
    )
    inventory = done["inventory"]
    xp = done["character"]["xp"]
    assert (
        client.post(
            "/adventure", json={"request_id": str(uuid4())}, headers=h
        ).status_code
        == 200
    )
    assert state(client, h)["expedition"]["id"] != eid
    assert (
        state(client, h)["inventory"] == inventory
        and state(client, h)["character"]["xp"] == xp
    )
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "EXPEDITION_COMPLETED")
            )
            == 1
        )


def test_completed_room_allows_normal_return(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    with Session.begin() as db:
        db.get(Character, s["character"]["id"]).strength = 100
    for e in s["map"]["enemies"]:
        kill(client, h, e["id"])
    navigate(client, h, "city1")
    assert state(client, h)["room"]["id"] == "city1"


def test_flee_global_pending_300_and_guild_rescues_only_150(client, monkeypatch):
    h = player(client)
    pending_records(h, client, [100, 100])
    s = begin(client, h, monkeypatch)
    monkeypatch.setattr(settings, "monster_reward", 100)
    with Session.begin() as db:
        db.get(Character, s["character"]["id"]).strength = 100
    kill(client, h, s["map"]["enemies"][0]["id"])
    s = state(client, h)
    inventory = s["inventory"]
    p = preview(client, h, s["expedition"]["id"])
    assert (
        p["pending_before"] == 300
        and p["reward_loss"] == 150
        and p["pending_after"] == 150
    )
    r = flee(client, h, s["expedition"]["id"], p["confirmation_token"])
    assert r.status_code == 200
    s2 = state(client, h)
    assert (
        s2["room"]["id"] == "city1"
        and s2["character"]["xp"] == 0
        and s2["inventory"] == inventory
    )
    assert s2["character"]["level"] == s["character"]["level"]
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    assert client.post("/guild/claim", json={}, headers=h).json()["paid"] == 150
    assert client.post("/guild/claim", json={}, headers=h).status_code == 409
    assert state(client, h)["character"]["coins"] == 150
    with Session() as db:
        assert db.get(Treasury, 1).balance == settings.initial_treasury - 150


@pytest.mark.parametrize(
    "amount,remaining,lost",
    [(0, 0, 0), (1, 0, 1), (3, 1, 2), (101, 50, 51), (300, 150, 150), (301, 150, 151)],
)
def test_rounding_applies_to_total_not_each_record(
    client, monkeypatch, amount, remaining, lost
):
    h = player(client)
    if amount:
        pending_records(
            h, client, [1] * (min(amount, 3) - 1) + [amount - (min(amount, 3) - 1)]
        )
    s = begin(client, h, monkeypatch)
    r = flee(client, h, s["expedition"]["id"])
    assert r.status_code == 200
    assert r.json()["pending_after"] == remaining and r.json()["reward_loss"] == lost
    assert client.get("/guild/rewards", headers=h).json()["total"] == remaining


@pytest.mark.parametrize("level,xp", [(9, 950), (10, 0), (15, 3200)])
def test_flee_resets_xp_without_level_coin_or_item_loss(client, monkeypatch, level, xp):
    h = player(client)
    s = begin(client, h, monkeypatch)
    with Session.begin() as db:
        c = db.get(Character, s["character"]["id"])
        c.level = level
        c.xp = xp
        c.coins = 123
    before = state(client, h)
    assert flee(client, h, s["expedition"]["id"]).status_code == 200
    after = state(client, h)
    assert (
        after["character"]["level"] == level
        and after["character"]["xp"] == 0
        and after["character"]["coins"] == 123
    )
    assert before["inventory"] == after["inventory"]


def test_level_gained_during_expedition_is_preserved(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    with Session.begin() as db:
        c = db.get(Character, s["character"]["id"])
        c.level = 9
        c.xp = 440
        c.strength = 100
    kill(
        client, h, s["map"]["enemies"][0]["id"]
    )  # Existing curve: level 9 needs 450, gain 30.
    assert (
        state(client, h)["character"]["level"] == 10
        and state(client, h)["character"]["xp"] == 20
    )
    assert flee(client, h, s["expedition"]["id"]).status_code == 200
    assert (
        state(client, h)["character"]["level"] == 10
        and state(client, h)["character"]["xp"] == 0
    )


def test_reconnect_and_login_keep_commitment(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "safe-pass-123"}
    ).json()
    auth = {"Authorization": "Bearer " + login["token"]}
    with TestClient(app) as other:
        assert state(other, auth)["expedition"]["id"] == s["expedition"]["id"]
        assert (
            other.post(
                "/adventure", json={"request_id": str(uuid4())}, headers=auth
            ).status_code
            == 409
        )


def test_flee_race_is_idempotent_and_does_not_penalize_next_expedition(
    client, monkeypatch
):
    h = player(client)
    pending_records(h, client, [300])
    s = begin(client, h, monkeypatch)
    eid = s["expedition"]["id"]
    token = preview(client, h, eid)["confirmation_token"]

    def run(_):
        with TestClient(app) as c:
            return flee(c, h, eid, token).json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    assert client.get("/guild/rewards", headers=h).json()["total"] == 150
    new = begin(client, h, monkeypatch)
    assert flee(client, h, eid, token).json()["replayed"]
    assert (
        state(client, h)["expedition"]["id"] == new["expedition"]["id"]
        and state(client, h)["room"]["id"] == new["room"]["id"]
    )
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "EXPEDITION_FLED")
            )
            == 1
        )


def test_flee_requires_confirmation_and_rejects_stale_values(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    eid = s["expedition"]["id"]
    p = preview(client, h, eid)
    assert (
        client.post(
            f"/expeditions/{eid}/flee",
            json={"confirmed": False, "confirmation_token": p["confirmation_token"]},
            headers=h,
        ).status_code
        == 422
    )
    pending_records(h, client, [100])
    assert flee(client, h, eid, p["confirmation_token"]).status_code == 409
    assert state(client, h)["expedition"]["status"] == "ACTIVE"
    assert flee(client, h, eid).status_code == 200


def test_flee_failure_rolls_back_every_effect(client, monkeypatch):
    import app.expeditions as exp

    h = player(client)
    pending_records(h, client, [300])
    s = begin(client, h, monkeypatch)
    with Session.begin() as db:
        db.get(Character, s["character"]["id"]).xp = 37
    token = preview(client, h, s["expedition"]["id"])["confirmation_token"]
    original = exp.event

    def fail(*a, **kw):
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(exp, "event", fail)
    with pytest.raises(RuntimeError):
        flee(client, h, s["expedition"]["id"], token)
    monkeypatch.setattr(exp, "event", original)
    after = state(client, h)
    assert (
        after["expedition"]["status"] == "ACTIVE"
        and after["character"]["xp"] == 37
        and after["room"]["id"] == s["room"]["id"]
    )
    assert client.get("/guild/rewards", headers=h).json()["total"] == 300


def test_flee_closes_active_battle_and_death_ends_failed_expedition(
    client, monkeypatch
):
    h = player(client)
    s = begin(client, h, monkeypatch)
    e = s["map"]["enemies"][0]
    walk_tiles(client, h, (e["x"], e["y"]))
    b = client.post("/battles", json={"monster": str(e["id"])}, headers=h).json()
    with Session.begin() as db:
        db.get(Character, s["character"]["id"]).hp = 1
    assert (
        client.post(
            f'/battles/{b["id"]}/action',
            json={"turn": 0, "action": "defend"},
            headers=h,
        ).json()["status"]
        == "lost"
    )
    assert state(client, h)["room"]["id"] == "city1"
    with Session() as db:
        assert db.get(Expedition, s["expedition"]["id"]).status == "FAILED"
    s = begin(client, h, monkeypatch)
    e = s["map"]["enemies"][0]
    walk_tiles(client, h, (e["x"], e["y"]))
    b = client.post("/battles", json={"monster": str(e["id"])}, headers=h).json()
    assert flee(client, h, s["expedition"]["id"]).status_code == 200
    with Session() as db:
        assert db.get(Battle, b["id"]).status == "fled"
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(
                    WorldEvent.kind == "COMBAT_FINISHED",
                    WorldEvent.payload["result"].as_string() == "fled",
                )
            )
            == 1
        )
    assert state(client, h)["battle"] is None


def test_ownership_and_claim_race_cannot_recover_old_value(client, monkeypatch):
    h = player(client)
    pending_records(h, client, [301])
    s = begin(client, h, monkeypatch)
    eid = s["expedition"]["id"]
    token = preview(client, h, eid)["confirmation_token"]
    other = player(client, "bob")
    assert (
        client.get(f"/expeditions/{eid}/flee-preview", headers=other).status_code == 404
    )

    def claim():
        with TestClient(app) as c:
            return c.post("/guild/claim", json={}, headers=h).status_code

    def escape():
        with TestClient(app) as c:
            return flee(c, h, eid, token).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(claim)
        b = pool.submit(escape)
        assert a.result() == 409 and b.result() == 200
    assert client.get("/guild/rewards", headers=h).json()["total"] == 150
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    reward = client.get("/rewards", headers=h).json()[0]
    assert (
        client.post(
            "/battles/" + str(reward["id"]) + "/claim", json={}, headers=h
        ).json()["paid"]
        == 150
    )


def test_common_paths_are_free_and_danger_does_not_scale_with_player(client):
    h = player(client)
    profiles = []
    for room in ("common_a", "common_b", "combat"):
        navigate(client, h, room)
        s = state(client, h)
        assert s["expedition"] is None and any(
            e["state"] == "ALIVE" for e in s["map"]["enemies"]
        )
        e = next(e for e in s["map"]["enemies"] if e["species"] == "slime")
        profiles.append((s["room"]["danger_tier"], e["max_hp"]))
    assert profiles == [(1, 24), (2, 30), (3, 36)]
    cid = s["character"]["id"]
    with Session.begin() as db:
        db.get(Character, cid).level = 50
    navigate(client, h, "common_a")
    s = state(client, h)
    assert (
        next(e["max_hp"] for e in s["map"]["enemies"] if e["species"] == "slime") == 24
    )
    with Session() as db:
        rows = db.scalars(
            select(EnemyInstance).where(
                EnemyInstance.character_id == cid, EnemyInstance.spawn_key == "slime"
            )
        ).all()
        assert sorted(e.attack for e in rows) == [6, 7, 8]
        assert sorted(e.defense for e in rows) == [2, 3, 3]


def test_simultaneous_new_adventures_create_one_active_room(client, monkeypatch):
    h = player(client)
    monkeypatch.setattr(settings, "secret_chance", 0)

    def run(_):
        with TestClient(app) as c:
            return c.post(
                "/adventure", json={"request_id": str(uuid4())}, headers=h
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [200, 409]
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Expedition)
                .where(Expedition.status == "ACTIVE")
            )
            == 1
        )


def test_cleared_expedition_cannot_be_fled_or_penalized(client, monkeypatch):
    h = player(client)
    s = begin(client, h, monkeypatch)
    with Session.begin() as db:
        db.get(Character, s["character"]["id"]).strength = 100
    for enemy in s["map"]["enemies"]:
        kill(client, h, enemy["id"])
    done = state(client, h)
    result = client.post(
        "/expeditions/" + str(s["expedition"]["id"]) + "/flee",
        json={"confirmed": True, "confirmation_token": "0" * 64},
        headers=h,
    )
    assert result.status_code == 409
    assert state(client, h)["character"]["xp"] == done["character"]["xp"]
