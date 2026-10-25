from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from test_game import clean, client, state, navigate, walk_tiles
from app.main import app
from app.database import Session
from app import models as m
from app.clock import utc_now
from app.config import settings
from test_death_economy import fresh, die


def admin(c, role="owner", name="operator"):
    h = fresh(c, name)
    with Session.begin() as db:
        account = db.scalar(select(m.Account).where(m.Account.username == name))
        db.add(m.AdminRole(account_id=account.id, role=role))
    r = c.post(
        "/admin/auth/login", json={"username": name, "password": "safe-pass-123"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}, h


def proposal(c, h, action, target="central_bank", params=None, id=None):
    return c.post(
        "/admin/operations/preview",
        headers=h,
        json={
            "operation_id": id or str(uuid4()),
            "action": action,
            "target": str(target),
            "params": params or {},
            "reason": "Teste explícito de integridade administrativa",
        },
    )


def commit(c, h, proposal):
    p = proposal.json() if hasattr(proposal, "json") else proposal
    return c.post(
        "/admin/operations/" + p["id"] + "/confirm",
        headers=h,
        json={"confirmed": True, "confirmation_token": p["confirmation_token"]},
    )


def execute(c, h, action, target="central_bank", params=None):
    p = proposal(c, h, action, target, params)
    assert p.status_code == 200, p.text
    r = commit(c, h, p)
    assert r.status_code == 200, r.text
    return r.json()


def test_player_token_admin_session_permissions_and_revoke(client):
    ah, h = admin(client, "observer")
    assert client.get("/admin/overview", headers=h).status_code == 401
    assert client.get("/admin/overview", headers=ah).status_code == 200
    assert (
        proposal(client, ah, "bank.issue", params={"amount": "100"}).status_code == 403
    )
    with Session.begin() as db:
        db.scalar(select(m.AdminRole)).role = "invalid"
    assert client.get("/admin/items", headers=ah).status_code == 403


def test_admin_login_rate_limit_and_expiration(client):
    h = fresh(client)
    for _ in range(5):
        assert (
            client.post(
                "/admin/auth/login",
                json={"username": "alice", "password": "bad-pass-123"},
            ).status_code
            == 403
        )
    assert (
        client.post(
            "/admin/auth/login", json={"username": "alice", "password": "bad-pass-123"}
        ).status_code
        == 429
    )


def test_official_supply_transfer_emission_burn_idempotence_and_sandbox(client):
    ah, h = admin(client)
    initial = client.get("/admin/economy", headers=ah).json()["indicators"]
    assert initial["reconciliation_gap"] == "0" and initial["central_bank"] == "0"
    p = proposal(
        client,
        ah,
        "bank.issue",
        params={"amount": "1000", "destination": "central_bank"},
    )
    r = commit(client, ah, p)
    assert r.status_code == 200, r.text
    assert commit(client, ah, p).json()["replayed"]
    execute(
        client,
        ah,
        "bank.transfer",
        params={"amount": "300", "source": "central_bank", "destination": "treasury"},
    )
    execute(client, ah, "bank.burn", params={"amount": "100", "source": "central_bank"})
    execute(client, ah, "sandbox.grant", target=1, params={"amount": "999999999"})
    indicators = client.get("/admin/economy", headers=ah).json()["indicators"]
    assert (
        indicators["central_bank"] == "600"
        and indicators["emissions"] == "1000"
        and indicators["retired"] == "100"
    )
    assert indicators["reconciliation_gap"] == "0" and indicators[
        "official_net"
    ] == str(int(initial["official_net"]) + 900)
    assert indicators["administrative_test_credits"] == "999999999"
    assert state(client, h)["character"]["coins"] == 0
    bad = proposal(
        client,
        ah,
        "bank.transfer",
        params={"amount": "1", "source": "sandbox", "destination": "treasury"},
    )
    assert bad.status_code == 422
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Ledger)
                .where(m.Ledger.reference == "admin:" + p.json()["id"])
            )
            == 1
        )


def test_stale_preview_and_concurrent_confirm_are_safe(client):
    ah, h = admin(client)
    p = proposal(
        client, ah, "bank.issue", params={"amount": 100, "destination": "treasury"}
    )
    execute(client, ah, "bank.issue", params={"amount": 50, "destination": "treasury"})
    assert commit(client, ah, p).status_code == 409
    p = proposal(
        client, ah, "bank.issue", params={"amount": 100, "destination": "central_bank"}
    )

    def run(_):
        with TestClient(app) as c:
            return commit(c, ah, p).json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    with Session() as db:
        assert db.get(m.CentralBank, 1).balance == 100


def test_admin_financial_insufficient_funds_rolls_back_and_is_audited(client):
    ah, h = admin(client)
    p = proposal(
        client,
        ah,
        "bank.transfer",
        params={"amount": 100, "source": "central_bank", "destination": "treasury"},
    )
    r = commit(client, ah, p)
    assert r.status_code == 409
    audit = client.get("/admin/audit", headers=ah).json()
    assert audit[0]["status"] == "FAILED" and "error" in audit[0]["after"]
    assert (
        client.get("/admin/economy", headers=ah).json()["indicators"][
            "reconciliation_gap"
        ]
        == "0"
    )


