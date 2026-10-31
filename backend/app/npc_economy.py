"""Finite custody stock. No implicit products/prices, restock or starting NPC cash."""

from sqlalchemy import select
from . import models as m, finance, lunar
from .game import fail, idle
from .rooms import current
from .world import distance


def at_service(db, c):
    idle(db, c)
    r = current(db, c)
    if (
        r.id not in ("guild", "auction_hall")
        or not r.data.get("npc")
        or distance((c.x, c.y), r.data["npc"]) > 1
    ):
        fail("Aproxime-se de um serviço da Guilda")


def quote(item, price, account):
    return lunar.fingerprint(
        [
            item.id,
            item.definition,
            item.owner,
            item.location,
            item.quantity,
            str(price),
            account,
        ]
    )


def sell_to_player(db, c, item_id, key, expected_quote=None):
    lunar.mutex(db)
    at_service(db, c)
    if not finance.active(db):
        fail("Cutover necessário")
    old = db.scalar(select(m.WorldEvent).where(m.WorldEvent.key == "npc-sale:" + key))
    if old:
        if old.payload != {"character": c.id, "item": item_id}:
            fail("Chave de compra já usada")
        return {"replayed": True}
    managed = db.scalar(
        select(m.NpcProfile.id)
        .join(m.NPCStock, m.NPCStock.account_id == m.NpcProfile.account_id)
        .where(m.NPCStock.item_id == item_id, m.NpcProfile.id != "guild")
    )
    if managed:
        fail("Use a loja atual do NPC e uma cotação por quantidade", 409)
    stock = db.get(m.NPCStock, item_id)
    item = db.get(m.Item, item_id)
    if not stock or not item or item.location != "npc" or item.owner is not None:
        fail("Estoque indisponível")
    if expected_quote is not None and expected_quote != quote(
        item, stock.sale_weight_mg, stock.account_id
    ):
        fail("Preço ou estoque mudou; revise a prévia")
    if finance.debt_mg(db, c):
        fail("Quite a dívida antes de comprar")
    from .inventory import ensure_collection_capacity
    from .config import settings

    ensure_collection_capacity(
        db,
        c,
        db.get(m.ItemDefinition, item.definition),
        item.quantity,
        settings.collection_slots,
    )
    if stock.sale_weight_mg % 1000:
        fail("Preço não representável")
    finance.move(
        db,
        f"player:{c.id}",
        stock.account_id,
        stock.sale_weight_mg // 1000,
        key,
        amortize=False,
    )
    # Context is immutable: item receipt is separate from the money receipt.
    db.add(
        m.WorldEvent(
            key="npc-sale:" + key,
            kind="NPC_SALE",
            payload={"character": c.id, "item": item_id},
        )
    )
    item.owner = c.id
    item.location = "inventory"
    db.delete(stock)
    return {"item_id": item.id}


