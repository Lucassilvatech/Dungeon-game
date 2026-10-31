"""NPC mutations plug into the existing permissioned preview/confirm pipeline."""

from types import SimpleNamespace
from sqlalchemy import select
from . import models as m, npc_economy as npc, market_pricing as pricing, lunar
from .game import fail
from .clock import utc_now

ACTIONS = {"npc.configure": "economy.manage", "npc.stock_transfer": "economy.manage"}
PROFILE_FIELDS = {
    "enabled",
    "production_enabled",
    "purchase_enabled",
    "sale_enabled",
    "fixed_margin",
    "factors",
}
POLICY_FIELDS = {
    "capacity",
    "reorder_point",
    "order_quantity",
    "target_stock",
    "minimum_lot_size",
    "order_step",
    "production_enabled",
    "buy_enabled",
    "sell_enabled",
}
PARAMS = {
    "npc.configure": PROFILE_FIELDS | {"expected_revision", "policies"},
    "npc.stock_transfer": {"destination", "definition_id", "quantity"},
}


def config_plan(db, target, params):
    row = db.get(m.NpcProfile, target)
    if not row:
        fail("NPC inexistente", 404)
    if (
        type(params.get("expected_revision")) is not int
        or params["expected_revision"] != row.revision
    ):
        fail("STALE_PREVIEW: configuração alterada; atualize os valores")
    after = SimpleNamespace(**{key: getattr(row, key) for key in PROFILE_FIELDS})
    for field in PROFILE_FIELDS:
        if field not in params:
            continue
        value = params[field]
        if field.endswith("enabled") and type(value) is not bool:
            fail("Flag inválida", 422)
        if field == "fixed_margin":
            lunar.integer(value)
            if value > 1000000000 or target not in ("guild", "merchant"):
                fail("Margem fixa disponível apenas na Guilda e no Comerciante", 422)
        if field == "factors":
            if not isinstance(value, dict) or set(value) - set(row.factors):
                fail("Fator não pertence a este NPC", 422)
            for factor in value.values():
                lunar.integer(factor, True)
                if factor > 1000000:
                    fail("Fator excede limite administrativo", 422)
            value = {**row.factors, **value}
        setattr(after, field, value)
    changes = params.get("policies", [])
    if not isinstance(changes, list) or len(changes) > 30:
        fail("Lote de políticas inválido", 422)
    reviewed, ids = [], set()
    counts = npc.quantities(db, row.account_id)
    for change in changes:
        if not isinstance(change, dict) or set(change) - POLICY_FIELDS - {
            "definition_id",
            "expected_revision",
        }:
            fail("Campos de política inválidos", 422)
        definition = change.get("definition_id")
        if not isinstance(definition, str) or definition in ids:
            fail("Política duplicada ou inválida", 422)
        ids.add(definition)
        old = db.get(m.NpcInventoryPolicy, (target, definition))
        if not old:
            fail("Política inexistente", 404)
        if (
            type(change.get("expected_revision")) is not int
            or change["expected_revision"] != old.revision
        ):
            fail("STALE_PREVIEW: política de estoque alterada; atualize o lote")
        proposed = {key: change.get(key, getattr(old, key)) for key in POLICY_FIELDS}
        for key, value in proposed.items():
            if key.endswith("enabled"):
                if type(value) is not bool:
                    fail("Flag inválida", 422)
            else:
                lunar.integer(
                    value, key in ("order_quantity", "minimum_lot_size", "order_step")
                )
                if value > 1000000000:
                    fail("Quantidade excede limite administrativo", 422)
        if proposed["capacity"] < max(
            counts.get(definition, 0),
            proposed["reorder_point"],
            proposed["target_stock"],
        ):
            fail("Capacidade deve cobrir estoque atual, ponto de reposição e alvo", 422)
        reviewed.append(
            {
                "definition_id": definition,
                "stock": str(counts.get(definition, 0)),
                "before": {k: getattr(old, k) for k in POLICY_FIELDS},
                "proposed": proposed,
                "revision": old.revision,
            }
        )
    profiles = {n.id: n for n in db.scalars(select(m.NpcProfile))}
    profiles[target] = after
    return {
        "npc": target,
        "revision": row.revision,
        "before": {k: getattr(row, k) for k in PROFILE_FIELDS},
        "proposed": {k: getattr(after, k) for k in PROFILE_FIELDS},
        "policies": reviewed,
        "market_before": pricing.latest(db).snapshot,
        "market_proposed": pricing.calculate(db, profiles),
        "money_created": "0",
        "stock_created": "0",
    }


def describe(db, action, target, p):
    if action == "npc.configure":
        return config_plan(db, target, p)
    source, destination = db.get(m.NpcProfile, target), db.get(
        m.NpcProfile, p.get("destination")
    )
    if not source or not destination or source.id == destination.id:
        fail("Origem/destino inválidos", 422)
    definition = p.get("definition_id")
    quantity = p.get("quantity")
    lunar.integer(quantity, True)
    policy = db.get(m.NpcInventoryPolicy, (destination.id, definition))
    stock = npc.quantities(db, source.account_id).get(definition, 0)
    dest_stock = npc.quantities(db, destination.account_id).get(definition, 0)
    if quantity > stock:
        fail("Estoque insuficiente")
    if destination.id != "guild" and (
        not policy or dest_stock + quantity > policy.capacity
    ):
        fail("Capacidade insuficiente")
    return {
        "source_npc": source.id,
        "destination_npc": destination.id,
        "definition": definition,
        "quantity": quantity,
        "source_before": str(stock),
        "destination_before": str(dest_stock),
        "policy_revision": policy.revision if policy else None,
        "money_created": "0",
        "warning": "Transferência administrativa de patrimônio existente; não é uma compra.",
    }


def apply(db, actor, op):
    if op.action == "npc.configure":
        plan = config_plan(db, op.target, op.params)
        row = db.get(m.NpcProfile, op.target)
        for key, value in plan["proposed"].items():
            setattr(row, key, value)
        row.revision += 1
        row.updated_at = utc_now()
        for change in plan["policies"]:
            policy = db.get(m.NpcInventoryPolicy, (op.target, change["definition_id"]))
            for key, value in change["proposed"].items():
                setattr(policy, key, value)
            policy.revision += 1
            policy.updated_at = utc_now()
        db.flush()
        pricing.refresh(db, str(actor.id), op.reason)
        npc.record(
            db,
            "npc-config:" + op.id,
            "NPC_CONFIG_UPDATED",
            actor=str(actor.id),
            reason=op.reason,
            request_id=op.id,
            new_revision=row.revision,
            **plan
        )
    else:
        plan = describe(db, op.action, op.target, op.params)
        source, dest = db.get(m.NpcProfile, op.target), db.get(
            m.NpcProfile, op.params["destination"]
        )
        movements = npc.transfer_stock(
            db,
            source.account_id,
            dest.account_id,
            op.params["definition_id"],
            op.params["quantity"],
        )
        npc.record(
            db,
            "npc-transfer:" + op.id,
            "NPC_INVENTORY_ADJUSTED",
            actor=str(actor.id),
            reason=op.reason,
            request_id=op.id,
            movements=movements,
            **plan
        )
    from .lunar_resources import assert_audit

    assert_audit(db)


def after(db, op):
    if op.action == "npc.configure":
        return npc.state(db, op.target, admin=True)
    return {
        "source": npc.quantities(db, db.get(m.NpcProfile, op.target).account_id),
        "destination": npc.quantities(
            db, db.get(m.NpcProfile, op.params["destination"]).account_id
        ),
    }
