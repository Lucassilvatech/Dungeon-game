from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from importlib import reload
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from test_game import clean, client, player, state, navigate, walk_tiles
from test_cutover import fresh_lunar, convert
from test_expeditions import begin, flee
from app import models as m, lunar_resources as resources, finance, lunar, game
from app.database import Session, engine
from app.config import settings
from app import mineral_lots as lots


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setattr(settings, "lunar_resource_spawn_enabled", True)
    monkeypatch.setattr(settings, "lunar_resource_spawn_chance_ppm", 1000000)
    monkeypatch.setattr(
        settings,
        "lunar_resource_weight_distribution",
        {"nugget_small": 1, "nugget_medium": 0, "nugget_large": 0},
    )
    monkeypatch.setattr(
        settings,
        "lunar_guild_prices",
        {"nugget_small": 7, "nugget_medium": 13, "nugget_large": 19},
    )


def setup(client, mp, asset="nugget_small"):
    h = player(client)
    convert()
    mp.setattr(resources, "roll", lambda *args: ("a" * 64, resources.WEIGHTS[asset]))
    s = begin(client, h, mp)
    r = s["map"]["lunar_resources"][0]
    walk_tiles(client, h, (r["x"], r["y"]))
    return h, s, r


def collect(client, h, r, key=None, **extra):
    return client.post(
        f"/expeditions/{r['expedition_id']}/lunar-resources/{r['id']}/collect",
        headers=h,
        json={"request_id": key or str(uuid4()), **extra},
    )


def invariant():
    with Session() as db:
        a = finance.reconcile(db)
        assert (
            a["gap_mg"] == "0"
            and not a["ledger_mismatches"]
            and not a["metadata_mismatches"]
        )
        return a


def test_seed_distribution_and_persisted_no_spawn(client, monkeypatch):
    with Session() as db:
        config = resources.policy(db)
    config["lunar_resource_spawn_chance_ppm"] = 10000
    decisions = [resources.roll(i, f"room:{i}", 77, 0, config) for i in range(10000)]
    assert 50 < sum(code is not None for d, code in decisions) < 160
    assert decisions == [
        resources.roll(i, f"room:{i}", 77, 0, config) for i in range(10000)
    ]
    h = player(client)
    convert()
    monkeypatch.setattr(settings, "lunar_resource_spawn_chance_ppm", 0)
    s = begin(client, h, monkeypatch)
    assert s["map"]["lunar_resources"] == []
    eid = s["expedition"]["id"]
    monkeypatch.setattr(settings, "lunar_resource_spawn_chance_ppm", 1000000)
    for _ in range(3):
        assert state(client, h)["map"]["lunar_resources"] == []
    with Session.begin() as db:
        c = db.get(m.Character, s["character"]["id"])
        g = resources.generate(
            db, c, db.get(m.Room, c.room_id), db.get(m.Expedition, eid)
        )
        assert not g.spawned
    assert flee(client, h, eid).status_code == 200
    new = begin(client, h, monkeypatch)
    assert new["expedition"]["id"] != eid and len(new["map"]["lunar_resources"]) == 1
    invariant()


