"""Audited explicit cash exchanges and independent Guild pricing."""

from sqlalchemy import select
from . import lunar, finance, models as m, guild_commerce as commerce
from .clock import utc_now
from .game import fail

ACTIONS = {
    a: "economy.manage"
    for a in (
        "royal.exchange",
        "guild.rebalance",
        "guild.item_prices",
        "guild.mineral_prices",
    )
}
ACKS = {"acknowledge_free", "acknowledge_arbitrage"}
PARAMS = {
    "royal.exchange": {"inputs", "outputs"},
    "guild.rebalance": {"initial"},
    "guild.item_prices": {
        "buy_price_units",
        "sell_price_units",
        "buy_enabled",
        "sell_enabled",
    }
    | ACKS,
    "guild.mineral_prices": set(commerce.MINERAL_KEYS) | ACKS,
}
INITIAL_KEY = "GUILD_DENOMINATION_REBALANCE_V1"


def rebalance_denominations(
    total_weight_mg,
    target_large_percent=70,
    target_medium_percent=20,
    target_small_percent=10,
):
    lunar.integer(total_weight_mg)
    percents = (target_large_percent, target_medium_percent, target_small_percent)
    if (
        any(type(n) is not int or n < 0 for n in percents)
        or sum(percents) != 100
        or total_weight_mg % 1000
    ):
        fail("Meta/massa de rebalanceamento inválida", 422)
    units = total_weight_mg // 1000
    # Nearest representable target, ties down; bounded by remaining physical value.
    large = min(units // 10, (units * target_large_percent + 499) // 1000)
    medium = min(
        (units - large * 10) // 5, (units * target_medium_percent + 249) // 500
    )
    small = units - large * 10 - medium * 5
    return {
        "quantities": {"coin_large": large, "coin_medium": medium, "coin_small": small},
        "weights_mg": {
            "coin_large": large * 10000,
            "coin_medium": medium * 5000,
            "coin_small": small * 1000,
        },
        "total_weight_mg": str(total_weight_mg),
        "target": list(percents),
    }


def price_state(db, key):
    return (
        commerce.mineral_policy(db)
        if key == "mineral"
        else commerce.item_policy(db, key)
    )


def price_values(db, key, p):
    before = price_state(db, key)
    names = (
        commerce.MINERAL_KEYS
        if key == "mineral"
        else ["buy_price_units", "sell_price_units", "buy_enabled", "sell_enabled"]
    )
    values = {k: before[k] for k in names}
    if key != "mineral":
        for k in ("buy_price_units", "sell_price_units"):
            values[k] = int(values[k])
    values.update({k: v for k, v in p.items() if k in names})
    for a in ACKS:
        if a in p and type(p[a]) is not bool:
            fail("Confirmações devem ser booleanas", 422)
    warnings = commerce.validate_prices(
        values, mineral=key == "mineral", acknowledgements=p
    )
    if key == "mineral" and type(values["lunar_guild_allow_zero_price"]) is not bool:
        fail("Flag de gratuidade inválida", 422)
    return before, values, warnings


def describe(db, action, target, p):
    if not finance.active(db):
        fail("Cutover Lunar deve estar ativo")
    if action == "royal.exchange":
        row = db.get(m.LunarAccount, finance.normalize(target))
        if not row:
            fail("Conta inexistente", 404)
        for field in ("inputs", "outputs"):
            values = p.get(field)
            if (
                not isinstance(values, dict)
                or not values
                or set(values) - set(finance.weights(db))
            ):
                fail("Informe moedas de entrada e saída", 422)
            for q in values.values():
                lunar.integer(q, True)
        before = finance.cash(db, row.id)
        delta = sum(
            (p["outputs"].get(k, 0) - p["inputs"].get(k, 0)) * w
            for k, w in finance.weights(db).items()
        )
        if delta:
            fail("Troca deve conservar massa", 422)
        after = {
            k: str(
                int(before["coins"][k]) - p["inputs"].get(k, 0) + p["outputs"].get(k, 0)
            )
            for k in before["coins"]
        }
        return {
            "account": row.id,
            "before": before,
            "after_coins": after,
            "difference_mg": "0",
            "supply_delta": "0",
            "fingerprint": lunar.fingerprint([row.id, before, p]),
        }
    if action == "guild.rebalance":
        if target != "guild":
            fail("Rebalanceamento exclusivo da Guilda", 422)
        if type(p.get("initial", True)) is not bool:
            fail("initial deve ser booleano", 422)
        before = finance.cash(db, "guild")
        proposal = rebalance_denominations(int(before["total_weight_mg"]))
        prior = db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == INITIAL_KEY))
        return {
            "account": "guild",
            "before": before,
            "proposal": proposal,
            "differences": {
                k: str(v - int(before["coins"][k]))
                for k, v in proposal["quantities"].items()
            },
            "difference_mg": "0",
            "supply_delta": "0",
            "initial": p.get("initial", True),
            "initial_receipt": prior.id if prior else None,
            "status": (
                "ALREADY_REBALANCED"
                if (p.get("initial", True) and prior)
                or all(
                    int(before["coins"][k]) == v
                    for k, v in proposal["quantities"].items()
                )
                else "READY"
            ),
            "fingerprint": lunar.fingerprint(["guild", before, proposal["target"]]),
        }
    if action in ("guild.item_prices", "guild.mineral_prices"):
        key = "mineral" if action == "guild.mineral_prices" else target
        if key != "mineral" and not db.get(m.ItemDefinition, key):
            fail("Item inexistente", 404)
        before, after, warnings = price_values(db, key, p)
        return {
            "policy_key": key,
            "before": before,
            "proposed": after,
            "warnings": warnings,
            "supply_delta": "0",
        }
    fail("Operação desconhecida", 422)


