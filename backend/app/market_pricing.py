"""Authoritative integral prices. No cash, stock or holdings are changed by repricing."""

from sqlalchemy import select
from . import models as m, lunar
from .game import fail
from .clock import utc_now

RAW = ("herb", "crystal", "ore")
SCALE = 10000


def ceil_price(numerator, denominator=SCALE):
    lunar.integer(numerator)
    lunar.integer(denominator, True)
    return (numerator + denominator - 1) // denominator


def fixed_price(unit, quantity, margin):
    for value in (unit, quantity, margin):
        lunar.integer(value)
    return unit * quantity + margin


def calculate(db, profiles=None):
    profiles = profiles or {n.id: n for n in db.scalars(select(m.NpcProfile))}
    prices, references = {}, {}
    for key in RAW:
        p = db.get(m.GuildItemPolicy, key)
        prices[key] = p.buy_price_units if p else 0
        references[key] = {
            "price": str(prices[key]),
            "revision": p.revision if p else 0,
        }
    recipes = list(
        db.scalars(
            select(m.NpcRecipe).order_by(m.NpcRecipe.priority, m.NpcRecipe.result_id)
        )
    )
    factors = {k: v.factors for k, v in profiles.items()}
    for recipe in recipes:
        cost = sum(prices[k] * quantity for k, quantity in recipe.ingredients.items())
        prices[recipe.result_id] = ceil_price(
            cost * factors[recipe.npc_id][recipe.factor_key]
        )
    return {
        "prices": {k: str(v) for k, v in prices.items()},
        "references": references,
        "factors": factors,
        "margins": {k: str(v.fixed_margin) for k, v in profiles.items()},
        "recipe_signature": [
            [r.result_id, r.ingredients, r.factor_key] for r in recipes
        ],
    }


def latest(db):
    return db.scalar(
        select(m.MarketRevision).order_by(m.MarketRevision.id.desc()).limit(1)
    )


def refresh(
    db,
    actor="npc-economy",
    reason="Revisão derivada das referências e políticas atuais",
):
    if not db.get(m.NpcProfile, "guild"):
        return None
    lunar.mutex(db)
    snapshot = calculate(db)
    fingerprint = lunar.fingerprint(snapshot)
    old = latest(db)
    if old and old.fingerprint == fingerprint:
        return old
    row = m.MarketRevision(
        fingerprint=fingerprint, snapshot=snapshot, actor=actor, reason=reason
    )
    db.add(row)
    db.flush()
    from .npc_economy import record

    record(
        db,
        f"market:{row.id}",
        "MARKET_PRICE_UPDATE",
        actor=actor,
        reason=reason,
        before_revision=old.id if old else None,
        revision=row.id,
        prices=snapshot["prices"],
    )
    record(
        db,
        f"derived:{row.id}",
        "RECIPE_PRICE_RECALCULATED",
        actor=actor,
        revision=row.id,
        prices=snapshot["prices"],
    )
    return row


def price(db, owner, definition, quantity, direction="buy"):
    from .guild_commerce import item_policy

    row = latest(db)
    revision = row.id if row else 0
    if owner == "guild":
        p = item_policy(db, definition)
        side = "sell" if direction == "buy" else "buy"
        unit = int(p[side + "_price_units"])
        profile = db.get(m.NpcProfile, "guild")
        margin = (
            profile.fixed_margin
            if profile and direction == "buy" and definition in RAW
            else 0
        )
        enabled = p[side + "_enabled"] and (
            not profile
            or profile.enabled
            and (
                profile.sale_enabled if direction == "buy" else profile.purchase_enabled
            )
        )
        policy_revision = p["revision"]
        minimum, step = 1, 1
    else:
        profile = db.scalar(
            select(m.NpcProfile).where(m.NpcProfile.account_id == owner)
        )
        policy = (
            db.get(m.NpcInventoryPolicy, (profile.id, definition)) if profile else None
        )
        if not row or not policy:
            fail("Item não negociado por este NPC", 404)
        unit = int(row.snapshot["prices"][definition])
        margin = (
            profile.fixed_margin
            if profile.id == "merchant" and direction == "buy"
            else 0
        )
        enabled = profile.enabled and (
            profile.sale_enabled and policy.sell_enabled
            if direction == "buy"
            else profile.purchase_enabled and policy.buy_enabled
        )
        policy_revision = [profile.revision, policy.revision]
        minimum, step = (
            (policy.minimum_lot_size, policy.order_step)
            if direction == "buy"
            else (1, 1)
        )
    if quantity < minimum or quantity % step:
        fail(
            f"LOT_SIZE: escolha ao menos {minimum} unidades em múltiplos de {step}", 422
        )
    return {
        "unit_price_units": str(unit),
        "base_price_units": str(unit * quantity),
        "fixed_margin_units": str(margin),
        "total_price_units": str(fixed_price(unit, quantity, margin)),
        "enabled": enabled,
        "price_revision": policy_revision,
        "market_revision": revision,
        "minimum_lot_size": minimum,
        "order_step": step,
    }
