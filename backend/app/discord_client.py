"""Strict observation adapter. No game.character/snapshot/sync, wandering or settlement.
The database transaction is read-only as a second barrier against future side effects.
Identity association lives separately in the authenticated link endpoints.
"""

from sqlalchemy import select, func, text
from . import models as m, game


def query(db, discord_id, section):
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    a = db.scalar(select(m.Account).where(m.Account.discord_id == discord_id))
    if not a:
        game.fail("Use /vincular primeiro", 404)
    c = db.scalar(select(m.Character).where(m.Character.account_id == a.id))
    if not c:
        game.fail("Crie seu personagem na Web primeiro", 404)
    room = db.get(m.Room, c.room_id)
    reserved = int(
        db.scalar(
            select(func.coalesce(func.sum(m.Auction.highest_bid), 0)).where(
                m.Auction.highest_bidder_id == c.id,
                m.Auction.status.in_(["OPEN", "CLOSED"]),
            )
        )
    )
    character = {
        k: getattr(c, k)
        for k in (
            "id",
            "name",
            "level",
            "xp",
            "hp",
            "energy",
            "floor",
            "room_id",
            "x",
            "y",
            "strength",
            "defense",
            "unspent_attribute_points",
            "attribute_point_debt",
            "coins",
            "adventure_streak",
        )
    }
    if section == "character":
        return {
            "character": character,
            "coins_exact": str(c.coins),
            "reserved_gold": str(reserved),
        }
    if section == "attributes":
        from .attributes import effective

        return {"attributes": effective(db, c), "points": c.unspent_attribute_points}
    if section in ("inventory", "equipment"):
        rows = game.inventory(db, c)
        for item in rows:
            item["rarity"] = db.get(m.ItemDefinition, item["definition"]).rarity
        return {section: [i for i in rows if section == "inventory" or i["equipped"]]}
    if section == "location":
        return {"room": room.name, "floor": c.floor, "x": c.x, "y": c.y}
    if section == "map":
        known = (
            db.execute(
                select(m.Room.name)
                .join(m.RoomState, m.RoomState.room_id == m.Room.id)
                .where(
                    m.RoomState.character_id == c.id,
                    (m.Room.owner_id == None) | (m.Room.owner_id == c.id),
                )
            )
            .scalars()
            .all()
        )
        return {
            "room": room.name,
            "floor": c.floor,
            "x": c.x,
            "y": c.y,
            "discovered_rooms": known,
        }
    if section == "expedition":
        e = db.scalar(
            select(m.Expedition).where(
                m.Expedition.character_id == c.id, m.Expedition.status == "ACTIVE"
            )
        )
        g = db.scalar(
            select(m.CombatEncounter).where(
                m.CombatEncounter.character_id == c.id,
                m.CombatEncounter.status == "ACTIVE",
            )
        )
        remaining = (
            db.scalar(
                select(func.count())
                .select_from(m.EnemyInstance)
                .where(
                    m.EnemyInstance.character_id == c.id,
                    m.EnemyInstance.room_id == e.room_id,
                    m.EnemyInstance.state != "DEAD",
                )
            )
            if e
            else 0
        )
        return {
            "expedition": (
                {
                    "id": e.id,
                    "status": e.status,
                    "room_id": e.room_id,
                    "floor": db.get(m.Room, e.room_id).floor_id,
                    "alive_enemies": remaining,
                }
                if e
                else None
            ),
            "encounter": (
                {"id": g.id, "turn": g.turn, "status": g.status, "size": g.size}
                if g
                else None
            ),
            "group": None,
        }
    if section == "rewards":
        rows = db.scalars(
            select(m.Battle)
            .where(
                m.Battle.character_id == c.id,
                m.Battle.status == "won",
                m.Battle.claimed == False,
            )
            .order_by(m.Battle.id)
        ).all()
        return {
            "guild_rewards": game.reward_summary_from(rows),
            "records": [game.battle_data(b) for b in rows],
        }
    if section == "debt":
        return {
            "debt": str(max(0, -c.coins)),
            "balance": str(c.coins),
            "reserved_gold": str(reserved),
        }
    if section == "contracts":
        from .contracts import listing

        return listing(db, c)
    if section == "auctions":
        from .auctions import payload

        rows = db.scalars(
            select(m.Auction)
            .where(
                m.Auction.hidden == False,
                m.Auction.archived == False,
                (
                    (m.Auction.former_owner_id == c.id)
                    | (m.Auction.highest_bidder_id == c.id)
                    | m.Auction.id.in_(
                        select(m.AuctionBid.auction_id).where(
                            m.AuctionBid.bidder_id == c.id
                        )
                    )
                ),
            )
            .order_by(m.Auction.id.desc())
            .limit(100)
        ).all()
        return {
            "auctions": [
                {
                    k: v
                    for k, v in {
                        **payload(db, r),
                        "own_reserved": str(
                            r.highest_bid
                            if r.highest_bidder_id == c.id
                            and r.status in ("OPEN", "CLOSED")
                            else 0
                        ),
                    }.items()
                    if k
                    not in ("former_owner_id", "highest_bidder_id", "death_event_id")
                }
                for r in rows
            ]
        }
    if section in ("wallet", "mineral"):
        from .lunar import wallet

        return {
            **wallet(db, f"player:{c.id}"),
            "legacy_balance": str(c.coins),
            "legacy_debt": str(max(0, -c.coins)),
        }
    if section == "recovery":
        rows = db.scalars(
            select(m.RecoveryItem)
            .where(m.RecoveryItem.character_id == c.id)
            .order_by(m.RecoveryItem.id.desc())
            .limit(100)
        ).all()
        return {
            "recovery": [
                {
                    "id": r.id,
                    "item_id": r.item_id,
                    "price": str(r.price),
                    "recovered": r.recovered_at is not None,
                }
                for r in rows
            ]
        }
    if section == "state":
        # Legacy observation URL; safe aggregate, deliberately no live game snapshot.
        return {
            "character": character,
            "coins_exact": str(c.coins),
            "reserved_gold": str(reserved),
            "room": {"id": room.id, "name": room.name},
            "read_only": True,
        }
    game.fail("Consulta não disponível", 404)
