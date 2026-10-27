"""Exact physical accounting. No seed balance; operations use one transaction mutex.
Asset weights are persisted, immutable while money exists; settings never reweight holdings.
Legacy coins remain untouched until a separate verified cutover.
"""

from collections import defaultdict
from math import gcd
import hashlib, json, logging
from sqlalchemy import select, text
from .models import LunarAccount, LunarAsset, LunarHolding, LunarEntry, LunarSupply
from fastapi import HTTPException


def fail(message, code=409):
    raise HTTPException(code, message)


ASSETS = {
    "nugget_small": ("nugget", 100000),
    "nugget_medium": ("nugget", 500000),
    "nugget_large": ("nugget", 1000000),
    "coin_small": ("coin", 1000),
    "coin_medium": ("coin", 5000),
    "coin_large": ("coin", 10000),
}


def integer(value, positive=False):
    if type(value) is not int or value < 0 or (positive and value == 0):
        fail("Quantidade deve ser inteira e não negativa", 422)
    return value


def mutex(db):
    db.execute(text("SELECT pg_advisory_xact_lock(7312027)"))
    db.execute(text("SELECT pg_advisory_xact_lock(7312030)"))


def initialize(db):
    mutex(db)
    if not db.get(LunarSupply, 1):
        db.add(
            LunarSupply(
                id=1,
                config={
                    "mode": "observe_only",
                    "legacy_coin_unit_weight_mg": 1000,
                    "generation_chance": None,
                    "size_distribution": None,
                    "max_per_expedition": None,
                    "floor_modifiers": {},
                    "events": {},
                    "anti_reroll": None,
                },
            )
        )
    for code, (kind, weight) in ASSETS.items():
        if not db.get(LunarAsset, code):
            db.add(LunarAsset(code=code, kind=kind, weight_mg=weight))
    db.flush()


def account(db, id, kind, character_id=None):
    mutex(db)
    row = db.get(LunarAccount, id)
    if row:
        if row.kind != kind or row.character_id != character_id:
            fail("Identidade econômica divergente")
        return row
    row = LunarAccount(id=id, kind=kind, character_id=character_id)
    db.add(row)
    db.flush()
    return row


def balances(db, id):
    return {
        h.asset_code: h.quantity
        for h in db.scalars(select(LunarHolding).where(LunarHolding.account_id == id))
    }


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def post(db, key, kind, actor, reason, postings, context=None, source=None):
    """Internal double-entry mutation; positive mass only from discovery/approved legacy backing.
    Replay is bound to all parameters. Failure is raised before modifying any balance.
    """
    mutex(db)
    if not reason or len(reason) > 500 or not key or len(key) > 160:
        fail("Referência ou justificativa inválida", 422)
    context = context or {}
    combined = defaultdict(int)
    for owner, asset, delta in postings:
        if type(delta) is not int:
            fail("Massa/quantidade fracionária não permitida", 422)
        combined[(owner, asset)] += delta
    rows = [
        {"account": o, "asset": a, "quantity": q}
        for (o, a), q in sorted(combined.items())
        if q
    ]
    digest = fingerprint([kind, actor, reason, rows, context, source])
    previous = db.scalar(select(LunarEntry).where(LunarEntry.key == key))
    if previous:
        if previous.fingerprint != digest:
            fail("Chave já utilizada com outra operação")
        return previous
    if not rows and kind not in (
        "DEBT_SETTLEMENT",
        "MEDICAL_OBLIGATION",
        "GENESIS_BACKING",
        "ZERO_TRANSFER",
        "DEBT_REPAYMENT",
    ):
        fail("Operação vazia", 422)
    supply = db.get(LunarSupply, 1)
    if not supply:
        fail("Infraestrutura lunar não inicializada")
    total = 0
    updates = []
    for row in rows:
        o, a, q = row["account"], row["asset"], row["quantity"]
        asset = db.get(LunarAsset, a)
        if not asset or not db.get(LunarAccount, o):
            fail("Conta ou ativo inexistente", 404)
        holding = db.get(LunarHolding, (o, a))
        before = holding.quantity if holding else 0
        if before + q < 0:
            fail("Saldo físico insuficiente")
        total += q * asset.weight_mg
        updates.append((holding, o, a, before + q))
    if total > 0 and source not in ("discovery", "legacy_backing"):
        fail("Operação criaria massa sem origem")
    if total < 0 and source != "destruction":
        fail("Operação destruiria massa sem destino")
    if (source == "discovery" and total <= 0) or (
        source == "legacy_backing" and total < 0
    ):
        fail("Entrada sem massa positiva")
    if source == "destruction" and total >= 0:
        fail("Destruição sem massa negativa")
    for h, o, a, q in updates:
        if h:
            h.quantity = q
        else:
            db.add(LunarHolding(account_id=o, asset_code=a, quantity=q))
    if source == "discovery":
        supply.discovered_mg += total
    if source == "legacy_backing":
        supply.legacy_backing_mg += total
    if source == "destruction":
        supply.destroyed_mg -= total
        supply.coin_burned_mg -= sum(
            r["quantity"] * db.get(LunarAsset, r["asset"]).weight_mg
            for r in rows
            if db.get(LunarAsset, r["asset"]).kind == "coin"
        )
    entry = LunarEntry(
        key=key,
        kind=kind,
        actor=actor,
        reason=reason,
        postings=rows,
        context=context,
        fingerprint=digest,
    )
    db.add(entry)
    db.flush()
    return entry


