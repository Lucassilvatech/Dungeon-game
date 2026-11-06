"""Debt enforcement uses units, funded Guild purchases, and cumulative new-debt milestones."""

from datetime import timedelta
from sqlalchemy import select
from .models import DebtCollection, Auction, Treasury
from .recovery import eligible, detach_units
from .economy import credit_player_gold
from .finance import active, funds, institution, debt_units
from .rooms import event
from .clock import utc_now
from .config import runtime_setting


def select_units(rows, debt):
    """Minimum cardinality: take largest units until cover; improve surplus by swaps.
    Stable ties use item ID. All available units when unable to cover. No death cap.
    Bounded whole-stack counts avoid inventory expansion and exponential subset search.
    """
    candidates = sorted(
        [(i, d, d.base_value or 0) for i, d in rows if (d.base_value or 0) > 0],
        key=lambda row: (-row[2], row[0].id),
    )
    selected = {}
    total = 0
    for item, d, value in candidates:
        count = min(item.quantity, max(0, (debt - total + value - 1) // value))
        if count:
            selected[item.id] = count
            total += count * value
        if total >= debt:
            break
    if total >= debt:
        # Local strict improvements preserve minimum item count and never uncover debt.
        for _ in range(len(candidates)):
            changed = False
            for old, _, old_value in candidates:
                if not selected.get(old.id):
                    continue
                for new, _, new_value in reversed(candidates):
                    excess = total - debt
                    if (
                        new.id != old.id
                        and selected.get(new.id, 0) < new.quantity
                        and 0 < old_value - new_value <= excess
                    ):
                        count = min(
                            selected[old.id],
                            new.quantity - selected.get(new.id, 0),
                            excess // (old_value - new_value),
                        )
                        selected[old.id] -= count
                        selected[new.id] = selected.get(new.id, 0) + count
                        total -= count * (old_value - new_value)
                        changed = True
            if not changed:
                break
    return [
        (i, d, selected[i.id]) for i, d, _ in candidates if selected.get(i.id)
    ], total


def collect(db, c):
    debt = debt_units(db, c)
    if debt < 1000 or c.debt_accrued < c.debt_next_collection:
        return None
    rows, total = select_units(eligible(db, c), debt)
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    from . import finance

    if total > institution(db, "treasury") or (
        active(db) and not finance.payment_quote(db, "treasury", total)["payable"]
    ):
        event(
            db,
            "DEBT_COLLECTION_DEFERRED",
            c,
            reason="Guilda precisa financiar avaliação; nenhuma moeda emitida",
            assessed=str(total),
        )
        return None
    record = DebtCollection(
        character_id=c.id,
        accrued_checkpoint=c.debt_accrued,
        debt_before=debt,
        debt_after=max(0, debt - total),
        assessed=total,
        surplus=max(0, total - debt),
        items=[],
    )
    db.add(record)
    db.flush()
    c.debt_next_collection = c.debt_accrued + 1000
    items = []
    for item, definition, count in rows:
        item = detach_units(db, item, count)
        item.location = "auction"
        assessed = (definition.base_value or 0) * count
        a = Auction(
            item_id=item.id,
            quantity=count,
            death_event_id=None,
            former_owner_id=c.id,
            opening_price=max(
                runtime_setting(db, "min_auction_start_price"), (assessed + 4) // 5
            ),
            ends_at=utc_now()
            + timedelta(hours=runtime_setting(db, "auction_duration_hours")),
            proceeds_destination="treasury",
            origin="guild_debt",
            assessed_value=assessed,
        )
        db.add(a)
        db.flush()
        items.append(
            {
                "item_id": item.id,
                "quantity": count,
                "assessed": str(assessed),
                "auction_id": a.id,
            }
        )
    if not active(db):
        treasury.balance -= total
    credit_player_gold(db, c, total, "treasury", f"debt-collection:{record.id}")
    if active(db):
        record.debt_after = debt_units(db, c)
        record.surplus = max(0, total - (debt - record.debt_after))
    record.items = items
    event(
        db,
        "GUILD_DEBT_COLLECTION",
        c,
        key=f"debt-collection:{record.id}",
        collection_id=record.id,
        debt_before=str(debt),
        debt_repaid=str(debt - record.debt_after),
        assessed=str(total),
        surplus=str(record.surplus),
        next_accrued=str(c.debt_next_collection),
        items=items,
    )
    return record
