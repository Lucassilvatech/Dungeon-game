from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from test_game import clean, client, state, player
from test_cutover import fresh_lunar, convert, wallet_fixture
from test_admin_migration import admin, proposal, commit, execute
from test_lunar_resources import at_guild
from test_royal_lots import injection, invariant
from app import (
    models as m,
    lunar,
    finance,
    guild_admin,
    guild_commerce as commerce,
    mineral_lots as lots,
)
from app.database import Session


def ready(client):
    ah, h = admin(client)
    cid = state(client, h)["character"]["id"]
    convert()
    at_guild(client, h)
    return ah, h, cid


def cash_inject(client, ah, owner, large=0, medium=0, small=0):
    execute(
        client,
        ah,
        "royal.injection",
        owner,
        {
            "coins": {"coin_large": large, "coin_medium": medium, "coin_small": small},
            "grams": 0,
            "strong_confirmation": "INJETAR",
        },
    )


def config(client, ah, definition="crystal", **params):
    return execute(client, ah, "guild.item_prices", definition, params)


def item(cid, qty=1, definition="crystal", guild=False):
    with Session.begin() as db:
        row = m.Item(
            owner=None if guild else cid,
            definition=definition,
            quantity=qty,
            location="npc" if guild else "inventory",
        )
        db.add(row)
        db.flush()
        if guild:
            db.add(m.NPCStock(item_id=row.id, account_id="guild", sale_weight_mg=0))
        return row.id


def q(client, h, i, qty=1, op="sell"):
    r = client.post(
        "/economy/shop/quote",
        headers=h,
        json={"item_id": i, "quantity": qty, "operation_type": op},
    )
    assert r.status_code == 200, r.text
    return r.json()


def trade(client, h, offer, request_id=None):
    return client.post(
        "/economy/shop/" + offer["operation_type"],
        headers=h,
        json={
            "item_id": offer["item_id"],
            "quantity": offer["quantity"],
            "quote": offer["quote_hash"],
            "request_id": request_id or str(uuid4()),
        },
    )


@pytest.mark.parametrize(
    "available,units,expected",
    [
        ({"coin_large": 10, "coin_medium": 10, "coin_small": 20}, n, e)
        for n, e in [
            (10, {"coin_large": 1}),
            (15, {"coin_large": 1, "coin_medium": 1}),
            (17, {"coin_large": 1, "coin_medium": 1, "coin_small": 2}),
            (19, {"coin_large": 1, "coin_medium": 1, "coin_small": 4}),
            (27, {"coin_large": 2, "coin_medium": 1, "coin_small": 2}),
            (100, {"coin_large": 10}),
        ]
    ]
    + [
        ({"coin_medium": 4, "coin_small": 20}, 19, {"coin_medium": 3, "coin_small": 4}),
        ({"coin_large": 1, "coin_small": 20}, 19, {"coin_large": 1, "coin_small": 9}),
    ],
)
def test_exact_bounded_selection(available, units, expected):
    assert (
        lunar.select_coins(
            available,
            {"coin_large": 10000, "coin_medium": 5000, "coin_small": 1000},
            units * 1000,
        )
        == expected
    )


def test_non_normalization_receipt_and_exact_transfer(client):
    ah, h, cid = ready(client)
    owner = f"player:{cid}"
    cash_inject(client, ah, owner, 72, 1, 2)
    cash_inject(client, ah, "guild", 0, 0, 3)
    with Session.begin() as db:
        before = finance.coin_mg(db, "guild")
        e = finance.move(db, "guild", owner, 3, "regression730")
        finance.move(db, "guild", owner, 3, "regression730")
        assert e.context["coins_transferred"] == {"coin_small": 3}
        assert lunar.balances(db, owner) == {
            "coin_large": 72,
            "coin_medium": 1,
            "coin_small": 5,
        }
        assert finance.coin_mg(db, "guild") == before - 3000
        assert finance.coin_mg(db, owner) == 730000
    wallet = client.get("/lunar/wallet", headers=h).json()
    assert wallet["coin_total_weight_mg"] == "730000"
    with Session.begin() as db:
        lunar.transfer(
            db,
            owner,
            "guild",
            {"coin_large": 3, "coin_medium": 1, "coin_small": 2},
            "transferpieces",
        )
        assert lunar.balances(db, "guild") == {
            "coin_large": 3,
            "coin_medium": 1,
            "coin_small": 2,
        }
    invariant()


