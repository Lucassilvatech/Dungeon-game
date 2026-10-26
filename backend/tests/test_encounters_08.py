from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from test_game import clean, client, player, state
from test_expeditions import begin, flee
from app.main import app
from app.database import Session
from app import models as m


def setup_group(client, monkeypatch, procedural=False):
    h = player(client)
    s = begin(client, h, monkeypatch) if procedural else state(client, h)
    cid = s["character"]["id"]
    with Session.begin() as db:
        enemies = db.scalars(
            select(m.EnemyInstance)
            .where(
                m.EnemyInstance.character_id == cid,
                m.EnemyInstance.room_id == s["room"]["id"],
            )
            .order_by(m.EnemyInstance.id)
        ).all()
        c = db.get(m.Character, cid)
        c.x = 4
        c.y = 5
        c.hp = 100
        for index, e in enumerate(enemies[:2]):
            e.x = 5 + index
            e.y = 5
            e.attack = 1
            e.hp = e.max_hp = 50
            e.category = "common"
        ids = [e.id for e in enemies[:2]]
    return h, ids, s


def start(client, h, ids, rid=None):
    return client.post(
        "/encounters",
        headers=h,
        json={"enemy_ids": ids, "request_id": rid or str(uuid4())},
    )


def act(client, h, g, target, action="attack", turn=None):
    return client.post(
        f"/encounters/{g['id']}/action",
        headers=h,
        json={
            "turn": g["turn"] if turn is None else turn,
            "target_id": target,
            "action": action,
        },
    )


def test_group_order_independent_states_rewards_once_and_reconnect(client, monkeypatch):
    h, ids, s = setup_group(client, monkeypatch)
    rid = str(uuid4())
    response = start(client, h, ids, rid)
    assert response.status_code == 200, response.text
    g = response.json()
    assert len(g["enemies"]) == 2
    assert start(client, h, ids, rid).json()["replayed"]
    first = act(client, h, g, ids[0], "defend")
    assert first.status_code == 200, first.text
    g = first.json()["encounter"]
    assert [r["actor"] for r in g["last_round"]] == ["player", "enemy", "enemy"]
    assert g["turn"] == 1 and g["damage_received"] == 4
    assert state(client, h)["encounter"]["turn"] == 1
    with Session.begin() as db:
        db.get(m.Character, s["character"]["id"]).strength = 999
    a = act(client, h, g, ids[1])
    assert a.status_code == 200, a.text
    g = a.json()["encounter"]
    assert next(e for e in g["enemies"] if e["id"] == ids[1])["state"] == "DEAD"
    assert act(client, h, g, ids[1]).status_code == 409
    assert act(client, h, g, ids[0], turn=0).status_code == 409
    end = act(client, h, g, ids[0])
    assert end.status_code == 200 and end.json()["status"] == "won"
    after = state(client, h)
    assert after["battle"] is None and after["encounter"] is None
    assert after["guild_rewards"]["count"] == 2
    assert after["character"]["xp"] >= 0
    assert act(client, h, g, ids[0]).status_code == 409
    assert state(client, h)["guild_rewards"]["count"] == 2
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Battle)
                .where(m.Battle.encounter_id == g["id"], m.Battle.status == "won")
            )
            == 2
        )


def test_target_selection_legacy_route_uses_global_turn_and_authorization(
    client, monkeypatch
):
    h, ids, s = setup_group(client, monkeypatch)
    g = start(client, h, ids).json()
    select_response = client.post(
        f"/encounters/{g['id']}/target",
        headers=h,
        json={"turn": 0, "target_id": ids[1]},
    )
    assert select_response.status_code == 200
    legacy = state(client, h)["battle"]
    assert legacy["enemy_id"] == ids[1] and legacy["turn"] == 0
    result = client.post(
        f"/battles/{legacy['id']}/action",
        headers=h,
        json={"turn": 0, "action": "defend"},
    )
    assert result.status_code == 200 and result.json()["encounter"]["turn"] == 1
    assert state(client, h)["battle"]["turn"] == 1
    other = player(client, "other")
    assert client.get(f"/encounters/{g['id']}", headers=other).status_code == 404
    assert act(client, other, g, ids[0]).status_code == 404


def test_group_turn_race_rolls_back_and_rejects_duplicate(client, monkeypatch):
    h, ids, s = setup_group(client, monkeypatch)
    g = start(client, h, ids).json()

    def run(_):
        with TestClient(app) as c:
            return act(c, h, g, ids[0], "defend").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [200, 409]
    assert state(client, h)["encounter"]["turn"] == 1
    assert state(client, h)["character"]["hp"] == 96


def test_group_cannot_bypass_procedural_flee_and_death_resolves_once(
    client, monkeypatch
):
    h, ids, s = setup_group(client, monkeypatch, True)
    g = start(client, h, ids).json()
    assert (
        client.post("/battles", headers=h, json={"monster": str(ids[0])}).status_code
        == 409
    )
    exit = s["room"]["exits"][0]
    assert (
        client.post(f"/rooms/exits/{exit['id']}", headers=h, json={}).status_code == 409
    )
    assert flee(client, h, s["expedition"]["id"]).status_code == 200
    assert state(client, h)["encounter"] is None
    with Session() as db:
        assert db.get(m.CombatEncounter, g["id"]).status == "FLED"


def test_group_death_resolves_once(client, monkeypatch):
    h, ids, s = setup_group(client, monkeypatch, True)
    g = start(client, h, ids).json()
    with Session.begin() as db:
        db.get(m.Character, s["character"]["id"]).hp = 1
    result = act(client, h, g, ids[0], "defend")
    assert result.status_code == 200, result.text
    after = state(client, h)
    assert result.json()["status"] == "lost" and after["death"] is not None
    assert after["character"]["coins"] == -100 and after["room"]["id"] == "city1"
    assert after["battle"] is None and after["encounter"] is None
    assert act(client, h, g, ids[0], "defend").status_code == 409
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.DeathEvent)) == 1


def test_group_validation_and_injected_failure_are_atomic(client, monkeypatch):
    h, ids, s = setup_group(client, monkeypatch)
    assert start(client, h, [ids[0], ids[0]]).status_code == 422
    assert start(client, h, ids + [99999]).status_code == 422
    g = start(client, h, ids).json()
    import app.encounters as service

    def broken(*args, **kwargs):
        raise RuntimeError("injected group counter failure")

    monkeypatch.setattr(service, "damage", broken)
    with pytest.raises(RuntimeError):
        act(client, h, g, ids[0])
    after = state(client, h)
    assert after["encounter"]["turn"] == 0 and after["character"]["hp"] == 100
    assert all(e["hp"] == 50 for e in after["encounter"]["enemies"])
