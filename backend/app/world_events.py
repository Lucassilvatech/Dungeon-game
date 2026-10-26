"""Scheduled, audited first-floor effects; overlapping rare events use highest multiplier."""

from datetime import datetime, timezone
from sqlalchemy import select
from .models import ScheduledWorldEvent, Room
from .clock import utc_now


def validate(db, p):
    from .game import fail

    try:
        start = datetime.fromisoformat(p["starts_at"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            raise ValueError("Timezone required")
        start = start.astimezone(timezone.utc).replace(tzinfo=None)
        duration = p["duration_minutes"]
        intensity = p["intensity"]
        if (
            type(duration) is not int
            or not 1 <= duration <= 10080
            or type(intensity) is not int
            or not 0 <= intensity <= 400
        ):
            raise ValueError("Limits")
        if (
            p["effect"] != "rare_spawn"
            or p["floor_id"] != 1
            or p.get("conditions", "new_adventures") != "new_adventures"
        ):
            raise ValueError("Unsupported effect")
        region = p["region"]
        room = db.get(Room, region) if region != "all" else None
        if region not in ("all", "procedural") and (
            not room or room.floor_id != 1 or room.owner_id is not None
        ):
            raise ValueError("Region")
        if not 1 <= len(p["name"]) <= 100 or not 1 <= len(p["description"]) <= 500:
            raise ValueError("Text")
    except (ValueError, KeyError, TypeError, AttributeError):
        fail(
            "Revise nome, descrição, região, intensidade, data com fuso e duração do evento",
            422,
        )
    from datetime import timedelta

    return {
        "name": p["name"],
        "description": p["description"],
        "region": region,
        "floor_id": 1,
        "effect": "rare_spawn",
        "intensity": intensity,
        "conditions": "new_adventures",
        "starts_at": start,
        "ends_at": start + timedelta(minutes=duration),
    }


def payload(e):
    now = utc_now()
    state = (
        "CANCELLED"
        if e.cancelled_at
        else (
            "SCHEDULED"
            if now < e.starts_at
            else "ENDED" if now >= e.ends_at else "ACTIVE"
        )
    )
    return {
        "id": e.id,
        "name": e.name,
        "description": e.description,
        "region": e.region,
        "floor_id": e.floor_id,
        "effect": "Aumentar monstros raros",
        "intensity": e.intensity,
        "conditions": "Somente novas aventuras; não altera encontros ativos",
        "starts_at": e.starts_at.isoformat() + "Z",
        "ends_at": e.ends_at.isoformat() + "Z",
        "duration_minutes": int((e.ends_at - e.starts_at).total_seconds() / 60),
        "state": state,
        "impact": f"Chance base de raros multiplicada por {1+e.intensity/100:g}, limitada a 25%. Sem alteração de boss ou miniboss.",
    }


def rare_multiplier(db, room):
    now = utc_now()
    events = db.scalars(
        select(ScheduledWorldEvent).where(
            ScheduledWorldEvent.floor_id == room.floor_id,
            ScheduledWorldEvent.cancelled_at == None,
            ScheduledWorldEvent.starts_at <= now,
            ScheduledWorldEvent.ends_at > now,
        )
    )
    return max(
        [1.0]
        + [
            1 + e.intensity / 100
            for e in events
            if e.region in ("all", "procedural", room.id)
        ]
    )