def test_insufficient_denominations_rolls_back_then_explicit_exchange(client):
    ah, h, cid = ready(client)
    cash_inject(client, ah, "guild", 5)
    with pytest.raises(HTTPException, match="") as error:
        with Session.begin() as db:
            finance.move(db, "guild", f"player:{cid}", 1, "nochange")
    assert "INSUFFICIENT_DENOMINATIONS" in str(error.value.detail)
    with Session.begin() as db:
        assert lunar.balances(db, "guild") == {"coin_large": 5}
    op = execute(
        client,
        ah,
        "royal.exchange",
        "guild",
        {"inputs": {"coin_large": 1}, "outputs": {"coin_small": 10}},
    )
    with Session.begin() as db:
        finance.move(db, "guild", f"player:{cid}", 1, "afterexchange")
        assert lunar.balances(db, "guild") == {"coin_large": 4, "coin_small": 9}
    # Cannot claim non-existent input canceled by an output of the same asset.
    bad = proposal(
        client,
        ah,
        "royal.exchange",
        "guild",
        {"inputs": {"coin_large": 5}, "outputs": {"coin_large": 4, "coin_small": 10}},
    )
    assert commit(client, ah, bad).status_code == 409
    invariant()


def test_mint_requested_denominations_persist_and_exchange_idempotent(client):
    ah, h, cid = ready(client)
    injection(client, ah, "treasury", 1450)
    execute(
        client,
        ah,
        "royal.mint",
        "treasury",
        {"coins": {"coin_large": 100, "coin_medium": 50, "coin_small": 200}},
    )
    with Session() as db:
        b = lunar.balances(db, "treasury")
        assert b["coin_medium"] == 50 and b["coin_small"] == 200
    p = proposal(
        client,
        ah,
        "royal.exchange",
        "treasury",
        {"inputs": {"coin_large": 1}, "outputs": {"coin_medium": 2}},
    )
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    invariant()


@pytest.mark.parametrize("units", [0, 1, 3, 7, 10, 11, 17, 100, 19498, 10**12])
def test_rebalance_mass_algorithm(units):
    r = guild_admin.rebalance_denominations(units * 1000)
    assert sum(r["weights_mg"].values()) == units * 1000
    if units == 19498:
        assert r["quantities"] == {
            "coin_large": 1365,
            "coin_medium": 780,
            "coin_small": 1948,
        }


def test_guild_initial_rebalance_fingerprint_replay_and_manual(client):
    ah, h, cid = ready(client)
    cash_inject(client, ah, "guild", 1949, 1, 3)
    p = proposal(client, ah, "guild.rebalance", "guild", {"initial": True})
    assert p.status_code == 200, p.text
    assert len(p.json()["before"]["fingerprint"]) == 64
    treasury = client.get("/admin/royal/accounts/treasury/details", headers=ah).json()
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    with Session() as db:
        assert lunar.balances(db, "guild") == {
            "coin_large": 1365,
            "coin_medium": 780,
            "coin_small": 1948,
        }
        supply = db.get(m.LunarSupply, 1)
        assert supply.minted_mg == 0
    assert (
        client.get("/admin/royal/accounts/treasury/details", headers=ah).json()
        == treasury
    )
    cash_inject(client, ah, "guild", 0, 0, 1)
    # V1 does not become a recurring policy, even after cash changes.
    r = execute(client, ah, "guild.rebalance", "guild", {"initial": True})
    assert r["before"]["status"] == "ALREADY_REBALANCED"
    stale = proposal(client, ah, "guild.rebalance", "guild", {"initial": False})
    cash_inject(client, ah, "guild", 0, 0, 1)
    assert "STALE_PREVIEW" in commit(client, ah, stale).text
    execute(client, ah, "guild.rebalance", "guild", {"initial": False})
    invariant()