def legacy_starter(client, h, mp, bidder=None, settled=False):
    dead = die(client, h, mp)
    cid = dead["character"]["id"]
    with Session.begin() as db:
        item = db.scalar(
            select(m.Item).where(m.Item.owner == cid, m.Item.definition == "sword")
        )
        item.owner = bidder if settled else None
        item.location = "inventory" if settled else "auction"
        a = m.Auction(
            item_id=item.id,
            quantity=1,
            death_event_id=dead["death"]["death_event_id"],
            former_owner_id=cid,
            highest_bidder_id=bidder,
            highest_bid=50 if bidder else 0,
            opening_price=20,
            started_at=utc_now(),
            ends_at=utc_now() + timedelta(hours=24),
            status="SETTLED" if settled else "OPEN",
            proceeds_destination="treasury",
        )
        db.add(a)
        db.flush()
        return a.id, item.id, cid


def test_protected_starter_survives_death_normal_items_lost_and_recovery(
    client, monkeypatch
):
    ah, h = admin(client)
    s = die(client, h, monkeypatch)
    assert [i["definition"] for i in s["inventory"]] == ["sword"]
    assert len(s["death"]["items"]) == 1
    aid, iid, cid = legacy_starter(client, h, monkeypatch)
    before = client.get("/admin/items/starter-diagnostics", headers=ah).json()
    assert any(x["auction"]["id"] == aid for x in before)
    assert (
        client.post(
            f"/auctions/{aid}/bids",
            headers=h,
            json={"amount": 50, "request_id": str(uuid4())},
        ).status_code
        == 409
    )
    p = proposal(client, ah, "items.recover_starter", target=aid)
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    with Session() as db:
        assert (
            db.get(m.Item, iid).owner == cid
            and db.get(m.Item, iid).location == "inventory"
        )
        assert db.get(m.Auction, aid).status == "CANCELLED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Item)
                .where(m.Item.owner == cid, m.Item.definition == "sword")
            )
            == 1
        )


def test_legitimate_buyer_keeps_starter_replacement_needs_authorized_operation(
    client, monkeypatch
):
    ah, h = admin(client)
    other = fresh(client, "buyer")
    bid = state(client, other)["character"]["id"]
    aid, iid, cid = legacy_starter(client, h, monkeypatch, bidder=bid, settled=True)
    p = proposal(client, ah, "items.recover_starter", target=aid)
    assert commit(client, ah, p).status_code == 409
    execute(client, ah, "items.replace_starter", target=aid)
    with Session() as db:
        assert db.get(m.Item, iid).owner == bid
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Item)
                .where(m.Item.owner == cid, m.Item.definition == "sword")
            )
            == 1
        )


def test_cancel_refunds_reserved_gold_and_preserves_history(client, monkeypatch):
    ah, h = admin(client)
    s = die(client, h, monkeypatch)
    aid = s["death"]["items"][0]["auction_id"]
    bidder = fresh(client, "bidder")
    cid = state(client, bidder)["character"]["id"]
    execute(
        client,
        ah,
        "bank.issue",
        params={"amount": 100, "destination": f"character:{cid}"},
    )
    assert (
        client.post(
            f"/auctions/{aid}/bids",
            headers=bidder,
            json={"amount": 50, "request_id": str(uuid4())},
        ).status_code
        == 200
    )
    execute(
        client, ah, "auctions.cancel", target=aid, params={"destination": "custody"}
    )
    assert (
        state(client, bidder)["coins_exact"] == "100"
        and state(client, bidder)["reserved_gold"] == "0"
    )
    with Session() as db:
        assert db.get(m.Auction, aid).status == "CANCELLED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.AuctionBid)
                .where(m.AuctionBid.auction_id == aid)
            )
            == 1
        )


