from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import text, select, func
from test_game import clean, client, player, state
from app import models as m, lunar, finance, cutover, economy
from app.database import Session, engine


@pytest.fixture(autouse=True)
def fresh_lunar(clean):
    with Session.begin() as db:
        db.execute(
            text(
                "TRUNCATE items,world_events,npc_profiles,market_revisions,lunar_entries,lunar_holdings,lunar_accounts,lunar_assets,lunar_supply,lunar_cutovers,lunar_debts RESTART IDENTITY CASCADE"
            )
        )
        lunar.initialize(db)
    from app.seed import seed

    seed()


def convert():
    with Session.begin() as db:
        p = cutover.preview(db)
        return cutover.confirm(
            db,
            p["fingerprint"],
            str(uuid4()),
            "test",
            "Conversão explicitamente autorizada no teste",
        )


def wallet_fixture(h, client, n):
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        delta = n - c.coins
        c.coins = n
        db.get(m.Treasury, 1).balance -= delta
    return cid


def test_preview_fingerprint_no_writes_and_genesis_replay(client):
    h = player(client)
    cid = wallet_fixture(h, client, 27)
    with Session.begin() as db:
        before = db.scalar(select(func.count()).select_from(m.LunarEntry))
        p = cutover.preview(db)
        p2 = cutover.preview(db)
        assert p["fingerprint"] == p2["fingerprint"] and p["composition"][
            f"player:{cid}"
        ] == {"coin_large": 2, "coin_medium": 1, "coin_small": 2}
        assert db.scalar(select(func.count()).select_from(m.LunarEntry)) == before
        db.get(m.Character, cid).coins = 28
        db.get(m.Treasury, 1).balance -= 1
        db.flush()
        with pytest.raises(HTTPException):
            cutover.confirm(
                db,
                p["fingerprint"],
                str(uuid4()),
                "test",
                "Confirmação de preview obsoleto",
            )
    assert convert()["status"] == "CONVERTED"
    with Session.begin() as db:
        assert finance.funds(db, db.get(m.Character, cid)) == 28
        assert (
            cutover.confirm(db, "x" * 64, str(uuid4()), "test", "Repetição autorizada")[
                "status"
            ]
            == "ALREADY_CONVERTED"
        )
        assert lunar.audit(db)["gap_mg"] == "0"
        assert db.scalar(select(m.LunarSupply.discovered_mg)) == 0
        assert (
            db.scalar(
                select(m.LunarEntry.kind).where(m.LunarEntry.key == "cutover:genesis")
            )
            == "GENESIS_BACKING"
        )


def test_concurrent_cutover_once_and_legacy_frozen(client):
    h = player(client)
    with Session.begin() as db:
        p = cutover.preview(db)

    def run(_):
        with Session.begin() as db:
            return cutover.confirm(
                db,
                p["fingerprint"],
                str(uuid4()),
                "test",
                "Teste de concorrência do cutover",
            )["status"]

    with ThreadPoolExecutor(3) as pool:
        r = list(pool.map(run, range(3)))
    assert r.count("CONVERTED") == 1 and r.count("ALREADY_CONVERTED") == 2
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError):
        with Session.begin() as db:
            db.execute(text("UPDATE characters SET coins=99"))


@pytest.mark.parametrize(
    "balance,paid,debt", [(100, 100, 0), (30, 30, 70), (0, 0, 100)]
)
def test_medical_debt_and_later_payment(client, balance, paid, debt):
    h = player(client)
    cid = wallet_fixture(h, client, balance)
    convert()
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        before = finance.coin_mg(db, "treasury")
        r = economy.medical_fee(db, c, 100, 99, 88)
        assert r["death_event_id"] == 99 and r["expedition_id"] == 88
        assert (
            r["paid"] == paid
            and finance.coin_mg(db, "treasury") == before + paid * 1000
        )
        assert finance.debt_mg(db, c) == debt * 1000
        assert lunar.audit(db)["gap_mg"] == "0"
        if debt:
            # Real bank transfer without automatic amortization, then explicit payment.
            finance.move(
                db, "treasury", f"player:{cid}", debt, "fund:repayment", amortize=False
            )
            finance.settle_debt(db, c, debt, "repay")
            finance.settle_debt(db, c, debt, "repay")
            assert (
                finance.debt_mg(db, c) == 0
                and finance.coin_mg(db, f"player:{cid}") == 0
            )
        assert c.coins == balance  # historical field never changed


