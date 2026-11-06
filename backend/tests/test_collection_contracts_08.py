from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from test_game import clean, client, player, state, walk_tiles, navigate
from app.database import Session
from app import models as m, contracts, admin_economy
from app.inventory import add_item
from app.config import settings


def post(client, h, path, key=None):
    return client.post(path, headers=h, json={"request_id": key or str(uuid4())})


def reception(client, h):
    navigate(client, h, "guild")
    s = state(client, h)
    walk_tiles(client, h, tuple(s["map"]["npc"]))


def publish(kind="collect", target="herb", required=2, slots=2, reward="20"):
    with Session.begin() as db:
        return contracts.publish(
            db,
            dict(
                name="Contrato de teste",
                description="Condições objetivas",
                kind=kind,
                target=target,
                required=required,
                slots=slots,
                reward=reward,
            ),
        ).id


def gap():
    with Session() as db:
        return admin_economy.metrics(db)["reconciliation_gap"]


def test_gather_stock_replay_owner_capacity_and_atomic_failure(client, monkeypatch):
    h = player(client)
    s = state(client, h)
    node = s["map"]["gather_nodes"][0]
    assert node["definition"] == "herb" and node["remaining"] == 3
    assert post(client, h, f"/resources/{node['id']}/collect").status_code == 409
    other = player(client, "other")
    assert post(client, other, f"/resources/{node['id']}/collect").status_code == 404
    walk_tiles(client, h, (node["x"], node["y"]))
    monkeypatch.setattr(settings, "collection_slots", 1)
    failed = post(client, h, f"/resources/{node['id']}/collect")
    assert failed.status_code == 409
    assert client.get("/resources", headers=h).json()[0]["remaining"] == 3
    monkeypatch.setattr(settings, "collection_slots", 30)
    key = str(uuid4())
    path = f"/resources/{node['id']}/collect"
    first = post(client, h, path, key)
    assert first.status_code == 200, first.text
    assert post(client, h, path, key).json()["replayed"]
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: post(client, h, path), range(4)))
    assert [r.status_code for r in results].count(200) == 2
    s = state(client, h)
    assert sum(i["quantity"] for i in s["inventory"] if i["definition"] == "herb") == 3
    assert s["map"]["gather_nodes"][0]["remaining"] == 0
    assert s["coins_exact"] == "0" and gap() == "0"


def test_funded_collection_contract_unique_payout_location_and_cancellation(client):
    h = player(client)
    d = publish()
    assert gap() == "0"
    assert post(client, h, f"/contracts/{d}/accept").status_code == 409
    reception(client, h)
    key = str(uuid4())
    a = post(client, h, f"/contracts/{d}/accept", key)
    assert a.status_code == 200, a.text
    aid = a.json()["id"]
    assert post(client, h, f"/contracts/{d}/accept", key).json()["replayed"]
    assert post(client, h, f"/contracts/accepted/{aid}/claim").status_code == 409
    navigate(client, h, "common_a")
    node = state(client, h)["map"]["gather_nodes"][0]
    walk_tiles(client, h, (node["x"], node["y"]))
    for _ in range(2):
        assert post(client, h, f"/resources/{node['id']}/collect").status_code == 200
    assert post(client, h, f"/contracts/accepted/{aid}/claim").status_code == 409
    reception(client, h)
    # Withdrawal must preserve already earned rights and release only unused budget.
    with Session.begin() as db:
        plan = contracts.cancel_publication(db, d, str(uuid4()))
        assert plan["retained"] == "20" and plan["refund"] == "20"
    assert gap() == "0"
    with ThreadPoolExecutor(4) as pool:
        results = list(
            pool.map(
                lambda _: post(client, h, f"/contracts/accepted/{aid}/claim"), range(4)
            )
        )
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert state(client, h)["coins_exact"] == "20" and gap() == "0"
    with Session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.Ledger)
                .where(m.Ledger.reference == f"contract-pay:{aid}")
            )
            == 1
        )
        assert db.get(m.GuildContract, d).reserved == 0


