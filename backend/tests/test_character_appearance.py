from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import select, func
import pytest
from test_game import clean, client, state, navigate, walk_tiles
from test_cutover import fresh_lunar
from test_physical_commerce import ready, cash_inject
from app import models as m, lunar, finance, character_appearance as looks
from app.database import Session
from app.config import settings
from app.village_sites import SITES, SERVICES


def near(cid):
    with Session.begin() as db:
        c = db.get(m.Character, cid)
        c.room_id = "barber_shop"
        c.x = 10
        c.y = 9


def offer(client, h, **choices):
    now = client.get("/character/appearance", headers=h).json()
    body = {
        "appearance": {k: now[k] for k in looks.DEFAULT} | choices,
        "expected_revision": now["revision"],
    }
    r = client.post("/appearance/barber/preview", headers=h, json=body)
    assert r.status_code == 200, r.text
    return body | {"quote": r.json()["quote"], "request_id": str(uuid4())}


def payment(client, h, body):
    return client.post("/appearance/barber/confirm", headers=h, json=body)


def test_catalog_creation_unrestricted_and_strict(client):
    for sex, hair, legs in [
        ("masculino", "long_wavy", "skirt"),
        ("feminino", "short_spiky", "reinforced_trousers"),
    ]:
        token = client.post(
            "/auth/register", json={"username": sex, "password": "safe-appearance-123"}
        ).json()["token"]
        h = {"Authorization": "Bearer " + token}
        catalog = client.get("/appearance/catalog", headers=h).json()
        assert len(catalog["options"]["hair_style_id"]) == 12
        assert [
            len(catalog["options"][k])
            for k in [
                "appearance_head",
                "appearance_torso",
                "appearance_legs",
                "appearance_feet",
            ]
        ] == [6, 6, 5, 4]
        assert (
            client.post(
                "/character",
                headers=h,
                json={"name": sex, "appearance": {"skin_tone": "hacked"}},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/character",
                headers=h,
                json={"name": sex, "appearance": {"strength": 999}},
            ).status_code
            == 422
        )
        r = client.post(
            "/character",
            headers=h,
            json={
                "name": sex,
                "appearance": {
                    "sexo_visual": sex,
                    "hair_style_id": hair,
                    "appearance_legs": legs,
                },
            },
        )
        assert r.status_code == 201, r.text
        s = r.json()
        assert (
            s["appearance"]["hair_style_id"] == hair
            and s["appearance"]["appearance_legs"] == legs
        )
        assert s["character"]["strength"] == 5 and s["character"]["coins"] == 0
        assert len(s["inventory"]) == 1
        assert client.get("/state", headers=h).json()["appearance"] == s["appearance"]


def test_legacy_default_read_without_insert(client):
    ah, h, cid = ready(client)
    with Session.begin() as db:
        db.delete(db.get(m.CharacterAppearance, cid))
    assert client.get("/character/appearance", headers=h).json() == {
        "revision": 0,
        **looks.DEFAULT,
    }
    with Session() as db:
        assert db.get(m.CharacterAppearance, cid) is None


def test_barber_payment_replay_and_unchanged_stats(client):
    ah, h, cid = ready(client)
    cash_inject(client, ah, f"player:{cid}", small=3)
    near(cid)
    before = state(client, h)
    body = offer(
        client,
        h,
        hair_style_id="braid",
        sexo_visual="feminino",
        skin_tone="skin_6",
        appearance_torso="mage_robe",
    )
    r = payment(client, h, body)
    assert r.status_code == 200, r.text
    replay = payment(client, h, body)
    assert replay.status_code == 200 and replay.json()["replay"]
    with Session() as db:
        assert finance.coin_mg(db, f"player:{cid}") == 2000
        assert finance.coin_mg(db, "npc:barber") == 1000
        assert lunar.audit(db)["gap_mg"] == "0"
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.WorldEvent)
                .where(m.WorldEvent.kind == "CHARACTER_APPEARANCE_CHANGED")
            )
            == 1
        )
    after = state(client, h)
    assert (
        after["inventory"] == before["inventory"]
        and after["attributes"] == before["attributes"]
    )
    assert after["appearance"]["revision"] == 2
    bad = body | {"appearance": body["appearance"] | {"skin_tone": "skin_1"}}
    assert payment(client, h, bad).status_code == 409


def test_barber_distance_funds_and_exact_denominations(client):
    ah, h, cid = ready(client)
    r = client.post(
        "/appearance/barber/preview",
        headers=h,
        json={"appearance": {"hair_color": "silver"}, "expected_revision": 1},
    )
    assert r.status_code == 409
    near(cid)
    body = offer(client, h, hair_color="silver")
    assert "INSUFFICIENT_FUNDS" in payment(client, h, body).text
    cash_inject(client, ah, f"player:{cid}", large=1)
    assert "INSUFFICIENT_DENOMINATIONS" in payment(client, h, body).text
    with Session() as db:
        assert looks.payload(db, cid)["revision"] == 1
        assert finance.coin_mg(db, "npc:barber") == 0


def test_stale_fee_and_revision_require_new_preview(client, monkeypatch):
    ah, h, cid = ready(client)
    cash_inject(client, ah, f"player:{cid}", small=6)
    near(cid)
    a = offer(client, h, hair_color="silver")
    b = offer(client, h, hair_color="blonde")
    monkeypatch.setattr(settings, "barber_fee_units", 2)
    assert "QUOTE_CHANGED" in payment(client, h, a).text
    monkeypatch.setattr(settings, "barber_fee_units", 1)
    assert payment(client, h, a).status_code == 200
    assert "APPEARANCE_CHANGED" in payment(client, h, b).text
    assert payment(client, h, a).json()["replay"]