def test_death_receipt_survives_reconnect_and_can_be_acknowledged(client, monkeypatch):
    from test_death_economy import die

    h = player(client)
    wallet_fixture(h, client, 30)
    convert()
    dead = die(client, h, monkeypatch)
    receipt = dead["death"]
    assert receipt["paid"] == 30 and receipt["newly_financed"] == 70
    assert state(client, h)["death"] == receipt
    assert (
        client.post(
            f'/deaths/{receipt["death_event_id"]}/acknowledge', headers=h, json={}
        ).status_code
        == 200
    )
    assert state(client, h)["death"] is None
    with Session() as db:
        assert finance.reconcile(db)["metadata_mismatches"] == []
    newcomer = player(client, "newcomer")
    cid = state(client, newcomer)["character"]["id"]
    with Session.begin() as db:
        economy.medical_fee(db, db.get(m.Character, cid), 100, 12345, 12345)
    wallet = client.get("/lunar/wallet", headers=newcomer).json()
    assert wallet["weight_mg"] == "0" and wallet["debt_weight_mg"] == "100000"


def test_funded_rewards_amortize_debt_without_creation(client):
    h = player(client)
    cid = wallet_fixture(h, client, -70)
    convert()
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        t = finance.coin_mg(db, "treasury")
        economy.credit_player_gold(db, c, 100, "treasury", "test:reward")
        assert (
            finance.coin_mg(db, "treasury") == t - 30000
            and finance.coin_mg(db, f"player:{cid}") == 30000
        )
        assert (
            finance.debt_mg(db, c) == 0
            and c.coins == -70
            and lunar.audit(db)["gap_mg"] == "0"
        )


def test_zero_backing_and_rollback(client, monkeypatch):
    h = player(client)
    with Session.begin() as db:
        db.get(m.Treasury, 1).balance = 0
        db.scalar(select(m.Ledger).where(m.Ledger.reference == "genesis")).amount = 0
    with Session.begin() as db:
        p = cutover.preview(db)

    def broken(db):
        return {"gap_mg": "1", "ledger_mismatches": []}

    with monkeypatch.context() as patch:
        patch.setattr(lunar, "audit", broken)
        with pytest.raises(HTTPException):
            with Session.begin() as db:
                cutover.confirm(
                    db,
                    p["fingerprint"],
                    str(uuid4()),
                    "test",
                    "Deve reverter integralmente",
                )
    with Session() as db:
        assert not finance.active(db) and not db.scalar(select(m.LunarEntry.id))
    assert convert()["status"] == "CONVERTED"