def test_bidirectional_item_prices_physical_cash_stock_and_stack(client):
    ah, h, cid = ready(client)
    cash_inject(client, ah, "guild", 10, 10, 10)
    config(
        client,
        ah,
        buy_price_units=17,
        sell_price_units=19,
        buy_enabled=True,
        sell_enabled=True,
    )
    i = item(cid, 10)
    quote = q(client, h, i, 1)
    assert quote["payment"]["coins"] == {
        "coin_large": "1",
        "coin_medium": "1",
        "coin_small": "2",
    }
    request = str(uuid4())
    r = trade(client, h, quote, request)
    assert r.status_code == 200, r.text
    assert trade(client, h, quote, request).json()["replayed"]
    sold = r.json()["item_id"]
    with Session() as db:
        assert db.get(m.Item, i).quantity == 9
        assert db.get(m.NPCStock, sold).account_id == "guild"
        assert lunar.balances(db, f"player:{cid}") == {
            "coin_large": 1,
            "coin_medium": 1,
            "coin_small": 2,
        }
    cash_inject(client, ah, f"player:{cid}", 0, 0, 3)
    bought = trade(client, h, q(client, h, sold, 1, "buy"))
    assert bought.status_code == 200, bought.text
    with Session() as db:
        assert not db.get(m.NPCStock, sold)
        assert (
            db.scalar(
                select(func.sum(m.Item.quantity)).where(
                    m.Item.owner == cid,
                    m.Item.definition == "crystal",
                    m.Item.location == "inventory",
                )
            )
            == 10
        )
        assert finance.coin_mg(db, f"player:{cid}") == 0
    invariant()


def test_prices_version_flags_zero_arbitrage_and_history(client):
    ah, h, cid = ready(client)
    i = item(cid)
    config(
        client,
        ah,
        buy_price_units=8,
        sell_price_units=13,
        buy_enabled=True,
        sell_enabled=True,
    )
    old = q(client, h, i)
    config(client, ah, buy_price_units=9)
    config(client, ah, buy_price_units=8)
    assert "STALE_QUOTE" in trade(client, h, old).text
    config(client, ah, buy_enabled=False)
    assert "GUILD_BUY_DISABLED" in trade(client, h, q(client, h, i)).text
    bad = proposal(
        client,
        ah,
        "guild.item_prices",
        "crystal",
        {"buy_price_units": 10, "sell_price_units": 8, "buy_enabled": True},
    )
    assert bad.status_code == 422 and "POSSIBLE_ARBITRAGE" in bad.text
    accepted = execute(
        client,
        ah,
        "guild.item_prices",
        "crystal",
        {
            "buy_price_units": 10,
            "sell_price_units": 8,
            "buy_enabled": True,
            "acknowledge_arbitrage": True,
        },
    )
    assert "POSSIBLE_ARBITRAGE" in accepted["before"]["warnings"]
    zero = proposal(
        client,
        ah,
        "guild.item_prices",
        "crystal",
        {"buy_price_units": 0, "sell_price_units": 0},
    )
    assert zero.status_code == 422 and "ZERO_PRICE" in zero.text
    config(client, ah, buy_price_units=0, sell_price_units=0, acknowledge_free=True)
    # A zero price is enabled, not implicitly disabled; no cash needs inventing.
    response = trade(client, h, q(client, h, i))
    assert response.status_code == 200, response.text
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.GuildPriceHistory)) == 6
        assert db.get(m.GuildItemPolicy, "crystal").sell_price_units == 0
    invariant()