def buy_from_player(db, c, item_id, npc, price_mg, key):
    # Internal service only: quote is server-provided, never a client price.
    lunar.mutex(db)
    at_service(db, c)
    if not finance.active(db):
        fail("Cutover necessário")
    old = db.scalar(select(m.WorldEvent).where(m.WorldEvent.key == "npc-buy:" + key))
    if old:
        if old.payload != {
            "character": c.id,
            "item": item_id,
            "npc": npc,
            "price_mg": str(price_mg),
        }:
            fail("Chave de venda já usada")
        return {"replayed": True}
    item = db.get(m.Item, item_id)
    if not item or item.owner != c.id or item.location != "inventory":
        fail("Item indisponível")
    d = db.get(m.ItemDefinition, item.definition)
    if d.id == "sword" or not d.death_transferable or item.equipped:
        fail("Item protegido")
    lunar.integer(price_mg, True)
    if price_mg % 1000:
        fail("Preço não representável")
    finance.ensure(db, npc)
    finance.move(db, npc, f"player:{c.id}", price_mg // 1000, key)
    db.add(
        m.WorldEvent(
            key="npc-buy:" + key,
            kind="NPC_PURCHASE",
            payload={
                "character": c.id,
                "item": item_id,
                "npc": npc,
                "price_mg": str(price_mg),
            },
        )
    )
    item.owner = None
    item.location = "npc"
    item.equipped = False
    db.add(m.NPCStock(item_id=item.id, account_id=npc, sale_weight_mg=price_mg))
    return {"item_id": item.id}


# Producers and the material merchant use the same Item/NPCStock custody and Lunar cash.
RAW = ("herb", "crystal", "ore")
RECIPES = [
    ("weak_healing_potion", "alchemist", {"herb": 2, "crystal": 1}, "alchemy", 10),
    ("healing_potion", "alchemist", {"herb": 4, "crystal": 2}, "alchemy", 11),
    ("energy_potion", "alchemist", {"herb": 1, "crystal": 4}, "alchemy", 12),
    ("moss_ingot", "blacksmith", {"ore": 5}, "smelting", 20),
    *[
        (key, "blacksmith", {"moss_ingot": qty}, "smithing", 30 + index)
        for index, (key, qty) in enumerate(
            [
                ("moss_sword", 3),
                ("moss_helmet", 2),
                ("moss_chest", 5),
                ("moss_gloves", 2),
                ("moss_pants", 4),
                ("moss_boots", 2),
            ]
        )
    ],
]
SERVICES = [
    {"id": "merchant", "name": "Comerciante", "x": 34, "y": 8, "sprite": "merchant"},
    {"id": "alchemist", "name": "Alquimista", "x": 36, "y": 15, "sprite": "alchemist"},
    {"id": "blacksmith", "name": "Ferreiro", "x": 16, "y": 22, "sprite": "blacksmith"},
]


def record(db, key, kind, **payload):
    from .clock import utc_now
    import logging

    db.add(
        m.WorldEvent(
            key=key,
            kind=kind,
            processed=True,
            payload={"occurred_at": utc_now().isoformat(), **payload},
        )
    )
    logging.getLogger("dungeon.npc_economy").info(
        kind.lower(), extra={"event_key": key}
    )


def stock(db, owner, definition=None, lock=False):
    q = (
        select(m.Item, m.NPCStock)
        .join(m.NPCStock, m.NPCStock.item_id == m.Item.id)
        .where(
            m.NPCStock.account_id == owner,
            m.Item.owner == None,
            m.Item.location == "npc",
        )
    )
    if definition is not None:
        q = q.where(m.Item.definition == definition)
    q = q.order_by(m.Item.id)
    if lock:
        q = q.with_for_update(of=(m.Item, m.NPCStock))
    return list(db.execute(q))


def quantities(db, owner):
    result = {}
    for item, _ in stock(db, owner):
        result[item.definition] = result.get(item.definition, 0) + item.quantity
    return result


def give(db, owner, definition, quantity):
    """Only approved initial stock or a fully validated recipe may create custody."""
    d = db.get(m.ItemDefinition, definition)
    ids = []
    while quantity:
        count = quantity if d.stackable else 1
        i = m.Item(owner=None, definition=definition, quantity=count, location="npc")
        db.add(i)
        db.flush()
        db.add(m.NPCStock(item_id=i.id, account_id=owner, sale_weight_mg=0))
        ids.append(i.id)
        quantity -= count
    db.flush()
    return ids


def consume(db, owner, definition, quantity):
    rows = stock(db, owner, definition, lock=True)
    if sum(i.quantity for i, _ in rows) < quantity:
        fail("Estoque insuficiente para a receita")
    movements = []
    for i, custody in rows:
        n = min(quantity, i.quantity)
        movements.append({"item_id": i.id, "quantity": n, "before": i.quantity})
        if n == i.quantity:
            db.delete(custody)
            i.location = "destroyed"
        else:
            i.quantity -= n
        quantity -= n
        if not quantity:
            break
    db.flush()
    return movements


def transfer_stock(db, source, destination, definition, quantity):
    lunar.integer(quantity, True)
    if source == destination:
        fail("Origem e destino devem diferir", 422)
    rows = stock(db, source, definition, lock=True)
    if sum(i.quantity for i, _ in rows) < quantity:
        fail("OUT_OF_STOCK: estoque insuficiente")
    target = db.scalar(
        select(m.NpcProfile).where(m.NpcProfile.account_id == destination)
    )
    policy = (
        db.get(m.NpcInventoryPolicy, (target.id, definition))
        if target and target.id != "guild"
        else None
    )
    if (
        target
        and target.id != "guild"
        and (
            not policy
            or quantities(db, destination).get(definition, 0) + quantity
            > policy.capacity
        )
    ):
        fail("Capacidade do NPC insuficiente")
    if not target:
        fail("NPC destinatário inexistente", 404)
    movements = []
    for i, custody in rows:
        n = min(quantity, i.quantity)
        oldid = i.id
        if n == i.quantity:
            custody.account_id = destination
            moved = i
        else:
            i.quantity -= n
            moved = m.Item(
                owner=None, definition=definition, quantity=n, location="npc"
            )
            db.add(moved)
            db.flush()
            db.add(
                m.NPCStock(item_id=moved.id, account_id=destination, sale_weight_mg=0)
            )
        movements.append({"source_item_id": oldid, "item_id": moved.id, "quantity": n})
        quantity -= n
        if not quantity:
            break
    db.flush()
    return movements


def initialize(db):
    """One historical material bootstrap per new profile, never replenishment."""
    from . import market_pricing as pricing

    lunar.mutex(db)
    definitions = [
        ("weak_healing_potion", "Poção de Cura Fraca", "consumable", None),
        ("healing_potion", "Poção de Cura", "consumable", None),
        ("energy_potion", "Poção de Energia", "consumable", None),
        ("moss_ingot", "Lingote de Musgo", "material", None),
        ("moss_sword", "Espada de Musgo", "weapon", "weapon"),
        ("moss_helmet", "Capacete de Musgo", "armor", "head"),
        ("moss_chest", "Peitoral de Musgo", "armor", "chest"),
        ("moss_gloves", "Luvas de Musgo", "armor", "hands"),
        ("moss_pants", "Calças de Musgo", "armor", "legs"),
        ("moss_boots", "Botas de Musgo", "armor", "feet"),
    ]
    for key, name, kind, slot in definitions:
        if not db.get(m.ItemDefinition, key):
            db.add(
                m.ItemDefinition(
                    id=key,
                    name=name,
                    kind=kind,
                    equipment_slot=slot,
                    power=0,
                    base_value=0,
                    stackable=slot is None,
                    max_stack_size=99 if slot is None else 1,
                    description="Mercadoria produzida na vila.",
                )
            )
    db.flush()
    for id, name, factors, initial in [
        ("guild", "Guilda", {}, {}),
        ("merchant", "Comerciante", {}, {}),
        (
            "alchemist",
            "Alquimista",
            {"alchemy": 12500},
            {
                "herb": 7,
                "crystal": 7,
                **{r[0]: 1 for r in RECIPES if r[1] == "alchemist"},
            },
        ),
        (
            "blacksmith",
            "Ferreiro",
            {"smelting": 12000, "smithing": 13000},
            {
                "ore": 90,
                **{
                    r[0]: 1
                    for r in RECIPES
                    if r[1] == "blacksmith" and r[0] != "moss_ingot"
                },
            },
        ),
    ]:
        if db.get(m.NpcProfile, id):
            continue
        owner = "guild" if id == "guild" else "npc:" + id
        existing = quantities(db, owner)
        finance.ensure(db, owner)
        profile = m.NpcProfile(
            id=id,
            account_id=owner,
            name=name,
            factors=factors,
            fixed_margin=1 if id in ("guild", "merchant") else 0,
        )
        db.add(profile)
        db.flush()
        if id == "guild":
            continue
        materials = (
            RAW
            if id == "merchant"
            else ("herb", "crystal") if id == "alchemist" else ("ore",)
        )
        for material in materials:
            db.add(
                m.NpcInventoryPolicy(
                    npc_id=id,
                    definition_id=material,
                    capacity=max(
                        existing.get(material, 0), 20 if id == "alchemist" else 100
                    ),
                    reorder_point=10,
                    order_quantity=10,
                    minimum_lot_size=10 if id == "merchant" else 1,
                    order_step=10 if id == "merchant" else 1,
                    production_enabled=False,
                    sell_enabled=id == "merchant",
                )
            )
        for result, producer, ingredients, factor, priority in RECIPES:
            if producer != id:
                continue
            db.add(
                m.NpcRecipe(
                    result_id=result,
                    npc_id=id,
                    ingredients=ingredients,
                    factor_key=factor,
                    priority=priority,
                )
            )
            db.add(
                m.NpcInventoryPolicy(
                    npc_id=id,
                    definition_id=result,
                    capacity=max(
                        existing.get(result, 0), 100 if result == "moss_ingot" else 2
                    ),
                    target_stock=0 if result == "moss_ingot" else 2,
                    buy_enabled=False,
                    sell_enabled=result != "moss_ingot",
                )
            )
        db.flush()
        added = (
            {}
            if existing
            else {
                key: {"quantity": n, "item_ids": give(db, owner, key, n)}
                for key, n in initial.items()
            }
        )
        record(
            db,
            "npc-initialize:" + id,
            "NPC_INITIAL_STOCK",
            npc=id,
            actor="seed",
            origin="APPROVED_HISTORICAL_STOCK",
            added=added,
            adopted=existing,
            money_created="0",
        )
    db.flush()
    pricing.refresh(
        db, "seed", "Inicialização idempotente da cadeia de produção autorizada"
    )
    city = db.get(m.Room, "city1")
    if city:
        previous = city.data.get("service_npcs")
        if previous is None:
            city.data = {**city.data, "service_npcs": SERVICES}


def require_service(db, c, owner):
    from .rooms import current

    idle(db, c)
    room = current(db, c)
    profile = db.scalar(select(m.NpcProfile).where(m.NpcProfile.account_id == owner))
    service = next(
        (
            n
            for n in room.data.get("service_npcs", [])
            if profile and n["id"] == profile.id
        ),
        None,
    )
    if (
        c.room_id != "city1"
        or not service
        or distance((c.x, c.y), (service["x"], service["y"])) > 1
    ):
        fail("Aproxime-se do NPC na vila")


def state(db, npc_id, admin=False):
    from . import market_pricing as pricing

    profile = db.get(m.NpcProfile, npc_id)
    if not profile:
        fail("NPC inexistente", 404)
    current = quantities(db, profile.account_id)
    revision = pricing.latest(db)
    rows = []
    for p in db.scalars(
        select(m.NpcInventoryPolicy)
        .where(m.NpcInventoryPolicy.npc_id == npc_id)
        .order_by(m.NpcInventoryPolicy.definition_id)
    ):
        d = db.get(m.ItemDefinition, p.definition_id)
        q = pricing.price(db, profile.account_id, d.id, p.minimum_lot_size)
        rows.append(
            {
                **{
                    k: getattr(p, k)
                    for k in (
                        "definition_id",
                        "capacity",
                        "reorder_point",
                        "order_quantity",
                        "target_stock",
                        "minimum_lot_size",
                        "order_step",
                        "production_enabled",
                        "buy_enabled",
                        "sell_enabled",
                        "revision",
                        "status",
                    )
                },
                "name": d.name,
                "stock": str(current.get(d.id, 0)),
                "price_units": revision.snapshot["prices"][d.id],
                "minimum_lot_quote": q,
                "equipment_slot": d.equipment_slot,
                "recipe": (
                    db.get(m.NpcRecipe, d.id).ingredients
                    if db.get(m.NpcRecipe, d.id)
                    else None
                ),
            }
        )
    from sqlalchemy import or_

    history = (
        list(
            db.scalars(
                select(m.WorldEvent)
                .where(
                    m.WorldEvent.kind.in_(
                        (
                            "NPC_PRODUCTION",
                            "NPC_PURCHASE",
                            "NPC_SALE",
                            "NPC_RESTOCK_REQUEST",
                            "NPC_CONFIG_UPDATED",
                            "NPC_INVENTORY_ADJUSTED",
                            "NPC_INITIAL_STOCK",
                        )
                    ),
                    or_(
                        m.WorldEvent.payload["npc"].as_string() == npc_id,
                        m.WorldEvent.payload["source_npc"].as_string() == npc_id,
                        m.WorldEvent.payload["destination_npc"].as_string() == npc_id,
                    ),
                )
                .order_by(m.WorldEvent.id.desc())
                .limit(100)
            )
        )
        if admin
        else []
    )

    return {
        "id": profile.id,
        "name": profile.name,
        "account_id": profile.account_id,
        **{
            k: getattr(profile, k)
            for k in (
                "enabled",
                "production_enabled",
                "purchase_enabled",
                "sale_enabled",
                "fixed_margin",
                "factors",
                "revision",
            )
        },
        "stock_items": [
            {
                "definition_id": key,
                "name": db.get(m.ItemDefinition, key).name,
                "quantity": str(value),
            }
            for key, value in current.items()
        ],
        "wallet": finance.cash(db, profile.account_id),
        "items": rows,
        "market_revision": revision.id,
        "last_update": profile.updated_at.isoformat(),
        "history": [
            {"id": h.id, "kind": h.kind, "request_id": h.key, **h.payload}
            for h in history
            if admin
            and npc_id
            in (
                h.payload.get("npc"),
                h.payload.get("source_npc"),
                h.payload.get("destination_npc"),
            )
        ],
    }