def split(db, id, source, outputs, key):
    mutex(db)
    original = db.get(LunarAsset, source)
    if not original or original.kind != "nugget" or source == "nugget_small":
        fail("Pepita não pode ser dividida")
    postings = [(id, source, -1)]
    weight = 0
    for code, q in outputs.items():
        integer(q, True)
        a = db.get(LunarAsset, code)
        if not a or a.kind != "nugget" or a.weight_mg >= original.weight_mg:
            fail("Resultado de divisão inválido")
        weight += a.weight_mg * q
        postings.append((id, code, q))
    if weight != original.weight_mg:
        fail("Divisão deve conservar massa exatamente")
    return post(db, key, "NUGGET_SPLIT", id, "Divisão gratuita e sem perda", postings)


def exchange(db, id, inputs, outputs, key):
    mutex(db)
    postings = []
    for sign, values in [(-1, inputs), (1, outputs)]:
        for code, q in values.items():
            integer(q, True)
            a = db.get(LunarAsset, code)
            if not a or a.kind != "coin":
                fail("Troca aceita apenas moedas")
            postings.append((id, code, sign * q))
    return post(
        db,
        key,
        "COIN_DENOMINATION_EXCHANGE",
        id,
        "Troca gratuita de denominações",
        postings,
    )


def mint(db, id, nuggets, coins, key):
    mutex(db)
    owner = db.get(LunarAccount, id)
    if not owner or owner.kind != "treasury":
        fail("Cunhagem exclusiva do Tesouro", 403)
    postings = []
    weight = 0
    for sign, values, kind in [(-1, nuggets, "nugget"), (1, coins, "coin")]:
        if not values:
            fail("Cunhagem exige minério e moedas")
        for code, q in values.items():
            integer(q, True)
            asset = db.get(LunarAsset, code)
            if not asset or asset.kind != kind:
                fail("Composição de cunhagem inválida")
            postings.append((id, code, sign * q))
            if sign > 0:
                weight += q * asset.weight_mg
    previous = db.scalar(select(LunarEntry).where(LunarEntry.key == key))
    entry = post(db, key, "COIN_MINT", id, "Cunhagem de minério já existente", postings)
    if not previous:
        db.get(LunarSupply, 1).minted_mg += weight
    return entry