def test_fast_travel_only_visited_permanent_no_combat_or_active_expedition(
    client, monkeypatch
):
    h = fresh(client)
    assert (
        client.post(
            "/fast-travel", headers=h, json={"destination": "combat"}
        ).status_code
        == 403
    )
    navigate(client, h, "combat")
    assert (
        client.post(
            "/fast-travel", headers=h, json={"destination": "city1"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/fast-travel", headers=h, json={"destination": "combat"}
        ).status_code
        == 200
    )
    from test_expeditions import begin

    s = begin(client, h, monkeypatch)
    assert (
        client.post(
            "/fast-travel", headers=h, json={"destination": "city1"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/fast-travel", headers=h, json={"destination": s["room"]["id"]}
        ).status_code
        == 409
    )


def test_auction_hall_separate_npc_and_admin_world_tools(client, monkeypatch):
    ah, h = admin(client)
    navigate(client, h, "auction_hall")
    s = state(client, h)
    assert s["map"]["npc_name"] == "Leiloeiro da Guilda"
    walk_tiles(client, h, tuple(s["map"]["npc"]))
    assert client.post("/interact", headers=h, json={}).json()["open_auctions"]
    assert client.post("/guild/claim", headers=h, json={}).status_code == 409
    execute(
        client, ah, "monsters.balance", target="slime", params={"hp": 25, "attack": 6}
    )
    execute(client, ah, "world.region", target="common_a", params={"danger_tier": 2})
    navigate(client, h, "common_a")
    s = state(client, h)
    blocked = {tuple(x) for x in s["map"]["walls"]} | {
        (e["x"], e["y"]) for e in s["map"]["enemies"]
    }
    spot = next(
        (x, y) for x in range(4, 12) for y in range(4, 12) if (x, y) not in blocked
    )
    execute(
        client,
        ah,
        "world.spawn",
        target="common_a",
        params={
            "character_id": s["character"]["id"],
            "species": "slime",
            "x": spot[0],
            "y": spot[1],
        },
    )
    enemies = state(client, h)["map"]["enemies"]
    assert any(e["spawn_key"].startswith("adm") for e in enemies)
    for module in (
        "overview",
        "economy",
        "guilds",
        "players",
        "items",
        "monsters",
        "auctions",
        "world",
        "audit",
    ):
        r = client.get("/admin/" + module, headers=ah)
        assert r.status_code == 200, r.text
        assert '"password"' not in r.text and '"token"' not in r.text


def test_fast_travel_combat_and_reconnect_discoveries(client):
    h = fresh(client)
    navigate(client, h, "common_a")
    s = state(client, h)
    e = next(e for e in s["map"]["enemies"] if e["state"] == "ALIVE")
    walk_tiles(client, h, (e["x"], e["y"]))
    assert (
        client.post("/battles", headers=h, json={"monster": str(e["id"])}).status_code
        == 200
    )
    assert (
        client.post(
            "/fast-travel", headers=h, json={"destination": "city1"}
        ).status_code
        == 409
    )
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "safe-pass-123"}
    ).json()
    auth = {"Authorization": "Bearer " + login["token"]}
    with TestClient(app) as other:
        destinations = other.get("/fast-travel", headers=auth).json()
        assert any(d["id"] == "common_a" for d in destinations)
        assert state(other, auth)["battle"] is not None


def test_starter_recovery_refunds_debtor_bidder_once(client, monkeypatch):
    ah, h = admin(client)
    bidder = fresh(client, "bidder")
    cid = state(client, bidder)["character"]["id"]
    aid, iid, owner = legacy_starter(client, h, monkeypatch, bidder=cid)
    with Session.begin() as db:
        db.get(m.Character, cid).coins = -50
    p = proposal(client, ah, "items.recover_starter", target=aid)
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    assert (
        state(client, bidder)["coins_exact"] == "0"
        and state(client, bidder)["reserved_gold"] == "0"
    )
    with Session() as db:
        assert db.get(m.Item, iid).owner == owner
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Ledger)
                .where(m.Ledger.reference == "admin-refund:" + p.json()["id"])
            )
            == 1
        )


def test_profile_changes_leave_existing_enemy_stats_and_xp_frozen(client):
    ah, h = admin(client)
    navigate(client, h, "common_a")
    s = state(client, h)
    cid = s["character"]["id"]
    with Session() as db:
        before = [
            (e.id, e.max_hp, e.attack, e.defense, e.xp_reward, e.state)
            for e in db.scalars(
                select(m.EnemyInstance)
                .where(m.EnemyInstance.character_id == cid)
                .order_by(m.EnemyInstance.id)
            )
        ]
    execute(
        client,
        ah,
        "monsters.balance",
        target="slime",
        params={"hp": 999, "attack": 100, "xp": 900},
    )
    with Session() as db:
        after = [
            (e.id, e.max_hp, e.attack, e.defense, e.xp_reward, e.state)
            for e in db.scalars(
                select(m.EnemyInstance)
                .where(m.EnemyInstance.character_id == cid)
                .order_by(m.EnemyInstance.id)
            )
        ]
    assert before == after


def test_admin_session_expiry_confirmation_required_and_atomic_rollback(
    client, monkeypatch
):
    ah, h = admin(client)
    p = proposal(
        client,
        ah,
        "bank.issue",
        params={"amount": "10000000000000000000000001", "destination": "central_bank"},
    )
    assert (
        p.status_code == 200
        and p.json()["impact"]["projected_accounts"]["central_bank"]
        == "10000000000000000000000001"
    )
    body = {"confirmed": False, "confirmation_token": p.json()["confirmation_token"]}
    assert (
        client.post(
            "/admin/operations/" + p.json()["id"] + "/confirm", headers=ah, json=body
        ).status_code
        == 422
    )
    import app.admin_economy as economy

    original = economy.ledger

    def fail(*args, **kwargs):
        raise RuntimeError("injected ledger failure")

    monkeypatch.setattr(economy, "ledger", fail)
    with pytest.raises(RuntimeError):
        commit(client, ah, p)
    with Session() as db:
        assert db.get(m.CentralBank, 1).balance == 0
    monkeypatch.setattr(economy, "ledger", original)
    assert commit(client, ah, p).status_code == 200
    with Session.begin() as db:
        db.scalar(select(m.AdminSession)).expires = utc_now() - timedelta(seconds=1)
    assert client.get("/admin/overview", headers=ah).status_code == 401
