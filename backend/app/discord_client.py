"""Service-authenticated Discord adapter; never a second game state or admin channel."""

from datetime import timedelta
import secrets
from uuid import uuid4
from sqlalchemy import select
from . import models as m, game
from .clock import utc_now
from .security import digest
from .rooms import event


def linked(db, discord_id):
    a = db.scalar(select(m.Account).where(m.Account.discord_id == discord_id))
    if not a:
        game.fail("Use /vincular primeiro", 404)
    return a


def query(db, discord_id, section):
    a = linked(db, discord_id)
    if section == "auctions":
        from .auctions import listing

        rows = listing(db)  # Takes financial mutex BEFORE the character lock.
        c = game.character(db, a)
        return {
            "auctions": [
                {
                    **row,
                    "own_reserved": (
                        row["highest_bid"]
                        if row["highest_bidder_id"] == c.id
                        and row["status"] in ("OPEN", "CLOSED")
                        else "0"
                    ),
                }
                for row in rows
            ]
        }
    c = game.character(db, a)
    if section == "contracts":
        from .contracts import listing

        return listing(db, c)
    s = game.snapshot(db, c)
    sections = {
        "character": {
            "character": s["character"],
            "coins_exact": s["coins_exact"],
            "reserved_gold": s["reserved_gold"],
        },
        "attributes": {
            "attributes": s["attributes"],
            "points": s["character"]["unspent_attribute_points"],
        },
        "inventory": {"inventory": s["inventory"]},
        "equipment": {"equipment": [i for i in s["inventory"] if i["equipped"]]},
        "location": {"room": s["room"]["name"], "floor": c.floor, "x": c.x, "y": c.y},
        "expedition": {"expedition": s["expedition"], "encounter": s["encounter"]},
        "rewards": {
            "guild_rewards": s["guild_rewards"],
            "records": s["reward_records"],
        },
        "debt": {
            "debt": str(max(0, -c.coins)),
            "balance": s["coins_exact"],
            "reserved_gold": s["reserved_gold"],
        },
    }
    if section not in sections:
        game.fail("Consulta não disponível", 404)
    return sections[section]


def equipment_state(db, c, item_id):
    game.idle(db, c)
    item = db.get(m.Item, item_id)
    if not item or item.owner != c.id or item.location != "inventory":
        game.fail("Item indisponível", 404)
    if db.get(m.ItemDefinition, item.definition).kind != "weapon":
        game.fail("Item não equipável")
    return {
        "room_id": c.room_id,
        "item_id": item.id,
        "inventory": [
            {"id": i.id, "equipped": i.equipped, "definition": i.definition}
            for i in db.scalars(
                select(m.Item)
                .where(m.Item.owner == c.id, m.Item.location == "inventory")
                .order_by(m.Item.id)
            )
        ],
    }


def preview(db, discord_id, item_id, equipped):
    a = linked(db, discord_id)
    c = game.character(db, a)
    before = equipment_state(db, c, item_id)
    token = secrets.token_urlsafe(32)
    op = m.DiscordOperation(
        id=str(uuid4()),
        account_id=a.id,
        character_id=c.id,
        discord_id=discord_id,
        item_id=item_id,
        equipped=equipped,
        before=before,
        confirmation_hash=digest(token),
        expires_at=utc_now() + timedelta(minutes=2),
    )
    db.add(op)
    db.flush()
    return {
        "id": op.id,
        "confirmation_token": token,
        "expires_in": 120,
        "message": f"{'Equipar' if equipped else 'Desequipar'} item #{item_id}? O backend validará novamente sua mochila e o combate.",
    }


def confirm(db, discord_id, id, token):
    a = linked(db, discord_id)
    c = game.character(db, a)
    op = db.scalar(
        select(m.DiscordOperation).where(m.DiscordOperation.id == id).with_for_update()
    )
    if (
        not op
        or op.account_id != a.id
        or op.character_id != c.id
        or op.discord_id != discord_id
    ):
        game.fail("Confirmação não pertence a você", 404)
    if not secrets.compare_digest(op.confirmation_hash, digest(token)):
        game.fail("Confirmação inválida", 403)
    if op.status == "APPLIED":
        return {**op.result, "replayed": True}
    if op.expires_at < utc_now():
        game.fail("Confirmação expirada; solicite outra prévia")
    if equipment_state(db, c, op.item_id) != op.before:
        game.fail("Estado mudou; solicite outra prévia")
    if op.equipped:
        game.equip(db, c, op.item_id)
    else:
        game.unequip(db, c, op.item_id)
    op.status = "APPLIED"
    op.result = {
        "message": "Equipamento atualizado no personagem compartilhado.",
        "item_id": op.item_id,
        "equipped": op.equipped,
    }
    event(
        db,
        "DISCORD_EQUIPMENT_CHANGED",
        c,
        key=f"discord-op:{op.id}",
        operation_id=op.id,
        item_id=op.item_id,
        equipped=op.equipped,
    )
    return op.result
