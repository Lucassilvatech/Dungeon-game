from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from .database import get_db
from . import models as m
from .admin_security import principal, require, login
from .admin_service import preview, confirm, data, ACTIONS, operation_payload
from .admin_economy import metrics
from .security import bearer, digest
from .clock import utc_now

router = APIRouter(prefix="/admin", tags=["administration"])


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)


@router.post("/auth/login")
def admin_login(body: Login, request: Request, db=Depends(get_db)):
    return login(
        db,
        body.username,
        body.password,
        request.client.host if request.client else "unknown",
    )


@router.get("/session")
def session(actor=Depends(principal)):
    return {
        "account_id": actor.id,
        "role": actor.role,
        "permissions": sorted(actor.permissions),
        "actions": {k: v for k, v in ACTIONS.items() if v in actor.permissions},
    }


@router.post("/auth/logout")
def logout(actor=Depends(principal), auth=Depends(bearer), db=Depends(get_db)):
    row = db.get(m.AdminSession, digest(auth.credentials))
    db.delete(row)
    return {"revoked": True}


class OperationInput(BaseModel):
    model_config = {"extra": "forbid"}
    operation_id: UUID
    action: str = Field(min_length=1, max_length=60)
    target: str = Field(min_length=1, max_length=80)
    params: dict = Field(default_factory=dict)
    reason: str = Field(min_length=10, max_length=500)


class Confirmation(BaseModel):
    model_config = {"extra": "forbid"}
    confirmed: Literal[True]
    confirmation_token: str = Field(min_length=64, max_length=64)

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit_true(cls, value):
        if value is not True:
            raise ValueError("Confirmação explícita obrigatória")
        return value


@router.post("/operations/preview")
def operation_preview(
    body: OperationInput, actor=Depends(principal), db=Depends(get_db)
):
    return preview(db, actor, body)


@router.post("/operations/{id}/confirm")
def operation_confirm(
    id: UUID, body: Confirmation, actor=Depends(principal), db=Depends(get_db)
):
    try:
        with db.begin_nested():
            return confirm(db, actor, str(id), body.confirmation_token)
    except HTTPException as exc:
        # Preserve rejected-operation audit, while rolling back every partial effect.
        from .auctions import mutex

        mutex(db)
        row = db.scalar(
            select(m.AdminOperation)
            .where(m.AdminOperation.id == str(id))
            .with_for_update()
        )
        if row and row.actor_id == actor.id and row.status != "COMMITTED":
            row.status = "FAILED"
            row.after = {"error": exc.detail}
            row.finished_at = utc_now()
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@router.get("/items/starter-diagnostics")
def starter_diagnostics(actor=Depends(principal), db=Depends(get_db)):
    require(actor, "items.read")
    result = []
    for a, i in db.execute(
        select(m.Auction, m.Item)
        .join(m.Item, m.Item.id == m.Auction.item_id)
        .where(m.Item.definition == "sword")
        .order_by(m.Auction.id)
    ):
        result.append(
            {
                "auction": data(a),
                "item": data(i),
                "recommendation": (
                    "recover_starter: original in custody; requires individual preview/confirmation"
                    if i.owner is None
                    and i.location == "auction"
                    and a.status in ("OPEN", "CLOSED", "UNSOLD")
                    else (
                        "replace_starter: review and authorize replacement; do not confiscate buyer's item"
                        if a.status == "SETTLED" and i.owner != a.former_owner_id
                        else "no automatic intervention"
                    )
                ),
            }
        )
    return result


