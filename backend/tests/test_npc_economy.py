from datetime import timedelta
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import pytest
from sqlalchemy import select, func, text
from fastapi import HTTPException
from test_game import clean, client, state, walk_tiles, navigate
from test_cutover import fresh_lunar
from test_physical_commerce import ready, cash_inject, config, item
from test_royal_lots import invariant
from test_admin_migration import execute, proposal, commit
from app import (
    models as m,
    npc_economy as npc,
    npc_production as production,
    market_pricing as pricing,
    finance,
    lunar,
    guild_catalog,
)
from app.database import Session
from app.clock import utc_now


def counts(id):
    with Session() as db:
        return npc.quantities(db, db.get(m.NpcProfile, id).account_id)


def cycle(now=None):
    with Session.begin() as db:
        return production.tick(db, now)


def configure(client, ah, id, **params):
    with Session() as db:
        rev = db.get(m.NpcProfile, id).revision
    return execute(
        client, ah, "npc.configure", id, {"expected_revision": rev, **params}
    )


def q(client, h, id, qty, definition=None, item_id=None):
    response = client.post(
        "/economy/npcs/" + id + "/quote",
        headers=h,
        json={
            "definition_id": definition,
            "item_id": item_id,
            "quantity": qty,
            "operation_type": "buy",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def buy(client, h, id, offer, key=None):
    return client.post(
        "/economy/npcs/" + id + "/trade",
        headers=h,
        json={
            k: offer[k]
            for k in ("definition_id", "item_id", "quantity", "operation_type")
        }
        | {"quote": offer["quote_hash"], "request_id": key or str(uuid4())},
    )


def near(cid, id):
    service = next(s for s in npc.SERVICES if s["id"] == id)
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        c.room_id = "city1"
        c.x = service["x"]
        c.y = service["y"] + 1


def test_initial_custody_exact_and_seed_idempotence(client):
    ah, h, cid = ready(client)
    assert counts("alchemist") == {
        "herb": 7,
        "crystal": 7,
        "weak_healing_potion": 1,
        "healing_potion": 1,
        "energy_potion": 1,
    }
    assert counts("blacksmith") == {
        "ore": 90,
        **{
            r[0]: 1
            for r in npc.RECIPES
            if r[1] == "blacksmith" and r[0] != "moss_ingot"
        },
    }
    assert counts("merchant") == {}
    from app.seed import seed

    with Session() as db:
        before = {
            p.id: (counts(p.id), finance.cash(db, p.account_id))
            for p in db.scalars(select(m.NpcProfile))
        }
        revision = pricing.latest(db).id
    seed()
    seed()
    with Session() as db:
        assert before == {
            p.id: (counts(p.id), finance.cash(db, p.account_id))
            for p in db.scalars(select(m.NpcProfile))
        }
        assert all(
            finance.coin_mg(db, "npc:" + id) == 0
            for id in ("merchant", "alchemist", "blacksmith")
        )
        assert pricing.latest(db).id == revision
    invariant()


def test_deterministic_complete_production_and_empty_materials(client):
    ah, h, cid = ready(client)
    result = cycle()
    assert counts("alchemist") == {
        "weak_healing_potion": 2,
        "healing_potion": 2,
        "energy_potion": 2,
    }
    assert counts("blacksmith") == {
        r[0]: 2 for r in npc.RECIPES if r[1] == "blacksmith" and r[0] != "moss_ingot"
    }
    smelt = next(r for r in result["production"] if r["definition"] == "moss_ingot")
    assert (
        smelt["quantity"] == 18
        and sum(p["quantity"] for p in smelt["inputs"]["ore"]) == 90
    )
    assert cycle()["replayed"]
    with Session() as db:
        assert (
            db.get(m.NpcInventoryPolicy, ("alchemist", "herb")).status == "WAIT_STOCK"
        )
        assert all(i.quantity == 1 for i, _ in npc.stock(db, "npc:blacksmith"))
    invariant()


@pytest.mark.parametrize(
    "result,ingredients",
    [
        ("weak_healing_potion", {"herb": 2, "crystal": 1}),
        ("healing_potion", {"herb": 4, "crystal": 2}),
        ("energy_potion", {"herb": 1, "crystal": 4}),
        ("moss_ingot", {"ore": 5}),
    ],
)
def test_recipes_persist_only_approved_ingredients(client, result, ingredients):
    ready(client)
    with Session() as db:
        assert db.get(m.NpcRecipe, result).ingredients == ingredients


def test_integral_prices_factors_and_fixed_fees():
    assert pricing.fixed_price(2, 10, 1) == 21
    assert pricing.fixed_price(1, 100, 1) == 101
    assert pricing.ceil_price(7 * 12500) == 9
    assert pricing.ceil_price(50 * 12000) == 60
    assert pricing.ceil_price(180 * 13000) == 234


def test_maximum_affine_lot_payment_matches_independent_enumeration():
    for large, middle, small in product(range(3), range(2), range(5)):
        available = {"coin_large": large, "coin_medium": middle, "coin_small": small}
        reachable = {
            a * 10 + b * 5 + c
            for a, b, c in product(
                range(large + 1), range(middle + 1), range(small + 1)
            )
        }
        for unit, fee, step in product((0, 1, 2, 7), (0, 1, 3), (1, 3, 10)):
            expected = max(
                [0] + [n for n in range(step, 61, step) if n * unit + fee in reachable]
            )
            assert (
                guild_catalog.maximum_exact_quantity(
                    available, unit, 60, fee, step, step
                )
                == expected
            )


def test_restock_real_lot_purchase_after_production(client):
    ah, h, cid = ready(client)
    configure(client, ah, "merchant", purchase_enabled=False)
    cash_inject(client, ah, "npc:alchemist", small=500)
    # Explicit material transfer, no material creation or fake merchant stock.
    for definition in ("herb", "crystal"):
        item(cid, 20, definition, guild=True)
        execute(
            client,
            ah,
            "npc.stock_transfer",
            "guild",
            {"destination": "merchant", "definition_id": definition, "quantity": 20},
        )
    before = counts("merchant")
    result = cycle()
    assert counts("alchemist") == {
        "herb": 10,
        "crystal": 10,
        "weak_healing_potion": 2,
        "healing_potion": 2,
        "energy_potion": 2,
    }
    assert counts("merchant") == {k: v - 10 for k, v in before.items()}
    assert [p["quantity"] for p in result["purchases"] if p["npc"] == "alchemist"] == [
        10,
        10,
    ]
    with Session() as db:
        assert finance.coin_mg(db, "npc:merchant") == 152000  # 10*5+1 and10*10+1
        assert finance.coin_mg(db, "npc:alchemist") == 348000
    invariant()


def test_merchant_buys_from_guild_with_real_cash_and_guild_fee(client):
    ah, h, cid = ready(client)
    config(
        client,
        ah,
        "herb",
        buy_price_units=1,
        sell_price_units=2,
        buy_enabled=True,
        sell_enabled=True,
    )
    item(cid, 20, "herb", guild=True)
    cash_inject(client, ah, "npc:merchant", small=21)
    cycle()
    assert counts("merchant")["herb"] == 10
    with Session() as db:
        assert finance.coin_mg(db, "npc:merchant") == 0
    invariant()


def test_waits_without_funds_stock_denominations_or_capacity(client):
    ah, h, cid = ready(client)
    cycle()
    assert counts("merchant") == {}
    with Session.begin() as db:
        p = db.get(m.NpcInventoryPolicy, ("alchemist", "herb"))
        p.capacity = 5
        p.reorder_point = 5
        npc.give(db, "npc:merchant", "herb", 10)
    cash_inject(client, ah, "npc:alchemist", large=10)
    cycle(utc_now() + timedelta(minutes=2))
    with Session() as db:
        assert (
            db.get(m.NpcInventoryPolicy, ("alchemist", "herb")).status
            == "WAIT_CAPACITY"
        )
        assert (
            db.get(m.NpcInventoryPolicy, ("alchemist", "crystal")).status
            == "WAIT_STOCK"
        )
    assert counts("merchant")["herb"] == 10
    invariant()


def test_market_revisions_propagate_and_unchanged_tick_does_not_reprice(client):
    ah, h, cid = ready(client)
    with Session() as db:
        before = pricing.latest(db).snapshot
        revision = pricing.latest(db).id
    config(client, ah, "herb", buy_price_units=10, acknowledge_arbitrage=True)
    with Session() as db:
        after = pricing.latest(db)
        assert after.id > revision
        assert all(
            int(after.snapshot["prices"][k]) > int(before["prices"][k])
            for k in ("weak_healing_potion", "healing_potion", "energy_potion")
        )
        assert after.snapshot["prices"]["moss_sword"] == before["prices"]["moss_sword"]
    config(client, ah, "ore", buy_price_units=20, acknowledge_arbitrage=True)
    with Session() as db:
        after = pricing.latest(db)
        revision = after.id
        assert all(
            int(after.snapshot["prices"][k]) > int(before["prices"][k])
            for k in (
                "moss_ingot",
                "moss_sword",
                "moss_helmet",
                "moss_chest",
                "moss_gloves",
                "moss_pants",
                "moss_boots",
            )
        )
    cycle()
    cycle(utc_now() + timedelta(minutes=2))
    with Session() as db:
        assert pricing.latest(db).id == revision
    invariant()


def test_admin_preview_read_only_factor_and_policy_revision_conflicts(client):
    ah, h, cid = ready(client)
    with Session() as db:
        row = db.get(m.NpcProfile, "alchemist")
        revision = row.revision
        before = pricing.latest(db).id
        event_count = db.scalar(select(func.count()).select_from(m.WorldEvent))
    p = proposal(
        client,
        ah,
        "npc.configure",
        "alchemist",
        {"expected_revision": revision, "factors": {"alchemy": 13500}},
    )
    assert p.status_code == 200, p.text
    with Session() as db:
        assert db.get(m.NpcProfile, "alchemist").factors == {"alchemy": 12500}
        assert (
            pricing.latest(db).id == before
            and db.scalar(select(func.count()).select_from(m.WorldEvent)) == event_count
        )
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    with Session() as db:
        assert db.get(m.NpcProfile, "alchemist").factors == {"alchemy": 13500}
        assert db.get(m.NpcProfile, "blacksmith").factors == {
            "smelting": 12000,
            "smithing": 13000,
        }
        assert pricing.latest(db).id > before
    assert (
        proposal(
            client,
            h,
            "npc.configure",
            "merchant",
            {"expected_revision": 1, "fixed_margin": 2},
        ).status_code
        == 401
    )
    assert (
        proposal(
            client,
            ah,
            "npc.configure",
            "alchemist",
            {"expected_revision": revision, "factors": {"alchemy": 14000}},
        ).status_code
        == 409
    )
    invariant()


def test_merchant_player_purchase_21_and_lot_restrictions(client):
    ah, h, cid = ready(client)
    config(client, ah, "herb", buy_price_units=2)
    with Session.begin() as db:
        npc.give(db, "npc:merchant", "herb", 30)
    near(cid, "merchant")
    cash_inject(client, ah, "player:" + str(cid), small=21)
    offer = q(client, h, "merchant", 10, "herb")
    assert offer["total_price_units"] == "21"
    key = str(uuid4())
    r = buy(client, h, "merchant", offer, key)
    assert r.status_code == 200, r.text
    assert buy(client, h, "merchant", offer, key).json()["replayed"]
    assert counts("merchant")["herb"] == 20
    with Session() as db:
        assert finance.coin_mg(db, "npc:merchant") == 21000
        assert finance.coin_mg(db, "player:" + str(cid)) == 0
    for quantity in (1, 3, 6, 7, 11):
        assert (
            client.post(
                "/economy/npcs/merchant/quote",
                headers=h,
                json={
                    "definition_id": "herb",
                    "quantity": quantity,
                    "operation_type": "buy",
                },
            ).status_code
            == 422
        )
    invariant()


def test_stale_quote_and_two_buyers_one_potion_conserve_money(client):
    ah, h, cid = ready(client)
    near(cid, "alchemist")
    cash_inject(client, ah, "player:" + str(cid), small=200)
    offer = q(client, h, "alchemist", 1, "weak_healing_potion")
    configure(client, ah, "alchemist", factors={"alchemy": 13500})
    assert buy(client, h, "alchemist", offer).status_code == 409
    offer = q(client, h, "alchemist", 1, "weak_healing_potion")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: buy(client, h, "alchemist", offer), range(2))
        )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert counts("alchemist").get("weak_healing_potion", 0) == 0
    invariant()


