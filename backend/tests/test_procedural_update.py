from uuid import uuid4
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from test_game import clean, client, state, navigate, walk_tiles
from test_death_economy import fresh, setup_lethal, lethal, wallet, bid
from test_expeditions import begin, flee, kill
from test_admin_migration import admin, proposal, commit
from app import models as m
from app.database import Session
from app.config import settings
from app.main import app
from app.procedural import generate, SPECIES, chance, proximity
from app.clock import utc_now


def test_equipment_effective_status_switch_unequip_reconnect_and_damage(client):
    h = fresh(client)
    s = state(client, h)
    cid = s["character"]["id"]
    sword = next(i for i in s["inventory"] if i["definition"] == "sword")
    assert s["attributes"]["strength"] == dict(
        base=5, equipment=0, temporary=0, effective=5
    )
    for _ in range(2):
        assert (
            client.post(
                f"/inventory/{sword['id']}/equip", headers=h, json={}
            ).status_code
            == 200
        )
        assert state(client, h)["attributes"]["strength"]["effective"] == 8
    other = next(i for i in s["inventory"] if i["definition"] == "iron_sword")
    with Session.begin() as db:
        db.get(m.ItemDefinition, "iron_sword").power = 7
    client.post(f"/inventory/{other['id']}/equip", headers=h, json={})
    assert state(client, h)["attributes"]["strength"]["effective"] == 12
    client.post(f"/inventory/{other['id']}/unequip", headers=h, json={})
    assert state(client, h)["attributes"]["strength"]["effective"] == 5
    client.post(f"/inventory/{sword['id']}/equip", headers=h, json={})
    navigate(client, h, "common_a")
    e = state(client, h)["map"]["enemies"][0]
    walk_tiles(client, h, (e["x"], e["y"]))
    b = client.post("/battles", headers=h, json={"monster": str(e["id"])}).json()
    result = client.post(
        f"/battles/{b['id']}/action", headers=h, json={"turn": 0, "action": "attack"}
    )
    assert result.json()["damage"] == 6
    with Session() as db:
        assert db.get(m.Character, cid).strength == 5


@pytest.mark.parametrize("p", [0, 0.25, 0.5, 0.75, 1])
def test_generator_limits_determinism_and_miniboss(p):
    for name, config in SPECIES.items():
        for seed in range(200):
            a = generate(config, 1, p, seed)
            assert a == generate(config, 1, p, seed)
            for key, value in a.items():
                low, high = config["floors"]["1"][key]
                assert low <= value <= high
            assert generate(config, 1, p, seed, "miniboss")["hp"] >= a["hp"]
    with pytest.raises(ValueError):
        generate(SPECIES["slime"], 1, None, 1)


def test_generator_statistical_bias_and_exact_formula():
    low = [generate(SPECIES["slime"], 1, 0, i)["level"] for i in range(3000)]
    near = [generate(SPECIES["slime"], 1, 1, i)["level"] for i in range(3000)]
    assert sum(near) > sum(low) * 1.25 and len(set(near)) > 1
    assert max(near) == 4  # Mandated floor/r<1 formula makes Lmax exclusive.
    assert chance(0) == 0.01 and chance(1) == 0.02 and chance(100) == 0.10


def test_graph_distance_unreachable(client):
    fresh(client)
    with Session.begin() as db:
        assert proximity(db, db.get(m.Room, "boss")) == 1
        assert proximity(db, db.get(m.Room, "combat")) > proximity(
            db, db.get(m.Room, "common_a")
        )
        room = m.Room(
            id="isolated", floor_id=1, kind="PROCEDURAL", name="No path", data={}
        )
        db.add(room)
        db.flush()
        assert proximity(db, room) is None


def test_sequence_once_reconnect_completion_cleanup_and_abandon(client, monkeypatch):
    h = fresh(client)
    s = begin(client, h, monkeypatch)
    room = s["room"]["id"]
    assert s["expedition"]["boss_chance"] == 0.01 and s["expedition"]["boss_rolled"]
    for _ in range(3):
        assert (
            state(client, h)["expedition"]["special_boss"]
            == s["expedition"]["special_boss"]
        )
    with Session.begin() as db:
        c = db.get(m.Character, s["character"]["id"])
        c.strength = 999
        c.hp = 999
    for e in s["map"]["enemies"]:
        kill(client, h, e["id"])
    for _ in range(3):
        assert state(client, h)["character"]["adventure_streak"] == 1
    assert state(client, h)["next_boss_chance"] == 0.02
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.EnemyInstance)
                .where(
                    m.EnemyInstance.room_id == room,
                    m.EnemyInstance.category.in_(["common", "rare", "miniboss"]),
                )
            )
            == 0
        )
    assert (
        client.post("/adventures/abandon-sequence", headers=h, json={}).status_code
        == 200
    )
    assert state(client, h)["next_boss_chance"] == 0.01