def test_concurrent_same_and_different_requests_do_not_double_charge(client):
    ah, h, cid = ready(client)
    cash_inject(client, ah, f"player:{cid}", small=6)
    near(cid)
    a = offer(client, h, hair_color="silver")
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: payment(client, h, a), range(2)))
    assert all(r.status_code == 200 for r in results)
    assert sum(bool(r.json()["replay"]) for r in results) == 1
    b = offer(client, h, hair_color="blonde")
    c = b | {"request_id": str(uuid4())}
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda b: payment(client, h, b), [b, c]))
    assert sorted(r.status_code for r in results) == [200, 409]
    with Session() as db:
        assert finance.coin_mg(db, "npc:barber") == 2000
        assert lunar.audit(db)["gap_mg"] == "0"


def test_barber_failure_rolls_back_cash_and_appearance(client, monkeypatch):
    ah, h, cid = ready(client)
    cash_inject(client, ah, f"player:{cid}", small=2)
    near(cid)
    body = offer(client, h, hair_color="silver")
    original = lunar.audit
    monkeypatch.setattr(lunar, "audit", lambda db: {**original(db), "gap_mg": "1"})
    assert "AUDIT_GAP" in payment(client, h, body).text
    with Session() as db:
        assert finance.coin_mg(db, "npc:barber") == 0
        assert finance.coin_mg(db, f"player:{cid}") == 2000
        assert looks.payload(db, cid)["revision"] == 1
    monkeypatch.setattr(lunar, "audit", original)
    assert payment(client, h, body).status_code == 200


def test_interiors_reachable_seed_preserves_custody_and_returns_to_door(client):
    ah, h, cid = ready(client)
    from app.seed import seed

    with Session() as db:
        before = {
            n.id: finance.cash(db, n.account_id)
            for n in db.scalars(select(m.NpcProfile))
        }
        items = [
            (i.id, i.owner, i.location, i.quantity) for i in db.scalars(select(m.Item))
        ]
    seed()
    seed()
    with Session() as db:
        assert before == {
            n.id: finance.cash(db, n.account_id)
            for n in db.scalars(select(m.NpcProfile))
        }
        assert items == [
            (i.id, i.owner, i.location, i.quantity) for i in db.scalars(select(m.Item))
        ]
    navigate(client, h, "city1")
    assert not state(client, h)["map"].get("service_npcs")
    for service in SERVICES:
        navigate(client, h, service["room_id"])
        s = state(client, h)
        assert s["room"]["safe"] and not s["map"]["enemies"]
        walk_tiles(client, h, (service["x"], service["y"]))
        r = client.post(
            "/economy/npcs/" + service["id"] + "/interact", headers=h, json={}
        )
        assert r.status_code == 200, r.text
        navigate(client, h, "city1")
        c = state(client, h)["character"]
        door = SITES[service["id"]]["door"]
        assert (c["x"], c["y"]) == (door[0], door[1] + 1)


def test_admin_fee_is_audited_and_invalidates_old_offer(client):
    from test_admin_migration import execute, proposal

    ah, h, cid = ready(client)
    cash_inject(client, ah, f"player:{cid}", small=5)
    near(cid)
    old = offer(client, h, hair_color="silver")
    for invalid in [0, -1, 1.5, True, 1001, "2"]:
        assert (
            proposal(
                client, ah, "economy.configure", "barber_fee_units", {"value": invalid}
            ).status_code
            == 422
        )
    execute(client, ah, "economy.configure", "barber_fee_units", {"value": 2})
    assert (
        client.get("/appearance/catalog", headers=h).json()["barber_fee_units"] == "2"
    )
    assert "QUOTE_CHANGED" in payment(client, h, old).text
    assert payment(client, h, offer(client, h, hair_color="silver")).status_code == 200
    with Session() as db:
        assert finance.coin_mg(db, "npc:barber") == 2000
        assert lunar.audit(db)["gap_mg"] == "0"


def test_appearance_presence_and_authorization_read_only(client):
    from app.presence import read_presence
    from test_game import player

    ah, h, cid = ready(client)
    other = player(client, "appearance_peer")
    other_id = state(client, other)["character"]["id"]
    with Session.begin() as db:
        a = db.get(m.Character, cid)
        b = db.get(m.Character, other_id)
        a.room_id = b.room_id = "city1"
        a.x = b.x = 12
        a.y = b.y = 18
        row = db.get(m.CharacterAppearance, cid)
        row.choices = {
            **row.choices,
            "hair_style_id": "ponytail",
            "sexo_visual": "masculino",
        }
    token = other["Authorization"].split()[1]
    result = read_presence(token, [cid, other_id])
    assert result[1]["players"][0]["appearance"]["hair_style_id"] == "ponytail"
    for _ in range(5):
        assert client.get("/character/appearance", headers=h).json()["revision"] == 1
    assert client.get("/character/appearance").status_code == 403
    assert client.post("/appearance/barber/confirm", json={}).status_code == 403
    assert (
        client.post(
            "/character/appearance",
            headers=h,
            json={"character_id": other_id, "hair_color": "silver"},
        ).status_code
        == 405
    )
    with Session() as db:
        assert finance.coin_mg(db, "npc:barber") == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(m.WorldEvent)
                .where(m.WorldEvent.kind == "CHARACTER_APPEARANCE_CHANGED")
            )
            == 0
        )


def test_barber_cannot_change_dead_character(client):
    ah, h, cid = ready(client)
    near(cid)
    with Session.begin() as db:
        db.get(m.Character, cid).hp = 0
    r = client.post(
        "/appearance/barber/preview",
        headers=h,
        json={"appearance": {"hair_color": "silver"}, "expected_revision": 1},
    )
    assert r.status_code == 409 and "resgate" in r.text