def test_independent_equipment_slots_and_ownership(client):
    ah, h, cid = ready(client)
    near(cid, "blacksmith")
    cash_inject(client, ah, "player:" + str(cid), small=2000)
    ids = []
    for definition in (
        "moss_sword",
        "moss_helmet",
        "moss_chest",
        "moss_gloves",
        "moss_pants",
        "moss_boots",
    ):
        with Session() as db:
            identity = npc.stock(db, "npc:blacksmith", definition)[0][0].id
        r = buy(
            client, h, "blacksmith", q(client, h, "blacksmith", 1, item_id=identity)
        )
        assert r.status_code == 200, r.text
        assert client.post(f"/inventory/{identity}/equip", headers=h).status_code == 200
        ids.append(identity)
    inventory = state(client, h)["inventory"]
    assert all(
        next(i for i in inventory if i["id"] == identity)["equipped"]
        for identity in ids
    )
    assert (
        len(
            {
                next(i for i in inventory if i["id"] == identity)["equipment_slot"]
                for identity in ids
            }
        )
        == 6
    )
    invariant()


def test_cycle_concurrency_and_restart_persist_no_double_production(client):
    ready(client)
    now = utc_now()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: cycle(now), range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    before = counts("alchemist"), counts("blacksmith")
    from app.seed import seed

    seed()
    assert cycle(now)["replayed"] and before == (
        counts("alchemist"),
        counts("blacksmith"),
    )
    invariant()


