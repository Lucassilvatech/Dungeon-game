"""Guild contracts spend real reserved treasury funds; progress never takes a financial mutex."""

from sqlalchemy import select, func
from .models import (
    GuildContract,
    CharacterContract,
    Item,
    ItemDefinition,
    Treasury,
    WorldEvent,
)
from .clock import utc_now
from .finance import active, institution
from .rooms import event
from .economy import ledger, credit_player_gold
from .config import settings


def validate(db, p):
    from .game import fail
    from .admin_economy import amount

    try:
        name = p["name"]
        description = p["description"]
        kind = p["kind"]
        target = p["target"]
        required = p["required"]
        slots = p["slots"]
        reward = amount(p["reward"])
        if not isinstance(target, str) or not 1 <= len(target) <= 30:
            raise ValueError()
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 100
            or not isinstance(description, str)
            or not 1 <= len(description) <= 500
        ):
            raise ValueError()
        if (
            type(required) is not int
            or not 1 <= required <= 1000
            or type(slots) is not int
            or not 1 <= slots <= 100
        ):
            raise ValueError()
        if kind == "kill":
            if target not in ("slime", "goblin"):
                raise ValueError()
        elif kind in ("collect", "deliver"):
            d = db.get(ItemDefinition, target)
            if (
                not d
                or d.kind != "material"
                or d.unique_item
                or not d.death_transferable
                or (kind == "collect" and target not in ("herb", "ore"))
            ):
                raise ValueError()
        else:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        fail("Configuração de contrato inválida", 422)
    return {
        "name": name,
        "description": description,
        "kind": kind,
        "target": target,
        "required": required,
        "slots": slots,
        "reward": reward,
    }


def publish(db, p, operation_id=None):
    from .game import fail

    data = validate(db, p)
    budget = data["reward"] * data["slots"]
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    if institution(db, "treasury") < budget:
        fail("Tesouro sem orçamento para garantir todas as vagas")
    contract = GuildContract(
        **data, reserved=budget, taken=0, operation_id=operation_id
    )
    db.add(contract)
    db.flush()
    if not active(db):
        treasury.balance -= budget
    ledger(
        db,
        f"contract-reserve:{contract.id}",
        "treasury",
        f"contract:{contract.id}",
        budget,
    )
    return contract


def definition(db, id, lock=False):
    from .game import fail

    query = select(GuildContract).where(GuildContract.id == id)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query)
    if not row:
        fail("Contrato inexistente", 404)
    return row


def payload(row):
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "kind": row.kind,
        "target": row.target,
        "required": row.required,
        "reward": str(row.reward),
        "slots": row.slots,
        "taken": row.taken,
        "available_slots": row.slots - row.taken if row.status == "OPEN" else 0,
        "reserved": str(row.reserved),
        "status": row.status,
        "location_rule": "Aceitar, entregar e resgatar junto à recepcionista da Guilda, fora de combate.",
    }


def listing(db, c, offset=0):
    definitions = db.scalars(
        select(GuildContract)
        .order_by(GuildContract.id.desc())
        .offset(offset)
        .limit(100)
    ).all()
    own = db.execute(
        select(CharacterContract, GuildContract)
        .join(GuildContract, GuildContract.id == CharacterContract.contract_id)
        .where(CharacterContract.character_id == c.id)
        .order_by(CharacterContract.id.desc())
        .offset(offset)
        .limit(100)
    ).all()
    return {
        "definitions": [payload(d) for d in definitions],
        "accepted": [
            {
                "id": a.id,
                "contract": payload(d),
                "progress": a.progress,
                "status": a.status,
                "can_claim": a.status == "ACTIVE" and a.progress >= d.required,
                "accepted_at": a.accepted_at.isoformat() + "Z",
            }
            for a, d in own
        ],
    }


def reception(db, c):
    from .game import idle, receptionist

    idle(db, c)
    receptionist(db, c)


