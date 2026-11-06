from uuid import uuid4
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from test_game import clean, client, state, navigate, walk_tiles
from test_expeditions import begin, pending_records
from app.main import app
from app.database import Session
from app.models import (
    Character,
    Battle,
    Item,
    ItemDefinition,
    Expedition,
    DeathEvent,
    Auction,
    AuctionBid,
    Ledger,
    Treasury,
    WorldEvent,
)
from app.clock import utc_now
from app.config import settings


def fresh(client, name="alice"):
    r = client.post(
        "/auth/register", json={"username": name, "password": "safe-pass-123"}
    )
    assert r.status_code == 201, r.text
    h = {"Authorization": "Bearer " + r.json()["token"]}
    r = client.post("/character", headers=h, json={"name": name})
    assert r.status_code == 201, r.text
    with Session.begin() as db:
        if not db.get(ItemDefinition, "iron_sword"):
            db.add(
                ItemDefinition(
                    id="iron_sword",
                    name="Espada de Ferro",
                    kind="weapon",
                    power=3,
                    base_value=100,
                )
            )
            db.flush()
        cid = r.json()["character"]["id"]
        db.add(Item(owner=cid, definition="iron_sword", quantity=1))
    return h


def setup_lethal(client, h, mp, **values):
    s = begin(client, h, mp)
    enemy = s["map"]["enemies"][0]
    with Session.begin() as db:
        c = db.get(Character, s["character"]["id"])
        c.hp = 1
        c.x, c.y = enemy["x"] + 1, enemy["y"]
        for k, v in values.items():
            setattr(c, k, v)
    b = client.post("/battles", headers=h, json={"monster": str(enemy["id"])})
    assert b.status_code == 200, b.text
    return s, b.json()


def lethal(client, h, b):
    return client.post(
        f'/battles/{b["id"]}/action',
        headers=h,
        json={"turn": b["turn"], "action": "defend"},
    )


def die(client, h, mp, **values):
    s, b = setup_lethal(client, h, mp, **values)
    r = lethal(client, h, b)
    assert r.status_code == 200 and r.json()["status"] == "lost", r.text
    after = state(client, h)
    assert after["room"]["id"] == "city1" and after["battle"] is None
    with Session() as db:
        assert db.get(Expedition, s["expedition"]["id"]).status == "FAILED"
    return after


def wallet(h, client, amount):
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.get(Character, cid).coins = amount
    return cid


def historical_die(client, h, mp, **values):
    """Reproduce a pre-0.7 listing to test escrow compatibility, never a runtime flag.
    The production death policy is covered separately by test_procedural_update.
    """
    import app.deaths as deaths
    from app.auctions import create_from_death

    with mp.context() as historical:
        historical.setattr(deaths, "lose", create_from_death)
        return die(client, h, historical, **values)


def auction_fixture(client, mp):
    owner = fresh(client)
    dead = historical_die(client, owner, mp)
    a = client.get("/auctions", headers=owner).json()[0]
    bidder = fresh(client, "bidder")
    wallet(bidder, client, 1000)
    return owner, bidder, a, dead


def bid(client, h, aid, amount, rid=None):
    return client.post(
        f"/auctions/{aid}/bids",
        headers=h,
        json={"amount": amount, "request_id": rid or str(uuid4())},
    )


def expire(aid):
    with Session.begin() as db:
        db.get(Auction, aid).ends_at = utc_now() - timedelta(seconds=1)


@pytest.mark.parametrize(
    "balance,expected",
    [
        (500, 400),
        (50, -50),
        (-70, -170),
        (-9950, -10000),
        (-9900, -10000),
        (-10000, -10000),
    ],
)
def test_medical_fee_balances_cap_and_level_penalty(
    client, monkeypatch, balance, expected
):
    h = fresh(client)
    with Session.begin() as db:
        db.get(ItemDefinition, "iron_sword").death_transferable = (
            False  # Isolate medical fee from independent confiscation.
        )
    monkeypatch.setattr(settings, "medical_fee_base", 100)
    s = die(
        client,
        h,
        monkeypatch,
        coins=balance,
        level=37,
        xp=950,
        unspent_attribute_points=2,
    )
    c, d = s["character"], s["death"]
    assert c["coins"] == expected and c["xp"] == 0
    assert c["level"] == (27 if expected == -10000 else 37)
    assert (
        d["medical_fee"] == 100
        and d["balance_before"] == balance
        and d["balance_after"] == expected
    )
    assert c["hp"] == 30 + (c["level"] - 1) * 5
    if expected == -10000:
        assert c["unspent_attribute_points"] == 0 and c["attribute_point_debt"] == 8
    with Session() as db:
        assert (
            db.get(Treasury, 1).balance
            == settings.initial_treasury + balance - expected
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Ledger)
                .where(Ledger.reference.like("medical:%"))
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(WorldEvent)
                .where(WorldEvent.kind == "PLAYER_DIED_IN_EXPEDITION")
            )
            == 1
        )