@pytest.mark.parametrize(
    "params",
    [
        {"fixed_margin": -1},
        {"factors": {"alchemy": 0}},
        {"factors": {"smithing": 12500}},
        {
            "policies": [
                {
                    "definition_id": "herb",
                    "expected_revision": 1,
                    "capacity": 6,
                    "reorder_point": 5,
                }
            ]
        },
        {
            "policies": [
                {
                    "definition_id": "herb",
                    "expected_revision": 1,
                    "capacity": 20,
                    "reorder_point": 21,
                }
            ]
        },
        {
            "policies": [
                {"definition_id": "herb", "expected_revision": 1, "order_quantity": 0}
            ]
        },
        {
            "policies": [
                {"definition_id": "herb", "expected_revision": 1, "minimum_lot_size": 0}
            ]
        },
        {
            "policies": [
                {"definition_id": "herb", "expected_revision": 1, "order_step": 0}
            ]
        },
    ],
)
def test_invalid_configuration_cannot_change_economy(client, params):
    ah, h, cid = ready(client)
    assert (
        proposal(
            client, ah, "npc.configure", "alchemist", {"expected_revision": 1, **params}
        ).status_code
        == 422
    )
    assert counts("alchemist")["herb"] == 7
    invariant()


def test_restock_waits_for_exact_denominations_and_does_not_repeat_wait_log(client):
    ah, h, cid = ready(client)
    config(client, ah, "herb", buy_price_units=2)
    with Session.begin() as db:
        npc.give(db, "npc:merchant", "herb", 30)
    cash_inject(client, ah, "npc:alchemist", large=3)
    now = utc_now()
    cycle(now)
    assert counts("merchant")["herb"] == 30
    with Session() as db:
        assert (
            db.get(m.NpcInventoryPolicy, ("alchemist", "herb")).status
            == "WAIT_INSUFFICIENT_DENOMINATIONS"
        )
        before = db.scalar(
            select(func.count())
            .select_from(m.WorldEvent)
            .where(m.WorldEvent.kind == "NPC_RESTOCK_REQUEST")
        )
    cycle(now + timedelta(minutes=2))
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.WorldEvent)
                .where(m.WorldEvent.kind == "NPC_RESTOCK_REQUEST")
            )
            == before
        )
    invariant()


