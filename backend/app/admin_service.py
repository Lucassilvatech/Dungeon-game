"""Allowlisted, previewed, confirmed operations. Mutex precedes all player locks."""

from datetime import timedelta
import hashlib, json, secrets
from sqlalchemy import select
from . import models as m
from .clock import utc_now
from .admin_security import require
from .auctions import mutex
from .game import fail
from .admin_economy import amount, account, balance
from .rooms import event

ACTIONS = {
    "npc.stock": "items.manage",
    "bank.issue": "economy.manage",
    "bank.burn": "economy.manage",
    "bank.transfer": "economy.manage",
    "economy.configure": "economy.manage",
    "sandbox.grant": "economy.manage",
    "sandbox.consume": "economy.manage",
    "players.heal": "players.manage",
    "players.add_xp": "players.manage",
    "players.travel": "players.manage",
    "items.create": "items.manage",
    "items.transfer": "items.manage",
    "items.protect": "items.manage",
    "items.recover_starter": "items.manage",
    "items.replace_starter": "items.manage",
    "monsters.balance": "monsters.manage",
    "world.spawn": "world.manage",
    "world.region": "world.manage",
    "auctions.cancel": "auctions.manage",
    "auctions.hide": "auctions.manage",
    "auctions.archive": "auctions.manage",
    "world.event_create": "world.manage",
    "world.event_cancel": "world.manage",
    "collection.refill": "collection.manage",
    "collection.disable": "collection.manage",
    "contracts.publish": "contracts.manage",
    "contracts.cancel": "contracts.manage",
}
PARAMS = {
    "npc.stock": {"account_id", "price_weight_mg"},
    "bank.issue": {"amount", "destination"},
    "bank.burn": {"amount", "source"},
    "bank.transfer": {"amount", "source", "destination"},
    "economy.configure": {"value"},
    "sandbox.grant": {"amount"},
    "sandbox.consume": {"amount"},
    "players.heal": set(),
    "players.add_xp": {"amount"},
    "players.travel": {"destination"},
    "items.create": {"definition", "quantity"},
    "items.transfer": {"owner_id"},
    "items.protect": set(),
    "items.recover_starter": set(),
    "items.replace_starter": set(),
    "monsters.balance": {"hp", "attack", "defense", "level", "xp"},
    "world.spawn": {"character_id", "species", "x", "y"},
    "world.region": {"danger_tier"},
    "auctions.cancel": {"destination"},
    "auctions.hide": set(),
    "auctions.archive": set(),
    "world.event_create": {
        "name",
        "description",
        "region",
        "floor_id",
        "effect",
        "intensity",
        "conditions",
        "starts_at",
        "duration_minutes",
    },
    "world.event_cancel": set(),
    "collection.refill": set(),
    "collection.disable": set(),
    "contracts.publish": {
        "name",
        "description",
        "kind",
        "target",
        "required",
        "reward",
        "slots",
    },
    "contracts.cancel": set(),
}

from . import royal

ACTIONS.update(royal.ACTIONS)
PARAMS.update(royal.PARAMS)


from . import guild_admin

ACTIONS.update(guild_admin.ACTIONS)
PARAMS.update(guild_admin.PARAMS)
PARAMS["economy.configure"] |= guild_admin.ACKS


def data(row):
    if row is None:
        return None
    result = {}
    for col in row.__table__.columns:
        if col.name in ("password", "token", "confirmation_hash"):
            continue
        v = getattr(row, col.name)
        if col.name in ("coins", "balance") and isinstance(
            row, (m.Character, m.Treasury, m.CentralBank)
        ):
            from sqlalchemy.orm import object_session
            from . import finance

            session = object_session(row)
            if session and finance.active(session):
                v = (
                    finance.funds(session, row)
                    if isinstance(row, m.Character)
                    else finance.institution(
                        session,
                        "treasury" if isinstance(row, m.Treasury) else "central_bank",
                    )
                )
        if col.name in (
            "coins",
            "balance",
            "base_value",
            "highest_bid",
            "opening_price",
            "amount",
            "reward_amount",
            "reward",
            "reserved",
        ):
            v = str(v) if v is not None else None
        elif hasattr(v, "isoformat"):
            v = v.isoformat() + "Z"
        result[col.name] = v
    return result