def test_stock_ownership_equipment_protected_capacity_and_no_change(
    client, monkeypatch
):
    ah, h, cid = ready(client)
    config(
        client,
        ah,
        buy_price_units=17,
        sell_price_units=18,
        buy_enabled=True,
        sell_enabled=True,
    )
    cash_inject(client, ah, f"player:{cid}", 2)
    stock = item(cid, guild=True)
    qbuy = q(client, h, stock, 1, "buy")
    failed = trade(client, h, qbuy)
    assert failed.status_code == 409 and "INSUFFICIENT_DENOMINATIONS" in failed.text
    with Session() as db:
        assert (
            db.get(m.NPCStock, stock) and finance.coin_mg(db, f"player:{cid}") == 20000
        )
    cash_inject(client, ah, "guild", 5)
    own = item(cid)
    assert "INSUFFICIENT_DENOMINATIONS" in trade(client, h, q(client, h, own)).text
    with Session.begin() as db:
        db.get(m.Item, own).equipped = True
    assert (
        client.post(
            "/economy/shop/quote",
            headers=h,
            json={"item_id": own, "quantity": 1, "operation_type": "sell"},
        ).status_code
        == 409
    )
    sword = next(i for i in state(client, h)["inventory"] if i["definition"] == "sword")
    assert (
        client.post(
            "/economy/shop/quote",
            headers=h,
            json={"item_id": sword["id"], "quantity": 1, "operation_type": "sell"},
        ).status_code
        == 409
    )
    with Session.begin() as db:
        db.get(m.Item, stock).location = "destroyed"
        db.delete(db.get(m.NPCStock, stock))
    assert "OUT_OF_STOCK" in trade(client, h, qbuy).text
    invariant()


def test_guild_concurrent_sale_single_stock_and_price_preview_rollback(
    client, monkeypatch
):
    ah, h, cid = ready(client)
    config(
        client,
        ah,
        buy_price_units=1,
        sell_price_units=1,
        buy_enabled=True,
        sell_enabled=True,
    )
    cash_inject(client, ah, f"player:{cid}", 0, 0, 5)
    i = item(cid, guild=True)
    offer = q(client, h, i, 1, "buy")
    with ThreadPoolExecutor(3) as pool:
        r = list(pool.map(lambda _: trade(client, h, offer), range(3)))
    assert sum(x.status_code == 200 for x in r) == 1
    stale = proposal(
        client,
        ah,
        "guild.item_prices",
        "crystal",
        {"buy_price_units": 2, "acknowledge_arbitrage": True},
    )
    config(client, ah, sell_enabled=False)
    assert "STALE_PREVIEW" in commit(client, ah, stale).text
    # Fail after material/payment writes: transaction must restore both.
    i = item(cid, guild=True)
    config(client, ah, sell_enabled=True)
    offer = q(client, h, i, 1, "buy")
    from app import lunar_resources

    def fail_audit(db):
        raise HTTPException(409, "Injected audit failure")

    monkeypatch.setattr(lunar_resources, "assert_audit", fail_audit)
    assert trade(client, h, offer).status_code == 409
    with Session() as db:
        assert db.get(m.NPCStock, i)


def test_mineral_bidirectional_whole_lot_rates_flags_and_liquidity(client):
    ah, h, cid = ready(client)
    id = injection(client, ah, f"player:{cid}", 684)
    cash_inject(client, ah, "guild", 100, 10, 20)
    offers = client.get("/lunar/guild-quotes", headers=h).json()
    q0 = next(r for r in offers["quotes"] if r["lot_id"] == id)
    assert q0["price_units"] == "547"
    r = client.post(
        "/lunar/guild-sell",
        headers=h,
        json={"lot_id": id, "quote": q0["quote_hash"], "request_id": str(uuid4())},
    )
    assert r.status_code == 200, r.text
    execute(
        client,
        ah,
        "guild.mineral_prices",
        "mineral",
        {
            "lunar_guild_sell_rate_milliunits_per_gram": 900,
            "lunar_guild_sell_enabled": True,
        },
    )
    offers = client.get("/lunar/guild-quotes", headers=h).json()
    offer = next(r for r in offers["guild_quotes"] if r["lot_id"] == id)
    assert offer["price_units"] == "615" and offer["weight_g"] == 684
    cash_inject(client, ah, f"player:{cid}", 10, 10, 10)
    body = {"lot_id": id, "quote": offer["quote_hash"], "request_id": str(uuid4())}
    r = client.post("/lunar/guild-buy", headers=h, json=body)
    assert r.status_code == 200, r.text
    assert client.post("/lunar/guild-buy", headers=h, json=body).json()["replayed"]
    with Session() as db:
        assert db.get(m.LunarMineralLot, id).owner_account_id == f"player:{cid}"
        assert db.get(m.LunarMineralLot, id).weight_mg == 684000
    invariant()