def test_lot_margin_targets_and_policy_changes_reach_shared_api(client):
    ah, h, cid = ready(client)
    configure(
        client,
        ah,
        "merchant",
        fixed_margin=3,
        policies=[
            {
                "definition_id": "herb",
                "expected_revision": 1,
                "capacity": 200,
                "minimum_lot_size": 20,
                "order_step": 20,
                "reorder_point": 20,
                "order_quantity": 40,
            }
        ],
    )
    configure(
        client,
        ah,
        "alchemist",
        policies=[
            {
                "definition_id": "herb",
                "expected_revision": 1,
                "capacity": 40,
                "reorder_point": 20,
                "order_quantity": 20,
            },
            {
                "definition_id": "weak_healing_potion",
                "expected_revision": 1,
                "capacity": 3,
                "target_stock": 3,
                "production_enabled": False,
            },
        ],
    )
    raw = client.get("/economy/npcs", headers=h)
    assert raw.status_code == 200
    admin = client.get("/admin/npc-economy", headers=ah).json()
    for public in raw.json():
        privileged = next(n for n in admin["npcs"] if n["id"] == public["id"])
        assert (
            public["items"] == privileged["items"]
            and public["wallet"] == privileged["wallet"]
        )
        assert public["history"] == []
    policy = next(
        p
        for p in next(n for n in raw.json() if n["id"] == "merchant")["items"]
        if p["definition_id"] == "herb"
    )
    assert policy["minimum_lot_quote"]["total_price_units"] == "103"  # 20*5+3
    assert (
        policy["minimum_lot_size"],
        policy["order_step"],
        policy["capacity"],
        policy["order_quantity"],
    ) == (20, 20, 200, 40)
    invariant()