def test_auction_hold_outbid_settlement_and_contract_escrow(client):
    from datetime import timedelta
    from app.clock import utc_now
    from app import auctions, contracts
    from test_game import navigate, walk_tiles

    h = player(client)
    cid = wallet_fixture(h, client, 200)
    other = player(client, "other")
    oid = wallet_fixture(other, client, 200)
    with Session.begin() as db:
        item = m.Item(owner=None, definition="crystal", quantity=1, location="auction")
        db.add(item)
        db.flush()
        a = m.Auction(
            item_id=item.id,
            quantity=1,
            former_owner_id=cid,
            opening_price=1,
            ends_at=utc_now() + timedelta(days=1),
        )
        db.add(a)
        db.flush()
        aid = a.id
        itemid = item.id
    convert()

    def bid(id, n, key):
        with Session.begin() as db:
            return auctions.bid(
                db, db.get(m.Account, db.get(m.Character, id).account_id), aid, n, key
            )

    key = str(uuid4())
    bid(cid, 50, key)
    bid(cid, 50, key)
    bid(oid, 60, str(uuid4()))
    with Session.begin() as db:
        assert (
            finance.coin_mg(db, f"player:{cid}") == 200000
            and finance.coin_mg(db, f"auction:{aid}") == 60000
        )
        db.get(m.Auction, aid).ends_at = utc_now() - timedelta(seconds=1)
    with Session.begin() as db:
        auctions.settle(db, aid)
        assert db.get(m.Item, itemid).owner == oid
        assert finance.reconcile(db)["metadata_mismatches"] == []
        d = contracts.publish(
            db,
            {
                "name": "Coleta financiada",
                "description": "Objetivo teste",
                "kind": "collect",
                "target": "herb",
                "required": 1,
                "slots": 2,
                "reward": "20",
            },
        )
        did = d.id
        assert finance.coin_mg(db, f"contract:{did}") == 40000
    navigate(client, h, "guild")
    s = state(client, h)
    walk_tiles(client, h, tuple(s["map"]["npc"]))
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        a = contracts.accept(db, c, did, str(uuid4()))
        acceptid = a["id"]
        contracts.progress(db, c, "collect", "herb", 1)
        contracts.claim(db, c, acceptid, str(uuid4()))
        contracts.claim(db, c, acceptid, str(uuid4()))
        contracts.cancel_publication(db, did, str(uuid4()))
        assert finance.coin_mg(db, f"contract:{did}") == 0
        assert (
            finance.reconcile(db)["metadata_mismatches"] == []
            and lunar.audit(db)["gap_mg"] == "0"
        )


def test_npc_zero_money_finite_stock_sale_purchase_and_retry(client):
    from app import npc_economy
    from test_game import navigate, walk_tiles

    h = player(client)
    cid = wallet_fixture(h, client, 100)
    convert()
    navigate(client, h, "guild")
    s = state(client, h)
    walk_tiles(client, h, tuple(s["map"]["npc"]))
    with Session.begin() as db:
        finance.ensure(db, "npc:smith")
        assert finance.coin_mg(db, "npc:smith") == 0
        item = m.Item(owner=None, definition="crystal", quantity=1, location="npc")
        db.add(item)
        db.flush()
        iid = item.id
        db.add(m.NPCStock(item_id=iid, account_id="npc:smith", sale_weight_mg=20000))
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        npc_economy.sell_to_player(db, c, iid, "npc:test:1")
        npc_economy.sell_to_player(db, c, iid, "npc:test:1")
        assert finance.coin_mg(db, "npc:smith") == 20000
        npc_economy.buy_from_player(db, c, iid, "npc:smith", 10000, "npc:test:2")
        npc_economy.buy_from_player(db, c, iid, "npc:smith", 10000, "npc:test:2")
        assert (
            finance.coin_mg(db, "npc:smith") == 10000
            and lunar.audit(db)["gap_mg"] == "0"
        )
    with pytest.raises(HTTPException):
        with Session.begin() as db:
            npc_economy.sell_to_player(
                db, db.get(m.Character, cid), iid + 999, "missing"
            )


def test_cutover_admin_permissions_recovery_and_no_abstract_admin_mint(client):
    from test_admin_migration import admin

    ah, h = admin(client)
    cid = wallet_fixture(h, client, 100)
    assert client.get("/admin/lunar/cutover/preview", headers=h).status_code == 401
    p = client.get("/admin/lunar/cutover/preview", headers=ah).json()
    body = {
        "fingerprint": p["fingerprint"],
        "request_id": str(uuid4()),
        "reason": "Conversão explícita auditada por API",
        "confirmed": True,
    }
    assert (
        client.post("/admin/lunar/cutover/confirm", headers=ah, json=body).status_code
        == 200
    )
    assert (
        client.post("/admin/lunar/cutover/confirm", headers=ah, json=body).json()[
            "status"
        ]
        == "ALREADY_CONVERTED"
    )
    with Session.begin() as db:
        from types import SimpleNamespace
        from app.admin_economy import execute

        with pytest.raises(HTTPException):
            execute(
                db,
                SimpleNamespace(
                    action="bank.issue", params={"amount": "1"}, id="forbidden"
                ),
            )
        c = db.get(m.Character, cid)
        economy.ledger(db, "recovery:fixture", f"character:{cid}", "npc:recovery", 20)
        economy.ledger(db, "recovery:fixture", f"character:{cid}", "npc:recovery", 20)
        assert (
            finance.coin_mg(db, "npc:recovery") == 20000
            and finance.coin_mg(db, f"player:{cid}") == 80000
        )
        assert lunar.audit(db)["gap_mg"] == "0"


