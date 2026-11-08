"""Cosmetic choices, independent of inventory/stats; paid edits use physical Lunar cash."""

import json
from pathlib import Path
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from . import models as m, lunar, finance
from .clock import utc_now
from .config import runtime_setting
from .game import fail

CATALOG = json.loads(Path(__file__).with_name("appearance_catalog.json").read_text())
OPTIONS = CATALOG["options"]
DEFAULT = {
    "sexo_visual": "masculino",
    "skin_tone": "skin_2",
    "hair_style_id": "short_spiky",
    "hair_color": "brown",
    "appearance_head": "none",
    "appearance_torso": "adventurer_tunic",
    "appearance_legs": "simple_trousers",
    "appearance_feet": "leather_boots",
}


class AppearanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sexo_visual: str = "masculino"
    skin_tone: str = "skin_2"
    hair_style_id: str = "short_spiky"
    hair_color: str = "brown"
    appearance_head: str = "none"
    appearance_torso: str = "adventurer_tunic"
    appearance_legs: str = "simple_trousers"
    appearance_feet: str = "leather_boots"

    @field_validator("*")
    @classmethod
    def allowed(cls, value, info):
        if value not in {row["id"] for row in OPTIONS[info.field_name]}:
            raise ValueError("Opção de aparência desconhecida")
        return value


class AppearancePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    appearance: AppearanceInput
    expected_revision: int = Field(ge=0, strict=True)


class AppearanceChange(AppearancePreview):
    request_id: UUID
    quote: str = Field(pattern=r"^[a-f0-9]{64}$")


def payload(db, character_id):
    row = db.get(m.CharacterAppearance, character_id)
    return {"revision": row.revision if row else 0, **(row.choices if row else DEFAULT)}


def payloads(db, ids):
    rows = {
        r.character_id: r
        for r in db.scalars(
            select(m.CharacterAppearance).where(
                m.CharacterAppearance.character_id.in_(ids)
            )
        )
    }
    return {
        cid: (
            {"revision": rows[cid].revision, **rows[cid].choices}
            if cid in rows
            else {"revision": 0, **DEFAULT}
        )
        for cid in ids
    }


def create(db, c, choices):
    db.add(
        m.CharacterAppearance(
            character_id=c.id, revision=1, choices=choices.model_dump()
        )
    )
    db.flush()


def require_barber(db, c):
    from .game import idle
    from .rooms import current
    from .deaths import latest
    from .expeditions import guard_departure
    from .world import distance

    idle(db, c)
    guard_departure(db, c)
    if c.hp <= 0 or latest(db, c):
        fail("Conclua o resgate antes de alterar a aparência")
    room = current(db, c)
    npc = next(
        (n for n in room.data.get("service_npcs", []) if n["id"] == "barber"), None
    )
    if (
        room.id != "barber_shop"
        or not npc
        or distance((c.x, c.y), (npc["x"], npc["y"])) > 1
    ):
        fail("Aproxime-se do Barbeiro em sua barbearia")
    if not finance.active(db):
        fail("O serviço do Barbeiro exige a economia Lunar ativada")


def catalog(db):
    fee = runtime_setting(db, "barber_fee_units")
    return {
        **CATALOG,
        "default": DEFAULT,
        "barber_fee_units": str(fee),
        "barber_fee_mg": str(fee * finance.UNIT),
    }


def preview(db, c, body):
    require_barber(db, c)
    before = payload(db, c.id)
    if before["revision"] != body.expected_revision:
        fail("APPEARANCE_CHANGED: atualize a aparência antes de confirmar")
    proposed = body.appearance.model_dump()
    if proposed == {k: before[k] for k in DEFAULT}:
        fail("Nenhuma mudança de aparência selecionada")
    fee = runtime_setting(db, "barber_fee_units")
    params = {
        "character_id": c.id,
        "revision": before["revision"],
        "appearance": proposed,
        "fee_units": fee,
        "catalog_version": CATALOG["version"],
    }
    payment = finance.payment_quote(db, f"player:{c.id}", fee)
    return {
        "quote": lunar.fingerprint(params),
        "before": before,
        "appearance": proposed,
        "fee_units": str(fee),
        "fee_mg": str(fee * finance.UNIT),
        "payment": payment,
        "destination": "npc:barber",
    }


def update(db, c, body):
    # Same lock order as all financial writers. Replay is bound to user + all inputs.
    lunar.mutex(db)
    key = f"barber:{c.id}:{body.request_id}"
    parameters = body.model_dump(mode="json", exclude={"request_id"})
    old = db.scalar(select(m.WorldEvent).where(m.WorldEvent.key == key))
    if old:
        if old.payload["parameters"] != parameters:
            fail("REQUEST_CONFLICT: referência já usada com outros dados")
        return {**old.payload["receipt"], "replay": True}
    offer = preview(db, c, body)
    if offer["quote"] != body.quote:
        fail("QUOTE_CHANGED: a taxa mudou; solicite nova prévia")
    if not offer["payment"]["payable"]:
        fail(offer["payment"]["error"])
    entry = finance.move(
        db,
        f"player:{c.id}",
        "npc:barber",
        int(offer["fee_units"]),
        key,
        amortize=False,
        actor=f"player:{c.id}",
        reason="Serviço do Barbeiro: alteração cosmética",
    )
    row = db.get(m.CharacterAppearance, c.id)
    if row is None:
        row = m.CharacterAppearance(character_id=c.id, revision=0, choices={})
        db.add(row)
    row.revision += 1
    row.choices = body.appearance.model_dump()
    row.updated_at = utc_now()
    db.flush()
    audit = lunar.audit(db)
    if int(audit["gap_mg"]) != 0:
        fail("AUDIT_GAP: alteração cancelada")
    receipt = {
        "message": "Aparência atualizada pelo Barbeiro.",
        "appearance": payload(db, c.id),
        "fee_units": offer["fee_units"],
        "ledger_entry_id": entry.id,
        "replay": False,
    }
    db.add(
        m.WorldEvent(
            key=key,
            kind="CHARACTER_APPEARANCE_CHANGED",
            processed=True,
            payload={
                "character": c.id,
                "parameters": parameters,
                "before": offer["before"],
                "receipt": receipt,
            },
        )
    )
    return receipt