def test_reconnect_reload_restart_queries_and_discord_never_reroll(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    eid = r["expedition_id"]
    with Session.begin() as db:
        db.get(
            m.Account, db.get(m.Character, s["character"]["id"]).account_id
        ).discord_id = "998877"
        initial = db.get(m.LunarResourceGeneration, eid).decision_hash
    for _ in range(4):
        assert state(client, h)["map"]["lunar_resources"] == [r]
    engine.dispose()
    reload(resources)
    with monkeypatch.context() as mp:
        mp.setattr(
            resources,
            "roll",
            lambda *a: (_ for _ in ()).throw(AssertionError("reroll")),
        )
        assert state(client, h)["map"]["lunar_resources"] == [r]
        with Session.begin() as db:
            c = db.get(m.Character, s["character"]["id"])
            assert (
                resources.generate(
                    db, c, db.get(m.Room, c.room_id), db.get(m.Expedition, eid)
                ).decision_hash
                == initial
            )
    from app.discord_client import query

    for section in ["mineral", "inventory", "expedition", "map"]:
        with Session.begin() as db:
            data = query(db, "998877", section)
            assert "lunar_resources" not in data and "decision_hash" not in str(data)
    assert state(client, h)["map"]["lunar_resources"] == [r]
    with Session() as db:
        assert (
            db.scalar(select(func.count()).select_from(m.LunarResourceOccurrence)) == 1
        )
        assert db.get(m.LunarSupply, 1).discovered_mg == 0


@pytest.mark.parametrize("asset,weight", list(resources.WEIGHTS.items()))
def test_collection_exact_mass_no_coins_and_replay(client, monkeypatch, asset, weight):
    h, s, r = setup(client, monkeypatch, asset)
    key = str(uuid4())
    assert collect(client, h, r, key).status_code == 200
    assert collect(client, h, r, key).json()["replayed"]
    assert collect(client, h, r).status_code == 409
    assert state(client, h)["map"]["lunar_resources"] == []
    assert state(client, h)["lunar_inventory"][0]["weight_mg"] == str(weight)
    with Session() as db:
        assert db.get(m.LunarSupply, 1).discovered_mg == weight
        assert finance.coin_mg(db, f"player:{s['character']['id']}") == 0
        e = db.scalar(
            select(m.LunarEntry).where(m.LunarEntry.kind == "DISCOVERED_MINERAL")
        )
        assert e.context["occurrence_id"] == r["id"] and e.context["weight_mg"] == str(
            weight
        )
    invariant()


def test_authorization_distance_strict_body_and_external_raid_member(
    client, monkeypatch
):
    h, s, r = setup(client, monkeypatch)
    other = player(client, "outsider")
    oid = state(client, other)["character"]["id"]
    with Session.begin() as db:
        raid = m.Raid(leader_id=s["character"]["id"], invite="private-fixture")
        db.add(raid)
        db.flush()
        db.add_all(
            [
                m.RaidMember(raid_id=raid.id, character_id=oid),
                m.RaidMember(raid_id=raid.id, character_id=s["character"]["id"]),
            ]
        )
        c = db.get(m.Character, s["character"]["id"])
        c.x = 0
        c.y = 0
    assert collect(client, other, r).status_code == 404
    assert collect(client, h, r, weight_mg=100000).status_code == 422
    assert collect(client, h, r, owner=oid).status_code == 422
    assert collect(client, h, r).status_code == 409
    with Session() as db:
        assert db.get(m.LunarSupply, 1).discovered_mg == 0


@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_collection_once(client, monkeypatch, same_request):
    h, s, r = setup(client, monkeypatch)
    shared = str(uuid4())

    def run(_):
        try:
            with Session.begin() as db:
                c = game.character(db, SimpleNamespace(id=s["character"]["id"]))
                return resources.collect(
                    db,
                    c,
                    r["expedition_id"],
                    r["id"],
                    shared if same_request else str(uuid4()),
                )
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(4) as pool:
        answers = list(pool.map(run, range(4)))
    assert sum(isinstance(a, dict) and not a["replayed"] for a in answers) == 1
    assert sum(a == 409 for a in answers) == (0 if same_request else 3)
    invariant()


def test_collection_capacity_and_split_share_inventory_slots(client, monkeypatch):
    h, s, r = setup(client, monkeypatch, "nugget_large")
    monkeypatch.setattr(settings, "collection_slots", 1)
    assert collect(client, h, r).status_code == 409
    monkeypatch.setattr(settings, "collection_slots", 2)
    assert collect(client, h, r).status_code == 200
    assert state(client, h)["collection_capacity"]["used"] == 2
    split = {
        "request_id": str(uuid4()),
        "source": "nugget_large",
        "outputs": {"nugget_medium": 2},
    }
    assert client.post("/lunar/nuggets/split", headers=h, json=split).status_code == 409
    monkeypatch.setattr(settings, "collection_slots", 3)
    assert client.post("/lunar/nuggets/split", headers=h, json=split).status_code == 200
    assert client.post("/lunar/nuggets/split", headers=h, json=split).status_code == 200
    assert state(client, h)["collection_capacity"]["used"] == 3
    from app.inventory import ensure_collection_capacity

    with Session.begin() as db:
        with pytest.raises(HTTPException):
            ensure_collection_capacity(
                db,
                db.get(m.Character, s["character"]["id"]),
                db.get(m.ItemDefinition, "herb"),
                1,
                3,
            )
    invariant()


def test_collection_rollback_and_terminal_sql_protection(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    with monkeypatch.context() as mp:

        def reject(db):
            raise HTTPException(409, "audit rejected")

        mp.setattr(resources, "assert_audit", reject)
        assert collect(client, h, r).status_code == 409
    assert state(client, h)["map"]["lunar_resources"] == [r]
    with Session() as db:
        assert db.get(m.LunarSupply, 1).discovered_mg == 0
    assert collect(client, h, r).status_code == 200
    for sql in [
        "UPDATE lunar_resource_occurrences SET state='AVAILABLE'",
        "DELETE FROM lunar_resource_occurrences",
        "UPDATE lunar_resource_generations SET spawned=false",
    ]:
        with pytest.raises(DBAPIError):
            with Session.begin() as db:
                db.execute(text(sql))
    invariant()


def test_expiry_completion_flee_and_closed_instance_no_revisit(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    assert flee(client, h, r["expedition_id"]).status_code == 200
    assert collect(client, h, r).status_code == 409
    with Session.begin() as db:
        assert db.get(m.LunarResourceOccurrence, r["id"]).state == "EXPIRED"
        assert db.get(m.LunarSupply, 1).discovered_mg == 0
        from app.rooms import enter

        with pytest.raises(HTTPException):
            enter(
                db,
                db.get(m.Character, s["character"]["id"]),
                db.get(m.Room, s["room"]["id"]),
            )
    new = begin(client, h, monkeypatch)
    nr = new["map"]["lunar_resources"][0]
    with Session.begin() as db:
        for e in db.scalars(
            select(m.EnemyInstance).where(m.EnemyInstance.room_id == new["room"]["id"])
        ):
            e.state = "DEAD"
            e.hp = 0
    assert state(client, h)["expedition"]["status"] == "COMPLETED"
    with Session() as db:
        assert db.get(m.LunarResourceOccurrence, nr["id"]).state == "EXPIRED"
    invariant()


def test_collection_races_with_end_and_reconnect(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    from app import expeditions

    def run(ending):
        try:
            with Session.begin() as db:
                c = game.character(db, SimpleNamespace(id=s["character"]["id"]))
                if ending:
                    p = expeditions.preview(db, c, r["expedition_id"])
                    return expeditions.flee(
                        db, c, r["expedition_id"], p["confirmation_token"]
                    )
                return resources.collect(
                    db, c, r["expedition_id"], r["id"], str(uuid4())
                )
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(run, [False, True]))
    assert state(client, h)["room"]["id"] == "city1"
    with Session() as db:
        row = db.get(m.LunarResourceOccurrence, r["id"])
        assert row.state in ("COLLECTED", "EXPIRED")
        assert db.get(m.LunarSupply, 1).discovered_mg == (
            100000 if row.state == "COLLECTED" else 0
        )
    invariant()


def at_guild(client, h):
    s = state(client, h)
    if s["expedition"] and s["expedition"]["status"] == "ACTIVE":
        assert flee(client, h, s["expedition"]["id"]).status_code == 200
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))


def sale_body(client, h, asset="nugget_medium"):
    q = next(
        q
        for q in client.get("/lunar/guild-quotes", headers=h).json()["quotes"]
        if q["weight_mg"] == str(resources.WEIGHTS[asset])
    )
    return {"lot_id": q["lot_id"], "quote": q["quote_hash"], "request_id": str(uuid4())}


def test_guild_finite_cash_server_price_replay_ownership_and_conservation(
    client, monkeypatch
):
    h, s, r = setup(client, monkeypatch, "nugget_medium")
    assert collect(client, h, r).status_code == 200
    at_guild(client, h)
    body = sale_body(client, h)
    assert client.post("/lunar/guild-sell", headers=h, json=body).status_code == 409
    with Session.begin() as db:
        finance.move(db, "treasury", "guild", 400, "fund-guild")
    assert (
        client.post(
            "/lunar/guild-sell", headers=h, json={**body, "weight_mg": 500000}
        ).status_code
        == 422
    )
    with Session() as db:
        assert finance.coin_mg(db, "guild") == 400000
        assert len(lots.held(db, f"player:{s['character']['id']}")) == 1
    assert client.post("/lunar/guild-sell", headers=h, json=body).status_code == 200
    monkeypatch.setattr(settings, "lunar_guild_buy_rate_milliunits_per_gram", 999)
    assert client.post("/lunar/guild-sell", headers=h, json=body).json()["replayed"]
    assert (
        client.post(
            "/lunar/guild-sell", headers=h, json={**body, "request_id": str(uuid4())}
        ).status_code
        == 409
    )
    with Session() as db:
        assert (
            finance.coin_mg(db, "guild") == 0
            and finance.coin_mg(db, f"player:{s['character']['id']}") == 400000
        )
        assert len(lots.held(db, "guild")) == 1
        assert db.get(m.LunarSupply, 1).discovered_mg == 500000
        assert resources.metrics(db)["lunar_resource_sold_to_guild_mg"] == "500000"
    invariant()


def test_double_sale_and_audit_rollback(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    assert collect(client, h, r).status_code == 200
    at_guild(client, h)
    with Session.begin() as db:
        finance.move(db, "treasury", "guild", 160, "fund-guild")
    body = sale_body(client, h, "nugget_small")
    with monkeypatch.context() as mp:
        mp.setattr(
            resources,
            "assert_audit",
            lambda db: (_ for _ in ()).throw(HTTPException(409, "audit rollback")),
        )
        assert client.post("/lunar/guild-sell", headers=h, json=body).status_code == 409
    with Session() as db:
        assert (
            finance.coin_mg(db, "guild") == 160000 and len(lots.held(db, "guild")) == 0
        )

    def run(_):
        try:
            with Session.begin() as db:
                c = game.character(db, SimpleNamespace(id=s["character"]["id"]))
                return resources.sell(
                    db, c, body["lot_id"], body["quote"], str(uuid4())
                )
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(run, range(2)))
    assert sum(isinstance(x, dict) for x in results) == 1 and results.count(409) == 1
    invariant()


def test_mineral_retained_on_death_and_available_expires(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    assert collect(client, h, r).status_code == 200
    with Session.begin() as db:
        c = db.get(m.Character, s["character"]["id"])
        e = db.scalar(
            select(m.EnemyInstance).where(m.EnemyInstance.room_id == c.room_id)
        )
        c.hp = 1
        c.x = e.x + 1
        c.y = e.y
        enemy = e.id
    b = client.post("/battles", headers=h, json={"monster": str(enemy)}).json()
    response = client.post(
        f"/battles/{b['id']}/action",
        headers=h,
        json={"turn": b["turn"], "action": "defend"},
    )
    assert response.status_code == 200 and response.json()["status"] == "lost"
    assert len(state(client, h)["lunar_inventory"]) == 1
    assert state(client, h)["death"]["newly_financed"] == 100
    invariant()


def test_admin_config_permissions_and_strict_values(client):
    from test_admin_migration import admin, proposal, commit

    ah, h = admin(client)
    for key, value in [
        ("lunar_resource_spawn_enabled", False),
        ("lunar_resource_spawn_chance_ppm", 2345),
        (
            "lunar_resource_weight_bands",
            [
                {"min_g": 100, "max_g": 200, "percent": 80},
                {"min_g": 201, "max_g": 700, "percent": 15},
                {"min_g": 701, "max_g": 1000, "percent": 5},
            ],
        ),
        (
            "lunar_guild_buy_rate_milliunits_per_gram",
            800,
        ),
    ]:
        p = proposal(client, ah, "economy.configure", key, {"value": value})
        assert p.status_code == 200, p.text
        assert commit(client, ah, p).status_code == 200
    assert client.get("/admin/lunar/resources", headers=h).status_code == 401
    assert client.get("/admin/lunar/resources", headers=ah).status_code == 200
    observer, _ = admin(client, "observer", "observer")
    assert (
        proposal(
            client,
            observer,
            "economy.configure",
            "lunar_resource_spawn_enabled",
            {"value": True},
        ).status_code
        == 403
    )
    for key, value in [
        ("lunar_resource_spawn_enabled", 1),
        ("lunar_resource_spawn_chance_ppm", 1.1),
        ("lunar_guild_buy_rate_milliunits_per_gram", 1.2),
        ("lunar_resource_weight_bands", []),
    ]:
        assert (
            proposal(client, ah, "economy.configure", key, {"value": value}).status_code
            == 422
        )


def test_concurrent_reconnect_collection_and_invalid_sale(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    quote = "0" * 64

    def run(action):
        try:
            with Session.begin() as db:
                c = game.character(db, SimpleNamespace(id=s["character"]["id"]))
                if action == "read":
                    return game.snapshot(db, c)
                if action == "sale":
                    return resources.sell(db, c, 999999, quote, str(uuid4()))
                return resources.collect(
                    db, c, r["expedition_id"], r["id"], str(uuid4())
                )
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(3) as pool:
        result = list(pool.map(run, ["collect", "read", "sale"]))
    assert result[2] == 409
    assert isinstance(result[0], dict) and result[0]["replayed"] is False
    assert isinstance(result[1], dict)
    assert state(client, h)["map"]["lunar_resources"] == []
    invariant()


def test_death_expires_uncollected_without_economic_entry(client, monkeypatch):
    h, s, r = setup(client, monkeypatch)
    with Session.begin() as db:
        c = db.get(m.Character, s["character"]["id"])
        e = db.scalar(
            select(m.EnemyInstance).where(m.EnemyInstance.room_id == c.room_id)
        )
        c.hp = 1
        c.x = e.x + 1
        c.y = e.y
        enemy = e.id
    b = client.post("/battles", headers=h, json={"monster": str(enemy)}).json()
    assert (
        client.post(
            f"/battles/{b['id']}/action",
            headers=h,
            json={"turn": b["turn"], "action": "defend"},
        ).status_code
        == 200
    )
    with Session() as db:
        assert db.get(m.LunarResourceOccurrence, r["id"]).state == "EXPIRED"
        assert db.get(m.LunarSupply, 1).discovered_mg == 0
    invariant()
