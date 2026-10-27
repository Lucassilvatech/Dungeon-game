"""Preview has no writes. Confirmation rechecks the complete locked financial snapshot."""

from sqlalchemy import select, func
from . import models as m, lunar, finance
from .clock import utc_now
from .game import fail


def preview(db):
    lunar.mutex(db)
    db.scalars(select(m.Character).order_by(m.Character.id).with_for_update()).all()
    db.scalar(select(m.Treasury).where(m.Treasury.id == 1).with_for_update())
    db.scalar(select(m.CentralBank).where(m.CentralBank.id == 1).with_for_update())
    from .admin_economy import metrics

    values = {
        f"player:{c.id}": max(0, c.coins) * 1000
        for c in db.scalars(select(m.Character).order_by(m.Character.id))
    }
    debts = {
        str(c.id): max(0, -c.coins) * 1000
        for c in db.scalars(select(m.Character).order_by(m.Character.id))
    }
    values.update(
        treasury=db.get(m.Treasury, 1).balance * 1000,
        central_bank=db.get(m.CentralBank, 1).balance * 1000,
        guild=0,
    )
    auctions = [
        {
            "id": a.id,
            "status": a.status,
            "bidder": a.highest_bidder_id,
            "bid": str(a.highest_bid),
            "item": a.item_id,
            "destination": a.proceeds_destination,
        }
        for a in db.scalars(select(m.Auction).order_by(m.Auction.id))
    ]
    for a in auctions:
        if a["status"] in ("OPEN", "CLOSED"):
            values[f"auction:{a['id']}"] = int(a["bid"]) * 1000
    contracts = [
        {
            "id": c.id,
            "reserved": str(c.reserved),
            "status": c.status,
            "reward": str(c.reward),
            "slots": c.slots,
            "taken": c.taken,
        }
        for c in db.scalars(select(m.GuildContract).order_by(m.GuildContract.id))
    ]
    for c in contracts:
        values[f"contract:{c['id']}"] = int(c["reserved"]) * 1000
    for a in db.scalars(
        select(m.LunarAccount).where(m.LunarAccount.kind.in_(["npc", "guild"]))
    ):
        values.setdefault(a.id, 0)
    errors = []
    w = finance.weights(db)
    if w.get("coin_small") != 1000 or any(v % 1000 for v in w.values()):
        errors.append(
            "Denominações incompatíveis com a API histórica de gramas inteiras"
        )
    if not finance.active(db):
        if db.scalar(select(m.LunarEntry.id).limit(1)) or db.scalar(
            select(m.LunarHolding.account_id)
            .where(m.LunarHolding.quantity != 0)
            .limit(1)
        ):
            errors.append("Estado Lunar prévio não vazio exige reconciliação explícita")
        if metrics(db)["reconciliation_gap"] != "0":
            errors.append("Ledger legado não reconcilia")
    for a in auctions:
        if int(a["bid"]) and a["status"] in ("OPEN", "CLOSED") and a["bidder"] is None:
            errors.append(f"Leilão {a['id']} sem dono da reserva")
    plan = (
        {k: finance.compose(db, v) for k, v in sorted(values.items())}
        if not errors
        else {}
    )
    state = {
        "accounts_mg": {k: str(v) for k, v in sorted(values.items())},
        "debts_mg": {k: str(v) for k, v in sorted(debts.items())},
        "auctions": auctions,
        "contracts": contracts,
        "denominations": w,
        "validation_errors": errors,
        "active": finance.active(db),
        "legacy_ledger": [
            [r.reference, r.source, r.destination, str(r.amount)]
            for r in db.scalars(select(m.Ledger).order_by(m.Ledger.id))
        ],
        "acceptances": [
            [r.id, r.contract_id, r.character_id, r.progress, r.status]
            for r in db.scalars(
                select(m.CharacterContract).order_by(m.CharacterContract.id)
            )
        ],
        "recovery": [
            [r.id, r.character_id, r.item_id, str(r.price), str(r.recovered_at)]
            for r in db.scalars(select(m.RecoveryItem).order_by(m.RecoveryItem.id))
        ],
    }
    return {
        **state,
        "mode": "dry_run",
        "timestamp": utc_now().isoformat() + "Z",
        "fingerprint": lunar.fingerprint(state),
        "composition": plan,
        "genesis_backing_mg": str(sum(values.values())),
        "receivables_mg": str(sum(debts.values())),
        "holds_mg": str(
            sum(v for k, v in values.items() if k.startswith(("auction:", "contract:")))
        ),
    }


def confirm(db, fingerprint, request_id, actor, reason):
    lunar.mutex(db)
    old = db.get(m.LunarCutover, 1)
    if old:
        return {
            "status": "ALREADY_CONVERTED",
            "request_id": old.request_id,
            "report": old.report,
        }
    p = preview(db)
    if p["fingerprint"] != fingerprint:
        fail("Estado mudou; solicite novo preview")
    if p["validation_errors"]:
        fail("Cutover bloqueado: " + "; ".join(p["validation_errors"]))
    if not reason or len(reason) > 500:
        fail("Justificativa obrigatória", 422)
    postings = []
    for id, coins in p["composition"].items():
        finance.ensure(db, id)
        postings.extend((id, code, q) for code, q in coins.items())
    for id in ["npc:recovery", "sink"]:
        finance.ensure(db, id)
    for id, mass in p["debts_mg"].items():
        db.add(
            m.LunarDebt(character_id=int(id), creditor="treasury", weight_mg=int(mass))
        )
    lunar.post(
        db,
        "cutover:genesis",
        "GENESIS_BACKING",
        actor,
        reason,
        postings,
        context={"fingerprint": fingerprint, "request_id": request_id},
        source="legacy_backing",
    )
    report = finance.reconcile(db)
    if (
        report["gap_mg"] != "0"
        or report["ledger_mismatches"]
        or report["metadata_mismatches"]
    ):
        fail("Auditoria rejeitou conversão")
    db.add(
        m.LunarCutover(
            id=1,
            request_id=request_id,
            fingerprint=fingerprint,
            actor=actor,
            reason=reason,
            report={**report, "initial_debts_mg": p["debts_mg"]},
        )
    )
    db.flush()
    return {"status": "CONVERTED", "report": report}
