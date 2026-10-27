from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import text, select
from sqlalchemy.exc import DBAPIError
from test_game import clean, client, player, state
from app.database import Session
from app import lunar, models as m


@pytest.fixture(autouse=True)
def lunar_empty(clean):
    with Session.begin() as db:
        db.execute(
            text(
                "TRUNCATE lunar_entries,lunar_holdings,lunar_accounts,lunar_assets,lunar_supply RESTART IDENTITY CASCADE"
            )
        )
        lunar.initialize(db)
        for id, kind in [
            ("treasury", "treasury"),
            ("guild", "guild"),
            ("npc:smith", "npc"),
        ]:
            lunar.account(db, id, kind)


def discover(db, owner="treasury", code="nugget_large", quantity=1, key=None):
    return lunar.post(
        db,
        key or str(uuid4()),
        "LUNAR_MINERAL_DISCOVERED",
        "server",
        "Fixture de descoberta isolada",
        [(owner, code, quantity)],
        source="discovery",
    )


@pytest.mark.parametrize(
    "source,outputs",
    [
        ("nugget_large", {"nugget_medium": 2}),
        ("nugget_large", {"nugget_small": 10}),
        ("nugget_large", {"nugget_medium": 1, "nugget_small": 5}),
        ("nugget_medium", {"nugget_small": 5}),
    ],
)
def test_split_preserves_exact_mass_and_replay(source, outputs):
    with Session.begin() as db:
        discover(db, code=source)
        before = lunar.wallet(db, "treasury")["weight_mg"]
        key = str(uuid4())
        receipt = lunar.split(db, "treasury", source, outputs, key)
        assert lunar.split(db, "treasury", source, outputs, key).id == receipt.id
        assert lunar.wallet(db, "treasury")["weight_mg"] == before
        assert lunar.audit(db)["gap_mg"] == "0"


def test_forbidden_mass_creation_fractional_and_invalid_small_split():
    for value in [True, 1.0, -1, "1"]:
        with pytest.raises(HTTPException):
            lunar.integer(value)
    with Session.begin() as db:
        discover(db, code="nugget_small")
        with pytest.raises(HTTPException):
            lunar.split(db, "treasury", "nugget_small", {"nugget_small": 1}, "bad")
        with pytest.raises(HTTPException):
            lunar.post(
                db,
                "forged",
                "COIN_TRANSFER",
                "npc",
                "Unbacked",
                [("npc:smith", "coin_large", 1)],
            )
        assert lunar.audit(db)["gap_mg"] == "0"


def test_mint_issue_exchange_transfer_and_burn_conserve_mass():
    with Session.begin() as db:
        discover(db)
        key = "mint"
        lunar.mint(db, "treasury", {"nugget_large": 1}, {"coin_large": 100}, key)
        lunar.mint(db, "treasury", {"nugget_large": 1}, {"coin_large": 100}, key)
        lunar.transfer(
            db, "treasury", "guild", {"coin_large": 50}, "issue", "COIN_ISSUE"
        )
        lunar.exchange(db, "guild", {"coin_large": 1}, {"coin_medium": 2}, "exchange")
        lunar.transfer(
            db, "guild", "npc:smith", {"coin_medium": 1}, "npc-sale", "NPC_SALE"
        )
        lunar.post(
            db,
            "ritual",
            "COIN_RITUAL_BURN",
            "npc:smith",
            "Sacrifício simulado",
            [("npc:smith", "coin_medium", -1)],
            source="destruction",
        )
        report = lunar.audit(db)
        assert report["discovered_mg"] == "1000000" and report["minted_mg"] == "1000000"
        assert (
            report["destroyed_mg"] == "5000"
            and report["coin_burned_mg"] == "5000"
            and report["gap_mg"] == "0"
        )


