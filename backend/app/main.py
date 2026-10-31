from .clock import utc_now
import secrets
from datetime import datetime, timedelta
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator, StrictInt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from .database import get_db
from .models import Account, Character, Item, Battle, LinkCode
from .security import (
    current_account,
    password_hash,
    password_matches,
    issue_token,
    digest,
)
from .config import settings
from . import game

from contextlib import asynccontextmanager
import asyncio
import os


@asynccontextmanager
async def lifespan(app):
    # Deterministic integration tests exercise settle_due directly on their disposable DB.
    from .auctions import sweeper

    from .npc_production import worker

    tasks = (
        []
        if os.getenv("TOWER_TEST_DATABASE") == "1"
        else [asyncio.create_task(sweeper()), asyncio.create_task(worker())]
    )
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Tower RPG", version="0.6.0", lifespan=lifespan)
from .request_controls import RequestControls

app.add_middleware(RequestControls)


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        status_code=409, content={"detail": "Nome ou operação já existente"}
    )


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class CharacterInput(BaseModel):
    name: str = Field(min_length=2, max_length=30, pattern=r"^[\w -]+$")


class Move(BaseModel):
    dx: int = Field(ge=-1, le=1)
    dy: int = Field(ge=-1, le=1)


class Start(BaseModel):
    monster: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$")


class Action(BaseModel):
    turn: int = Field(ge=0)
    action: Literal["attack", "skill", "defend"]


class Travel(BaseModel):
    floor: int


@app.get("/health")
def health(db=Depends(get_db)):
    from sqlalchemy import text

    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
def register(body: Credentials, db=Depends(get_db)):
    a = Account(username=body.username.lower(), password=password_hash(body.password))
    db.add(a)
    db.flush()
    return issue_token(db, a)


@app.post("/auth/login")
def login(body: Credentials, db=Depends(get_db)):
    a = db.scalar(select(Account).where(Account.username == body.username.lower()))
    valid = password_matches(
        body.password, a.password if a else "0" * 32 + ":" + "0" * 64
    )
    if not a or not valid:
        raise HTTPException(401, "Credenciais inválidas")
    return issue_token(db, a)


@app.post("/character", status_code=201)
def create(body: CharacterInput, a=Depends(current_account), db=Depends(get_db)):
    c = Character(account_id=a.id, name=body.name)
    db.add(c)
    db.flush()
    from .finance import ensure

    ensure(db, f"player:{c.id}")
    db.add(Item(owner=c.id, definition="sword", quantity=1))
    db.flush()
    from .rooms import discover, current

    discover(db, c, current(db, c))
    return game.snapshot(db, c)


@app.get("/state")
def state(a=Depends(current_account), db=Depends(get_db)):
    return game.snapshot(db, game.character(db, a), wander=True)