def test_partial_forced_fee_and_automatic_debt_without_breaking_coins(client):
    ah, h, cid = ready(client)
    cash_inject(client, ah, f"player:{cid}", 3)
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        f = finance.fee(db, c, 100, "fee:physical")
        assert f["paid"] == 30 and f["newly_financed"] == 70
        finance.move(db, "treasury", f"player:{cid}", 70, "repayphysical")
        assert finance.debt_mg(db, c) == 0
    cash_inject(client, ah, f"player:{cid}", 1)
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        f = finance.fee(db, c, 7, "fee:indivisible")
        assert f["paid"] == 0 and f["newly_financed"] == 7
        # A received 10g piece cannot be broken to settle the remaining 7g.
        finance.move(db, "treasury", f"player:{cid}", 10, "repaycannotbreak")
        assert finance.debt_mg(db, c) == 7000
    invariant()


def test_admin_permissions_and_history_immutable(client):
    ah, h, cid = ready(client)
    config(client, ah, buy_price_units=8)
    assert proposal(client, h, "guild.rebalance", "guild").status_code == 401
    with Session.begin() as db:
        account = db.get(m.Character, cid).account_id
        db.get(m.AdminRole, account).role = "observer"
    assert proposal(client, ah, "guild.rebalance", "guild").status_code == 403
    assert client.get("/admin/guild/commerce", headers=ah).status_code == 200
    with pytest.raises(DBAPIError):
        with Session.begin() as db:
            db.execute(text("UPDATE guild_price_history SET reason='tamper'"))


def test_auction_escrow_outbid_and_settlement_keep_actual_pieces(client):
    from app import auctions
    from datetime import timedelta
    from app.clock import utc_now

    ah, h, cid = ready(client)
    hb = player(client, "bidder")
    cb = state(client, hb)["character"]["id"]
    cash_inject(client, ah, f"player:{cid}", 1, 1, 5)
    cash_inject(client, ah, f"player:{cb}", 2, 1, 5)
    with Session.begin() as db:
        i = m.Item(owner=None, definition="crystal", quantity=1, location="auction")
        db.add(i)
        db.flush()
        a = m.Auction(
            item_id=i.id,
            quantity=1,
            former_owner_id=cid,
            opening_price=1,
            ends_at=utc_now() + timedelta(hours=1),
            proceeds_destination="treasury",
            origin="guild_debt",
            assessed_value=1,
        )
        db.add(a)
        db.flush()
        aid = a.id
        auctions.bid(
            db,
            db.get(m.Account, db.get(m.Character, cid).account_id),
            aid,
            17,
            str(uuid4()),
        )
        assert lunar.balances(db, f"auction:{aid}") == {
            "coin_large": 1,
            "coin_medium": 1,
            "coin_small": 2,
        }
        auctions.bid(
            db,
            db.get(m.Account, db.get(m.Character, cb).account_id),
            aid,
            27,
            str(uuid4()),
        )
        assert lunar.balances(db, f"player:{cid}") == {
            "coin_large": 1,
            "coin_medium": 1,
            "coin_small": 5,
        }
        assert lunar.balances(db, f"auction:{aid}") == {
            "coin_large": 2,
            "coin_medium": 1,
            "coin_small": 2,
        }
        a.ends_at = utc_now() - timedelta(seconds=1)
        before = lunar.balances(db, "treasury")
        auctions.settle(db, aid)
        after = lunar.balances(db, "treasury")
        assert all(
            after.get(k, 0) - before.get(k, 0) == q
            for k, q in {"coin_large": 2, "coin_medium": 1, "coin_small": 2}.items()
        )
        assert finance.coin_mg(db, f"auction:{aid}") == 0
    invariant()