def test_flee_and_death_reset_sequence(client, monkeypatch):
    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.get(m.Character, cid).adventure_streak = 8
    s = begin(client, h, monkeypatch)
    assert s["expedition"]["boss_chance"] == 0.09
    assert flee(client, h, s["expedition"]["id"]).status_code == 200
    assert state(client, h)["character"]["adventure_streak"] == 0
    with Session.begin() as db:
        db.get(m.Character, cid).adventure_streak = 9
    s, b = setup_lethal(client, h, monkeypatch)
    assert lethal(client, h, b).status_code == 200
    assert state(client, h)["character"]["adventure_streak"] == 0


@pytest.mark.parametrize("count", [0, 1, 2, 3, 5, 20])
def test_death_unit_limit_protection_and_common_destruction(client, monkeypatch, count):
    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        for i in db.scalars(
            select(m.Item).where(m.Item.owner == cid, m.Item.definition != "sword")
        ):
            db.delete(i)
        if count:
            db.add(m.Item(owner=cid, definition="crystal", quantity=count))
    monkeypatch.setattr("app.recovery.loss_count", lambda n: n)
    s, b = setup_lethal(client, h, monkeypatch)
    assert lethal(client, h, b).status_code == 200
    after = state(client, h)
    lost = after["death"]["items"]
    assert sum(i["quantity"] for i in lost) == min(5, count)
    assert all(i["destination"] == "destroyed" for i in lost)
    assert any(i["definition"] == "sword" for i in after["inventory"])
    assert client.get("/auctions", headers=h).json() == []


def test_personal_recovery_price_ownership_atomic_and_replay(client, monkeypatch):
    h = fresh(client)
    other = fresh(client, "other")
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        d = db.get(m.ItemDefinition, "iron_sword")
        d.rarity = "rare"
        d.base_value = 500
    monkeypatch.setattr("app.recovery.loss_count", lambda n: n)
    s, b = setup_lethal(client, h, monkeypatch)
    assert lethal(client, h, b).status_code == 200
    items = client.get("/recovery", headers=h).json()
    assert len(items) == 1 and items[0]["price"] == "1000"
    assert client.get("/recovery", headers=other).json() == []
    rid = items[0]["id"]
    request = {"request_id": str(uuid4())}
    assert (
        client.post(f"/recovery/{rid}/recover", headers=other, json=request).status_code
        == 404
    )
    navigate(client, h, "recovery_hall")
    walk_tiles(client, h, state(client, h)["map"]["npc"])
    assert (
        client.post(f"/recovery/{rid}/recover", headers=h, json=request).status_code
        == 409
    )
    wallet(h, client, 1000)

    def run(_):
        with TestClient(app) as c:
            return c.post(f"/recovery/{rid}/recover", headers=h, json=request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert (
        all(r.status_code == 200 for r in results)
        and sum(r.json()["replayed"] for r in results) == 1
    )
    assert state(client, h)["coins_exact"] == "0"
    with Session() as db:
        assert db.get(m.Item, items[0]["item_id"]).owner == cid
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Ledger)
                .where(m.Ledger.reference == f"recovery:{rid}")
            )
            == 1
        )


@pytest.mark.parametrize(
    "values,total,count,balance",
    [
        ([1001], 1001, 1, 1),
        ([500], 500, 1, -500),
        ([1000] * 5, 1000, 1, 0),
        ([100] * 20, 1000, 10, 0),
        ([800, 700, 300], 1000, 2, 0),
    ],
)
def test_debt_selection_surplus_and_no_death_cap(client, values, total, count, balance):
    from app.debt import collect

    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        for i in db.scalars(
            select(m.Item).where(m.Item.owner == cid, m.Item.definition != "sword")
        ):
            db.delete(i)
        for index, value in enumerate(values):
            key = f"value{index}"
            db.add(
                m.ItemDefinition(
                    id=key, name=key, kind="weapon", power=0, base_value=value
                )
            )
            db.flush()
            db.add(m.Item(owner=cid, definition=key, quantity=1))
        c = db.get(m.Character, cid)
        c.coins = -1000
        record = collect(db, c)
        assert record.assessed == total and c.coins == balance
        assert sum(i["quantity"] for i in record.items) == count
        assert collect(db, c) is None
    auctions = client.get("/auctions", headers=h).json()
    assert sum(a["quantity"] for a in auctions) == count
    assert all(a["origin"] == "guild_debt" for a in auctions)