def accept(db, c, id, request_id):
    from .game import fail

    old = db.scalar(
        select(CharacterContract).where(
            CharacterContract.character_id == c.id,
            CharacterContract.request_id == request_id,
        )
    )
    if old:
        if old.contract_id != id:
            fail("Chave de aceitação já usada com outro contrato")
        return {"id": old.id, "status": old.status, "replayed": True}
    previous = db.scalar(
        select(CharacterContract).where(
            CharacterContract.character_id == c.id, CharacterContract.contract_id == id
        )
    )
    if previous:
        return {"id": previous.id, "status": previous.status, "replayed": True}
    reception(db, c)
    d = definition(db, id, True)
    if d.status != "OPEN" or d.taken >= d.slots:
        fail("Contrato sem vagas ou retirado")
    count = db.scalar(
        select(func.count())
        .select_from(CharacterContract)
        .where(
            CharacterContract.character_id == c.id, CharacterContract.status == "ACTIVE"
        )
    )
    if count >= settings.max_active_contracts:
        fail("Limite de contratos ativos atingido")
    a = CharacterContract(
        character_id=c.id, contract_id=d.id, request_id=request_id, progress=0
    )
    db.add(a)
    d.taken += 1
    db.flush()
    from .observability import add

    add(db, c, contracts_accepted=1)
    event(
        db,
        "CONTRACT_ACCEPTED",
        c,
        key=f"contract-accept:{a.id}",
        acceptance_id=a.id,
        contract_id=d.id,
        reward=str(d.reward),
    )
    return {
        "id": a.id,
        "message": "Contrato aceito; recompensa já garantida pela reserva da Guilda.",
    }


def progress(db, c, kind, target, quantity):
    rows = db.execute(
        select(CharacterContract, GuildContract)
        .join(GuildContract, GuildContract.id == CharacterContract.contract_id)
        .where(
            CharacterContract.character_id == c.id,
            CharacterContract.status == "ACTIVE",
            GuildContract.status == "OPEN",
            GuildContract.kind == kind,
            GuildContract.target == target,
        )
    ).all()
    for a, d in rows:
        a.progress = min(d.required, a.progress + quantity)


def owned(db, c, id):
    from .game import fail

    a = db.scalar(
        select(CharacterContract)
        .where(CharacterContract.id == id, CharacterContract.character_id == c.id)
        .with_for_update()
    )
    if not a:
        fail("Aceitação de contrato inexistente", 404)
    return a, definition(db, a.contract_id, True)


def deliver(db, c, id, request_id):
    from .game import fail

    key = f"contract-delivery:{c.id}:{request_id}"
    old = db.scalar(select(WorldEvent).where(WorldEvent.key == key))
    if old:
        if old.payload["acceptance_id"] != id:
            fail("Chave de entrega já usada em outro contrato")
        return {"message": "Entrega já confirmada.", "replayed": True}
    reception(db, c)
    a, d = owned(db, c, id)
    if a.progress >= d.required:
        return {"message": "Materiais já entregues.", "replayed": True}
    if a.status != "ACTIVE" or d.status != "OPEN" or d.kind != "deliver":
        fail("Contrato não aceita entrega")
    item_definition = db.get(ItemDefinition, d.target)
    if (
        item_definition.kind != "material"
        or not item_definition.death_transferable
        or item_definition.unique_item
    ):
        fail("Material protegido ou inelegível")
    rows = db.scalars(
        select(Item)
        .where(
            Item.owner == c.id,
            Item.definition == d.target,
            Item.location == "inventory",
            Item.equipped == False,
        )
        .order_by(Item.id)
        .with_for_update()
    ).all()
    required = d.required - a.progress
    if sum(i.quantity for i in rows) < required:
        fail("Materiais insuficientes; nenhuma unidade foi consumida")
    remaining = required
    consumed = []
    for item in rows:
        units = min(remaining, item.quantity)
        if not units:
            continue
        consumed.append({"item_id": item.id, "quantity": units})
        if units == item.quantity:
            item.location = "consumed"
        else:
            item.quantity -= units
        remaining -= units
    a.progress = d.required
    from .observability import add

    add(db, c, contract_items_delivered=required)
    event(db, "CONTRACT_DELIVERED", c, key=key, acceptance_id=a.id, items=consumed)
    return {
        "message": "Entrega confirmada. A reserva garante seu pagamento, inclusive se a publicação for retirada."
    }