def get(db, model, id):
    try:
        row = db.get(
            model,
            (
                int(id)
                if isinstance(
                    model.__table__.primary_key.columns.values()[0].type,
                    __import__("sqlalchemy").Integer,
                )
                else id
            ),
        )
    except (ValueError, TypeError):
        fail("Identificador inválido", 422)
    if not row:
        fail("Entidade inexistente", 404)
    return row


def lock_resources(db, action, target, p):
    # Metadata is re-read after locks. Auction/admin mutex serializes custody changes.
    ids = set()
    item = None
    auction = None
    if action == "npc.stock":
        item = get(db, m.Item, target)
        if item.owner:
            ids.add(item.owner)
    if action.startswith("players.") or action in ("items.create",):
        ids.add(int(target))
    if action in ("items.transfer",):
        item = get(db, m.Item, target)
        if item.owner:
            ids.add(item.owner)
        ids.add(int(p["owner_id"]))
    if action in (
        "items.recover_starter",
        "items.replace_starter",
        "auctions.cancel",
        "auctions.hide",
        "auctions.archive",
    ):
        auction = get(db, m.Auction, target)
        item = get(db, m.Item, auction.item_id)
        ids.add(auction.former_owner_id)
        if auction.highest_bidder_id:
            ids.add(auction.highest_bidder_id)
        if item.owner:
            ids.add(item.owner)
    if action.startswith("bank."):
        for name in (
            p.get("source", "central_bank"),
            p.get("destination", "central_bank"),
        ):
            if name.startswith("character:") and name[10:].isdigit():
                ids.add(int(name[10:]))
    if action == "world.spawn":
        ids.add(int(p["character_id"]))
    if action.startswith("collection."):
        node = get(db, m.ResourceNode, target)
        ids.add(node.character_id)
    if action == "contracts.cancel":
        ids.update(
            db.scalars(
                select(m.CharacterContract.character_id).where(
                    m.CharacterContract.contract_id == int(target),
                    m.CharacterContract.status == "ACTIVE",
                )
            )
        )
    if ids:
        db.scalars(
            select(m.Character)
            .where(m.Character.id.in_(sorted(ids)))
            .order_by(m.Character.id)
            .with_for_update()
        ).all()
    if auction:
        db.scalar(select(m.Auction).where(m.Auction.id == auction.id).with_for_update())
    if item:
        db.scalar(select(m.Item).where(m.Item.id == item.id).with_for_update())
    if action.startswith("bank."):
        db.scalar(select(m.CentralBank).where(m.CentralBank.id == 1).with_for_update())
        db.scalar(select(m.Treasury).where(m.Treasury.id == 1).with_for_update())
    if action in ("contracts.publish", "contracts.cancel"):
        if action == "contracts.cancel":
            db.scalar(
                select(m.GuildContract)
                .where(m.GuildContract.id == int(target))
                .with_for_update()
            )
        db.scalar(select(m.Treasury).where(m.Treasury.id == 1).with_for_update())
    if action.startswith("collection."):
        db.scalar(
            select(m.ResourceNode)
            .where(m.ResourceNode.id == int(target))
            .with_for_update()
        )
    db.expire_all()  # Metadata fetched before waiting must not become a stale identity-map read.


