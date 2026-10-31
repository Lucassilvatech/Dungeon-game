"""Persistent deterministic cycles, independent of views and player proximity."""

from datetime import datetime
from sqlalchemy import select
from fastapi import HTTPException
from . import models as m, npc_economy as npc, market_pricing as pricing, finance, lunar
from .clock import utc_now


def policies(db, id):
    return {
        p.definition_id: p
        for p in db.scalars(
            select(m.NpcInventoryPolicy).where(m.NpcInventoryPolicy.npc_id == id)
        )
    }


def produce(db, profile, key):
    rules = policies(db, profile.id)
    recipes = list(
        db.scalars(
            select(m.NpcRecipe)
            .where(m.NpcRecipe.npc_id == profile.id)
            .order_by(m.NpcRecipe.priority)
        )
    )
    if not profile.enabled or not profile.production_enabled:
        return []
    actions = []
    for recipe in recipes:
        p = rules[recipe.result_id]
        if not p.production_enabled:
            continue
        counts = npc.quantities(db, profile.account_id)
        target = p.target_stock
        if recipe.result_id == "moss_ingot":
            target += sum(
                max(0, rules[r.result_id].target_stock - counts.get(r.result_id, 0))
                * r.ingredients.get("moss_ingot", 0)
                for r in recipes
                if r.result_id != "moss_ingot" and rules[r.result_id].production_enabled
            )
        target = min(target, p.capacity)
        needed = max(0, target - counts.get(recipe.result_id, 0))
        amount = min(
            [needed, 1000]
            + [counts.get(k, 0) // q for k, q in recipe.ingredients.items()]
        )
        if not amount:
            p.status = "AT_TARGET" if not needed else "WAIT_MATERIAL"
            continue
        consumed = {
            k: npc.consume(db, profile.account_id, k, q * amount)
            for k, q in recipe.ingredients.items()
        }
        outputs = npc.give(db, profile.account_id, recipe.result_id, amount)
        revision = pricing.latest(db).id
        result = {
            "npc": profile.id,
            "actor": "npc-economy",
            "definition": recipe.result_id,
            "quantity": amount,
            "inputs": consumed,
            "output_item_ids": outputs,
            "before": counts.get(recipe.result_id, 0),
            "after": counts.get(recipe.result_id, 0) + amount,
            "revision": revision,
            "price_units": pricing.latest(db).snapshot["prices"][recipe.result_id],
        }
        npc.record(db, f"{key}:produce:{recipe.result_id}", "NPC_PRODUCTION", **result)
        actions.append(result)
        p.status = "PRODUCED"
        p.updated_at = utc_now()
    return actions


def restock(db, profile, key):
    if not profile.enabled or not profile.purchase_enabled:
        return []
    source_id = "guild" if profile.id == "merchant" else "merchant"
    source = db.get(m.NpcProfile, source_id)
    outcomes = []
    for definition, p in policies(db, profile.id).items():
        if definition not in npc.RAW or not p.buy_enabled:
            continue
        current = npc.quantities(db, profile.account_id).get(definition, 0)
        if current >= p.reorder_point:
            p.status = "STOCKED"
            continue
        try:
            with db.begin_nested():
                if not source or not source.enabled or not source.sale_enabled:
                    raise HTTPException(409, "WAIT_SUPPLIER")
                source_policy = (
                    db.get(m.NpcInventoryPolicy, (source.id, definition))
                    if source.id != "guild"
                    else None
                )
                minimum = source_policy.minimum_lot_size if source_policy else 1
                step = source_policy.order_step if source_policy else 1
                quantity = ((max(p.order_quantity, minimum) + step - 1) // step) * step
                if current + quantity > p.capacity:
                    raise HTTPException(409, "WAIT_CAPACITY")
                offer = pricing.price(db, source.account_id, definition, quantity)
                if not offer["enabled"]:
                    raise HTTPException(409, "WAIT_DISABLED")
                if npc.quantities(db, source.account_id).get(definition, 0) < quantity:
                    raise HTTPException(409, "WAIT_STOCK")
                payment = finance.payment_quote(
                    db, profile.account_id, int(offer["total_price_units"])
                )
                if not payment["payable"]:
                    raise HTTPException(409, "WAIT_" + payment["error"])
                transfer = finance.move(
                    db,
                    profile.account_id,
                    source.account_id,
                    int(offer["total_price_units"]),
                    f"{key}:pay:{definition}",
                    amortize=False,
                )
                movements = npc.transfer_stock(
                    db, source.account_id, profile.account_id, definition, quantity
                )
                result = {
                    "npc": profile.id,
                    "source_npc": source.id,
                    "actor": "npc-economy",
                    "definition": definition,
                    "quantity": quantity,
                    "source": source.account_id,
                    "destination": profile.account_id,
                    "quote": offer,
                    "receipt": transfer.id,
                    "movements": movements,
                    "revision": offer["market_revision"],
                }
                npc.record(db, f"{key}:purchase:{definition}", "NPC_PURCHASE", **result)
                p.status = "PURCHASED"
                p.updated_at = utc_now()
                outcomes.append(result)
        except HTTPException as exc:
            status = str(exc.detail)
            if not status.startswith("WAIT_"):
                status = "WAIT_CONFLICT"
            # One waiting event on transition, not the same warning every cycle.
            if p.status != status:
                npc.record(
                    db,
                    f"{key}:request:{definition}",
                    "NPC_RESTOCK_REQUEST",
                    npc=profile.id,
                    actor="npc-economy",
                    definition=definition,
                    stock=current,
                    requested=p.order_quantity,
                    source_npc=source_id,
                    status=status,
                )
            p.status = status
            p.updated_at = utc_now()
    return outcomes


def tick(db, now=None):
    from .config import settings

    if not finance.active(db):
        return {"status": "WAIT_CUTOVER"}
    lunar.mutex(db)
    now = now or utc_now()
    bucket = (
        int((now - datetime(1970, 1, 1)).total_seconds())
        // settings.npc_economy_tick_seconds
    )
    revision = pricing.latest(db)
    if not revision:
        return {"status": "WAIT_INITIALIZATION"}
    report = {
        "revision": revision.id,
        "production": [],
        "purchases": [],
        "replayed": True,
    }
    for id in ("alchemist", "blacksmith", "merchant"):
        p = db.get(m.NpcProfile, id)
        if not p or p.last_cycle >= bucket:
            continue
        key = f"npc-cycle:{bucket}:{id}"
        report["production"] += produce(db, p, key)
        report["purchases"] += restock(db, p, key)
        p.last_cycle = bucket
        p.updated_at = now
        report["replayed"] = False
    from .lunar_resources import assert_audit

    assert_audit(db)
    return report


async def worker():
    import asyncio, logging
    from .config import settings
    from .database import Session

    while True:
        await asyncio.sleep(settings.npc_economy_tick_seconds)
        try:

            def run():
                with Session.begin() as db:
                    return tick(db)

            await asyncio.to_thread(run)
        except Exception:
            logging.getLogger("dungeon.npc_economy").exception("npc_cycle_failed")