@router.get("/{module}")
def view(
    module: str,
    q: str = "",
    offset: int = 0,
    actor=Depends(principal),
    db=Depends(get_db),
):
    if module == "royal":
        require(actor, "economy.read")
        from .royal import overview

        return overview(db)
    if offset < 0:
        raise HTTPException(422, "Página inválida")
    permission = "economy.read" if module == "lunar" else module + ".read"
    require(actor, permission)
    if module == "lunar":
        from . import finance, lunar, cutover

        return {
            "active": finance.active(db),
            "audit": finance.metrics(db) if finance.active(db) else lunar.audit(db),
            "preview": (
                cutover.preview(db)
                if not finance.active(db) and "economy.manage" in actor.permissions
                else None
            ),
        }
    if module == "encounters":
        from .encounters import payload

        return [
            payload(db, g)
            for g in db.scalars(
                select(m.CombatEncounter)
                .order_by(m.CombatEncounter.id.desc())
                .offset(offset)
                .limit(100)
            )
        ]
    if module == "collection":
        return [
            {**data(n), "name": db.get(m.ItemDefinition, n.definition).name}
            for n in db.scalars(
                select(m.ResourceNode)
                .order_by(m.ResourceNode.id.desc())
                .offset(offset)
                .limit(100)
            )
        ]
    if module == "contracts":
        from .contracts import payload

        return {
            "definitions": [
                payload(d)
                for d in db.scalars(
                    select(m.GuildContract)
                    .order_by(m.GuildContract.id.desc())
                    .offset(offset)
                    .limit(100)
                )
            ],
            "acceptances": [
                data(a)
                for a in db.scalars(
                    select(m.CharacterContract)
                    .order_by(m.CharacterContract.id.desc())
                    .offset(offset)
                    .limit(100)
                )
            ],
        }
    if module == "metrics":
        from .observability import summary

        return summary(db)
    if module == "overview":
        return {
            "players": db.scalar(select(func.count()).select_from(m.Character)),
            "active_expeditions": db.scalar(
                select(func.count())
                .select_from(m.Expedition)
                .where(m.Expedition.status == "ACTIVE")
            ),
            "economy": metrics(db),
            "first_floor_only": True,
        }
    if module == "economy":
        entries = db.scalars(
            select(m.Ledger).order_by(m.Ledger.id.desc()).offset(offset).limit(100)
        ).all()
        return {
            "indicators": metrics(db),
            "ledger": [data(e) for e in entries],
            "settings": [data(e) for e in db.scalars(select(m.GameSetting))],
            "default_configuration": {
                k: getattr(__import__("app.config", fromlist=["settings"]).settings, k)
                for k in (
                    "medical_fee_base",
                    "monster_reward",
                    "boss_reward",
                    "auction_duration_hours",
                    "min_auction_start_price",
                    "auction_proceeds_destination",
                )
            },
        }
    if module == "guilds":
        return [
            {
                "id": 1,
                "name": "Guilda do primeiro andar",
                "treasury": str(
                    __import__("app.finance", fromlist=["institution"]).institution(
                        db, "treasury"
                    )
                ),
                "pending_obligations": metrics(db)["pending_obligations"],
            }
        ]
    if module == "players":
        query = select(m.Character).where(m.Character.name.ilike("%" + q + "%"))
        return [
            {
                **data(c),
                "account": {
                    "id": c.account_id,
                    "username": db.get(m.Account, c.account_id).username,
                },
                "inventory": [
                    data(i)
                    for i in db.scalars(select(m.Item).where(m.Item.owner == c.id))
                ],
                "active_battle": data(
                    db.scalar(
                        select(m.Battle).where(
                            m.Battle.character_id == c.id, m.Battle.status == "active"
                        )
                    )
                ),
                "active_expedition": data(
                    db.scalar(
                        select(m.Expedition).where(
                            m.Expedition.character_id == c.id,
                            m.Expedition.status == "ACTIVE",
                        )
                    )
                ),
            }
            for c in db.scalars(
                query.order_by(m.Character.id).offset(offset).limit(100)
            )
        ]
    if module == "items":
        return {
            "definitions": [
                data(d)
                for d in db.scalars(
                    select(m.ItemDefinition).where(
                        m.ItemDefinition.name.ilike("%" + q + "%")
                    )
                )
            ],
            "instances": [
                data(i)
                for i in db.scalars(
                    select(m.Item).order_by(m.Item.id).offset(offset).limit(100)
                )
            ],
        }
    if module == "monsters":
        return {
            "definitions": [data(d) for d in db.scalars(select(m.MonsterDefinition))],
            "instances": [
                data(e)
                for e in db.scalars(
                    select(m.EnemyInstance)
                    .order_by(m.EnemyInstance.id.desc())
                    .offset(offset)
                    .limit(100)
                )
            ],
        }
    if module == "auctions":
        from .auctions import detail

        query = select(m.Auction)
        if q:
            query = query.where(m.Auction.status == q.upper())
        return [
            detail(db, a.id, administrative=True)
            for a in db.scalars(
                query.order_by(m.Auction.id.desc()).offset(offset).limit(100)
            )
        ]
    if module == "world":
        return {
            "rooms": [
                data(r)
                for r in db.scalars(
                    select(m.Room).where(m.Room.floor_id == 1, m.Room.owner_id == None)
                )
            ],
            "scheduled_events": [
                __import__("app.world_events", fromlist=["payload"]).payload(e)
                for e in db.scalars(
                    select(m.ScheduledWorldEvent)
                    .order_by(m.ScheduledWorldEvent.starts_at.desc())
                    .offset(offset)
                    .limit(100)
                )
            ],
            "events": [
                data(e)
                for e in db.scalars(
                    select(m.WorldEvent)
                    .order_by(m.WorldEvent.id.desc())
                    .offset(offset)
                    .limit(100)
                )
            ],
        }
    if module == "audit":
        return [
            data(o)
            for o in db.scalars(
                select(m.AdminOperation)
                .order_by(m.AdminOperation.created_at.desc())
                .offset(offset)
                .limit(100)
            )
        ]
    raise HTTPException(404, "Módulo inexistente")