def describe(db, action, target, p):
    if action in guild_admin.ACTIONS:
        return guild_admin.describe(db, action, target, p)
    if action.startswith("royal."):
        return royal.describe(db, action, target, p)
    from .finance import active

    if action in ("bank.issue", "bank.burn") and active(db):
        fail("Emissão abstrata e burn comum desativados após o cutover")
    if action == "npc.stock":
        from .finance import active

        if not active(db):
            fail("Cutover necessário")
        item = get(db, m.Item, target)
        d = db.get(m.ItemDefinition, item.definition)
        price = amount(p["price_weight_mg"])
        owner = p["account_id"]
        if (
            not isinstance(owner, str)
            or not (owner == "guild" or owner.startswith("npc:"))
            or len(owner) > 80
        ):
            fail("Conta comercial inválida", 422)
        if (
            price % 1000
            or d.id == "sword"
            or not d.death_transferable
            or item.equipped
            or item.location not in ("inventory", "npc")
        ):
            fail("Estoque/preço protegido ou inválido")
        return {"item": data(item), "npc_account": owner, "price_weight_mg": str(price)}
    if action.startswith("collection."):
        return {"node": data(get(db, m.ResourceNode, target))}
    if action == "contracts.publish":
        from .contracts import validate, payload

        if target != "guild":
            fail("Publicação exige a Guilda do primeiro andar", 422)
        values = validate(db, p)
        return {
            "parameters": {**values, "reward": str(values["reward"])},
            "reservation": str(values["reward"] * values["slots"]),
            "accounts": {
                "treasury": str(
                    __import__("app.finance", fromlist=["institution"]).institution(
                        db, "treasury"
                    )
                )
            },
            "recent_contracts": [
                payload(row)
                for row in db.scalars(
                    select(m.GuildContract)
                    .order_by(m.GuildContract.id.desc())
                    .limit(10)
                )
            ],
        }
    if action == "contracts.cancel":
        from .contracts import cancellation_plan

        d = get(db, m.GuildContract, target)
        return {
            "contract": data(d),
            "accounts": {
                "treasury": str(
                    __import__("app.finance", fromlist=["institution"]).institution(
                        db, "treasury"
                    )
                )
            },
            **cancellation_plan(db, d),
        }
    if action == "world.event_create":
        from .world_events import validate

        values = validate(db, p)
        return {
            "event": {
                k: (v.isoformat() + "Z" if hasattr(v, "isoformat") else v)
                for k, v in values.items()
            },
            "impact": f"Raros: multiplicador {1+values['intensity']/100:g}; teto 25%; só novas aventuras. Eventos sobrepostos usam maior multiplicador.",
        }
    if action == "world.event_cancel":
        return {"event": data(get(db, m.ScheduledWorldEvent, target))}
    if action.startswith("bank."):
        n = amount(p.get("amount"))
        names = set()
        if action != "bank.issue":
            names.add(p.get("source", "central_bank"))
        if action != "bank.burn":
            names.add(p.get("destination", "central_bank"))
        result = {name: str(balance(account(db, name))) for name in sorted(names)}
        return {
            "accounts": result,
            "amount": str(n),
            "supply_delta": str(
                n if action == "bank.issue" else -n if action == "bank.burn" else 0
            ),
        }
    if action.startswith("players."):
        return {"character": data(get(db, m.Character, target))}
    if action == "items.create":
        owner = get(db, m.Character, target)
        d = get(db, m.ItemDefinition, p["definition"])
        return {
            "character": data(owner),
            "definition": data(d),
            "quantity": amount(p["quantity"]),
            "inventory": [
                data(i)
                for i in db.scalars(
                    select(m.Item)
                    .where(m.Item.owner == owner.id, m.Item.definition == d.id)
                    .order_by(m.Item.id)
                )
            ],
        }
    if action == "items.transfer":
        return {
            "item": data(get(db, m.Item, target)),
            "recipient": data(get(db, m.Character, p["owner_id"])),
        }
    if action == "items.protect":
        return {"definition": data(get(db, m.ItemDefinition, target))}
    if action in (
        "items.recover_starter",
        "items.replace_starter",
        "auctions.cancel",
        "auctions.hide",
        "auctions.archive",
    ):
        a = get(db, m.Auction, target)
        return {
            "auction": data(a),
            "item": data(get(db, m.Item, a.item_id)),
            "bidder": (
                data(db.get(m.Character, a.highest_bidder_id))
                if a.highest_bidder_id
                else None
            ),
            "former_owner": data(get(db, m.Character, a.former_owner_id)),
            "former_owner_starter_ids": list(
                db.scalars(
                    select(m.Item.id).where(
                        m.Item.owner == a.former_owner_id,
                        m.Item.definition == "sword",
                        m.Item.location == "inventory",
                    )
                )
            ),
        }
    if action == "monsters.balance":
        return {"definition": data(get(db, m.MonsterDefinition, target))}
    if action == "world.region":
        return {"room": data(get(db, m.Room, target))}
    if action == "world.spawn":
        return {
            "room": data(get(db, m.Room, target)),
            "character": data(get(db, m.Character, p["character_id"])),
            "instances": [
                data(e)
                for e in db.scalars(
                    select(m.EnemyInstance)
                    .where(
                        m.EnemyInstance.character_id == int(p["character_id"]),
                        m.EnemyInstance.room_id == target,
                    )
                    .order_by(m.EnemyInstance.id)
                )
            ],
        }
    if action == "economy.configure":
        from .config import runtime_setting
        from .lunar_resources import CONFIG, validate_setting

        if target in CONFIG:
            validate_setting(target, p.get("value"))
            if target in guild_admin.commerce.MINERAL_KEYS:
                before, after, warnings = guild_admin.price_values(
                    db,
                    "mineral",
                    {
                        target: p["value"],
                        **{k: v for k, v in p.items() if k in guild_admin.ACKS},
                    },
                )
                return {
                    "key": target,
                    "value": runtime_setting(db, target),
                    "before": before,
                    "proposed": after,
                    "warnings": warnings,
                }
            return {
                "key": target,
                "value": runtime_setting(db, target),
                "impact": "Somente novas expedições; decisões persistidas não são reroladas. Preço comercial independente da massa.",
            }

        if target not in {
            "medical_fee_base",
            "monster_reward",
            "boss_reward",
            "min_auction_start_price",
            "auction_duration_hours",
            "auction_proceeds_destination",
        }:
            fail("Parâmetro não administrável", 422)
        value = p.get("value")
        if target == "auction_proceeds_destination":
            if value not in ("treasury", "sink"):
                fail("Destino inválido", 422)
        elif (
            type(value) not in (int, float)
            or not __import__("math").isfinite(value)
            or value < 0
            or (
                target in ("min_auction_start_price", "auction_duration_hours")
                and value <= 0
            )
            or value > 1000000
            or (target != "auction_duration_hours" and type(value) is not int)
        ):
            fail("Valor inválido", 422)
        return {"key": target, "value": runtime_setting(db, target)}
    if action.startswith("sandbox."):
        get(db, m.Account, target)
        r = db.get(m.AdminTestCredit, int(target))
        return {"test_credit": str(r.balance if r else 0), "official_money": False}
    fail("Operação não suportada", 422)


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def preview(db, actor, body):
    action = body.action
    if action not in ACTIONS:
        fail("Operação desconhecida", 422)
    require(actor, ACTIONS[action])
    if set(body.params) - PARAMS[action]:
        fail("Parâmetros não permitidos", 422)
    mutex(db)
    old = db.get(m.AdminOperation, str(body.operation_id))
    if old:
        if old.actor_id != actor.id or (
            old.action,
            old.target,
            old.params,
            old.reason,
        ) != (action, body.target, body.params, body.reason):
            fail("Identificador de operação já usado")
        return operation_payload(old)
    try:
        lock_resources(db, action, body.target, body.params)
        before = describe(db, action, body.target, body.params)
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
        fail("Parâmetros obrigatórios inválidos ou ausentes", 422)
    token = fingerprint(
        {
            "before": before,
            "action": action,
            "target": body.target,
            "params": body.params,
            "actor": actor.id,
            "nonce": secrets.token_hex(16),
        }
    )
    op = m.AdminOperation(
        id=str(body.operation_id),
        actor_id=actor.id,
        action=action,
        target=body.target,
        params=body.params,
        reason=body.reason,
        before=before,
        confirmation_hash=token,
        status="PREVIEW",
        expires=utc_now() + timedelta(minutes=5),
    )
    db.add(op)
    db.flush()
    return operation_payload(op)


