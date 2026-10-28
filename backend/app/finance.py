"""Operational facade: historical unit = 1g; holdings are authoritative, legacy frozen.
All writes lock financial -> lunar -> characters. No unbacked credit or common burn.
"""

from sqlalchemy import select, func
from . import models as m, lunar
from fastapi import HTTPException


def fail(message, code=409):
    raise HTTPException(code, message)


from .clock import utc_now

UNIT = 1000


def active(db):
    return bool(db.scalar(select(m.LunarCutover.id).where(m.LunarCutover.id == 1)))


def normalize(id):
    return id.replace("character:", "player:", 1) if id.startswith("character:") else id


def ensure(db, id):
    id = normalize(id)
    if not db.get(m.LunarAccount, id):
        kind = (
            "player"
            if id.startswith("player:")
            else (
                "escrow"
                if id.startswith(("auction:", "contract:"))
                else (
                    "guild"
                    if id == "guild"
                    else (
                        "treasury"
                        if id in ("treasury", "central_bank", "sink")
                        else "npc"
                    )
                )
            )
        )
        lunar.account(db, id, kind, int(id.split(":")[1]) if kind == "player" else None)
    return id


def weights(db):
    return {
        a.code: a.weight_mg
        for a in db.scalars(select(m.LunarAsset).where(m.LunarAsset.kind == "coin"))
    }


def compose(db, mass):
    result = {}
    for code, weight in sorted(weights(db).items(), key=lambda kv: -kv[1]):
        q, mass = divmod(mass, weight)
        if q:
            result[code] = q
    if mass:
        fail("Massa não representável sem arredondamento")
    return result


def coin_mg(db, id):
    return int(
        db.scalar(
            select(
                func.coalesce(
                    func.sum(m.LunarHolding.quantity * m.LunarAsset.weight_mg), 0
                )
            )
            .join(m.LunarAsset, m.LunarAsset.code == m.LunarHolding.asset_code)
            .where(
                m.LunarHolding.account_id == normalize(id), m.LunarAsset.kind == "coin"
            )
        )
    )


def debt_mg(db, c):
    row = db.get(m.LunarDebt, c.id)
    return row.weight_mg if row else 0


def debt_units(db, c):
    return debt_mg(db, c) // UNIT if active(db) else max(0, -c.coins)


def funds(db, c):
    return (
        (coin_mg(db, f"player:{c.id}") - debt_mg(db, c)) // UNIT
        if active(db)
        else c.coins
    )


def institution(db, id):
    if active(db):
        return coin_mg(db, id) // UNIT
    if id == "treasury":
        return db.get(m.Treasury, 1).balance
    if id == "central_bank":
        return db.get(m.CentralBank, 1).balance
    return 0


def debt(db, c):
    row = db.get(m.LunarDebt, c.id)
    if not row:
        row = m.LunarDebt(character_id=c.id, creditor="treasury", weight_mg=0)
        db.add(row)
        db.flush()
    return row


def move(db, source, target, units, key, *, amortize=True, actor=None, reason=None):
    lunar.mutex(db)
    lunar.integer(units)
    if source in ("mint", "initial_supply", "burn"):
        fail("Fonte sem lastro físico")
    source, target = ensure(db, source), ensure(db, target)
    old = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == key))
    parameters = [source, target, units, amortize]
    if old:
        if old.context.get("parameters") != parameters:
            fail("Referência financeira já usada com outros valores")
        if (actor is not None and old.actor != actor) or (
            reason is not None and old.reason != reason
        ):
            fail("Referência financeira já vinculada a outro ator ou justificativa")
        return old
    if source == target:
        fail("Origem e destino devem diferir")
    mass = units * UNIT
    if coin_mg(db, source) < mass:
        fail("Saldo físico insuficiente")
    changes = {source: -mass, target: mass}
    repaid = 0
    if amortize and target.startswith("player:"):
        c = db.get(m.Character, int(target.split(":")[1]))
        ob = debt(db, c)
        repaid = min(mass, ob.weight_mg)
        if repaid:
            changes[target] -= repaid
            changes["treasury"] = changes.get("treasury", 0) + repaid
    postings = []
    for owner, delta in sorted(changes.items()):
        before = lunar.balances(db, owner)
        after = compose(db, coin_mg(db, owner) + delta)
        postings.extend(
            (owner, code, after.get(code, 0) - before.get(code, 0))
            for code in weights(db)
        )
    result = lunar.post(
        db,
        key,
        (
            "DEBT_SETTLEMENT"
            if repaid
            else "ZERO_TRANSFER" if units == 0 else "COIN_TRANSFER"
        ),
        actor or source,
        reason or "Pagamento físico com origem explícita",
        postings,
        context={"parameters": parameters, "debt_repaid_mg": str(repaid)},
    )
    if repaid:
        ob.weight_mg -= repaid
    return result


