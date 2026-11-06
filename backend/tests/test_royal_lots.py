from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import os, json, subprocess, hashlib
from pathlib import Path
import pytest, psycopg
from sqlalchemy import select, text, func, create_engine
from sqlalchemy.orm import Session as SASession
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
from test_game import clean, client, state, player
from test_cutover import fresh_lunar, convert
from test_admin_migration import admin, proposal, commit, execute
from test_expeditions import begin
from test_lunar_resources import at_guild
from app import (
    models as m,
    mineral_lots as lots,
    lunar_resources as resources,
    lunar,
    finance,
)
from app.database import Session
from app.config import settings, Settings


def ready(client):
    ah, h = admin(client)
    convert()
    cid = state(client, h)["character"]["id"]
    return ah, h, cid


def injection(client, ah, owner, grams):
    execute(
        client,
        ah,
        "royal.injection",
        owner,
        {"grams": grams, "coins": {}, "strong_confirmation": "INJETAR"},
    )
    with Session() as db:
        return lots.held(db, owner)[-1].id


def invariant():
    with Session() as db:
        r = finance.reconcile(db)
        assert (
            r["gap_mg"] == "0"
            and not r["ledger_mismatches"]
            and not r["metadata_mismatches"]
        ), r
        return r


def collect_weight(client, mp, h, weight):
    mp.setattr(resources, "roll", lambda *args: ("b" * 64, weight))
    s = begin(client, h, mp)
    r = s["map"]["lunar_resources"][0]
    with Session.begin() as db:
        c = db.get(m.Character, s["character"]["id"])
        c.x, c.y = r["x"], r["y"]
    response = client.post(
        f"/expeditions/{r['expedition_id']}/lunar-resources/{r['id']}/collect",
        headers=h,
        json={"request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()["lot_id"], r


def test_definitive_defaults_and_statistical_generation():
    cfg = Settings(_env_file=None)
    assert (
        cfg.lunar_resource_spawn_enabled
        and cfg.lunar_resource_spawn_chance_ppm == 20000
    )
    assert (
        cfg.lunar_guild_buy_rate_milliunits_per_gram == 800
        and cfg.royal_admin_extraordinary_controls_enabled
    )
    conf = {
        k: getattr(cfg, k)
        for k in [
            "lunar_resource_spawn_enabled",
            "lunar_resource_spawn_chance_ppm",
            "lunar_resource_weight_bands",
        ]
    }
    result = [resources.roll(i, f"stat:{i}", 77, 0, conf)[1] for i in range(100000)]
    weights = [w // 1000 for w in result if w]
    assert 1750 < len(weights) < 2250
    counts = [
        sum(lo <= w <= hi for w in weights)
        for lo, hi in [(100, 200), (201, 700), (701, 1000)]
    ]
    assert (
        abs(counts[0] / len(weights) - 0.8) < 0.04
        and abs(counts[1] / len(weights) - 0.15) < 0.035
        and abs(counts[2] / len(weights) - 0.05) < 0.025
    )
    assert all(100 <= w <= 1000 for w in weights)
    assert result == [
        resources.roll(i, f"stat:{i}", 77, 0, conf)[1] for i in range(100000)
    ]
    for band in range(3):
        bands = [
            {**b, "percent": 100 if i == band else 0}
            for i, b in enumerate(cfg.lunar_resource_weight_bands)
        ]
        conf = {
            **conf,
            "lunar_resource_spawn_chance_ppm": 1000000,
            "lunar_resource_weight_bands": bands,
        }
        values = {
            resources.roll(i, f"bounds:{i}", 12, 0, conf)[1] // 1000
            for i in range(10000)
        }
        assert (
            min(values) == bands[band]["min_g"] and max(values) == bands[band]["max_g"]
        )


@pytest.mark.parametrize("weight", [143000, 684000, 917000, 1000000])
def test_variable_collection_individual_identity_and_retry(client, monkeypatch, weight):
    ah, h, cid = ready(client)
    id, r = collect_weight(client, monkeypatch, h, weight)
    with Session() as db:
        row = db.get(m.LunarMineralLot, id)
        assert (
            row.weight_mg == weight
            and row.owner_account_id == f"player:{cid}"
            and row.origin_occurrence_id == r["id"]
        )
        entry = db.get(m.LunarEntry, row.source_entry_id)
        assert (
            entry.kind == "DISCOVERED_MINERAL"
            and entry.postings[0]["quantity"] == weight
        )
        assert db.get(m.LunarSupply, 1).discovered_mg == weight
        g = db.get(m.LunarResourceGeneration, r["expedition_id"])
        assert g.config_snapshot["selected_weight_mg"] == str(weight)
        key = db.get(m.LunarResourceOccurrence, r["id"]).receipt_key.split(":")[-1]
    response = client.post(
        f"/expeditions/{r['expedition_id']}/lunar-resources/{r['id']}/collect",
        headers=h,
        json={"request_id": key},
    )
    assert response.json()["replayed"]
    assert client.get("/lunar/wallet", headers=h).json()["mineral_weight_mg"] == str(
        weight
    )
    invariant()


@pytest.mark.parametrize(
    "weight,parts", [(684, [500, 184]), (684, [300, 200, 184]), (100, [1, 99])]
)
def test_free_splitting_lineage_and_idempotence(client, weight, parts):
    ah, h, cid = ready(client)
    owner = f"player:{cid}"
    id = injection(client, ah, owner, weight)
    body = {"request_id": str(uuid4()), "fragments_g": parts}
    path = f"/lunar/lots/{id}/split"
    assert client.post(path, headers=h, json=body).status_code == 200
    assert client.post(path, headers=h, json=body).status_code == 200
    assert (
        client.post(
            path, headers=h, json={**body, "request_id": str(uuid4())}
        ).status_code
        == 409
    )
    data = client.get(f"/admin/lunar/lots/{id}/lineage", headers=ah).json()
    assert data["root_id"] == id and len(data["lots"]) == len(parts) + 1
    assert sorted(
        r["weight_g"] for r in data["lots"] if r["state"] == "HELD"
    ) == sorted(parts)
    assert any(e["kind"] == "MINERAL_SPLIT" for e in data["history"])
    invariant()


def test_split_validation_ownership_capacity_and_concurrency(client, monkeypatch):
    ah, h, cid = ready(client)
    id = injection(client, ah, f"player:{cid}", 100)
    other = player(client, "external")
    assert (
        client.post(
            f"/lunar/lots/{id}/split",
            headers=other,
            json={"request_id": str(uuid4()), "fragments_g": [1, 99]},
        ).status_code
        == 404
    )
    for parts in [[0, 100], [-1, 101], [70, 29], [1.0, 99], ["1", 99]]:
        assert (
            client.post(
                f"/lunar/lots/{id}/split",
                headers=h,
                json={"request_id": str(uuid4()), "fragments_g": parts},
            ).status_code
            == 422
        )
    monkeypatch.setattr(settings, "collection_slots", 3)
    body = {"request_id": str(uuid4()), "fragments_g": [1, 99]}
    assert (
        client.post(f"/lunar/lots/{id}/split", headers=h, json=body).status_code == 409
    )
    monkeypatch.setattr(settings, "collection_slots", 4)

    def run(_):
        return client.post(
            f"/lunar/lots/{id}/split",
            headers=h,
            json={"request_id": str(uuid4()), "fragments_g": [1, 99]},
        ).status_code

    with ThreadPoolExecutor(3) as pool:
        answers = list(pool.map(run, range(3)))
    assert answers.count(200) == 1 and answers.count(409) == 2
    invariant()


@pytest.mark.parametrize(
    "grams,expected", [(100, 80), (143, 114), (500, 400), (684, 547), (1000, 800)]
)
def test_integer_price_examples(grams, expected):
    assert resources.price(grams * 1000, 800) == expected


def test_no_rounding_arbitrage():
    for rate in [0, 1, 799, 800, 999, 1000, 1307]:
        for g in range(2, 1001):
            for a in range(1, g, 7):
                assert resources.price(a * 1000, rate) + resources.price(
                    (g - a) * 1000, rate
                ) <= resources.price(g * 1000, rate)


def test_guild_rate_versions_cash_and_identity(client):
    ah, h, cid = ready(client)
    id = injection(client, ah, f"player:{cid}", 684)
    at_guild(client, h)
    q = client.get("/lunar/guild-quotes", headers=h).json()["quotes"][0]
    assert q["price_units"] == "547" and q["rate"] == 800
    body = {"request_id": str(uuid4()), "lot_id": id, "quote": q["quote_hash"]}
    assert client.post("/lunar/guild-sell", headers=h, json=body).status_code == 409
    # Treasury must explicitly obtain small/medium pieces before funding547.
    execute(
        client,
        ah,
        "royal.exchange",
        "treasury",
        {"inputs": {"coin_large": 1}, "outputs": {"coin_medium": 1, "coin_small": 5}},
    )
    execute(
        client,
        ah,
        "royal.transfer_coins",
        "treasury",
        {"destination": "guild", "amount_units": 547},
    )
    execute(
        client,
        ah,
        "economy.configure",
        "lunar_guild_buy_rate_milliunits_per_gram",
        {"value": 999},
    )
    assert client.post("/lunar/guild-sell", headers=h, json=body).status_code == 409
    execute(
        client,
        ah,
        "economy.configure",
        "lunar_guild_buy_rate_milliunits_per_gram",
        {"value": 800},
    )
    assert (
        client.post("/lunar/guild-sell", headers=h, json=body).status_code == 409
    )  # revision prevents old quote revival
    q = client.get("/lunar/guild-quotes", headers=h).json()["quotes"][0]
    body["quote"] = q["quote_hash"]
    assert client.post("/lunar/guild-sell", headers=h, json=body).status_code == 200
    execute(
        client,
        ah,
        "economy.configure",
        "lunar_guild_buy_rate_milliunits_per_gram",
        {"value": 801},
    )
    assert client.post("/lunar/guild-sell", headers=h, json=body).json()["replayed"]
    with Session() as db:
        assert db.get(m.LunarMineralLot, id).owner_account_id == "guild"
        assert finance.coin_mg(db, "guild") == 0
        b = lunar.balances(db, f"player:{cid}")
        assert b["coin_large"] == 54 and b["coin_medium"] == 1 and b["coin_small"] == 2
    invariant()


def test_manual_mint_partial_lot_exact_denominations_and_replay(client):
    ah, h, cid = ready(client)
    id = injection(client, ah, "treasury", 684)
    with Session() as db:
        before = lunar.balances(db, "treasury")
    p = proposal(
        client,
        ah,
        "royal.mint",
        "treasury",
        {"coins": {"coin_large": 30, "coin_medium": 20, "coin_small": 37}},
    )
    assert p.status_code == 200, p.text
    assert p.json()["before"]["mint_plan"] == [
        {"lot_id": id, "consume_mg": "437000", "remaining_mg": "247000"}
    ]
    assert commit(client, ah, p).status_code == 200
    assert commit(client, ah, p).json()["replayed"]
    with Session() as db:
        assert lots.mass(db, "treasury") == 247000
        assert db.get(m.LunarMineralLot, id).state == "SPLIT"
        assert db.get(m.LunarSupply, 1).minted_mg == 437000
        now = lunar.balances(db, "treasury")
        assert all(
            now.get(a, 0) - before.get(a, 0) == q
            for a, q in [("coin_large", 30), ("coin_medium", 20), ("coin_small", 37)]
        )
        children = db.scalars(
            select(m.LunarMineralLot).where(m.LunarMineralLot.parent_lot_id == id)
        ).all()
        assert {(r.weight_mg, r.state) for r in children} == {
            (437000, "MINTED"),
            (247000, "HELD"),
        }
    invariant()


def test_royal_conservation_chain_collect_split_sell_transfer_mint_burn(
    client, monkeypatch
):
    ah, h, cid = ready(client)
    root, r = collect_weight(client, monkeypatch, h, 684000)
    assert (
        client.post(
            f"/lunar/lots/{root}/split",
            headers=h,
            json={"request_id": str(uuid4()), "fragments_g": [500, 184]},
        ).status_code
        == 200
    )
    at_guild(client, h)
    execute(
        client,
        ah,
        "royal.transfer_coins",
        "treasury",
        {"destination": "guild", "amount_units": 400},
    )
    q = next(
        q
        for q in client.get("/lunar/guild-quotes", headers=h).json()["quotes"]
        if q["weight_g"] == 500
    )
    assert (
        client.post(
            "/lunar/guild-sell",
            headers=h,
            json={
                "request_id": str(uuid4()),
                "lot_id": q["lot_id"],
                "quote": q["quote_hash"],
            },
        ).status_code
        == 200
    )
    execute(
        client,
        ah,
        "royal.transfer_lot",
        "guild",
        {"lot_id": q["lot_id"], "destination": "treasury"},
    )
    execute(
        client,
        ah,
        "royal.mint",
        "treasury",
        {"coins": {"coin_large": 30, "coin_medium": 20, "coin_small": 37}},
    )
    execute(
        client,
        ah,
        "royal.transfer_coins",
        "treasury",
        {"destination": f"player:{cid}", "amount_units": 10},
    )
    execute(
        client,
        ah,
        "royal.burn",
        "treasury",
        {"grams": 10, "coins": {"coin_large": 1}, "strong_confirmation": "DESTRUIR"},
    )
    a = invariant()
    assert (
        a["discovered_mg"] == "684000"
        and a["admin_injected_mg"] == "0"
        and a["destroyed_mg"] == "20000"
    )
    lineage = client.get(f"/admin/lunar/lots/{root}/lineage", headers=ah).json()
    assert (
        lineage["origin_occurrence"]["id"] == r["id"]
        and lineage["origin_occurrence"]["collector"] == cid
    )
    assert {
        "DISCOVERED_MINERAL",
        "MINERAL_SPLIT",
        "MINERAL_SALE",
        "MINERAL_TRANSFER",
        "MINT",
        "ADMIN_BURN",
    } <= {e["kind"] for e in lineage["history"]}


def test_admin_confiscation_injection_burn_flag_and_permissions(client):
    ah, h, cid = ready(client)
    owner = f"player:{cid}"
    id = injection(client, ah, owner, 100)
    execute(
        client,
        ah,
        "royal.transfer_lot",
        owner,
        {"lot_id": id, "destination": "treasury"},
    )
    with Session() as db:
        assert db.get(m.LunarMineralLot, id).owner_account_id == "treasury"
    execute(
        client,
        ah,
        "royal.injection",
        "treasury",
        {"grams": 111, "coins": {"coin_large": 5}, "strong_confirmation": "INJETAR"},
    )
    a = invariant()
    assert a["admin_injected_mg"] == "261000" and a["discovered_mg"] == "0"
    assert (
        proposal(
            client,
            ah,
            "royal.burn",
            "treasury",
            {"grams": 1, "coins": {}, "strong_confirmation": "no"},
        ).status_code
        == 422
    )
    execute(
        client,
        ah,
        "royal.burn",
        "treasury",
        {"grams": 10, "coins": {"coin_large": 2}, "strong_confirmation": "DESTRUIR"},
    )
    assert invariant()["destroyed_mg"] == "30000"
    reader, _ = admin(client, "observer", "reader")
    assert client.get("/admin/royal", headers=reader).status_code == 200
    assert (
        proposal(
            client,
            reader,
            "royal.injection",
            "treasury",
            {"grams": 1, "strong_confirmation": "INJETAR"},
        ).status_code
        == 403
    )
    assert client.get("/admin/royal", headers=h).status_code == 401
    assert client.get("/admin/royal", headers={"X-Bot-Key": "fake"}).status_code in (
        401,
        403,
    )
    execute(
        client,
        ah,
        "economy.configure",
        "royal_admin_extraordinary_controls_enabled",
        {"value": False},
    )
    assert (
        proposal(
            client,
            ah,
            "royal.injection",
            "treasury",
            {"grams": 1, "coins": {}, "strong_confirmation": "INJETAR"},
        ).status_code
        == 403
    )
    assert (
        proposal(
            client,
            ah,
            "royal.burn",
            "treasury",
            {"grams": 1, "coins": {}, "strong_confirmation": "DESTRUIR"},
        ).status_code
        == 403
    )


def test_stale_preview_rollback_and_lot_sql_guards(client, monkeypatch):
    ah, h, cid = ready(client)
    id = injection(client, ah, "treasury", 100)
    old = proposal(
        client,
        ah,
        "royal.transfer_lot",
        "treasury",
        {"lot_id": id, "destination": "guild"},
    )
    execute(
        client,
        ah,
        "royal.transfer_lot",
        "treasury",
        {"lot_id": id, "destination": f"player:{cid}"},
    )
    assert commit(client, ah, old).status_code == 409
    before = invariant()["admin_injected_mg"]
    p = proposal(
        client,
        ah,
        "royal.injection",
        "treasury",
        {"grams": 9, "coins": {}, "strong_confirmation": "INJETAR"},
    )
    with monkeypatch.context() as mp:
        mp.setattr(
            resources,
            "assert_audit",
            lambda db: (_ for _ in ()).throw(HTTPException(409, "rollback proof")),
        )
        assert commit(client, ah, p).status_code == 409
    assert invariant()["admin_injected_mg"] == before
    for sql in [
        "UPDATE lunar_mineral_lots SET weight_mg=1000",
        "DELETE FROM lunar_mineral_lots",
    ]:
        with pytest.raises(DBAPIError):
            with Session.begin() as db:
                db.execute(text(sql))
    invariant()


def test_post_collection_discord_observation_is_pure(client, monkeypatch):
    ah, h, cid = ready(client)
    id, r = collect_weight(client, monkeypatch, h, 143000)
    with Session.begin() as db:
        db.get(m.Account, db.get(m.Character, cid).account_id).discord_id = "987654321"
    from app.discord_client import query

    with Session() as db:
        before = db.scalar(select(func.count()).select_from(m.LunarEntry))
    for section in ["mineral", "wallet", "inventory", "expedition", "map"]:
        with Session.begin() as db:
            q = query(db, "987654321", section)
            if section == "mineral":
                assert (
                    q["lots"][0]["lot_id"] == id and q["mineral_weight_mg"] == "143000"
                )
            if section == "inventory":
                assert q["mineral_inventory"][0]["lot_id"] == id
            assert "lunar_resources" not in q
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(m.LunarEntry)) == before


def test_fixed_nugget_migration_preserves_mass_owners_and_historical_ledger(tmp_path):
    # A separate old-schema PostgreSQL, never the active fixture database or production.
    name = "royal_migration_" + uuid4().hex[:10]
    with psycopg.connect(
        "postgresql://tower:tower@localhost:5432/postgres", autocommit=True
    ) as c:
        c.execute("CREATE DATABASE " + name)
    url = "postgresql+psycopg://tower:tower@localhost:5432/" + name
    env = {**os.environ, "DATABASE_URL": url}
    root = Path(__file__).resolve().parents[2]
    python = root / ".venv/bin/alembic"
    if not python.exists():
        python = "alembic"
    subprocess.run(
        [str(python), "upgrade", "7f422c075115"],
        cwd=root / "backend",
        env=env,
        check=True,
        capture_output=True,
    )
    e = create_engine(url)
    with SASession(e) as db, db.begin():
        if not db.get(m.Floor, 1):
            db.add(m.Floor(id=1, name="Fixture"))
        db.flush()
        if not db.get(m.Room, "city1"):
            db.add(m.Room(id="city1", floor_id=1, name="Fixture", kind="CITY", data={}))
        db.flush()
        a = m.Account(username="migration", password="test-unused")
        db.add(a)
        db.flush()
        c = m.Character(account_id=a.id, name="Migration")
        db.add(c)
        db.flush()
        cid = c.id
    with psycopg.connect("postgresql://tower:tower@localhost:5432/" + name) as c:
        for code, (kind, weight) in lunar.ASSETS.items():
            if code != "mineral_mg":
                c.execute(
                    "INSERT INTO lunar_assets(code,kind,weight_mg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (code, kind, weight),
                )
        for owner, kind, char in [
            (f"player:{cid}", "player", cid),
            ("guild", "guild", None),
            ("treasury", "treasury", None),
            ("npc:fixture", "npc", None),
        ]:
            c.execute(
                "INSERT INTO lunar_accounts(id,kind,character_id) VALUES (%s,%s,%s)",
                (owner, kind, char),
            )
        c.execute("UPDATE lunar_supply SET discovered_mg=1700000")
        posts = [
            {"account": f"player:{cid}", "asset": "nugget_small", "quantity": 2},
            {"account": "guild", "asset": "nugget_medium", "quantity": 1},
            {"account": "treasury", "asset": "nugget_large", "quantity": 1},
        ]
        for p in posts:
            c.execute(
                "INSERT INTO lunar_holdings(account_id,asset_code,quantity) VALUES (%s,%s,%s)",
                (p["account"], p["asset"], p["quantity"]),
            )
        c.execute(
            "INSERT INTO lunar_entries(key,kind,actor,reason,fingerprint,postings,context,created_at) VALUES ('fixture','LUNAR_MINERAL_DISCOVERED','test','Historical fixture',%s,%s::json,'{}',timezone('utc',now()))",
            ("1" * 64, json.dumps(posts)),
        )
        prior = c.execute(
            "SELECT row_to_json(r)::text FROM lunar_entries r"
        ).fetchone()[0]
    subprocess.run(
        [str(python), "upgrade", "head"],
        cwd=root / "backend",
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [str(python), "check"],
        cwd=root / "backend",
        env=env,
        check=True,
        capture_output=True,
    )
    with SASession(e) as db:
        rows = lots.held(db)
        assert len(rows) == 4 and sum(r.weight_mg for r in rows) == 1700000
        assert sorted((r.owner_account_id, r.weight_mg) for r in rows) == sorted(
            [
                (f"player:{cid}", 100000),
                (f"player:{cid}", 100000),
                ("guild", 500000),
                ("treasury", 1000000),
            ]
        )
        assert db.scalar(select(func.sum(m.LunarHolding.quantity))) == 0
        assert lunar.audit(db)["gap_mg"] == "0"
        assert (
            db.execute(
                text(
                    "SELECT row_to_json(r)::text FROM lunar_entries r WHERE key='fixture'"
                )
            ).scalar()
            == prior
        )
    e.dispose()


def test_available_legacy_occurrence_collects_into_new_individual_lot(
    client, monkeypatch
):
    from sqlalchemy import event

    ah, h, cid = ready(client)

    def legacy_asset(mapper, connection, target):
        target.asset_code = "nugget_small"

    event.listen(m.LunarResourceOccurrence, "before_insert", legacy_asset)
    try:
        id, r = collect_weight(client, monkeypatch, h, 100000)
    finally:
        event.remove(m.LunarResourceOccurrence, "before_insert", legacy_asset)
    with Session() as db:
        old = db.get(m.LunarResourceOccurrence, r["id"])
        assert old.asset_code == "nugget_small" and old.state == "COLLECTED"
        lot = db.get(m.LunarMineralLot, id)
        assert lot.origin_occurrence_id == old.id and lot.weight_mg == 100000
        entry = db.get(m.LunarEntry, lot.source_entry_id)
        assert entry.postings == [
            {"account": f"player:{cid}", "asset": "mineral_mg", "quantity": 100000}
        ]
    invariant()