def test_repeated_death_at_cap_min_level_and_attribute_debt(client, monkeypatch):
    h = fresh(client)
    with Session.begin() as db:
        db.get(ItemDefinition, "iron_sword").death_transferable = (
            False  # Isolate medical fee from independent confiscation.
        )
    s = die(client, h, monkeypatch, level=16, coins=-10000, unspent_attribute_points=2)
    assert s["character"]["level"] == 6 and s["character"]["attribute_point_debt"] == 8
    s = die(client, h, monkeypatch)
    assert s["character"]["level"] == 1 and s["character"]["coins"] == -10000
    assert (
        s["death"]["levels_lost"] == 5 and s["character"]["attribute_point_debt"] == 13
    )
    s = die(client, h, monkeypatch)
    assert (
        s["death"]["levels_lost"] == 0 and s["character"]["attribute_point_debt"] == 13
    )
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(DeathEvent)) == 3


def test_death_loses_all_pending_preserves_claimed_levels_and_custody_ids(
    client, monkeypatch
):
    h = fresh(client)
    pending_records(h, client, [300, 550])
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.add(Item(owner=cid, definition="crystal", quantity=12))
        db.add(
            ItemDefinition(
                id="system_flag",
                name="Marca técnica",
                kind="system",
                death_transferable=False,
            )
        )
        db.flush()
        flag = Item(owner=cid, definition="system_flag", quantity=1)
        db.add(flag)
        sword = db.scalar(
            select(Item).where(Item.owner == cid, Item.definition == "sword")
        )
        sword.equipped = True
        db.add(
            Battle(
                character_id=cid,
                monster="slime",
                hp=0,
                status="won",
                claimed=True,
                reward_amount=444,
            )
        )
    before = state(client, h)["inventory"]
    s = die(client, h, monkeypatch, level=10, xp=150, coins=500)
    assert s["death"]["xp_lost"] == 150 and s["death"]["pending_lost"] == 850
    assert s["character"]["level"] == 10 and s["character"]["coins"] == 400
    assert any(i["name"] == "Marca técnica" for i in s["inventory"])
    with Session() as db:
        lost = db.scalars(select(Item).where(Item.location == "destroyed")).all()
        assert 0 <= sum(i.quantity for i in lost) <= 5
        assert all(i.owner is None and not i.equipped for i in lost)
        assert sum(i["quantity"] for i in before) == sum(
            i["quantity"] for i in s["inventory"]
        ) + sum(i.quantity for i in lost)
        assert db.scalar(select(func.count()).select_from(Auction)) == 0
        assert (
            db.scalar(
                select(Battle.reward_amount).where(
                    Battle.claimed == True, Battle.reward_amount == 444
                )
            )
            == 444
        )
    assert client.get("/guild/rewards", headers=h).json()["total"] == 0
    assert client.get("/rewards", headers=h).json() == []
    old = s["death"]
    assert (
        client.post(
            f'/battles/{old["battle_id"]}/claim', headers=h, json={}
        ).status_code
        == 409
    )
    assert state(client, h)["death"] == old  # Persisted across reconnect/refresh.
    other = fresh(client, "other")
    assert (
        client.post(
            f'/deaths/{old["death_event_id"]}/acknowledge', headers=other, json={}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f'/deaths/{old["death_event_id"]}/acknowledge', headers=h, json={}
        ).status_code
        == 200
    )
    assert state(client, h)["death"] is None