def test_contract_reserve_payment_and_refund_physical_denominations(client):
    from app import contracts

    ah, h, cid = ready(client)
    execute(
        client,
        ah,
        "royal.exchange",
        "treasury",
        {"inputs": {"coin_large": 1}, "outputs": {"coin_medium": 1, "coin_small": 5}},
    )
    params = {
        "name": "Contrato físico",
        "description": "Sem normalização",
        "kind": "collect",
        "target": "herb",
        "required": 1,
        "slots": 1,
        "reward": "17",
    }
    with Session.begin() as db:
        d = contracts.publish(db, params)
        assert lunar.balances(db, f"contract:{d.id}") == {
            "coin_large": 1,
            "coin_medium": 1,
            "coin_small": 2,
        }
        c = db.get(m.Character, cid)
        accepted = contracts.accept(db, c, d.id, str(uuid4()))
        contracts.progress(db, c, "collect", "herb", 1)
        accepted_id = db.scalar(
            select(m.CharacterContract.id).where(
                m.CharacterContract.character_id == cid,
                m.CharacterContract.contract_id == d.id,
            )
        )
        contracts.claim(db, c, accepted_id, str(uuid4()))
        assert lunar.balances(db, f"player:{cid}") == {
            "coin_large": 1,
            "coin_medium": 1,
            "coin_small": 2,
        }
        # Reuse existing pieces through a funded transfer, then reserve/cancel.
        finance.move(
            db, f"player:{cid}", "treasury", 17, "returnfixture", amortize=False
        )
        d = contracts.publish(db, params)
        before = lunar.balances(db, "treasury")
        contracts.cancel_publication(db, d.id, str(uuid4()))
        after = lunar.balances(db, "treasury")
        assert all(
            after.get(k, 0) - before.get(k, 0) == q
            for k, q in {"coin_large": 1, "coin_medium": 1, "coin_small": 2}.items()
        )
    invariant()


def test_capacity_merge_and_full_inventory_no_material_loss(client, monkeypatch):
    from app.config import settings

    ah, h, cid = ready(client)
    config(
        client,
        ah,
        buy_price_units=8,
        sell_price_units=13,
        buy_enabled=True,
        sell_enabled=True,
    )
    cash_inject(client, ah, f"player:{cid}", 3, 2, 10)
    stock = item(cid, qty=3, guild=True)
    monkeypatch.setattr(settings, "collection_slots", 1)
    r = trade(client, h, q(client, h, stock, 1, "buy"))
    assert r.status_code == 409 and "Mochila" in r.text
    with Session() as db:
        assert db.get(m.Item, stock).quantity == 3 and db.get(m.NPCStock, stock)
    own = item(cid, qty=4)
    monkeypatch.setattr(settings, "collection_slots", 2)
    r = trade(client, h, q(client, h, stock, 2, "buy"))
    assert r.status_code == 200, r.text
    with Session() as db:
        assert db.get(m.Item, own).quantity == 6 and db.get(m.Item, stock).quantity == 1
        assert db.get(m.NPCStock, stock)
    invariant()


def test_historical_exchange_and_guild_sale_receipts_replay_without_writes(client):
    from app import npc_economy

    ah, h, cid = ready(client)
    owner = f"player:{cid}"
    cash_inject(client, ah, owner, 1)
    cash_inject(client, ah, "guild", 1)
    with Session.begin() as db:
        old = lunar.post(
            db,
            "legacy-exchange",
            "COIN_DENOMINATION_EXCHANGE",
            owner,
            "Troca gratuita de denominações",
            [(owner, "coin_large", -1), (owner, "coin_medium", 2)],
        )
        count = db.scalar(select(func.count()).select_from(m.LunarEntry))
        assert (
            lunar.exchange(
                db, owner, {"coin_large": 1}, {"coin_medium": 2}, "legacy-exchange"
            ).id
            == old.id
        )
        assert db.scalar(select(func.count()).select_from(m.LunarEntry)) == count
    iid = item(cid)
    request = str(uuid4())
    with Session.begin() as db:
        i = db.get(m.Item, iid)
        oldquote = npc_economy.quote(i, 10000, "guild")
        npc_economy.buy_from_player(
            db, db.get(m.Character, cid), iid, "guild", 10000, f"shop:{cid}:{request}"
        )
        count = db.scalar(select(func.count()).select_from(m.LunarEntry))
    r = client.post(
        "/economy/shop/sell",
        headers=h,
        json={"item_id": iid, "quote": oldquote, "request_id": request},
    )
    assert r.status_code == 200 and r.json()["replayed"], r.text
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.LunarEntry)) == count
    invariant()