def operation_payload(op):
    projected = dict(op.before.get("accounts", {}))
    if op.action.startswith("bank."):
        n = amount(op.params["amount"])
        if op.action != "bank.issue":
            key = op.params.get("source", "central_bank")
            projected[key] = str(int(projected[key]) - n)
        if op.action != "bank.burn":
            key = op.params.get("destination", "central_bank")
            projected[key] = str(int(projected[key]) + n)
    if op.action == "contracts.publish":
        projected["treasury"] = str(
            int(projected["treasury"]) - int(op.before["reservation"])
        )
        projected["contract_reserve"] = op.before["reservation"]
    if op.action == "contracts.cancel":
        projected["treasury"] = str(
            int(projected["treasury"]) + int(op.before["refund"])
        )
        projected["contract_reserve"] = op.before["retained"]
    return {
        **data(op),
        "confirmation_token": op.confirmation_hash if op.status == "PREVIEW" else None,
        "impact": {
            "action": op.action,
            "params": op.params,
            "supply_delta": op.before.get("supply_delta", "0"),
            "projected_accounts": projected,
            "requires_confirmation": True,
        },
    }


def confirm(db, actor, id, token):
    mutex(db)
    op = db.scalar(
        select(m.AdminOperation).where(m.AdminOperation.id == id).with_for_update()
    )
    if not op or op.actor_id != actor.id:
        fail("Operação inexistente", 404)
    require(actor, ACTIONS[op.action])
    if not secrets.compare_digest(op.confirmation_hash, token):
        fail("Confirmação inválida", 403)
    if op.status == "COMMITTED":
        return {**operation_payload(op), "replayed": True}
    if op.status != "PREVIEW":
        fail("Operação rejeitada; gere uma nova prévia")
    if op.expires <= utc_now():
        fail("Prévia expirada; gere uma nova")
    lock_resources(db, op.action, op.target, op.params)
    # refresh expired operation after row lock; all data is server-authoritative.
    before = describe(db, op.action, op.target, op.params)
    if fingerprint(before) != fingerprint(op.before):
        fail("STALE_PREVIEW: estado mudou desde a prévia; gere uma nova confirmação")
    apply(db, actor, op)
    db.flush()
    op.after = describe(db, op.action, op.target, op.params)
    op.status = "COMMITTED"
    op.finished_at = utc_now()
    import logging

    logging.getLogger("admin.audit").info(
        "admin_operation_committed",
        extra={
            "operation_id": op.id,
            "actor_id": actor.id,
            "action": op.action,
            "target": op.target,
        },
    )
    return {**operation_payload(op), "replayed": False}