def test_delivery_is_atomic_and_not_repeated_and_personal_cancel_frees_slot(client):
    h = player(client)
    d = publish("deliver", "herb", required=3, slots=1)
    reception(client, h)
    aid = post(client, h, f"/contracts/{d}/accept").json()["id"]
    path = f"/contracts/accepted/{aid}/deliver"
    assert post(client, h, path).status_code == 409
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        add_item(db, db.get(m.Character, cid), "herb", 3, "fixture-herb")
    key = str(uuid4())
    assert post(client, h, path, key).status_code == 200
    assert post(client, h, path, key).json()["replayed"]
    assert post(client, h, f"/contracts/accepted/{aid}/cancel").status_code == 409
    other = player(client, "other")
    assert post(client, other, f"/contracts/accepted/{aid}/claim").status_code == 404
    assert post(client, h, f"/contracts/accepted/{aid}/claim").status_code == 200
    assert not any(i["definition"] == "herb" for i in state(client, h)["inventory"])
    d2 = publish("kill", "slime", slots=1)
    a2 = post(client, h, f"/contracts/{d2}/accept").json()["id"]
    assert post(client, h, f"/contracts/accepted/{a2}/cancel").status_code == 200
    with Session() as db:
        assert db.get(m.GuildContract, d2).taken == 0
    assert gap() == "0"


def test_no_funds_no_publication_and_progress_not_retroactive(client):
    h = player(client)
    d = publish("kill", "slime")
    cid = state(client, h)["character"]["id"]
    with Session.begin() as db:
        contracts.progress(db, db.get(m.Character, cid), "kill", "slime", 10)
    reception(client, h)
    aid = post(client, h, f"/contracts/{d}/accept").json()["id"]
    with Session.begin() as db:
        a = db.get(m.CharacterContract, aid)
        assert a.progress == 0
        contracts.progress(db, db.get(m.Character, cid), "kill", "slime", 1)
        assert a.progress == 1
    with Session.begin() as db:
        before = db.scalar(select(func.count()).select_from(m.GuildContract))
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            contracts.publish(
                db,
                dict(
                    name="Insolvente",
                    description="Sem orçamento",
                    kind="kill",
                    target="slime",
                    required=1,
                    slots=100,
                    reward="999999999999999999999999999999999999999",
                ),
            )
        assert db.scalar(select(func.count()).select_from(m.GuildContract)) == before
    assert gap() == "0"


def test_admin_contract_and_stock_require_preview_permission_and_fresh_confirmation(
    client,
):
    from test_admin_migration import admin, proposal, commit

    ah, h = admin(client)
    # No real money may come from sandbox credits; preview reserves Treasury money.
    params = dict(
        name="Recurso da Guilda",
        description="Coletar após aceitação",
        kind="collect",
        target="herb",
        required=2,
        slots=2,
        reward="20",
    )
    p = proposal(client, ah, "contracts.publish", "guild", params)
    assert p.status_code == 200, p.text
    r = commit(client, ah, p)
    assert r.status_code == 200, r.text
    assert commit(client, ah, p).json()["replayed"]
    with Session() as db:
        d = db.scalar(select(m.GuildContract))
        did = d.id
    assert client.get("/admin/contracts", headers=ah).status_code == 200
    assert client.get("/admin/contracts", headers=h).status_code == 401
    oh, _ = admin(client, "observer", "observer")
    assert proposal(client, oh, "contracts.cancel", did).status_code == 403
    # A completed right appearing after preview must invalidate the cancellation plan.
    reception(client, h)
    aid = post(client, h, f"/contracts/{did}/accept").json()["id"]
    p = proposal(client, ah, "contracts.cancel", did)
    assert p.status_code == 200, p.text
    with Session.begin() as db:
        db.get(m.CharacterContract, aid).progress = 2
    assert commit(client, ah, p).status_code == 409
    fresh = proposal(client, ah, "contracts.cancel", did)
    assert commit(client, ah, fresh).status_code == 200
    navigate(client, h, "common_a")
    node = state(client, h)["map"]["gather_nodes"][0]
    p = proposal(client, ah, "collection.disable", node["id"])
    assert p.status_code == 200, p.text
    assert commit(client, ah, p).status_code == 200
    walk_tiles(client, h, (node["x"], node["y"]))
    assert post(client, h, f"/resources/{node['id']}/collect").status_code == 409
    p = proposal(client, ah, "collection.refill", node["id"])
    assert commit(client, ah, p).status_code == 200
    assert post(client, h, f"/resources/{node['id']}/collect").status_code == 200
    assert gap() == "0"