def test_death_race_idempotence_and_old_receipt_never_mutates_new_expedition(
    client, monkeypatch
):
    h = fresh(client)
    with Session.begin() as db:
        db.get(ItemDefinition, "iron_sword").death_transferable = (
            False  # Isolate death replay from item collection.
        )
    s, b = setup_lethal(client, h, monkeypatch, level=37, coins=-9950, xp=29)

    def run(_):
        with TestClient(app) as c:
            return lethal(c, h, b).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [200, 409]
    dead = state(client, h)
    assert dead["character"]["level"] == 27
    new = begin(client, h, monkeypatch)
    from app.deaths import resolve

    with Session.begin() as db:
        c = db.scalar(
            select(Character)
            .where(Character.id == s["character"]["id"])
            .with_for_update()
        )
        assert resolve(db, c, db.get(Battle, b["id"])) == dead["death"]
    now = state(client, h)
    assert now["room"]["id"] == new["room"]["id"] and now["character"]["level"] == 27
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(DeathEvent)) == 1
        assert db.scalar(select(func.count()).select_from(Auction)) == 0


def test_death_failure_rolls_back_fee_pending_items_battle_and_event(
    client, monkeypatch
):
    import app.deaths as deaths

    h = fresh(client)
    pending_records(h, client, [850])
    s, b = setup_lethal(client, h, monkeypatch, coins=50, xp=37)
    original = deaths.lose

    def fail(*args):
        original(*args)
        raise RuntimeError("injected custody failure")

    monkeypatch.setattr(deaths, "lose", fail)
    with pytest.raises(RuntimeError):
        lethal(client, h, b)
    now = state(client, h)
    assert (
        now["character"]["coins"] == 50
        and now["character"]["xp"] == 37
        and now["character"]["hp"] == 1
    )
    assert now["expedition"]["status"] == "ACTIVE" and now["battle"]["turn"] == 0
    assert (
        len(now["inventory"]) == 2
        and client.get("/guild/rewards", headers=h).json()["total"] == 850
    )
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(DeathEvent)) == 0
        assert db.scalar(select(func.count()).select_from(Auction)) == 0
        assert db.get(Treasury, 1).balance == settings.initial_treasury


@pytest.mark.parametrize("amount,expected", [(300, -200), (800, 300)])
def test_guild_credit_automatically_amortizes_debt(client, amount, expected):
    h = fresh(client)
    pending_records(h, client, [amount])
    wallet(h, client, -500)
    navigate(client, h, "guild")
    walk_tiles(client, h, tuple(state(client, h)["map"]["npc"]))
    r = client.post("/guild/claim", headers=h, json={})
    assert r.status_code == 200 and r.json()["paid"] == amount
    assert state(client, h)["character"]["coins"] == expected


def test_common_room_death_has_no_new_penalties(client, monkeypatch):
    h = fresh(client)
    navigate(client, h, "common_a")
    s = state(client, h)
    e = s["map"]["enemies"][0]
    with Session.begin() as db:
        c = db.get(Character, s["character"]["id"])
        c.hp = 1
        c.x = e["x"] + 1
        c.y = e["y"]
        c.coins = 50
        c.xp = 29
    b = client.post("/battles", headers=h, json={"monster": str(e["id"])}).json()
    assert lethal(client, h, b).json()["status"] == "lost"
    now = state(client, h)
    assert (
        now["death"] is None
        and now["character"]["coins"] == 50
        and now["character"]["xp"] == 29
    )
    assert len(now["inventory"]) == 2


def test_auction_prices_stacks_fallback_and_player_only(client, monkeypatch):
    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    monkeypatch.setattr(settings, "min_auction_start_price", 3)
    with Session.begin() as db:
        db.add(Item(owner=cid, definition="crystal", quantity=20))
        db.add(ItemDefinition(id="unknown", name="Relíquia sem preço", kind="weapon"))
        db.flush()
        db.add(Item(owner=cid, definition="unknown", quantity=1))
    historical_die(client, h, monkeypatch)
    listings = client.get("/auctions", headers=h).json()
    assert {a["name"]: a["opening_price"] for a in listings} == {
        "Espada de Ferro": "20",
        "Cristal da clareira": "40",
        "Relíquia sem preço": "3",
    }
    assert client.post(
        f'/auctions/{listings[0]["id"]}/bids',
        json={"amount": 40, "request_id": str(uuid4())},
    ).status_code in (401, 403)
    assert (
        client.post(
            f'/auctions/{listings[0]["id"]}/bids',
            headers=h,
            json={"amount": 40, "request_id": str(uuid4()), "npc_id": "receptionist"},
        ).status_code
        == 422
    )