def test_web_shop_quotes_admin_stock_and_poor_guild_rejection(client):
    from test_admin_migration import admin, proposal, commit, execute
    from test_game import navigate, walk_tiles

    ah, h = admin(client)
    cid = wallet_fixture(h, client, 100)
    with Session.begin() as db:
        item = m.Item(owner=cid, definition="crystal", quantity=1, location="inventory")
        db.add(item)
        db.flush()
        iid = item.id
    convert()
    p = proposal(
        client,
        ah,
        "npc.stock",
        iid,
        {"account_id": "npc:smith", "price_weight_mg": "20000"},
    )
    assert p.status_code == 200, p.text
    r = commit(client, ah, p)
    assert r.status_code == 200, r.text
    navigate(client, h, "guild")
    s = state(client, h)
    walk_tiles(client, h, tuple(s["map"]["npc"]))
    shop = client.get("/economy/shop", headers=h).json()
    row = next(i for i in shop["stock"] if i["item_id"] == iid)
    body = {"request_id": str(uuid4()), "item_id": iid, "quote": "a" * 64}
    assert client.post("/economy/shop/buy", headers=h, json=body).status_code == 409
    body["quote"] = row["quote"]
    r = client.post("/economy/shop/buy", headers=h, json=body)
    assert r.status_code == 200, r.text
    assert client.post("/economy/shop/buy", headers=h, json=body).json()["replayed"]
    offer = next(
        i
        for i in client.get("/economy/shop", headers=h).json()["offers"]
        if i["item_id"] == iid
    )
    sell = {"request_id": str(uuid4()), "item_id": iid, "quote": offer["quote"]}
    assert (
        client.post("/economy/shop/sell", headers=h, json=sell).status_code == 409
    )  # guild has zero cash
    execute(
        client,
        ah,
        "bank.transfer",
        params={"amount": "20", "source": "treasury", "destination": "guild"},
    )
    r = client.post("/economy/shop/sell", headers=h, json=sell)
    assert r.status_code == 200, r.text
    assert client.post("/economy/shop/sell", headers=h, json=sell).json()["replayed"]
    with Session() as db:
        assert finance.reconcile(db)["gap_mg"] == "0"


def test_discord_after_cutover_is_readonly_and_does_not_settle(client, monkeypatch):
    from test_discord_08 import link, snapshot

    h = player(client)
    wallet_fixture(h, client, 27)
    bh, _ = link(client, h, monkeypatch)
    convert()
    before = snapshot()
    for section in [
        "character",
        "inventory",
        "debt",
        "wallet",
        "mineral",
        "auctions",
        "contracts",
    ]:
        r = client.get("/discord/123/queries/" + section, headers=bh)
        assert r.status_code == 200, r.text
    assert snapshot() == before
    assert client.get("/discord/123/queries/wallet", headers=bh).json()[
        "legacy_conversion_active"
    ]