def test_transfers_and_trades_rollback_when_material_move_fails(client, monkeypatch):
    ah, h, cid = ready(client)
    near(cid, "alchemist")
    cash_inject(client, ah, "player:" + str(cid), small=100)
    offer = q(client, h, "alchemist", 1, "weak_healing_potion")
    from app import guild_commerce

    def abort(*args, **kwargs):
        raise HTTPException(409, "rollback stock")

    monkeypatch.setattr(guild_commerce, "transfer_item", abort)
    response = buy(client, h, "alchemist", offer)
    assert response.status_code == 409
    assert counts("alchemist")["weak_healing_potion"] == 1
    with Session() as db:
        assert finance.coin_mg(db, "player:" + str(cid)) == 100000
        assert finance.coin_mg(db, "npc:alchemist") == 0
    invariant()


def test_near_service_inventory_capacity_ownership_and_legacy_bypass(
    client, monkeypatch
):
    ah, h, cid = ready(client)
    cash_inject(client, ah, "player:" + str(cid), small=500)
    offer = q(client, h, "alchemist", 1, "weak_healing_potion")
    assert buy(client, h, "alchemist", offer).status_code == 409
    near(cid, "alchemist")
    from app.config import settings

    monkeypatch.setattr(settings, "collection_slots", 1)
    assert buy(client, h, "alchemist", offer).status_code == 409
    with Session() as db:
        identity = npc.stock(db, "npc:alchemist", "weak_healing_potion")[0][0].id
    assert (
        client.post(
            "/economy/shop/buy",
            headers=h,
            json={"item_id": identity, "quote": "0" * 64, "request_id": str(uuid4())},
        ).status_code
        == 409
    )
    assert counts("alchemist")["weak_healing_potion"] == 1
    invariant()


