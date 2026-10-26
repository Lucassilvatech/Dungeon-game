"""Death loot only. Auction commands serialize before locking participating players.
Escrow is debited from spendable coins and stored in highest_bid, never spent twice.
"""

from datetime import timedelta
from sqlalchemy import select, text
from .models import Auction, AuctionBid, Item, ItemDefinition, Character, Treasury
from .clock import utc_now
from .config import settings, runtime_setting
from .rooms import event
from .economy import credit_player_gold, reserve_gold, ledger


def mutex(db):
    # All bids and settlements share this transaction lock, including background sweeps.
    # Death creates NEW listings only and never takes this lock under a player lock.
    db.execute(text("SELECT pg_advisory_xact_lock(7312027)"))


def create_from_death(db, c, death):
    rows = db.execute(
        select(Item, ItemDefinition)
        .join(ItemDefinition, Item.definition == ItemDefinition.id)
        .where(
            Item.owner == c.id,
            Item.location == "inventory",
            ItemDefinition.death_transferable == True,
            ItemDefinition.id != "sword",
        )
        .order_by(Item.id)
        .with_for_update(of=Item)
    ).all()
    lost = []
    now = utc_now()
    for item, definition in rows:
        total = (definition.base_value or 0) * item.quantity
        opening = max(runtime_setting(db, "min_auction_start_price"), (total + 4) // 5)
        item.owner = None
        item.equipped = False
        item.location = "auction"
        auction = Auction(
            item_id=item.id,
            quantity=item.quantity,
            death_event_id=death.id,
            former_owner_id=c.id,
            opening_price=opening,
            started_at=now,
            ends_at=now
            + timedelta(hours=runtime_setting(db, "auction_duration_hours")),
            proceeds_destination=runtime_setting(db, "auction_proceeds_destination"),
        )
        db.add(auction)
        db.flush()
        lost.append(
            dict(
                item_id=item.id,
                name=definition.name,
                quantity=item.quantity,
                auction_id=auction.id,
                opening_price=str(opening),
            )
        )
        event(
            db,
            "AUCTION_CREATED_FROM_DEATH",
            c,
            key=f"auction-created:{death.id}:{item.id}",
            auction_id=auction.id,
            death_event_id=death.id,
            item_id=item.id,
            quantity=item.quantity,
            opening_price=str(opening),
        )
    return lost


def payload(db, a):
    item = db.get(Item, a.item_id)
    definition = db.get(ItemDefinition, item.definition)
    return dict(
        id=a.id,
        item_id=item.id,
        name=definition.name,
        quantity=a.quantity,
        description=definition.description,
        kind=definition.kind,
        attributes={"power": definition.power},
        protected=not definition.death_transferable or definition.id == "sword",
        accepts_bids=not a.hidden and not a.archived and a.status == "OPEN"
        and definition.death_transferable
        and definition.id != "sword"
        and a.ends_at > utc_now(),
        minimum_increment="1",
        next_bid=str(max(a.opening_price, a.highest_bid + 1)),
        origin=a.origin,
        assessed_value=str(a.assessed_value),
        hidden=a.hidden, archived=a.archived,
        death_event_id=a.death_event_id,
        delivery="Same item/stack, unequipped, on settlement",
        former_owner_id=a.former_owner_id,
        opening_price=str(a.opening_price),
        highest_bid=str(a.highest_bid),
        highest_bidder_id=a.highest_bidder_id,
        status=a.status,
        started_at=a.started_at.isoformat() + "Z",
        ends_at=a.ends_at.isoformat() + "Z",
        proceeds_destination=a.proceeds_destination,
    )


def settle_locked(db, a):
    """Caller holds auction mutex; lock winner before item/Treasury, never the reverse."""
    from .game import fail

    if a.status != "OPEN":
        return payload(db, a)
    transferable(db, a)
    if a.ends_at > utc_now():
        fail("Leilão ainda está aberto")
    if a.highest_bidder_id is None:
        a.status = (
            "UNSOLD"  # Archive custody; no destruction, relisting or NPC purchase.
        )
    else:
        winner = db.scalar(
            select(Character)
            .where(Character.id == a.highest_bidder_id)
            .with_for_update()
        )
        item = db.scalar(select(Item).where(Item.id == a.item_id).with_for_update())
        if item.owner is not None or item.location != "auction":
            raise RuntimeError("Auction custody invariant violated")
        item.owner = winner.id
        item.location = "inventory"
        item.equipped = False
        if a.proceeds_destination == "treasury":
            treasury = db.scalar(
                select(Treasury).where(Treasury.id == 1).with_for_update()
            )
            treasury.balance += a.highest_bid
        ledger(
            db,
            f"auction-settle:{a.id}",
            f"auction:{a.id}",
            a.proceeds_destination,
            a.highest_bid,
        )
        a.status = "SETTLED"
        event(
            db,
            "AUCTION_SETTLED",
            winner,
            key=f"auction-settle:{a.id}",
            auction_id=a.id,
            item_id=item.id,
            amount=str(a.highest_bid),
            destination=a.proceeds_destination,
        )
    a.settled_at = utc_now()
    db.flush()
    if a.status == "UNSOLD":
        owner = db.get(Character, a.former_owner_id)
        event(
            db, "AUCTION_UNSOLD", owner, key=f"auction-unsold:{a.id}", auction_id=a.id
        )
    return payload(db, a)


def settle_due(db):
    mutex(db)
    rows = db.scalars(
        select(Auction)
        .join(Item, Item.id == Auction.item_id)
        .join(ItemDefinition, ItemDefinition.id == Item.definition)
        .where(
            Auction.status == "OPEN",
            Auction.ends_at <= utc_now(),
            ItemDefinition.death_transferable == True,
            ItemDefinition.id != "sword",
        )
        .order_by(Auction.id)
        .limit(100)
        .with_for_update()
    ).all()
    # A batch retains Treasury locks until commit. Lock ALL winners first;
    # otherwise a guild payment holding a later winner could wait for Treasury
    # while this batch waits for that character (a cross-domain deadlock).
    winners = sorted(
        {a.highest_bidder_id for a in rows if a.highest_bidder_id is not None}
    )
    if winners:
        db.scalars(
            select(Character)
            .where(Character.id.in_(winners))
            .order_by(Character.id)
            .with_for_update()
        ).all()
    for a in rows:
        settle_locked(db, a)
    return len(rows)


def listing(db, offset=0):
    settle_due(db)
    return [
        payload(db, a)
        for a in db.scalars(
            select(Auction).where(Auction.hidden == False, Auction.archived == False).order_by(Auction.id.desc()).offset(offset).limit(100)
        )
    ]


def bid(db, account, auction_id, amount, request_id):
    from . import game

    mutex(db)  # Must be BEFORE game.character's row lock.
    c = game.character(db, account)
    previous = db.scalar(
        select(AuctionBid).where(
            AuctionBid.bidder_id == c.id, AuctionBid.request_id == request_id
        )
    )
    if previous:
        if previous.auction_id != auction_id or previous.amount != amount:
            game.fail("Chave de lance já usada com outros dados")
        return {"bid_id": previous.id, "amount": str(previous.amount), "replayed": True}
    a = db.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
    if not a:
        game.fail("Leilão inexistente", 404)
    transferable(db, a)
    if a.hidden or a.archived:
        game.fail("Leilão indisponível", 404)
    if a.status != "OPEN" or a.ends_at <= utc_now():
        game.fail("Leilão encerrado")
    if amount < a.opening_price or amount <= a.highest_bid:
        game.fail("Lance deve cobrir o preço inicial e superar o maior lance")
    # Re-raising your own bid reserves ONLY the difference, but debt still forbids bidding.
    additional = amount - a.highest_bid if a.highest_bidder_id == c.id else amount
    record = AuctionBid(
        auction_id=a.id, bidder_id=c.id, amount=amount, request_id=request_id
    )
    db.add(record)
    db.flush()
    reserve_gold(db, c, additional, f"auction-bid:{record.id}", a.id)
    if a.highest_bidder_id is not None and a.highest_bidder_id != c.id:
        old = db.scalar(
            select(Character)
            .where(Character.id == a.highest_bidder_id)
            .with_for_update()
        )
        credit_player_gold(
            db, old, a.highest_bid, f"auction:{a.id}", f"auction-refund:{record.id}"
        )
    a.highest_bidder_id = c.id
    a.highest_bid = amount
    event(
        db,
        "AUCTION_BID",
        c,
        key=f"auction-bid:{record.id}",
        auction_id=a.id,
        bid_id=record.id,
        amount=str(amount),
        reserved=str(additional),
    )
    return {"bid_id": record.id, "amount": str(amount), "replayed": False}


def settle(db, auction_id):
    from .game import fail

    mutex(db)
    a = db.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
    if not a:
        fail("Leilão inexistente", 404)
    return settle_locked(db, a)


async def sweeper():
    import asyncio
    import logging
    from .database import Session

    def run():
        with Session.begin() as db:
            settle_due(db)

    while True:
        try:
            await asyncio.to_thread(run)
        except Exception:
            logging.getLogger(__name__).exception(
                "Auction sweep failed; transaction rolled back; retrying"
            )
        await asyncio.sleep(settings.auction_sweep_seconds)


def transferable(db, a):
    from .game import fail

    item = db.get(Item, a.item_id)
    definition = db.get(ItemDefinition, item.definition)
    if definition.id == "sword" or not definition.death_transferable:
        fail(
            "Item protegido: negociação suspensa; requer recuperação administrativa individual"
        )


def detail(db, auction_id, administrative=False):
    from .game import fail

    a = db.get(Auction, auction_id)
    if not a or ((a.hidden or a.archived) and not administrative):
        fail("Leilão inexistente", 404)
    return {
        **payload(db, a),
        "bids": [
            dict(
                id=b.id,
                bidder_id=b.bidder_id,
                amount=str(b.amount),
                created_at=b.created_at.isoformat() + "Z",
            )
            for b in db.scalars(
                select(AuctionBid)
                .where(AuctionBid.auction_id == a.id)
                .order_by(AuctionBid.id.desc())
            )
        ],
    }
