"""All wallet credits, escrow debits and medical fees use the character lock.
A signed wallet automatically amortizes debt; no second debt currency exists.
"""

from sqlalchemy import select
from .models import Ledger, Treasury
from .rooms import event
from .clock import utc_now

DEBT_LIMIT = 10000


def ledger(db, reference, source, destination, amount):
    db.add(
        Ledger(
            reference=reference, source=source, destination=destination, amount=amount
        )
    )


def credit_player_gold(db, c, amount, source, reference):
    if amount < 0:
        raise ValueError("Credit must be nonnegative")
    before = c.coins
    c.coins += amount
    ledger(db, reference, source, f"character:{c.id}", amount)
    repaid = min(amount, max(0, -before))
    if repaid:
        from .observability import add

        add(db, c, debt_repaid=repaid)
        event(
            db,
            "MEDICAL_DEBT_REPAID",
            c,
            reference=reference,
            amount=repaid,
            balance_before=before,
            balance_after=c.coins,
        )
    return repaid


def reserve_gold(db, c, amount, reference, auction_id):
    from .game import fail

    if c.coins <= 0 or amount <= 0 or c.coins < amount:
        fail(
            "Saldo disponível insuficiente; jogadores endividados não podem dar lances"
        )
    c.coins -= amount
    ledger(db, reference, f"character:{c.id}", f"auction:{auction_id}", amount)


def medical_fee(db, c, assessed, death_id, expedition_id):
    before = c.coins
    after = max(-DEBT_LIMIT, before - assessed)
    charged = before - after
    c.coins = after
    c.debt_accrued += max(0, -after) - max(0, -before)
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    treasury.balance += charged
    ledger(db, f"medical:{death_id}", f"character:{c.id}", "treasury", charged)
    audit = dict(
        player_id=c.id,
        expedition_id=expedition_id,
        death_event_id=death_id,
        medical_fee=assessed,
        charged=charged,
        waived=assessed - charged,
        balance_before=before,
        balance_after=after,
        reason="expedition_death",
        timestamp=utc_now().isoformat() + "Z",
        newly_financed=max(0, -after) - max(0, -before),
    )
    from .observability import add

    add(db, c, medical_fees=charged, new_medical_debt=audit["newly_financed"])
    event(db, "MEDICAL_FEE", c, key=f"medical-fee:{death_id}", **audit)
    if after < 0:
        event(db, "MEDICAL_DEBT", c, key=f"medical-debt:{death_id}", **audit)
    return audit