def test_recovery_real_endpoint_transfers_to_recovery_account_once(client):
    from test_game import navigate, walk_tiles

    h = player(client)
    cid = wallet_fixture(h, client, 100)
    with Session.begin() as db:
        db.add(
            m.ItemDefinition(
                id="rareblade",
                name="Lâmina rara",
                kind="weapon",
                power=4,
                base_value=10,
                rarity="rare",
            )
        )
        db.flush()
        item = m.Item(
            owner=None, definition="rareblade", quantity=1, location="recovery"
        )
        db.add(item)
        exp = m.Expedition(
            character_id=cid, room_id="common_a", seed=123, status="FAILED"
        )
        db.add(exp)
        b = m.Battle(
            character_id=cid, monster="slime", hp=0, status="lost", room_id="common_a"
        )
        db.add(b)
        db.flush()
        death = m.DeathEvent(
            character_id=cid, expedition_id=exp.id, battle_id=b.id, receipt={}
        )
        db.add(death)
        db.flush()
        r = m.RecoveryItem(
            character_id=cid, item_id=item.id, death_event_id=death.id, price=20
        )
        db.add(r)
        db.flush()
        rid = r.id
        iid = item.id
    convert()
    navigate(client, h, "city1")
    s = state(client, h)
    walk_tiles(client, h, tuple(s["map"]["npc"]))
    body = {"request_id": str(uuid4())}
    result = client.post(f"/recovery/{rid}/recover", headers=h, json=body)
    assert result.status_code == 200, result.text
    assert client.post(f"/recovery/{rid}/recover", headers=h, json=body).json()[
        "replayed"
    ]
    with Session() as db:
        assert finance.coin_mg(db, "npc:recovery") == 20000
        assert db.get(m.Item, iid).owner == cid
        assert finance.reconcile(db)["gap_mg"] == "0"


def test_operational_concurrency_contract_claim_bid_and_npc_stock(client):
    from app import contracts, auctions, npc_economy
    from app.clock import utc_now
    from datetime import timedelta
    from test_game import navigate, walk_tiles

    h = player(client)
    cid = wallet_fixture(h, client, 200)
    other = player(client, "other")
    oid = wallet_fixture(other, client, 200)
    convert()
    navigate(client, h, "guild")
    s = state(client, h)
    walk_tiles(client, h, tuple(s["map"]["npc"]))
    with Session.begin() as db:
        d = contracts.publish(
            db,
            {
                "name": "Contrato concorrente",
                "description": "Objetivo único",
                "kind": "collect",
                "target": "herb",
                "required": 1,
                "slots": 1,
                "reward": "20",
            },
        )
        c = db.get(m.Character, cid)
        acceptance = contracts.accept(db, c, d.id, str(uuid4()))
        contracts.progress(db, c, "collect", "herb", 1)
        acceptid = acceptance["id"]
        finance.ensure(db, "npc:race")
        i = m.Item(owner=None, definition="crystal", quantity=1, location="npc")
        db.add(i)
        db.flush()
        iid = i.id
        db.add(m.NPCStock(item_id=iid, account_id="npc:race", sale_weight_mg=20000))
        i2 = m.Item(owner=None, definition="crystal", quantity=1, location="auction")
        db.add(i2)
        db.flush()
        a = m.Auction(
            item_id=i2.id,
            quantity=1,
            former_owner_id=cid,
            opening_price=1,
            ends_at=utc_now() + timedelta(days=1),
        )
        db.add(a)
        db.flush()
        aid = a.id
    with ThreadPoolExecutor(4) as pool:
        r = list(
            pool.map(
                lambda _: client.post(
                    f"/contracts/accepted/{acceptid}/claim",
                    headers=h,
                    json={"request_id": str(uuid4())},
                ),
                range(4),
            )
        )
    assert all(x.status_code == 200 for x in r)
    quote = next(
        i
        for i in client.get("/economy/shop", headers=h).json()["stock"]
        if i["item_id"] == iid
    )["quote"]
    with ThreadPoolExecutor(4) as pool:
        r = list(
            pool.map(
                lambda _: client.post(
                    "/economy/shop/buy",
                    headers=h,
                    json={"request_id": str(uuid4()), "item_id": iid, "quote": quote},
                ),
                range(4),
            )
        )
    assert sum(x.status_code == 200 for x in r) == 1

    def bid(v):
        id, n = v
        try:
            with Session.begin() as db:
                auctions.bid(
                    db,
                    db.get(m.Account, db.get(m.Character, id).account_id),
                    aid,
                    n,
                    str(uuid4()),
                )
            return True
        except HTTPException:
            return False

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(bid, [(cid, 50), (oid, 60)]))
    with Session() as db:
        assert db.get(m.Auction, aid).highest_bid == 60
        assert finance.coin_mg(db, f"auction:{aid}") == 60000
        audit = finance.reconcile(db)
        assert audit["gap_mg"] == "0" and not audit["metadata_mismatches"]