def claim(db, c, id, request_id):
    from .game import fail

    a, d = owned(db, c, id)
    if a.status == "PAID":
        return {
            "paid": str(d.reward),
            "replayed": True,
            "message": "Recompensa já paga.",
        }
    reception(db, c)
    if a.status != "ACTIVE" or a.progress < d.required or d.reserved < d.reward:
        fail("Contrato incompleto ou reserva inconsistente")
    d.reserved -= d.reward
    a.status = "PAID"
    a.finished_at = utc_now()
    a.claim_request_id = request_id
    credit_player_gold(db, c, d.reward, f"contract:{d.id}", f"contract-pay:{a.id}")
    if d.reserved == 0 and d.status == "OPEN":
        d.status = "COMPLETED"
    from .observability import add

    add(db, c, contract_rewards_claimed=d.reward, contracts_paid=1)
    event(
        db,
        "CONTRACT_PAID",
        c,
        key=f"contract-pay:{a.id}",
        acceptance_id=a.id,
        contract_id=d.id,
        amount=str(d.reward),
    )
    return {
        "paid": str(d.reward),
        "message": f"Contrato pago: {d.reward} moedas transferidas da reserva.",
    }


def cancel_personal(db, c, id):
    from .game import fail, idle

    idle(db, c)
    a, d = owned(db, c, id)
    if a.status == "CANCELLED":
        return {"replayed": True, "message": "Contrato já cancelado."}
    if a.status != "ACTIVE" or a.progress >= d.required:
        fail("Resgate o direito já concluído; cancelamento não destrói sua recompensa")
    a.status = "CANCELLED"
    a.finished_at = utc_now()
    d.taken -= 1
    event(
        db, "CONTRACT_CANCELLED", c, key=f"contract-cancel:{a.id}", acceptance_id=a.id
    )
    return {
        "message": "Contrato cancelado; vaga liberada e orçamento mantido em garantia da publicação."
    }


def cancellation_plan(db, d):
    rows = db.scalars(
        select(CharacterContract)
        .where(
            CharacterContract.contract_id == d.id, CharacterContract.status == "ACTIVE"
        )
        .order_by(CharacterContract.id)
    ).all()
    ready = sum(a.progress >= d.required for a in rows)
    return {
        "acceptances": [
            {
                "id": a.id,
                "character_id": a.character_id,
                "progress": a.progress,
                "status": a.status,
            }
            for a in rows
        ],
        "retained": str(ready * d.reward),
        "refund": str(d.reserved - ready * d.reward),
    }


def cancel_publication(db, id, operation_id):
    from .game import fail

    d = definition(db, id, True)
    if d.status != "OPEN":
        fail("Publicação já encerrada")
    plan = cancellation_plan(db, d)
    refund = int(plan["refund"])
    if refund < 0:
        fail("Reserva inconsistente; investigue antes de cancelar")
    treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update())
    if not active(db):
        treasury.balance += refund
    d.reserved -= refund
    d.status = "CANCELLED"
    ledger(
        db, f"contract-cancel:{operation_id}", f"contract:{d.id}", "treasury", refund
    )
    for a in db.scalars(
        select(CharacterContract).where(
            CharacterContract.contract_id == d.id, CharacterContract.status == "ACTIVE"
        )
    ):
        if a.progress < d.required:
            a.status = "CANCELLED"
            a.finished_at = utc_now()
            d.taken -= 1
    return plan
