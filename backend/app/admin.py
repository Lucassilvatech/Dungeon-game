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
    if offset < 0:
        raise HTTPException(422, "Página inválida")
    permission = module + ".read"
    require(actor, permission)
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
                "treasury": str(db.get(m.Treasury, 1).balance),
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