def test_debt_milestone_cumulative_new_debt(client):
    from app.debt import collect

    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        c.coins = -1000
        db.get(m.ItemDefinition, "iron_sword").base_value = 500
        collect(db, c)
        assert c.coins == -500 and c.debt_next_collection == 1000
        c.coins = -1499
        c.debt_accrued = 999
        assert collect(db, c) is None
        c.coins = -1500
        c.debt_accrued = 1000
        assert collect(db, c) is not None
        assert collect(db, c) is None


def test_hide_refunds_archive_and_private_history(client):
    from app.debt import collect

    ah, h = admin(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        c.coins = -1000
        collect(db, c)
    a = client.get("/auctions", headers=h).json()[0]
    other = fresh(client, "bidder")
    wallet(other, client, 1000)
    assert bid(client, other, a["id"], 100).status_code == 200
    p = proposal(client, ah, "auctions.hide", target=a["id"])
    assert commit(client, ah, p).status_code == 200
    assert state(client, other)["coins_exact"] == "1000"
    assert client.get("/auctions", headers=h).json() == []
    assert client.get(f"/auctions/{a['id']}", headers=h).status_code == 404
    assert bid(client, other, a["id"], 200).status_code == 404
    p = proposal(client, ah, "auctions.archive", target=a["id"])
    assert commit(client, ah, p).status_code == 200
    history = client.get("/admin/auctions", headers=ah).json()
    assert (
        history[0]["hidden"] and history[0]["archived"] and len(history[0]["bids"]) == 1
    )


def test_world_event_preview_application_permissions_cancel(client):
    from app.world_events import rare_multiplier

    ah, h = admin(client)
    params = dict(
        name="Raros em dobro",
        description="Mais raros em novas aventuras",
        region="procedural",
        floor_id=1,
        effect="rare_spawn",
        intensity=100,
        conditions="new_adventures",
        starts_at=(utc_now() - timedelta(minutes=1)).isoformat() + "Z",
        duration_minutes=60,
    )
    p = proposal(client, ah, "world.event_create", target="first-floor", params=params)
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    events = client.get("/admin/world", headers=ah).json()["scheduled_events"]
    assert events[0]["state"] == "ACTIVE"
    with Session() as db:
        room = db.get(m.Room, "common_a")
        room.kind = "PROCEDURAL"
        assert rare_multiplier(db, room) == 2
    p = proposal(client, ah, "world.event_cancel", target=events[0]["id"])
    assert commit(client, ah, p).status_code == 200
    assert (
        client.get("/admin/world", headers=ah).json()["scheduled_events"][0]["state"]
        == "CANCELLED"
    )
    assert client.get("/admin/world", headers=h).status_code == 401


def test_zero_loss_endpoint_and_same_item_not_duplicated(client, monkeypatch):
    h = fresh(client)
    monkeypatch.setattr("app.recovery.loss_count", lambda n: 0)
    s, b = setup_lethal(client, h, monkeypatch)
    before = state(client, h)["inventory"]
    assert lethal(client, h, b).status_code == 200
    after = state(client, h)
    assert after["death"]["items"] == []
    assert sorted(i["id"] for i in before) == sorted(
        i["id"] for i in after["inventory"]
    )


def test_debt_auction_does_not_repay_twice(client):
    from app.debt import collect
    from test_death_economy import expire

    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        c.coins = -1000
        db.get(m.ItemDefinition, "iron_sword").base_value = 1001
        collect(db, c)
    assert state(client, h)["coins_exact"] == "1"
    other = fresh(client, "buyer")
    wallet(other, client, 2000)
    a = client.get("/auctions", headers=h).json()[0]
    assert bid(client, other, a["id"], 1500).status_code == 200
    expire(a["id"])
    assert (
        client.post(f"/auctions/{a['id']}/settle", headers=other, json={}).status_code
        == 200
    )
    assert state(client, h)["coins_exact"] == "1"
    with Session() as db:
        assert (
            db.get(m.Item, a["item_id"]).owner
            == state(client, other)["character"]["id"]
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Ledger)
                .where(m.Ledger.reference.like("debt-collection:%"))
            )
            == 1
        )


def test_structural_and_nontransferable_items_excluded(client):
    from app.recovery import eligible

    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.add(
            m.ItemDefinition(
                id="structural",
                name="Estrutural",
                kind="system",
                power=0,
                base_value=5000,
            )
        )
        db.flush()
        db.add(m.Item(owner=cid, definition="structural", quantity=1))
        assert all(
            d.id not in ("structural", "sword")
            for i, d in eligible(db, db.get(m.Character, cid))
        )