def test_bids_reserve_outbid_refunds_and_settle_exact_id_once(client, monkeypatch):
    owner, bidder, a, dead = auction_fixture(client, monkeypatch)
    aid = a["id"]
    bidder_id = state(client, bidder)["character"]["id"]
    rid = str(uuid4())
    assert bid(client, bidder, aid, 200, rid).status_code == 200
    assert bid(client, bidder, aid, 200, rid).json()["replayed"]
    assert (
        state(client, bidder)["character"]["coins"] == 800
        and state(client, bidder)["reserved_gold"] == "200"
    )
    assert bid(client, bidder, aid, 250).status_code == 200
    assert state(client, bidder)["character"]["coins"] == 750
    other = fresh(client, "other")
    wallet(other, client, 1000)
    assert bid(client, other, aid, 300).status_code == 200
    assert state(client, bidder)["character"]["coins"] == 1000
    assert state(client, other)["character"]["coins"] == 700
    expire(aid)

    def finish(_):
        with TestClient(app) as c:
            return c.post(f"/auctions/{aid}/settle", headers=bidder, json={})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(finish, range(2)))
    assert all(
        r.status_code == 200 and r.json()["status"] == "SETTLED" for r in results
    )
    assert state(client, owner)["character"]["coins"] == -100
    assert state(client, other)["reserved_gold"] == "0"
    with Session() as db:
        item = db.get(Item, a["item_id"])
        assert (
            item.owner == state(client, other)["character"]["id"]
            and item.location == "inventory"
            and not item.equipped
        )
        assert db.get(Treasury, 1).balance == settings.initial_treasury + 400
        assert (
            db.scalar(
                select(func.count())
                .select_from(Ledger)
                .where(Ledger.reference == f"auction-settle:{aid}")
            )
            == 1
        )


@pytest.mark.parametrize(
    "balance,amount",
    [
        (-500, 20),
        (0, 20),
        (19, 20),
        (1000, 19),
        (1000, 0),
        (1000, -1),
        (1000, 1.5),
        (1000, True),
    ],
)
def test_invalid_or_unfunded_bids_rejected(client, monkeypatch, balance, amount):
    owner, h, a, _ = auction_fixture(client, monkeypatch)
    wallet(h, client, balance)
    assert bid(client, h, a["id"], amount).status_code in (409, 422)
    assert state(client, h)["character"]["coins"] == balance


def test_no_business_bid_ceiling_and_exact_large_gold(client, monkeypatch):
    _, h, a, _ = auction_fixture(client, monkeypatch)
    huge = 10**25 + 123
    wallet(h, client, huge)
    assert bid(client, h, a["id"], str(huge)).status_code == 200
    assert state(client, h)["coins_exact"] == "0"
    assert state(client, h)["reserved_gold"] == str(huge)
    expire(a["id"])
    assert (
        client.post(f'/auctions/{a["id"]}/settle', headers=h, json={}).status_code
        == 200
    )
    with Session() as db:
        assert db.get(Treasury, 1).balance == settings.initial_treasury + 100 + huge


def test_unsold_keeps_item_and_overdue_bids_rejected(client, monkeypatch):
    owner, h, a, _ = auction_fixture(client, monkeypatch)
    expire(a["id"])
    assert bid(client, h, a["id"], 20).status_code == 409
    listings = client.get("/auctions", headers=h).json()
    assert listings[0]["status"] == "UNSOLD"
    with Session() as db:
        item = db.get(Item, a["item_id"])
        assert item.owner is None and item.location == "auction"


def test_bid_races_no_double_spend_and_one_highest_bidder(client, monkeypatch):
    _, h, a, _ = auction_fixture(client, monkeypatch)
    other = fresh(client, "other")
    wallet(other, client, 1000)

    def run(auth):
        with TestClient(app) as c:
            return bid(c, auth, a["id"], 200).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, [h, other])) == [200, 409]
    assert sum(state(client, auth)["character"]["coins"] for auth in (h, other)) == 1800
    # Same player's competing bids across two auctions cannot spend a wallet twice.
    historical_die(client, h, monkeypatch, coins=200)
    auctions = client.get("/auctions", headers=other).json()
    second = next(x for x in auctions if x["id"] != a["id"])
    wallet(other, client, 200)

    def run2(aid):
        with TestClient(app) as c:
            return bid(c, other, aid, 300 if aid == a["id"] else 200).status_code

    # Existing winner may be other; available wallet still enforces funding.
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(run2, [a["id"], second["id"]]))
    assert statuses.count(200) <= 1
    assert state(client, other)["character"]["coins"] >= 0