def set_prices(db, actor, op, key, params):
    before, values, _ = price_values(db, key, params)
    if key == "mineral":
        for k, v in values.items():
            row = db.get(m.GameSetting, k)
            value = {"value": v, "revision": op.id}
            if row:
                row.value = value
            else:
                db.add(m.GameSetting(key=k, value=value))
    else:
        row = db.get(m.GuildItemPolicy, key)
        if not row:
            row = m.GuildItemPolicy(definition_id=key, revision=0)
            db.add(row)
        for k, v in values.items():
            setattr(row, k, v)
        row.revision += 1
        row.updated_by = f"admin:{actor.id}"
        row.updated_at = utc_now()
    db.flush()
    db.add(
        m.GuildPriceHistory(
            request_id=op.id,
            policy_key=key,
            before=before,
            after=price_state(db, key),
            actor_id=actor.id,
            reason=op.reason,
        )
    )


def apply(db, actor, op):
    who = f"admin:{actor.id}"
    if op.action == "royal.exchange":
        lunar.exchange(
            db,
            finance.normalize(op.target),
            op.params["inputs"],
            op.params["outputs"],
            f"admin-exchange:{op.id}",
            actor=who,
            reason=op.reason,
        )
    elif op.action == "guild.rebalance":
        preview = describe(db, op.action, op.target, op.params)
        key = (
            INITIAL_KEY
            if op.params.get("initial", True)
            else f"guild-rebalance:{op.id}"
        )
        if db.scalar(select(m.LunarEntry).where(m.LunarEntry.key == key)):
            return
        finance.ensure(db, "guild")
        before = preview["before"]
        after = preview["proposal"]["quantities"]
        lunar.post(
            db,
            key,
            "GUILD_DENOMINATION_REBALANCE",
            who,
            op.reason,
            [("guild", k, after[k] - int(before["coins"][k])) for k in after],
            context={
                "before": before,
                "after": after,
                "target": [70, 20, 10],
                "difference_mg": "0",
                "total_before": before["total_weight_mg"],
                "total_after": before["total_weight_mg"],
                "fingerprint": preview["fingerprint"],
                "admin_operation_id": op.id,
            },
        )
    elif op.action in ("guild.item_prices", "guild.mineral_prices"):
        set_prices(
            db,
            actor,
            op,
            "mineral" if op.action == "guild.mineral_prices" else op.target,
            op.params,
        )
    else:
        fail("Operação desconhecida", 422)
    from .lunar_resources import assert_audit

    assert_audit(db)