@router.get("/lunar/audit")
def lunar_audit(actor=Depends(principal), db=Depends(get_db)):
    require(actor, "economy.read")
    from . import finance, lunar

    from .lunar_resources import metrics as resource_metrics

    return {
        **(finance.metrics(db) if finance.active(db) else lunar.audit(db)),
        **resource_metrics(db),
    }


@router.get("/lunar/legacy-preview")
def lunar_legacy_preview(actor=Depends(principal), db=Depends(get_db)):
    require(actor, "economy.read")
    from .lunar import legacy_preview

    return legacy_preview(db)


@router.get("/lunar/cutover/preview")
def cutover_preview(actor=Depends(principal), db=Depends(get_db)):
    require(actor, "economy.manage")
    from .cutover import preview

    return preview(db)


class CutoverConfirmation(BaseModel):
    model_config = {"extra": "forbid"}
    fingerprint: str = Field(min_length=64, max_length=64)
    request_id: UUID
    reason: str = Field(min_length=10, max_length=500)
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit(cls, value):
        if value is not True:
            raise ValueError("Confirmação explícita obrigatória")
        return value


@router.post("/lunar/cutover/confirm")
def cutover_confirm(
    body: CutoverConfirmation, actor=Depends(principal), db=Depends(get_db)
):
    require(actor, "economy.manage")
    from .cutover import confirm

    return confirm(
        db, body.fingerprint, str(body.request_id), f"admin:{actor.id}", body.reason
    )


@router.get("/lunar/resources")
def lunar_resources_view(offset: int = 0, actor=Depends(principal), db=Depends(get_db)):
    require(actor, "economy.read")
    from .lunar_resources import metrics, CONFIG
    from .config import runtime_setting

    return {
        "metrics": metrics(db),
        "configuration": {k: runtime_setting(db, k) for k in sorted(CONFIG)},
        "occurrences": [
            data(r)
            for r in db.scalars(
                select(m.LunarResourceOccurrence)
                .order_by(m.LunarResourceOccurrence.id.desc())
                .offset(max(0, offset))
                .limit(100)
            )
        ],
    }


@router.get("/lunar/lots")
def mineral_lots_list(
    owner: str = "",
    kind: str = "",
    state: str = "",
    origin: str = "",
    occurrence: int | None = None,
    expedition: int | None = None,
    min_g: int = 0,
    max_g: int = 1000000000,
    offset: int = 0,
    actor=Depends(principal),
    db=Depends(get_db),
):
    require(actor, "economy.read")
    from .mineral_lots import payload

    q = select(m.LunarMineralLot).join(
        m.LunarAccount, m.LunarAccount.id == m.LunarMineralLot.owner_account_id
    )
    if owner:
        q = q.where(m.LunarMineralLot.owner_account_id == owner)
    if kind:
        q = q.where(m.LunarAccount.kind == kind)
    if state:
        q = q.where(m.LunarMineralLot.state == state)
    if occurrence:
        q = q.where(m.LunarMineralLot.origin_occurrence_id == occurrence)
    if expedition:
        q = q.join(
            m.LunarResourceOccurrence,
            m.LunarResourceOccurrence.id == m.LunarMineralLot.origin_occurrence_id,
        ).where(m.LunarResourceOccurrence.expedition_id == expedition)
    if origin:
        q = q.join(
            m.LunarEntry, m.LunarEntry.id == m.LunarMineralLot.source_entry_id
        ).where(m.LunarEntry.kind == origin)
    q = q.where(
        m.LunarMineralLot.weight_mg >= min_g * 1000,
        m.LunarMineralLot.weight_mg <= max_g * 1000,
    )
    return {
        "lots": [
            payload(r)
            for r in db.scalars(
                q.order_by(m.LunarMineralLot.id).offset(max(0, offset)).limit(100)
            )
        ]
    }