def fee(db, c, assessed, reference):
    lunar.mutex(db)
    old = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == reference))
    if old:
        return old.context["fee"]
    before = funds(db, c)
    available = coin_mg(db, f"player:{c.id}") // UNIT
    paid = min(available, assessed)
    ob = debt(db, c)
    financed = min(assessed - paid, max(0, 10000 - ob.weight_mg // UNIT))
    if paid:
        move(
            db, f"player:{c.id}", "treasury", paid, reference + ":paid", amortize=False
        )
    ob.weight_mg += financed * UNIT
    c.debt_accrued += financed
    result = {
        "medical_fee": assessed,
        "charged": paid + financed,
        "paid": paid,
        "newly_financed": financed,
        "waived": assessed - paid - financed,
        "balance_before": before,
        "balance_after": funds(db, c),
    }
    lunar.post(
        db,
        reference,
        "MEDICAL_OBLIGATION",
        f"player:{c.id}",
        "Taxa paga e obrigação financiada separadas",
        [],
        context={"fee": result},
    )
    return result


def settle_debt(db, c, units, key):
    lunar.mutex(db)
    old = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == key))
    if old:
        if old.context.get("parameters") != [
            f"player:{c.id}",
            "treasury",
            units,
            False,
        ]:
            fail("Chave de pagamento já utilizada")
        return old
    lunar.integer(units, True)
    if units > debt_mg(db, c) // UNIT:
        fail("Pagamento excede a dívida")
    amount = units
    result = move(db, f"player:{c.id}", "treasury", amount, key, amortize=False)
    if not result.context.get("debt_settled"):
        # Receipt must contain amount at creation; do not edit append-only history.
        ob = debt(db, c)
        ob.weight_mg -= amount * UNIT
        lunar.post(
            db,
            key + ":debt",
            "DEBT_REPAYMENT",
            f"player:{c.id}",
            "Baixa simultânea de obrigação e recebível",
            [],
            context={"character_id": c.id, "weight_mg": str(amount * UNIT)},
        )
    return result