def test_market_and_npc_history_are_immutable(client):
    ready(client)
    cycle()
    from sqlalchemy.exc import DBAPIError

    with Session() as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE market_revisions SET reason='tamper'"))
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM world_events WHERE kind='NPC_PRODUCTION'"))
        db.rollback()
    invariant()


def test_observation_is_pure_and_partial_restock_never_overfills(client):
    ah, h, cid = ready(client)
    with Session() as db:
        before = db.scalar(select(func.count()).select_from(m.WorldEvent))
    for _ in range(3):
        assert client.get("/economy/npcs", headers=h).status_code == 200
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.WorldEvent)) == before
    assert counts("alchemist")["herb"] == 7
    configure(
        client,
        ah,
        "alchemist",
        production_enabled=False,
        policies=[
            {"definition_id": "herb", "expected_revision": 1, "order_quantity": 20}
        ],
    )
    with Session.begin() as db:
        npc.give(db, "npc:merchant", "herb", 40)
    cash_inject(client, ah, "npc:alchemist", small=500)
    cycle()
    assert (
        counts("alchemist")["herb"] == 7
    )  # 7+20 exceeds capacity20; no hidden truncation or overflow
    with Session() as db:
        assert (
            db.get(m.NpcInventoryPolicy, ("alchemist", "herb")).status
            == "WAIT_CAPACITY"
        )
    invariant()


def test_shop_purchase_and_worker_cycle_serialize_without_duplicate_items(client):
    ah, h, cid = ready(client)
    near(cid, "alchemist")
    cash_inject(client, ah, "player:" + str(cid), small=100)
    offer = q(client, h, "alchemist", 1, "weak_healing_potion")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(buy, client, h, "alchemist", offer)
        b = pool.submit(cycle)
        response, result = a.result(), b.result()
    assert response.status_code in (200, 409)
    s = state(client, h)
    owned = sum(
        i["quantity"]
        for i in s["inventory"]
        if i["definition"] == "weak_healing_potion"
    )
    produced = sum(
        e["quantity"]
        for e in result["production"]
        if e["definition"] == "weak_healing_potion"
    )
    assert counts("alchemist")["weak_healing_potion"] + owned == 1 + produced
    assert counts("alchemist")["weak_healing_potion"] <= 2 and owned <= 1
    invariant()


def test_legacy_admin_stock_writer_cannot_bypass_new_npc_capacity(client):
    ah, h, cid = ready(client)
    identity = item(cid, 21, "herb")
    p = proposal(
        client,
        ah,
        "npc.stock",
        str(identity),
        {"account_id": "npc:alchemist", "price_weight_mg": "1000"},
    )
    assert p.status_code == 409 and "Capacidade" in p.text
    assert counts("alchemist")["herb"] == 7
    invariant()


def test_all_three_services_are_reachable_by_real_movement_and_interaction(client):
    ah, h, cid = ready(client)
    navigate(client, h, "city1")
    for service in npc.SERVICES:
        walk_tiles(client, h, (service["x"], service["y"]))
        response = client.post(
            "/economy/npcs/" + service["id"] + "/interact", headers=h, json={}
        )
        assert (
            response.status_code == 200
            and response.json()["open_npc_shop"] == service["id"]
        )


def test_autonomous_operations_emit_structured_logs_but_idle_does_not_spam(
    client, caplog
):
    import json

    ready(client)
    caplog.clear()
    now = utc_now()
    cycle(now)
    messages = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "dungeon.npc_economy"
    ]
    assert any(
        r["event"] == "npc_production" and r["npc"] == "alchemist" and r["event_key"]
        for r in messages
    )
    assert all("password" not in r and "token" not in r for r in messages)
    caplog.clear()
    cycle(now + timedelta(minutes=2))
    assert not [r for r in caplog.records if r.name == "dungeon.npc_economy"]