@app.post("/move")
def move(body: Move, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    game.move(db, c, body.dx, body.dy)
    return game.snapshot(db, c)


@app.post("/interact")
def interact(a=Depends(current_account), db=Depends(get_db)):
    return game.interact(db, game.character(db, a))


@app.post("/travel")
def travel(body: Travel, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    game.travel(db, c, body.floor)
    return game.snapshot(db, c)


@app.post("/battles")
def start(body: Start, a=Depends(current_account), db=Depends(get_db)):
    return game.start_battle(db, game.character(db, a), body.monster)


@app.post("/battles/{battle_id}/action")
def action(
    battle_id: int, body: Action, a=Depends(current_account), db=Depends(get_db)
):
    return game.action(db, game.character(db, a), battle_id, body.turn, body.action)


@app.get("/rewards")
def rewards(a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    return [
        game.battle_data(b)
        for b in db.scalars(
            select(Battle).where(
                Battle.character_id == c.id,
                Battle.status == "won",
                Battle.claimed == False,
            )
        )
    ]


@app.post("/battles/{battle_id}/claim")
def claim(battle_id: int, a=Depends(current_account), db=Depends(get_db)):
    return game.claim(db, game.character(db, a), battle_id)


@app.post("/inventory/{item_id}/equip")
def equip(item_id: int, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    game.equip(db, c, item_id)
    db.flush()
    return game.snapshot(db, c)


@app.post("/discord/code")
def link_code(a=Depends(current_account), db=Depends(get_db)):
    # Lock account to serialize code replacement.
    db.scalar(select(Account).where(Account.id == a.id).with_for_update())
    old = db.scalar(select(LinkCode).where(LinkCode.account_id == a.id))
    if old:
        db.delete(old)
        db.flush()
    code = secrets.token_urlsafe(12)
    db.add(
        LinkCode(
            code=digest(code),
            account_id=a.id,
            expires=utc_now() + timedelta(minutes=5),
        )
    )
    return {"code": code, "expires_in": 300}


def bot_access(x_bot_key: str = Header(default="")):
    if not settings.discord_service_key or not secrets.compare_digest(
        x_bot_key, settings.discord_service_key
    ):
        raise HTTPException(403, "Acesso do bot não autorizado")


class Link(BaseModel):
    code: str
    discord_id: str = Field(pattern=r"^[0-9]{1,30}$")


@app.post("/discord/link", dependencies=[Depends(bot_access)])
def link(body: Link, db=Depends(get_db)):
    code = db.scalar(
        select(LinkCode).where(LinkCode.code == digest(body.code)).with_for_update()
    )
    if not code or code.expires < utc_now():
        raise HTTPException(400, "Código inválido ou expirado")
    a = db.scalar(
        select(Account).where(Account.id == code.account_id).with_for_update()
    )
    existing = db.scalar(select(Account).where(Account.discord_id == body.discord_id))
    if existing and existing.id != a.id:
        raise HTTPException(409, "Discord já vinculado a outra conta")
    a.discord_id = body.discord_id
    db.delete(code)
    return {"linked": True}


@app.get("/discord/{discord_id}/state", dependencies=[Depends(bot_access)])
def discord_state(discord_id: str, db=Depends(get_db)):
    from .discord_client import query

    return query(db, discord_id, "state")


from uuid import UUID
from . import exploration


class AdventureInput(BaseModel):
    request_id: UUID


class InviteInput(BaseModel):
    invite: str = Field(min_length=8, max_length=32)


@app.post("/rooms/exits/{exit_id}")
def exit_room(exit_id: int, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    exploration.exit_room(db, c, exit_id)
    return game.snapshot(db, c)


@app.post("/adventure")
def adventure(body: AdventureInput, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    return exploration.adventure(db, c, str(body.request_id))


@app.post("/dungeons/{room_id}/enter")
def dungeon(room_id: str, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    exploration.secret_travel(db, c, room_id)
    return game.snapshot(db, c)


@app.post("/dungeons/leave")
def leave_dungeon(a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    exploration.leave_secret(db, c)
    return game.snapshot(db, c)


@app.post("/raids")
def raid_create(a=Depends(current_account), db=Depends(get_db)):
    return exploration.create_raid(db, game.character(db, a))


@app.post("/raids/join")
def raid_join(body: InviteInput, a=Depends(current_account), db=Depends(get_db)):
    return exploration.join_raid(db, game.character(db, a), body.invite)


@app.post("/raids/leave")
def raid_leave(a=Depends(current_account), db=Depends(get_db)):
    return exploration.leave_raid(db, game.character(db, a))


from .presence import room_socket

app.websocket("/ws/rooms")(room_socket)


@app.post("/rest")
def rest(a=Depends(current_account), db=Depends(get_db)):
    return game.rest(db, game.character(db, a))


@app.get("/guild/rewards")
def guild_rewards(a=Depends(current_account), db=Depends(get_db)):
    return game.reward_summary(db, game.character(db, a))


@app.post("/guild/claim")
def guild_claim(a=Depends(current_account), db=Depends(get_db)):
    return game.claim_all(db, game.character(db, a))


@app.post("/training/reset")
def reset_training(a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    game.idle(db, c)
    from .rooms import current, discover, RoomType

    if current(db, c).kind != RoomType.TRAINING:
        game.fail("Vá ao pátio de treinamento")
    discover(db, c, current(db, c)).generation += 1
    return {"message": "Novo exercício de treinamento, sem recompensas."}


class FleeConfirmation(BaseModel):
    confirmed: Literal[True]
    confirmation_token: str = Field(min_length=64, max_length=64)


@app.get("/expeditions/{expedition_id}/flee-preview")
def flee_preview(expedition_id: int, a=Depends(current_account), db=Depends(get_db)):
    from .expeditions import preview

    return preview(db, game.character(db, a), expedition_id)


@app.post("/expeditions/{expedition_id}/flee")
def flee_expedition(
    expedition_id: int,
    body: FleeConfirmation,
    a=Depends(current_account),
    db=Depends(get_db),
):
    from .expeditions import flee

    return flee(db, game.character(db, a), expedition_id, body.confirmation_token)


class AttributeInput(BaseModel):
    model_config = {"extra": "forbid"}
    strength: int = Field(default=0, ge=0, le=2147483647, strict=True)
    defense: int = Field(default=0, ge=0, le=2147483647, strict=True)
    request_id: UUID


@app.post("/character/attributes")
def allocate_attributes(
    body: AttributeInput, a=Depends(current_account), db=Depends(get_db)
):
    from .attributes import allocate

    return allocate(
        db, game.character(db, a), body.strength, body.defense, str(body.request_id)
    )


@app.post("/deaths/{death_id}/acknowledge")
def acknowledge_death(death_id: int, a=Depends(current_account), db=Depends(get_db)):
    from .deaths import acknowledge

    return acknowledge(db, game.character(db, a), death_id)


class BidInput(BaseModel):
    model_config = {"extra": "forbid"}
    amount: str | int
    request_id: UUID

    @field_validator("amount", mode="before")
    @classmethod
    def whole_gold(cls, value):
        if type(value) is int and value > 0:
            return value
        if (
            isinstance(value, str)
            and value.isascii()
            and value.isdigit()
            and int(value) > 0
        ):
            return int(value)
        raise ValueError("Informe um lance inteiro positivo")


@app.get("/auctions")
def auctions(offset: int = 0, a=Depends(current_account), db=Depends(get_db)):
    from .auctions import listing

    if offset < 0:
        game.fail("Página inválida", 422)
    if not db.scalar(select(Character.id).where(Character.account_id == a.id)):
        game.fail("Crie seu personagem primeiro", 404)
    return listing(db, offset)


@app.post("/auctions/{auction_id}/bids")
def auction_bid(
    auction_id: int, body: BidInput, a=Depends(current_account), db=Depends(get_db)
):
    from .auctions import bid

    return bid(db, a, auction_id, int(body.amount), str(body.request_id))


@app.post("/auctions/{auction_id}/settle")
def settle_auction(auction_id: int, a=Depends(current_account), db=Depends(get_db)):
    from .auctions import settle

    if not db.scalar(select(Character.id).where(Character.account_id == a.id)):
        game.fail("Crie seu personagem primeiro", 404)
    return settle(db, auction_id)


class FastTravelInput(BaseModel):
    destination: str = Field(min_length=1, max_length=80)


@app.get("/fast-travel")
def fast_destinations(a=Depends(current_account), db=Depends(get_db)):
    from .fast_travel import destinations

    return destinations(db, game.character(db, a))


@app.post("/fast-travel")
def fast_travel(body: FastTravelInput, a=Depends(current_account), db=Depends(get_db)):
    from .fast_travel import travel

    c = game.character(db, a)
    travel(db, c, body.destination)
    return game.snapshot(db, c)


@app.get("/auctions/{auction_id}")
def auction_details(auction_id: int, a=Depends(current_account), db=Depends(get_db)):
    from .auctions import detail

    if not db.scalar(select(Character.id).where(Character.account_id == a.id)):
        game.fail("Crie seu personagem primeiro", 404)
    return detail(db, auction_id)


from .admin import router as admin_router

app.include_router(admin_router)


@app.post("/inventory/{item_id}/unequip")
def unequip(item_id: int, a=Depends(current_account), db=Depends(get_db)):
    c = game.character(db, a)
    game.unequip(db, c, item_id)
    return game.snapshot(db, c)


@app.post("/adventures/abandon-sequence")
def abandon_sequence(a=Depends(current_account), db=Depends(get_db)):
    from .expeditions import abandon_sequence

    return abandon_sequence(db, game.character(db, a))


class RecoveryConfirmation(BaseModel):
    request_id: UUID


@app.get("/recovery")
def recovery_items(a=Depends(current_account), db=Depends(get_db)):
    from .recovery import listing

    return listing(db, game.character(db, a))


@app.post("/recovery/{id}/recover")
def recovery_item(
    id: int, body: RecoveryConfirmation, a=Depends(current_account), db=Depends(get_db)
):
    from .recovery import recover

    return recover(db, game.character(db, a), id, str(body.request_id))


@app.post("/auth/logout")
def logout(
    a=Depends(current_account),
    auth=Depends(__import__("app.security", fromlist=["bearer"]).bearer),
    db=Depends(get_db),
):
    from .models import AuthSession

    row = db.get(AuthSession, digest(auth.credentials))
    if row:
        db.delete(row)
    return {"revoked": True}


@app.post("/auth/logout-all")
def logout_all(a=Depends(current_account), db=Depends(get_db)):
    from .models import AuthSession
    from sqlalchemy import delete

    db.scalar(select(Account).where(Account.id == a.id).with_for_update())
    db.execute(delete(AuthSession).where(AuthSession.account_id == a.id))
    return {"revoked": True, "all_sessions": True}


class EncounterStart(BaseModel):
    model_config = {"extra": "forbid"}
    enemy_ids: list[int] = Field(min_length=2, max_length=3)
    request_id: UUID


class EncounterAction(BaseModel):
    model_config = {"extra": "forbid"}
    turn: int = Field(ge=0, strict=True)
    target_id: int = Field(gt=0, strict=True)
    action: Literal["attack", "skill", "defend"]


class EncounterTarget(BaseModel):
    turn: int = Field(ge=0, strict=True)
    target_id: int = Field(gt=0, strict=True)


@app.post("/encounters")
def encounter_start(
    body: EncounterStart, a=Depends(current_account), db=Depends(get_db)
):
    from .encounters import start

    return start(db, game.character(db, a), body.enemy_ids, str(body.request_id))


@app.get("/encounters/{id}")
def encounter_detail(id: int, a=Depends(current_account), db=Depends(get_db)):
    from .encounters import get, payload

    return payload(db, get(db, game.character(db, a), id))


@app.post("/encounters/{id}/target")
def encounter_target(
    id: int, body: EncounterTarget, a=Depends(current_account), db=Depends(get_db)
):
    from .encounters import select_target

    return select_target(db, game.character(db, a), id, body.target_id, body.turn)


@app.post("/encounters/{id}/action")
def encounter_action(
    id: int, body: EncounterAction, a=Depends(current_account), db=Depends(get_db)
):
    from .encounters import action

    return action(db, game.character(db, a), id, body.turn, body.target_id, body.action)


@app.get("/metrics")
def player_metrics(a=Depends(current_account), db=Depends(get_db)):
    from .observability import summary

    return summary(db, game.character(db, a).id)


class GameOperation(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID


@app.get("/resources")
def resource_nodes(a=Depends(current_account), db=Depends(get_db)):
    from .resources import state

    return state(db, game.character(db, a))


@app.post("/resources/{id}/collect")
def resource_collect(
    id: int, body: GameOperation, a=Depends(current_account), db=Depends(get_db)
):
    from .resources import collect

    return collect(db, game.character(db, a), id, str(body.request_id))


@app.get("/contracts")
def contracts(offset: int = 0, a=Depends(current_account), db=Depends(get_db)):
    from .contracts import listing

    if offset < 0:
        game.fail("Página inválida", 422)
    return listing(db, game.character(db, a), offset)


@app.post("/contracts/{id}/accept")
def contract_accept(
    id: int, body: GameOperation, a=Depends(current_account), db=Depends(get_db)
):
    from .contracts import accept
    from .auctions import mutex

    mutex(db)
    return accept(db, game.character(db, a), id, str(body.request_id))


@app.post("/contracts/accepted/{id}/deliver")
def contract_deliver(
    id: int, body: GameOperation, a=Depends(current_account), db=Depends(get_db)
):
    from .contracts import deliver
    from .auctions import mutex

    mutex(db)
    return deliver(db, game.character(db, a), id, str(body.request_id))


@app.post("/contracts/accepted/{id}/claim")
def contract_claim(
    id: int, body: GameOperation, a=Depends(current_account), db=Depends(get_db)
):
    from .contracts import claim
    from .auctions import mutex

    mutex(db)
    return claim(db, game.character(db, a), id, str(body.request_id))


@app.post("/contracts/accepted/{id}/cancel")
def contract_cancel(
    id: int, body: GameOperation, a=Depends(current_account), db=Depends(get_db)
):
    from .contracts import cancel_personal
    from .auctions import mutex

    mutex(db)
    return cancel_personal(db, game.character(db, a), id)


@app.post("/discord/unlink")
def unlink_discord(a=Depends(current_account), db=Depends(get_db)):
    account = db.scalar(select(Account).where(Account.id == a.id).with_for_update())
    account.discord_id = None
    return {
        "message": "Vínculo Discord removido; confirmações anteriores deixam de autorizar ações."
    }


@app.get("/discord/{discord_id}/queries/{section}", dependencies=[Depends(bot_access)])
def discord_query(discord_id: str, section: str, db=Depends(get_db)):
    from .discord_client import query

    return query(db, discord_id, section)


@app.post(
    "/discord/{discord_id}/equipment/preview",
    dependencies=[Depends(bot_access)],
    deprecated=True,
)
@app.post(
    "/discord/{discord_id}/operations/{id}/confirm",
    dependencies=[Depends(bot_access)],
    deprecated=True,
)
def discord_gameplay_gone():
    raise HTTPException(410, "Discord é somente observação. Use a Web para jogar.")


@app.get("/lunar/wallet")
def lunar_wallet(a=Depends(current_account), db=Depends(get_db)):
    from . import lunar

    lunar.mutex(db)
    c = game.character(db, a)
    return {
        **lunar.wallet(db, f"player:{c.id}"),
        "legacy_balance": str(
            __import__("app.finance", fromlist=["funds"]).funds(db, c)
        ),
        "legacy_debt": str(
            __import__("app.finance", fromlist=["debt_units"]).debt_units(db, c)
        ),
    }


class LunarComposition(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID
    source: str
    outputs: dict[str, StrictInt]


@app.post("/lunar/nuggets/split")
def lunar_split(body: LunarComposition, a=Depends(current_account), db=Depends(get_db)):
    from . import lunar

    lunar.mutex(db)
    c = game.character(db, a)
    game.idle(db, c)
    id = f"player:{c.id}"
    lunar.account(db, id, "player", c.id)
    from .lunar_resources import capacity
    from .models import LunarEntry

    key = f"player:{c.id}:{body.request_id}"
    if not db.scalar(select(LunarEntry.id).where(LunarEntry.key == key)):
        capacity(db, c, max(0, sum(body.outputs.values()) - 1))
    entry = lunar.split(
        db, id, body.source, body.outputs, f"player:{c.id}:{body.request_id}"
    )
    return {"receipt": entry.id, "wallet": lunar.wallet(db, id)}


class LunarExchange(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID
    inputs: dict[str, StrictInt]
    outputs: dict[str, StrictInt]


@app.post("/lunar/coins/exchange")
def lunar_exchange(body: LunarExchange, a=Depends(current_account), db=Depends(get_db)):
    from . import lunar

    lunar.mutex(db)
    c = game.character(db, a)
    game.idle(db, c)
    game.receptionist(db, c)
    id = f"player:{c.id}"
    lunar.account(db, id, "player", c.id)
    entry = lunar.exchange(
        db, id, body.inputs, body.outputs, f"player:{c.id}:{body.request_id}"
    )
    return {"receipt": entry.id, "wallet": lunar.wallet(db, id)}


@app.get("/economy/shop")
def economy_shop(a=Depends(current_account), db=Depends(get_db)):
    from .guild_commerce import catalog

    return catalog(db, game.character(db, a))


@app.get("/economy/shop/catalog")
def guild_catalog(a=Depends(current_account), db=Depends(get_db)):
    from .guild_catalog import catalog

    return catalog(db, game.character(db, a))


class CatalogQuoteInput(BaseModel):
    model_config = {"extra": "forbid"}
    definition_id: str | None = Field(default=None, min_length=1, max_length=30)
    item_id: StrictInt | None = Field(default=None, gt=0)
    quantity: StrictInt = Field(gt=0, le=9007199254740991)
    operation_type: Literal["buy", "sell"]


class CatalogTradeInput(CatalogQuoteInput):
    quote: str = Field(min_length=64, max_length=64)
    request_id: UUID


@app.post("/economy/shop/catalog/quote")
def guild_catalog_quote(
    body: CatalogQuoteInput, a=Depends(current_account), db=Depends(get_db)
):
    from .guild_catalog import quote

    return quote(
        db,
        game.character(db, a),
        body.quantity,
        body.operation_type,
        body.definition_id,
        body.item_id,
    )


@app.post("/economy/shop/catalog/trade")
def guild_catalog_trade(
    body: CatalogTradeInput, a=Depends(current_account), db=Depends(get_db)
):
    from .guild_catalog import trade

    return trade(
        db,
        game.character(db, a),
        body.quantity,
        body.operation_type,
        body.quote,
        str(body.request_id),
        body.definition_id,
        body.item_id,
    )


class TradeRequest(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID
    item_id: StrictInt = Field(gt=0)
    quantity: StrictInt | None = Field(default=None, gt=0)
    quote: str = Field(min_length=64, max_length=64)


class GuildQuoteRequest(BaseModel):
    model_config = {"extra": "forbid"}
    item_id: StrictInt = Field(gt=0)
    quantity: StrictInt = Field(gt=0)
    operation_type: Literal["buy", "sell"]


@app.post("/economy/shop/quote")
def guild_item_quote(
    body: GuildQuoteRequest, a=Depends(current_account), db=Depends(get_db)
):
    from .guild_commerce import item_quote

    return item_quote(
        db, game.character(db, a), body.item_id, body.quantity, body.operation_type
    )


@app.post("/economy/shop/buy")
def economy_buy(body: TradeRequest, a=Depends(current_account), db=Depends(get_db)):
    from . import guild_commerce, npc_economy

    c = game.character(db, a)
    from .models import NPCStock, WorldEvent

    legacy = db.scalar(
        select(WorldEvent).where(
            WorldEvent.key == f"npc-sale:shop:{c.id}:{body.request_id}"
        )
    )
    if legacy:
        if body.quantity is not None:
            raise HTTPException(422, "Recibo NPC legado não aceita quantidade nova")
        return npc_economy.sell_to_player(
            db, c, body.item_id, f"shop:{c.id}:{body.request_id}", body.quote
        )
    stock = db.get(NPCStock, body.item_id)
    if stock and stock.account_id != "guild":
        if body.quantity is not None:
            raise HTTPException(422, "Comércio NPC legado transfere o estoque inteiro")
        return npc_economy.sell_to_player(
            db, c, body.item_id, f"shop:{c.id}:{body.request_id}", body.quote
        )
    return guild_commerce.item_trade(
        db, c, body.item_id, body.quantity, body.quote, str(body.request_id), "buy"
    )


@app.post("/economy/shop/sell")
def economy_sell(body: TradeRequest, a=Depends(current_account), db=Depends(get_db)):
    from .guild_commerce import item_trade
    from .models import WorldEvent

    c = game.character(db, a)
    legacy = db.scalar(
        select(WorldEvent).where(
            WorldEvent.key == f"npc-buy:shop:{c.id}:{body.request_id}"
        )
    )
    if legacy:
        if (
            body.quantity is not None
            or legacy.payload.get("character") != c.id
            or legacy.payload.get("item") != body.item_id
        ):
            raise HTTPException(
                409, "Referência histórica já utilizada com outro item/parâmetros"
            )
        return {
            "replayed": True,
            "message": "Venda histórica já confirmada; nenhum novo movimento.",
        }
    return item_trade(
        db, c, body.item_id, body.quantity, body.quote, str(body.request_id), "sell"
    )


class DebtPayment(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID
    amount: StrictInt = Field(gt=0)


@app.post("/economy/debt/pay")
def economy_debt_pay(body: DebtPayment, a=Depends(current_account), db=Depends(get_db)):
    from . import finance

    c = game.character(db, a)
    game.idle(db, c)
    game.receptionist(db, c)
    if not finance.active(db):
        raise HTTPException(409, "Conversão Lunar ainda inativa")
    if not finance.debt_mg(db, c):
        return {"message": "Nenhuma dívida pendente."}
    finance.settle_debt(db, c, body.amount, f"debt-pay:{c.id}:{body.request_id}")
    return {"message": "Pagamento da dívida confirmado."}


class LunarCollectInput(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID


@app.post("/expeditions/{expedition_id}/lunar-resources/{resource_id}/collect")
def collect_lunar_resource(
    expedition_id: int,
    resource_id: int,
    body: LunarCollectInput,
    a=Depends(current_account),
    db=Depends(get_db),
):
    from .lunar_resources import collect

    return collect(
        db, game.character(db, a), expedition_id, resource_id, str(body.request_id)
    )


@app.get("/lunar/guild-quotes")
def lunar_guild_quotes(a=Depends(current_account), db=Depends(get_db)):
    from .guild_commerce import mineral_quotes
    from .finance import active, coin_mg, cash

    c = game.character(db, a)
    return {
        "active": active(db),
        "guild_coin_mg": str(coin_mg(db, "guild")),
        "quotes": mineral_quotes(db, c, "sell"),
        "guild_quotes": mineral_quotes(db, c, "buy"),
        "guild_cash": cash(db, "guild"),
    }


class LunarSaleInput(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID
    lot_id: StrictInt = Field(gt=0)
    quote: str = Field(min_length=64, max_length=64)


@app.post("/lunar/guild-sell")
def sell_lunar_mineral(
    body: LunarSaleInput, a=Depends(current_account), db=Depends(get_db)
):
    from .lunar_resources import sell

    return sell(
        db, game.character(db, a), body.lot_id, body.quote, str(body.request_id)
    )


@app.post("/lunar/guild-buy")
def buy_lunar_mineral(
    body: LunarSaleInput, a=Depends(current_account), db=Depends(get_db)
):
    from .guild_commerce import mineral_trade

    return mineral_trade(
        db, game.character(db, a), body.lot_id, body.quote, str(body.request_id), "buy"
    )


class LotSplitInput(BaseModel):
    model_config = {"extra": "forbid"}
    request_id: UUID
    fragments_g: list[StrictInt] = Field(min_length=2, max_length=1000)


@app.post("/lunar/lots/{lot_id}/split")
def split_lot(
    lot_id: int, body: LotSplitInput, a=Depends(current_account), db=Depends(get_db)
):
    from . import mineral_lots as lots

    c = game.character(db, a)
    game.idle(db, c)
    e = lots.split(
        db,
        f"player:{c.id}",
        lot_id,
        body.fragments_g,
        f"lot-split:{c.id}:{body.request_id}",
    )
    return {"receipt": e.id, "message": "Pepita dividida sem taxa e sem perda."}


@app.get("/economy/npcs")
def npc_list(a=Depends(current_account), db=Depends(get_db)):
    from . import npc_economy as npc
    from .models import NpcProfile

    game.character(db, a)
    return [
        npc.state(db, row.id)
        for row in db.scalars(
            select(NpcProfile).where(NpcProfile.id != "guild").order_by(NpcProfile.id)
        )
    ]


def npc_owner(db, npc_id):
    from .models import NpcProfile

    row = db.get(NpcProfile, npc_id)
    if not row or row.id == "guild":
        raise HTTPException(404, "NPC inexistente")
    return row.account_id


@app.get("/economy/npcs/{npc_id}/shop")
def npc_shop(npc_id: str, a=Depends(current_account), db=Depends(get_db)):
    from .guild_catalog import catalog

    return catalog(db, game.character(db, a), account=npc_owner(db, npc_id))


@app.post("/economy/npcs/{npc_id}/quote")
def npc_shop_quote(
    npc_id: str, body: CatalogQuoteInput, a=Depends(current_account), db=Depends(get_db)
):
    from .guild_catalog import quote

    return quote(
        db,
        game.character(db, a),
        body.quantity,
        body.operation_type,
        body.definition_id,
        body.item_id,
        account=npc_owner(db, npc_id),
    )


@app.post("/economy/npcs/{npc_id}/trade")
def npc_shop_trade(
    npc_id: str, body: CatalogTradeInput, a=Depends(current_account), db=Depends(get_db)
):
    from .guild_catalog import trade

    return trade(
        db,
        game.character(db, a),
        body.quantity,
        body.operation_type,
        body.quote,
        str(body.request_id),
        body.definition_id,
        body.item_id,
        account=npc_owner(db, npc_id),
    )


@app.post("/economy/npcs/{npc_id}/interact")
def npc_interact(npc_id: str, a=Depends(current_account), db=Depends(get_db)):
    from .npc_economy import require_service

    require_service(db, game.character(db, a), npc_owner(db, npc_id))
    return {"open_npc_shop": npc_id, "message": "Balcão aberto."}