@router.get("/lunar/lots/{lot_id}/lineage")
def mineral_lineage(lot_id: int, actor=Depends(principal), db=Depends(get_db)):
    require(actor, "economy.read")
    from .mineral_lots import lineage

    return lineage(db, lot_id)


@router.get("/royal/accounts/{account_id}/details")
def royal_account_details(
    account_id: str, actor=Depends(principal), db=Depends(get_db)
):
    require(actor, "economy.read")
    from . import mineral_lots as lots, finance

    row = db.get(m.LunarAccount, account_id)
    if not row:
        raise HTTPException(404, "Conta inexistente")
    return {
        "account": account_id,
        "coins": __import__("app.lunar", fromlist=["balances"]).balances(
            db, account_id
        ),
        "lots": [lots.payload(r) for r in lots.held(db, account_id)],
        "debt_mg": (
            str(finance.debt_mg(db, db.get(m.Character, row.character_id)))
            if row.character_id
            else "0"
        ),
        "inventory": (
            [
                data(i)
                for i in db.scalars(
                    select(m.Item).where(
                        m.Item.owner == row.character_id, m.Item.location == "inventory"
                    )
                )
            ]
            if row.character_id
            else []
        ),
    }


@router.get("/lunar/entries")
def royal_entries(
    owner: str = "", offset: int = 0, actor=Depends(principal), db=Depends(get_db)
):
    require(actor, "economy.read")
    from sqlalchemy import cast
    from sqlalchemy.dialects.postgresql import JSONB

    q = select(m.LunarEntry)
    if owner:
        q = q.where(cast(m.LunarEntry.postings, JSONB).contains([{"account": owner}]))
    return [
        data(e)
        for e in db.scalars(
            q.order_by(m.LunarEntry.id.desc()).offset(max(offset, 0)).limit(100)
        )
    ]


@router.get("/guild/commerce")
def guild_commerce_admin(offset: int = 0, actor=Depends(principal), db=Depends(get_db)):
    require(actor, "economy.read")
    from . import guild_commerce as commerce, guild_admin, finance
    from .mineral_lots import held, payload

    return {
        "cash": finance.cash(db, "guild"),
        "target": [70, 20, 10],
        "rebalance": (
            guild_admin.describe(db, "guild.rebalance", "guild", {"initial": True})
            if finance.active(db)
            else None
        ),
        "items": commerce.admin_catalog(db),
        "mineral": commerce.mineral_policy(db),
        "stock": [
            {
                "item_id": i.id,
                "definition": i.definition,
                "quantity": i.quantity,
                "name": db.get(m.ItemDefinition, i.definition).name,
            }
            for n, i in db.execute(
                select(m.NPCStock, m.Item)
                .join(m.Item, m.Item.id == m.NPCStock.item_id)
                .where(
                    m.NPCStock.account_id == "guild",
                    m.Item.location == "npc",
                    m.Item.owner == None,
                )
                .order_by(m.Item.id)
                .limit(100)
            )
        ],
        "lots": [payload(r) for r in held(db, "guild")],
        "history": [
            data(r)
            for r in db.scalars(
                select(m.GuildPriceHistory)
                .order_by(m.GuildPriceHistory.created_at.desc())
                .offset(max(0, offset))
                .limit(100)
            )
        ],
        "trades": [
            data(r)
            for r in db.scalars(
                select(m.GuildTradeReceipt)
                .order_by(m.GuildTradeReceipt.created_at.desc())
                .offset(max(0, offset))
                .limit(100)
            )
        ],
    }