def test_parallel_double_spend_has_one_receipt_and_no_negative_balance():
    with Session.begin() as db:
        discover(db, code="nugget_small")
        lunar.mint(db, "treasury", {"nugget_small": 1}, {"coin_large": 10}, "mint")

    def send(_):
        try:
            with Session.begin() as db:
                lunar.transfer(
                    db, "treasury", "guild", {"coin_large": 10}, str(uuid4())
                )
            return True
        except HTTPException:
            return False

    with ThreadPoolExecutor(4) as pool:
        assert sum(pool.map(send, range(4))) == 1
    with Session() as db:
        assert lunar.audit(db)["gap_mg"] == "0"


@pytest.mark.parametrize(
    "required,expected",
    [
        (1000, {"s": 1}),
        (5000, {"m": 1}),
        (10000, {"l": 1}),
        (16000, {"l": 1, "m": 1, "s": 1}),
    ],
)
def test_exact_coin_selection(required, expected):
    assert (
        lunar.select_coins(
            {"s": 100, "m": 10, "l": 10}, {"s": 1000, "m": 5000, "l": 10000}, required
        )
        == expected
    )
    with pytest.raises(HTTPException):
        lunar.select_coins({"l": 1}, {"s": 1000, "m": 5000, "l": 10000}, 5000)


def test_ledger_cannot_be_edited_and_failed_mint_rolls_back():
    with Session.begin() as db:
        entry = discover(db)
        id = entry.id
    with pytest.raises(DBAPIError):
        with Session.begin() as db:
            db.execute(
                text("UPDATE lunar_entries SET reason=:r WHERE id=:id"),
                {"r": "tamper", "id": id},
            )
    with pytest.raises(HTTPException):
        with Session.begin() as db:
            lunar.mint(
                db, "treasury", {"nugget_large": 1}, {"coin_large": 101}, "bad-mint"
            )
    with Session() as db:
        assert (
            lunar.wallet(db, "treasury")["weight_mg"] == "1000000"
            and lunar.audit(db)["gap_mg"] == "0"
        )


def test_wallet_ownership_strict_request_and_legacy_preview_are_read_only(client):
    h = player(client)
    other = player(client, "other")
    c = state(client, h)["character"]["id"]
    with Session.begin() as db:
        lunar.account(db, f"player:{c}", "player", c)
        discover(db, f"player:{c}")
    body = {
        "request_id": str(uuid4()),
        "source": "nugget_large",
        "outputs": {"nugget_medium": 2},
    }
    assert (
        client.post("/lunar/nuggets/split", headers=other, json=body).status_code == 409
    )
    assert client.post("/lunar/nuggets/split", headers=h, json=body).status_code == 200
    assert client.post("/lunar/nuggets/split", headers=h, json=body).status_code == 200
    body["outputs"] = {"nugget_medium": 2.0}
    assert client.post("/lunar/nuggets/split", headers=h, json=body).status_code == 422
    assert client.get("/lunar/wallet", headers=h).json()["weight_mg"] == "1000000"
    with Session.begin() as db:
        before = lunar.audit(db)
        preview = lunar.legacy_preview(db)
        assert (
            preview["legacy_coin_unit_weight_mg"] == "1000"
            and not preview["conversion_active"]
        )
        assert lunar.audit(db) == before


def test_denomination_configuration_freezes_and_audit_detects_state_tampering(caplog):
    with Session.begin() as db:
        lunar.configure_empty_denominations(
            db, {"coin_small": 2000, "coin_medium": 10000, "coin_large": 20000}
        )
        discover(db)
        with pytest.raises(HTTPException):
            lunar.configure_empty_denominations(
                db, {"coin_small": 1000, "coin_medium": 5000, "coin_large": 10000}
            )
        db.get(m.LunarHolding, ("treasury", "nugget_large")).quantity = 2
        report = lunar.audit(db)
        assert report["gap_mg"] == "1000000" and report["ledger_mismatches"]
        assert "lunar_mass_invariant_failed" in caplog.text