def cancel_auction(db, op, restore=False):
    from .economy import credit_player_gold

    a = get(db, m.Auction, op.target)
    item = get(db, m.Item, a.item_id)
    if (
        a.status not in ("OPEN", "CLOSED", "UNSOLD")
        or item.location != "auction"
        or item.owner is not None
    ):
        fail("Item já entregue ou leilão finalizado; não será retirado do comprador")
    if restore and item.definition != "sword":
        fail("Recuperação prioritária restrita à espada inicial", 422)
    if a.highest_bidder_id and a.highest_bid:
        bidder = get(db, m.Character, a.highest_bidder_id)
        credit_player_gold(
            db, bidder, a.highest_bid, f"auction:{a.id}", f"admin-refund:{op.id}"
        )
    a.status = "CANCELLED"
    a.settled_at = utc_now()
    if restore or op.params.get("destination") == "former_owner":
        item.owner = a.former_owner_id
        item.location = "inventory"
        item.equipped = False
    elif op.params.get("destination", "custody") != "custody":
        fail("Destino de cancelamento inválido", 422)


def apply(db, actor, op):
    if op.action in guild_admin.ACTIONS:
        return guild_admin.apply(db, actor, op)
    if op.action.startswith("royal."):
        return royal.apply(db, actor, op)
    from . import game
    from .inventory import add_item

    p = op.params
    action = op.action
    if action == "npc.stock":
        from .finance import ensure

        item = get(db, m.Item, op.target)
        owner = ensure(db, p["account_id"])
        item.owner = None
        item.location = "npc"
        item.equipped = False
        db.add(
            m.NPCStock(
                item_id=item.id,
                account_id=owner,
                sale_weight_mg=amount(p["price_weight_mg"]),
            )
        )
    elif action == "contracts.publish":
        from .contracts import publish

        publish(db, p, op.id)
    elif action == "contracts.cancel":
        from .contracts import cancel_publication

        cancel_publication(db, int(op.target), op.id)
    elif action.startswith("collection."):
        n = get(db, m.ResourceNode, op.target)
        if action == "collection.refill":
            n.remaining = n.capacity
            n.enabled = True
        else:
            n.enabled = False
        event(
            db,
            "RESOURCE_ADMIN_CHANGED",
            get(db, m.Character, n.character_id),
            node_id=n.id,
            operation_id=op.id,
            remaining=n.remaining,
            enabled=n.enabled,
        )
    elif action.startswith("bank."):
        from .admin_economy import execute

        execute(db, op)
    elif action in ("sandbox.grant", "sandbox.consume"):
        r = db.get(m.AdminTestCredit, int(op.target))
        if not r:
            r = m.AdminTestCredit(account_id=int(op.target), balance=0)
            db.add(r)
        n = amount(p["amount"])
        if action == "sandbox.consume" and r.balance < n:
            fail("Créditos de teste insuficientes")
        r.balance += n if action == "sandbox.grant" else -n
    elif action == "economy.configure":
        if op.target in guild_admin.commerce.MINERAL_KEYS:
            return guild_admin.set_prices(
                db,
                actor,
                op,
                "mineral",
                {
                    op.target: p["value"],
                    **{k: v for k, v in p.items() if k in guild_admin.ACKS},
                },
            )
        r = db.get(m.GameSetting, op.target)
        if r:
            r.value = {"value": p["value"], "revision": op.id}
        else:
            db.add(
                m.GameSetting(
                    key=op.target, value={"value": p["value"], "revision": op.id}
                )
            )
    elif action.startswith("players."):
        c = get(db, m.Character, op.target)
        game.idle(db, c)
        if action == "players.heal":
            from .expeditions import guard_departure

            guard_departure(db, c)
            game.rest(db, c)
        elif action == "players.add_xp":
            n = amount(p["amount"])
            if n > 1000000:
                fail("Concessão de XP excede o lote administrativo permitido", 422)
            from .attributes import gain_levels

            c.xp += n
            gain_levels(db, c, source="admin")
        else:
            from .fast_travel import travel

            travel(db, c, p["destination"])
        event(
            db,
            "ADMIN_PLAYER_ADJUSTED",
            c,
            operation_id=op.id,
            actor_id=actor.id,
            action=action,
        )
    elif action == "items.create":
        c = get(db, m.Character, op.target)
        n = amount(p["quantity"])
        if n > 1000:
            fail("Criação excede 1000 unidades por operação", 422)
        add_item(db, c, p["definition"], n, "admin:" + op.id)
    elif action == "items.transfer":
        item = get(db, m.Item, op.target)
        if (
            item.definition == "sword"
            or item.location != "inventory"
            or item.owner is None
        ):
            fail("Item protegido ou fora da mochila")
        old = get(db, m.Character, item.owner)
        new = get(db, m.Character, p["owner_id"])
        game.idle(db, old)
        game.idle(db, new)
        item.owner = new.id
        item.equipped = False
    elif action == "items.protect":
        get(db, m.ItemDefinition, op.target).death_transferable = False
    elif action == "items.recover_starter":
        cancel_auction(db, op, restore=True)
    elif action == "items.replace_starter":
        a = get(db, m.Auction, op.target)
        item = get(db, m.Item, a.item_id)
        if (
            item.definition != "sword"
            or a.status != "SETTLED"
            or item.owner == a.former_owner_id
        ):
            fail("Reposição exige espada entregue legitimamente a outro proprietário")
        c = get(db, m.Character, a.former_owner_id)
        if db.scalar(
            select(m.Item.id).where(
                m.Item.owner == c.id,
                m.Item.definition == "sword",
                m.Item.location == "inventory",
            )
        ):
            fail("Antigo proprietário já possui espada inicial")
        add_item(db, c, "sword", 1, "admin:" + op.id)
    elif action in ("auctions.cancel", "auctions.hide", "auctions.archive"):
        a = get(db, m.Auction, op.target)
        if action == "auctions.archive" and a.status in ("OPEN", "CLOSED"):
            fail("Cancele com reembolso antes de arquivar um leilão ativo")
        if action == "auctions.cancel" or (
            action == "auctions.hide" and a.status in ("OPEN", "CLOSED", "UNSOLD")
        ):
            cancel_auction(db, op)
        if action in ("auctions.hide", "auctions.archive"):
            a.hidden = True
        if action == "auctions.archive":
            a.archived = True
    elif action == "world.event_create":
        from .world_events import validate

        db.add(m.ScheduledWorldEvent(id=op.id, operation_id=op.id, **validate(db, p)))
    elif action == "world.event_cancel":
        e = get(db, m.ScheduledWorldEvent, op.target)
        if e.cancelled_at is None:
            e.cancelled_at = utc_now()
    elif action == "monsters.balance":
        d = get(db, m.MonsterDefinition, op.target)
        for k, v in p.items():
            if (
                type(v) is not int
                or v < 0
                or v > 1000000
                or (k in ("hp", "level") and v < 1)
            ):
                fail("Parâmetro de monstro inválido", 422)
            setattr(d, k, v)
    elif action == "world.region":
        r = get(db, m.Room, op.target)
        v = p["danger_tier"]
        if (
            r.floor_id != 1
            or r.kind not in ("COMMON", "COMBAT", "BOSS")
            or type(v) is not int
            or not 0 <= v <= 10
        ):
            fail("Região/tier inválido", 422)
        r.danger_tier = v
    elif action == "world.spawn":
        from .enemies import instances
        from .rooms import discover

        c = get(db, m.Character, p["character_id"])
        r = get(db, m.Room, op.target)
        if (
            c.room_id != r.id
            or r.floor_id != 1
            or r.kind not in ("COMMON", "COMBAT", "BOSS")
        ):
            fail(
                "Spawn exige personagem na região de combate permanente do primeiro andar"
            )
        game.idle(db, c)
        enemies = instances(db, c)
        x = p["x"]
        y = p["y"]
        if (
            type(x) is not int
            or type(y) is not int
            or not (0 < x < r.data["width"] - 1 and 0 < y < r.data["height"] - 1)
            or [x, y] in r.data["walls"]
            or (x, y) == (c.x, c.y)
            or any(e.state != "DEAD" and (e.x, e.y) == (x, y) for e in enemies)
        ):
            fail("Posição de spawn inválida", 422)
        from .layouts import reachable

        if (x, y) not in reachable(r.data) or db.scalar(
            select(m.RoomConnection.id).where(
                m.RoomConnection.source == r.id,
                m.RoomConnection.x == x,
                m.RoomConnection.y == y,
            )
        ):
            fail("Spawn deve ficar em piso acessível, fora das saídas", 422)
        d = get(db, m.MonsterDefinition, p["species"])
        if d.id in ("dummy", "warden"):
            fail("Espécie restrita ao seu encontro original", 422)
        from .danger import scale_stats

        stats = tuple(getattr(d, k) for k in ("hp", "attack", "defense", "level", "xp"))
        hp, attack, defense, level, _ = scale_stats(stats, r.danger_tier, r.kind)
        e = m.EnemyInstance(
            character_id=c.id,
            room_id=r.id,
            generation=discover(db, c, r).generation,
            spawn_key="adm" + op.id.replace("-", ""),
            species=d.id,
            state="ALIVE",
            hp=hp,
            max_hp=hp,
            xp_reward=stats[4],
            attack=attack,
            defense=defense,
            level=level,
            x=x,
            y=y,
            home_x=x,
            home_y=y,
        )
        db.add(e)
        db.flush()
        event(
            db,
            "ADMIN_ENEMY_SPAWNED",
            c,
            enemy_id=e.id,
            operation_id=op.id,
            actor_id=actor.id,
        )
