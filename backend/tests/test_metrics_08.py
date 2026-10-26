from test_game import clean, client, player, state, walk_tiles
from test_expeditions import kill
from test_encounters_08 import setup_group, start, act
from sqlalchemy import select
from app.database import Session
from app import models as m


def test_single_metrics_aggregate_effective_damage_and_do_not_duplicate(client):
    h = player(client)
    s = state(client, h)
    target = s["map"]["enemies"][0]
    kill(client, h, target["id"])
    report = client.get("/metrics", headers=h).json()
    totals = report["totals"]
    assert report["sample_size"] == 1 and totals["combats_won"] == 1
    assert totals["damage_dealt"] == target["max_hp"]
    assert totals["combat_turns"] > 0 and report["average_combat_seconds"] >= 0
    assert totals["monsters_defeated"] == 1 and totals["xp_earned"] == 30
    assert client.get("/metrics", headers=h).json()["totals"] == totals
    other = player(client, "other")
    assert client.get("/metrics", headers=other).json()["sample_size"] == 0


def test_group_metrics_one_summary_for_two_individual_rewards(client, monkeypatch):
    h, ids, s = setup_group(client, monkeypatch)
    g = start(client, h, ids).json()
    with Session.begin() as db:
        db.get(m.Character, s["character"]["id"]).strength = 999
    g = act(client, h, g, ids[0]).json()["encounter"]
    result = act(client, h, g, ids[1])
    assert result.status_code == 200
    data = client.get("/metrics", headers=h).json()
    assert data["sample_size"] == 1 and data["totals"]["groups_finished"] == 1
    assert data["totals"]["monsters_defeated"] == 2
    assert data["totals"]["damage_dealt"] == 100
    assert data["totals"]["combat_turns"] == 2
    assert data["totals"]["combats_won"] == 1


def test_historical_duration_is_unknown_not_backfilled(client):
    h = player(client)
    s = state(client, h)
    enemy = s["map"]["enemies"][0]
    walk_tiles(client, h, (enemy["x"], enemy["y"]))
    b = client.post("/battles", headers=h, json={"monster": str(enemy["id"])}).json()
    with Session.begin() as db:
        db.get(m.Battle, b["id"]).started_at = None
        db.get(m.Character, s["character"]["id"]).strength = 999
    assert (
        client.post(
            f"/battles/{b['id']}/action",
            headers=h,
            json={"turn": 0, "action": "attack"},
        ).status_code
        == 200
    )
    assert client.get("/metrics", headers=h).json()["average_combat_seconds"] is None