def metrics(db):
    from .game import reward_value

    report = reconcile(db)
    groups = {kind: 0 for kind in ["player", "treasury", "guild", "npc", "escrow"]}
    for a in db.scalars(select(m.LunarAccount)):
        groups[a.kind] = groups.get(a.kind, 0) + coin_mg(db, a.id)
    obligations = int(
        db.scalar(select(func.coalesce(func.sum(m.LunarDebt.weight_mg), 0)))
    )
    supply = db.get(m.LunarSupply, 1)
    total = sum(int(v) for v in report["accounts"].values())
    expected = (
        supply.discovered_mg
        + supply.legacy_backing_mg
        + supply.admin_injected_mg
        - supply.destroyed_mg
    )
    return {
        **report,
        "migration_status": "CONVERTED",
        "official_net": str(total // UNIT),
        "expected_net": str(expected // UNIT),
        "reconciliation_gap": report["gap_mg"],
        "player_available": str(groups["player"] // UNIT),
        "player_signed": str((groups["player"] - obligations) // UNIT),
        "medical_debt": str(obligations // UNIT),
        "escrow": str(groups["escrow"] // UNIT),
        "contract_reserves": str(
            sum(
                coin_mg(db, a.id)
                for a in db.scalars(
                    select(m.LunarAccount).where(m.LunarAccount.id.like("contract:%"))
                )
            )
            // UNIT
        ),
        "guild_treasury": str(coin_mg(db, "treasury") // UNIT),
        "central_bank": str(coin_mg(db, "central_bank") // UNIT),
        "pending_obligations": str(
            sum(
                reward_value(b)
                for b in db.scalars(
                    select(m.Battle).where(
                        m.Battle.status == "won", m.Battle.claimed == False
                    )
                )
            )
        ),
        "genesis": str(supply.legacy_backing_mg // UNIT),
        "emissions": str(supply.minted_mg // UNIT),
        "retired": str(supply.destroyed_mg // UNIT),
        "administrative_test_credits": str(
            db.scalar(select(func.coalesce(func.sum(m.AdminTestCredit.balance), 0)))
        ),
        "wealth_distribution": [
            {
                "id": c.id,
                "name": c.name,
                "available": str(coin_mg(db, f"player:{c.id}") // UNIT),
                "debt": str(debt_mg(db, c) // UNIT),
            }
            for c in db.scalars(select(m.Character).order_by(m.Character.id).limit(100))
        ],
        "daily_flows": [],
        "suggestions": [],
        "unavailable": ["Agregação diária dos fluxos Lunar ainda não disponível"],
        "lunar_genesis_backing_mg": str(supply.legacy_backing_mg),
        "lunar_discovered_mg": str(supply.discovered_mg),
        "lunar_minted_mg": str(supply.minted_mg),
        "lunar_burned_mg": str(supply.destroyed_mg),
        "lunar_treasury_coin_mg": str(coin_mg(db, "treasury")),
        "lunar_guild_coin_mg": str(coin_mg(db, "guild")),
        "lunar_player_coin_mg": str(groups["player"]),
        "lunar_npc_coin_mg": str(groups["npc"]),
        "lunar_escrow_coin_mg": str(groups["escrow"]),
        "lunar_circulating_coin_mg": str(
            groups["player"] + groups["guild"] + groups["npc"]
        ),
        "lunar_receivable_mg": str(obligations),
        "lunar_debt_mg": str(obligations),
        "lunar_audit_gap_mg": report["gap_mg"],
    }


def reconcile(db):
    report = lunar.audit(db)
    errors = []
    for a in db.scalars(select(m.Auction)):
        expected = a.highest_bid * UNIT if a.status in ("OPEN", "CLOSED") else 0
        if coin_mg(db, f"auction:{a.id}") != expected:
            errors.append(f"auction:{a.id}")
    for c in db.scalars(select(m.GuildContract)):
        if coin_mg(db, f"contract:{c.id}") != c.reserved * UNIT:
            errors.append(f"contract:{c.id}")
    record = db.get(m.LunarCutover, 1)
    initial = (
        record.report.get("initial_debts_mg", {})
        if record
        else {
            str(c.id): str(max(0, -c.coins) * UNIT)
            for c in db.scalars(select(m.Character))
        }
    )
    expected = {int(k): int(v) for k, v in initial.items()}
    for e in db.scalars(select(m.LunarEntry)):
        if e.kind == "MEDICAL_OBLIGATION":
            cid = int(e.actor.split(":")[1])
            expected[cid] = (
                expected.get(cid, 0) + e.context["fee"]["newly_financed"] * UNIT
            )
        elif e.kind == "DEBT_REPAYMENT":
            cid = e.context["character_id"]
            expected[cid] = expected.get(cid, 0) - int(e.context["weight_mg"])
        elif int(e.context.get("debt_repaid_mg", "0")):
            cid = int(e.context["parameters"][1].split(":")[1])
            expected[cid] = expected.get(cid, 0) - int(e.context["debt_repaid_mg"])
    actual = {d.character_id: d.weight_mg for d in db.scalars(select(m.LunarDebt))}
    for cid in set(expected) | set(actual):
        if expected.get(cid, 0) != actual.get(cid, 0):
            errors.append(f"debt:{cid}")
    from .lunar_resources import audit as resource_audit

    errors.extend(resource_audit(db))
    if errors:
        import logging

        logging.getLogger("dungeon.lunar").critical(
            "financial_metadata_invariant_failed count=%s", len(errors)
        )
    return {**report, "metadata_mismatches": errors}