def select_coins(available, weights, required):
    """Bounded exact change for three divisible denominations, O(denominations).
    Reject non-divisible configurations instead of greedy overpayment.
    """
    integer(required, True)
    order = sorted(weights, key=lambda a: weights[a], reverse=True)
    for code in order:
        integer(weights[code], True)
        integer(available.get(code, 0))
    if any(weights[order[i]] % weights[order[i + 1]] for i in range(len(order) - 1)):
        fail("Denominações exigem cadeia divisível", 422)
    remaining = required
    chosen = {}
    for code in order:
        count = min(available.get(code, 0), remaining // weights[code])
        if count:
            chosen[code] = count
            remaining -= count * weights[code]
    if remaining:
        fail("Não há combinação exata de moedas disponíveis")
    return chosen


def transfer(db, source, target, coins, key, kind="COIN_TRANSFER"):
    mutex(db)
    p = []
    if source == target:
        fail("Contas de origem e destino devem diferir")
    for code, q in coins.items():
        integer(q, True)
        a = db.get(LunarAsset, code)
        if not a or a.kind != "coin":
            fail("Pagamento aceita moedas")
        p.extend([(source, code, -q), (target, code, q)])
    if not p:
        fail("Pagamento vazio")
    return post(db, key, kind, source, "Transferência de moedas existentes", p)


def wallet(db, id):
    assets = {a.code: a for a in db.scalars(select(LunarAsset))}
    held = balances(db, id)
    from . import finance
    from .models import LunarDebt

    owner = db.get(LunarAccount, id)
    # A player can incur a fee before receiving their first physical coin/account.
    character_id = owner.character_id if owner else None
    if not character_id and id.startswith("player:") and id[7:].isdigit():
        character_id = int(id[7:])
    obligation = (
        db.get(LunarDebt, character_id) if character_id and finance.active(db) else None
    )
    return {
        "migration_status": "CONVERTED" if finance.active(db) else "LEGACY",
        "debt_weight_mg": str(obligation.weight_mg if obligation else 0),
        "account": id,
        "assets": {
            code: {
                "quantity": str(held.get(code, 0)),
                "weight_mg": str(a.weight_mg),
                "total_weight_mg": str(held.get(code, 0) * a.weight_mg),
                "kind": a.kind,
            }
            for code, a in assets.items()
        },
        "weight_mg": str(sum(q * assets[code].weight_mg for code, q in held.items())),
        "legacy_conversion_active": finance.active(db),
    }


def audit(db):
    mutex(db)
    db.flush()
    s = db.get(LunarSupply, 1)
    if not s:
        return {"initialized": False, "mode": "observe_only"}
    assets = {a.code: a for a in db.scalars(select(LunarAsset))}
    totals = defaultdict(int)
    owners = defaultdict(int)
    counts = defaultdict(int)
    for h in db.scalars(select(LunarHolding)):
        mass = h.quantity * assets[h.asset_code].weight_mg
        totals[assets[h.asset_code].kind] += mass
        owners[h.account_id] += mass
        counts[h.asset_code] += h.quantity
    gap = sum(totals.values()) - (
        s.discovered_mg + s.legacy_backing_mg - s.destroyed_mg
    )
    ledger_balances = defaultdict(int)
    for entry in db.scalars(select(LunarEntry)):
        for r in entry.postings:
            ledger_balances[(r["account"], r["asset"])] += r["quantity"]
    physical = {
        (h.account_id, h.asset_code): h.quantity
        for h in db.scalars(select(LunarHolding))
    }
    mismatches = [
        {
            "account": o,
            "asset": a,
            "difference": str(physical.get((o, a), 0) - ledger_balances.get((o, a), 0)),
        }
        for o, a in sorted(set(physical) | set(ledger_balances))
        if physical.get((o, a), 0) != ledger_balances.get((o, a), 0)
    ]
    if mismatches:
        logging.getLogger("dungeon.lunar").critical(
            "lunar_ledger_invariant_failed accounts=%s", len(mismatches)
        )
    if gap:
        logging.getLogger("dungeon.lunar").critical(
            "lunar_mass_invariant_failed gap_mg=%s", gap
        )
    return {
        "mode": "observe_only",
        "discovered_mg": str(s.discovered_mg),
        "legacy_backing_mg": str(s.legacy_backing_mg),
        "destroyed_mg": str(s.destroyed_mg),
        "minted_mg": str(s.minted_mg),
        "coin_burned_mg": str(s.coin_burned_mg),
        "held_by_kind": {k: str(v) for k, v in totals.items()},
        "accounts": {k: str(v) for k, v in owners.items()},
        "quantities": {k: str(v) for k, v in counts.items()},
        "gap_mg": str(gap),
        "ledger_mismatches": mismatches,
    }


def legacy_preview(db):
    from . import models as m
    from .admin_economy import metrics

    from .auctions import mutex as financial_mutex

    financial_mutex(db)
    db.scalars(select(m.Character).order_by(m.Character.id).with_for_update()).all()
    db.scalar(select(m.Treasury).where(m.Treasury.id == 1).with_for_update())
    db.scalar(select(m.CentralBank).where(m.CentralBank.id == 1).with_for_update())
    scale = 1000
    values = {
        f"player:{c.id}": max(c.coins, 0) for c in db.scalars(select(m.Character))
    }
    debts = {
        f"player:{c.id}": -c.coins
        for c in db.scalars(select(m.Character))
        if c.coins < 0
    }
    values["treasury"] = db.get(m.Treasury, 1).balance
    values["central_bank"] = db.get(m.CentralBank, 1).balance
    values.update(
        {
            f"auction:{a.id}": a.highest_bid
            for a in db.scalars(
                select(m.Auction).where(m.Auction.status.in_(["OPEN", "CLOSED"]))
            )
        }
    )
    values.update(
        {f"contract:{c.id}": c.reserved for c in db.scalars(select(m.GuildContract))}
    )
    return {
        "mode": "dry_run",
        "conversion_active": False,
        "legacy_coin_unit_weight_mg": str(scale),
        "required_backing_mg": str(sum(values.values()) * scale),
        "positive_accounts": {k: str(v * scale) for k, v in values.items()},
        "debt_obligations_mg": {k: str(v * scale) for k, v in debts.items()},
        "legacy_reconciliation_gap": metrics(db)["reconciliation_gap"],
        "fingerprint": fingerprint([values, debts, scale]),
    }


def configure_empty_denominations(db, weights):
    """Configuration before first issuance only; never reweight circulating assets."""
    mutex(db)
    if set(weights) != {"coin_small", "coin_medium", "coin_large"}:
        fail("Informe as três denominações", 422)
    for q in weights.values():
        integer(q, True)
    if (
        weights["coin_medium"] % weights["coin_small"]
        or weights["coin_large"] % weights["coin_medium"]
    ):
        fail("Pesos devem formar cadeia divisível", 422)
    if db.scalar(select(LunarEntry.id).limit(1)) or db.scalar(
        select(LunarHolding.account_id).where(LunarHolding.quantity > 0).limit(1)
    ):
        fail("Configuração congelada após primeira movimentação")
    for code, weight in weights.items():
        db.get(LunarAsset, code).weight_mg = weight