def test_auction_item_can_be_lost_again_without_duplicate_custody(client, monkeypatch):
    _, h, a, _ = auction_fixture(client, monkeypatch)
    assert bid(client, h, a["id"], 20).status_code == 200
    expire(a["id"])
    client.post(f'/auctions/{a["id"]}/settle', headers=h, json={})
    dead = historical_die(client, h, monkeypatch)
    with Session() as db:
        rows = db.scalars(select(Auction).where(Auction.item_id == a["item_id"])).all()
        assert sorted(x.status for x in rows) == ["OPEN", "SETTLED"]
        assert db.get(Item, a["item_id"]).owner is None
        assert sum(x["item_id"] == a["item_id"] for x in dead["death"]["items"]) == 1


def test_auction_refund_amortizes_debt_and_reservation_survives_death(
    client, monkeypatch
):
    _, h, a, _ = auction_fixture(client, monkeypatch)
    wallet(h, client, 200)
    assert bid(client, h, a["id"], 200).status_code == 200
    dead = die(client, h, monkeypatch)
    assert dead["character"]["coins"] == -100 and dead["reserved_gold"] == "200"
    other = fresh(client, "other")
    wallet(other, client, 300)
    assert bid(client, other, a["id"], 300).status_code == 200
    assert state(client, h)["character"]["coins"] == 100
    assert state(client, h)["reserved_gold"] == "0"


def test_auction_settlement_failure_rolls_back_custody_and_treasury(
    client, monkeypatch
):
    import app.auctions as auctions

    _, h, a, _ = auction_fixture(client, monkeypatch)
    assert bid(client, h, a["id"], 200).status_code == 200
    expire(a["id"])

    def fail(*args, **kwargs):
        raise RuntimeError("injected ledger failure")

    monkeypatch.setattr(auctions, "ledger", fail)
    with pytest.raises(RuntimeError):
        client.post(f'/auctions/{a["id"]}/settle', headers=h, json={})
    with Session() as db:
        assert db.get(Auction, a["id"]).status == "OPEN"
        assert db.get(Item, a["item_id"]).owner is None
        assert db.get(Treasury, 1).balance == settings.initial_treasury + 100


def allocation(client, h, strength=0, defense=0, rid=None):
    return client.post(
        "/character/attributes",
        headers=h,
        json={
            "strength": strength,
            "defense": defense,
            "request_id": rid or str(uuid4()),
        },
    )


def test_level_points_accumulate_pay_debt_and_never_auto_allocate(client):
    from app.attributes import gain_levels

    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        c = db.get(Character, cid)
        c.xp = 50 + 100 + 150
        assert gain_levels(db, c) == 3
        assert (
            c.level == 4
            and c.unspent_attribute_points == 3
            and c.strength == 5
            and c.defense == 2
        )
    assert allocation(client, h, strength=1).status_code == 200
    rid = str(uuid4())
    assert allocation(client, h, strength=1, defense=1, rid=rid).status_code == 200
    assert allocation(client, h, strength=1, defense=1, rid=rid).json()["replayed"]
    c = state(client, h)["character"]
    assert (c["strength"], c["defense"], c["unspent_attribute_points"]) == (7, 3, 0)
    assert allocation(client, h, strength=1).status_code == 409
    with Session.begin() as db:
        c = db.get(Character, cid)
        c.attribute_point_debt = 2
        c.xp = 200 + 250 + 300
        gain_levels(db, c)
        assert (
            c.level == 7
            and c.attribute_point_debt == 0
            and c.unspent_attribute_points == 1
        )
        assert c.strength == 7


@pytest.mark.parametrize(
    "body",
    [
        {"strength": -1},
        {"strength": 1.5},
        {"strength": True},
        {"strength": 2147483648},
        {"vitality": 1},
        {"strength": 0, "defense": 0},
    ],
)
def test_invalid_attribute_distribution_rejected(client, body):
    h = fresh(client)
    body["request_id"] = str(uuid4())
    assert client.post("/character/attributes", headers=h, json=body).status_code == 422
    assert state(client, h)["character"]["strength"] == 5


