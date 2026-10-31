from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from test_game import clean, client, state, player, navigate, walk_tiles
from test_cutover import fresh_lunar
from test_physical_commerce import ready, config, cash_inject, item
from test_royal_lots import invariant
from test_admin_migration import execute, proposal, commit
from app import models as m, lunar, finance, guild_catalog as catalog
from app.database import Session
from app.config import settings


def view(client, h):
    return client.get("/economy/shop/catalog", headers=h).json()


def quote(client, h, qty, direction="sell", definition="herb", item_id=None):
    r = client.post(
        "/economy/shop/catalog/quote",
        headers=h,
        json={
            "definition_id": definition if item_id is None else None,
            "item_id": item_id,
            "quantity": qty,
            "operation_type": direction,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def trade(client, h, q, id=None):
    return client.post(
        "/economy/shop/catalog/trade",
        headers=h,
        json={
            k: q[k] for k in ["definition_id", "item_id", "quantity", "operation_type"]
        }
        | {"quote": q["quote_hash"], "request_id": id or str(uuid4())},
    )


def revision(definition):
    with Session() as db:
        return db.get(m.GuildItemPolicy, definition).revision


def test_maximum_exact_quantity_matches_exhaustive_physical_combinations():
    for g, middle, small in product(range(4), range(4), range(8)):
        available = {"coin_large": g, "coin_medium": middle, "coin_small": small}
        reachable = {
            a * 10 + b * 5 + c
            for a, b, c in product(range(g + 1), range(middle + 1), range(small + 1))
        }
        for price in range(1, 26):
            for limit in [0, 1, 7, 25, 1000]:
                expected = max(
                    [0]
                    + [
                        q
                        for q in range(min(limit, max(reachable) // price) + 1)
                        if price * q in reachable
                    ]
                )
                assert (
                    catalog.maximum_exact_quantity(available, price, limit) == expected
                )
    assert catalog.maximum_exact_quantity({"coin_large": 2}, 19, 100) == 0
    assert catalog.maximum_exact_quantity({"coin_large": 2}, 0, 12345) == 12345


def test_aggregated_real_stock_above_99_and_no_catalog_money_writes(client):
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
    for n in [99] * 30 + [30]:
        item(cid, n, "herb", guild=True)
    with Session() as db:
        before = db.scalar(select(func.count()).select_from(m.LunarEntry))
    for _ in range(3):
        cards = [r for r in view(client, h)["buy"] if r["definition_id"] == "herb"]
        assert len(cards) == 1 and cards[0]["quantity"] == "3000"
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.LunarEntry)) == before
        assert (
            db.scalar(
                select(func.sum(m.Item.quantity))
                .join(m.NPCStock, m.NPCStock.item_id == m.Item.id)
                .where(m.Item.definition == "herb")
            )
            == 3000
        )
    invariant()


def test_sell_all_multi_stack_receipt_atomic_and_protected_excluded(client):
    ah, h, cid = ready(client)
    config(client, ah, "herb", buy_price_units=1, buy_enabled=True)
    for n in [99, 99, 42]:
        item(cid, n, "herb")
    protected = item(cid, 99, "herb")
    with Session.begin() as db:
        db.get(m.Item, protected).equipped = True
    cards = view(client, h)["sell"]
    herb = next(r for r in cards if r["definition_id"] == "herb")
    assert herb["maximum_quantity"] == "240" and herb["quantity"] == "240"
    assert not any(r["item_id"] == protected for r in cards)
    cash_inject(client, ah, "guild", 24)
    offer = quote(client, h, 240)
    assert offer["total_price_units"] == "240" and len(offer["selection"]) == 3
    req = str(uuid4())
    r = trade(client, h, offer, req)
    assert r.status_code == 200, r.text
    assert trade(client, h, offer, req).json()["replayed"]
    assert (
        next(r for r in view(client, h)["buy"] if r["definition_id"] == "herb")[
            "quantity"
        ]
        == "240"
    )
    with Session() as db:
        assert db.get(m.Item, protected).owner == cid
        assert finance.coin_mg(db, f"player:{cid}") == 240000
        assert (
            db.scalar(
                select(func.sum(m.Item.quantity))
                .join(m.NPCStock, m.NPCStock.item_id == m.Item.id)
                .where(m.Item.definition == "herb")
            )
            == 240
        )
    invariant()


def test_buy_large_guild_stack_splits_player_inventory_and_maximum_capacity(
    client, monkeypatch
):
    ah, h, cid = ready(client)
    config(client, ah, "herb", buy_price_units=1, sell_price_units=2, sell_enabled=True)
    original = item(cid, 12438, "herb", guild=True)
    cash_inject(client, ah, f"player:{cid}", 1000, 10, 10)
    monkeypatch.setattr(settings, "collection_slots", 5)
    card = next(r for r in view(client, h)["buy"] if r["definition_id"] == "herb")
    assert card["quantity"] == "12438" and card["maximum_quantity"] == "297"
    r = trade(client, h, quote(client, h, 250, "buy"))
    assert r.status_code == 200, r.text
    with Session() as db:
        own = list(
            db.scalars(
                select(m.Item).where(
                    m.Item.owner == cid,
                    m.Item.location == "inventory",
                    m.Item.definition == "herb",
                )
            )
        )
        assert sorted(i.quantity for i in own) == [52, 99, 99]
        assert db.get(m.Item, original).quantity == 12188 and db.get(
            m.NPCStock, original
        )
    card = next(r for r in view(client, h)["buy"] if r["definition_id"] == "herb")
    assert card["maximum_quantity"] == "47"
    fail = trade(client, h, quote(client, h, 48, "buy"))
    assert fail.status_code == 409 and "Mochila" in fail.text
    invariant()


def test_maximum_stock_money_denominations_capacity_and_free_price(client, monkeypatch):
    ah, h, cid = ready(client)
    config(client, ah, "herb", sell_price_units=19, sell_enabled=True)
    item(cid, 50, "herb", guild=True)
    cash_inject(client, ah, f"player:{cid}", 2)
    assert view(client, h)["buy"][0]["maximum_quantity"] == "0"
    config(client, ah, "herb", sell_price_units=10, sell_enabled=True)
    assert view(client, h)["buy"][0]["maximum_quantity"] == "2"
    config(
        client,
        ah,
        "herb",
        sell_price_units=0,
        sell_enabled=True,
        acknowledge_free=True,
        acknowledge_arbitrage=True,
    )
    monkeypatch.setattr(settings, "collection_slots", 3)
    assert view(client, h)["buy"][0]["maximum_quantity"] == "50"
    r = trade(client, h, quote(client, h, 50, "buy"))
    assert r.status_code == 200, r.text
    with Session() as db:
        assert finance.coin_mg(db, f"player:{cid}") == 20000
    assert not view(client, h)["buy"]
    invariant()


def test_aggregate_stale_price_stock_ownership_overflow_and_rollback(
    client, monkeypatch
):
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
    item(cid, 10, "herb")
    cash_inject(client, ah, "guild", 0, 0, 10)
    old = quote(client, h, 10)
    config(client, ah, "herb", buy_price_units=2)
    assert "STALE_QUOTE" in trade(client, h, old).text
    another = player(client, "outsider")
    assert (
        client.post(
            "/economy/shop/catalog/quote",
            headers=another,
            json={"definition_id": "herb", "quantity": 1, "operation_type": "sell"},
        ).status_code
        == 409
    )
    for q in [True, 1.5, 0, -1, 9007199254740992]:
        assert (
            client.post(
                "/economy/shop/catalog/quote",
                headers=h,
                json={"definition_id": "herb", "quantity": q, "operation_type": "sell"},
            ).status_code
            == 422
        )
    offer = quote(client, h, 5)
    from app import lunar_resources

    def abort(db):
        raise HTTPException(409, "Forced audit rollback")

    monkeypatch.setattr(lunar_resources, "assert_audit", abort)
    assert trade(client, h, offer).status_code == 409
    with Session() as db:
        assert finance.coin_mg(db, "guild") == 10000
        assert (
            db.scalar(
                select(func.sum(m.Item.quantity)).where(
                    m.Item.owner == cid, m.Item.definition == "herb"
                )
            )
            == 10
        )


def test_concurrent_aggregate_buy_and_request_replay(client):
    ah, h, cid = ready(client)
    config(client, ah, "herb", buy_price_units=1, sell_price_units=1, sell_enabled=True)
    item(cid, 99, "herb", guild=True)
    item(cid, 1, "herb", guild=True)
    cash_inject(client, ah, f"player:{cid}", 20)
    offer = quote(client, h, 100, "buy")
    req = str(uuid4())
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(lambda _: trade(client, h, offer, req), range(3)))
    assert (
        all(r.status_code == 200 for r in results)
        and sum(r.json()["replayed"] for r in results) == 2
    )
    with Session() as db:
        assert (
            db.scalar(
                select(func.sum(m.Item.quantity)).where(
                    m.Item.owner == cid,
                    m.Item.definition == "herb",
                    m.Item.location == "inventory",
                )
            )
            == 100
        )
        assert finance.coin_mg(db, f"player:{cid}") == 100000
    assert trade(client, h, offer).status_code == 409
    invariant()


def test_equipment_identity_never_aggregates(client):
    ah, h, cid = ready(client)
    with Session.begin() as db:
        db.add(
            m.ItemDefinition(
                id="iron",
                name="Ferro de teste",
                kind="weapon",
                power=2,
                stackable=False,
                max_stack_size=1,
                death_transferable=True,
            )
        )
    ids = [item(cid, 1, "iron", guild=True) for _ in range(2)]
    config(client, ah, "iron", sell_price_units=1, sell_enabled=True)
    cash_inject(client, ah, f"player:{cid}", 0, 0, 1)
    cards = view(client, h)["buy"]
    assert len(cards) == 2 and {c["item_id"] for c in cards} == set(ids)
    r = trade(client, h, quote(client, h, 1, "buy", item_id=ids[0]))
    assert r.status_code == 200, r.text
    with Session() as db:
        assert (
            db.get(m.Item, ids[0]).owner == cid and db.get(m.Item, ids[1]).owner is None
        )
    invariant()


def changes():
    return [
        {
            "definition_id": "herb",
            "expected_revision": revision("herb"),
            "buy_price_units": 1,
            "sell_price_units": 2,
            "buy_enabled": True,
            "sell_enabled": True,
        },
        {
            "definition_id": "ore",
            "expected_revision": revision("ore"),
            "buy_price_units": 2,
            "sell_price_units": 4,
            "buy_enabled": True,
            "sell_enabled": True,
        },
    ]


def test_batch_prices_two_items_individual_history_reason_and_replay(client):
    ah, h, cid = ready(client)
    p = proposal(client, ah, "guild.batch_prices", "guild", {"changes": changes()})
    assert p.status_code == 200, p.text
    result = commit(client, ah, p)
    assert result.status_code == 200, result.text
    assert commit(client, ah, p).json()["replayed"]
    with Session() as db:
        rows = list(
            db.scalars(
                select(m.GuildPriceHistory).where(
                    m.GuildPriceHistory.request_id == p.json()["id"]
                )
            )
        )
        assert len(rows) == 2 and {r.policy_key for r in rows} == {"herb", "ore"}
        assert all(
            r.actor_id
            and len(r.reason) >= 10
            and r.after["revision"] == r.before["revision"] + 1
            for r in rows
        )
        assert db.get(m.GuildItemPolicy, "herb").sell_price_units == 2
        assert db.get(m.GuildItemPolicy, "ore").buy_price_units == 2
    # Individual save remains available and changes only the requested side.
    old = revision("herb")
    config(client, ah, "herb", buy_price_units=2, expected_revision=old)
    with Session() as db:
        assert db.get(m.GuildItemPolicy, "herb").sell_price_units == 2
    invariant()


def test_batch_conflict_rollback_and_permission_preserve_other_policies(
    client, monkeypatch
):
    ah, h, cid = ready(client)
    edits = changes()
    p = proposal(client, ah, "guild.batch_prices", "guild", {"changes": edits})
    config(client, ah, "herb", buy_price_units=3)
    r = commit(client, ah, p)
    assert r.status_code == 409 and "STALE_BATCH" in r.text
    with Session() as db:
        assert db.get(m.GuildItemPolicy, "ore").buy_price_units == 8
    assert (
        proposal(
            client, h, "guild.batch_prices", "guild", {"changes": changes()}
        ).status_code
        == 401
    )
    from app import guild_admin

    original = guild_admin.set_prices

    def fail_second(db, actor, op, key, params):
        if key == "ore":
            raise HTTPException(409, "abort whole batch")
        return original(db, actor, op, key, params)

    monkeypatch.setattr(guild_admin, "set_prices", fail_second)
    new = proposal(client, ah, "guild.batch_prices", "guild", {"changes": changes()})
    assert commit(client, ah, new).status_code == 409
    with Session() as db:
        assert db.get(m.GuildItemPolicy, "herb").buy_price_units == 3
        assert not list(
            db.scalars(
                select(m.GuildPriceHistory).where(
                    m.GuildPriceHistory.request_id == new.json()["id"]
                )
            )
        )
    invariant()


def test_price_warnings_only_for_active_risks_and_batch_duplicate_guard(client):
    ah, h, cid = ready(client)
    for params, warning in [
        (
            {
                "buy_price_units": 10,
                "sell_price_units": 8,
                "buy_enabled": True,
                "sell_enabled": True,
            },
            "POSSIBLE_ARBITRAGE",
        ),
        ({"buy_price_units": 0, "buy_enabled": True}, "ZERO_PRICE"),
    ]:
        assert warning in proposal(client, ah, "guild.item_prices", "herb", params).text
    # Zero prices on disabled operations need no free acknowledgement.
    config(
        client,
        ah,
        "herb",
        buy_price_units=0,
        sell_price_units=0,
        buy_enabled=False,
        sell_enabled=False,
    )
    execute(
        client,
        ah,
        "guild.mineral_prices",
        "mineral",
        {
            "lunar_guild_buy_enabled": False,
            "lunar_guild_sell_enabled": False,
            "lunar_guild_allow_zero_price": True,
        },
    )
    duplicated = changes()
    duplicated.append(duplicated[0])
    assert (
        proposal(
            client, ah, "guild.batch_prices", "guild", {"changes": duplicated}
        ).status_code
        == 422
    )
    invariant()


def test_recovery_city_tent_proximity_and_old_guild_edges_removed(client):
    ah, h, cid = ready(client)
    navigate(client, h, "city1")
    s = state(client, h)
    assert s["map"]["npc"] == [5, 30] and s["map"]["npc_role"] == "recovery"
    assert any(d["kind"] == "recovery_tent" for d in s["map"]["decorations"])
    assert client.post("/interact", headers=h, json={}).status_code == 409
    walk_tiles(client, h, (5, 30))
    r = client.post("/interact", headers=h, json={})
    assert r.status_code == 200 and r.json()["open_recovery"]
    assert (
        not any(d["id"] == "recovery_hall" for d in s["fast_travel"])
        if "fast_travel" in s
        else True
    )
    with Session() as db:
        from app.rooms import room_payload

        guild = db.get(m.Character, cid)
        guild.room_id = "guild"
        payload, _ = room_payload(db, guild)
        assert len(payload["exits"]) == 3
    invariant()


def test_batch_concurrent_confirm_same_revision_has_one_winner(client):
    ah, h, cid = ready(client)
    p = proposal(client, ah, "guild.batch_prices", "guild", {"changes": changes()})
    other = proposal(client, ah, "guild.batch_prices", "guild", {"changes": changes()})
    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(
            workers.map(lambda candidate: commit(client, ah, candidate), [p, other])
        )
    assert sorted(r.status_code for r in responses) == [200, 409]
    with Session() as db:
        ids = [p.json()["id"], other.json()["id"]]
        rows = list(
            db.scalars(
                select(m.GuildPriceHistory).where(
                    m.GuildPriceHistory.request_id.in_(ids)
                )
            )
        )
        assert len(rows) == 2 and len({r.request_id for r in rows}) == 1
    invariant()


def test_recovery_historical_fast_travel_redirect_and_batch_reason_validation(client):
    ah, h, cid = ready(client)
    navigate(client, h, "city1")
    response = client.post(
        "/fast-travel", headers=h, json={"destination": "recovery_hall"}
    )
    # Historical clients keep a valid destination; no entry into the archived room.
    assert response.status_code == 200, response.text
    s = state(client, h)
    assert s["room"]["id"] == "city1" and [
        s["character"]["x"],
        s["character"]["y"],
    ] == [5, 31]
    assert client.post("/interact", headers=h, json={}).json()["open_recovery"]
    r = client.post(
        "/admin/operations/preview",
        headers=ah,
        json={
            "operation_id": str(uuid4()),
            "action": "guild.batch_prices",
            "target": "guild",
            "params": {"changes": changes()},
            "reason": "curta",
        },
    )
    assert r.status_code == 422
    invariant()