def test_attribute_concurrent_spending_and_storage_overflow(client):
    h = fresh(client)
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        db.get(Character, cid).unspent_attribute_points = 5

    def run(_):
        with TestClient(app) as c:
            return allocation(c, h, strength=3).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [200, 409]
    with Session.begin() as db:
        db.get(Character, cid).strength = 2147483647
    assert allocation(client, h, strength=1).status_code == 422
    assert state(client, h)["character"]["unspent_attribute_points"] == 2


def test_real_combat_level_gain_grants_manual_point(client, monkeypatch):
    from test_expeditions import kill

    h = fresh(client)
    s = begin(client, h, monkeypatch)
    with Session.begin() as db:
        c = db.get(Character, s["character"]["id"])
        c.xp = 45
        c.strength = 100
        from app.models import EnemyInstance

        expected_xp = db.get(EnemyInstance, s["map"]["enemies"][0]["id"]).xp_reward - 5
    kill(client, h, s["map"]["enemies"][0]["id"])
    c = state(client, h)["character"]
    assert (
        c["level"] == 2
        and c["xp"] == expected_xp
        and c["unspent_attribute_points"] == 1
        and c["strength"] == 100
    )


def test_auction_sink_proceeds_do_not_credit_dead_owner(client, monkeypatch):
    monkeypatch.setattr(settings, "auction_proceeds_destination", "sink")
    owner, h, a, _ = auction_fixture(client, monkeypatch)
    assert bid(client, h, a["id"], 20).status_code == 200
    expire(a["id"])
    assert (
        client.post(f'/auctions/{a["id"]}/settle', headers=h, json={}).json()["status"]
        == "SETTLED"
    )
    assert state(client, owner)["character"]["coins"] == -100
    with Session() as db:
        assert db.get(Treasury, 1).balance == settings.initial_treasury + 100


def test_due_batch_and_concurrent_guild_payment_do_not_deadlock(client, monkeypatch):
    import threading
    import time
    import app.auctions as auctions
    import app.game as game

    owner = fresh(client)
    cid = state(client, owner)["character"]["id"]
    with Session.begin() as db:
        db.add(Item(owner=cid, definition="crystal", quantity=1))
    historical_die(client, owner, monkeypatch)
    lots = client.get("/auctions", headers=owner).json()
    one = fresh(client, "one")
    two = fresh(client, "two")
    wallet(one, client, 1000)
    wallet(two, client, 1000)
    assert bid(client, one, lots[0]["id"], 100).status_code == 200
    assert bid(client, two, lots[1]["id"], 100).status_code == 200
    # Settle order is ascending id; its later winner also wants a Guild payment.
    later = one if lots[0]["id"] > lots[1]["id"] else two
    pending_records(later, client, [300])
    navigate(client, later, "guild")
    walk_tiles(client, later, tuple(state(client, later)["map"]["npc"]))
    for lot in lots:
        expire(lot["id"])
    first_settled = threading.Event()
    payment_attempted = threading.Event()
    original_event = auctions.event
    original_character = game.character

    def observed_event(db, kind, *args, **kw):
        original_event(db, kind, *args, **kw)
        if kind == "AUCTION_SETTLED" and not first_settled.is_set():
            first_settled.set()
            assert payment_attempted.wait(5)
            time.sleep(
                0.05
            )  # Let the competing transaction reach its row/Treasury lock.

    def observed_character(*args, **kw):
        if first_settled.is_set():
            payment_attempted.set()
        return original_character(*args, **kw)

    monkeypatch.setattr(auctions, "event", observed_event)
    monkeypatch.setattr(game, "character", observed_character)

    def sweep():
        with Session.begin() as db:
            return auctions.settle_due(db)

    def pay():
        assert first_settled.wait(5)
        with TestClient(app) as c:
            return c.post("/guild/claim", headers=later, json={})

    with ThreadPoolExecutor(max_workers=2) as pool:
        sweeping = pool.submit(sweep)
        paying = pool.submit(pay)
        assert sweeping.result(timeout=15) == 2
        result = paying.result(timeout=15)
        assert result.status_code == 200 and result.json()["paid"] == 300
    assert state(client, later)["character"]["coins"] == 1200
    with Session() as db:
        assert all(a.status == "SETTLED" for a in db.scalars(select(Auction)))
        assert (
            db.get(Treasury, 1).balance == settings.initial_treasury + 100 + 200 - 300
        )
