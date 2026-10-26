"""Daily aggregates under the character lock; no permanent individual turn log."""

from datetime import timedelta
from sqlalchemy import text
from .models import GameplayDay
from .clock import utc_now


def add(db, c, **values):
    key = (c.id, utc_now().date())
    cache = db.info.setdefault("gameplay_metric_cache", {})
    row = cache.get(key)
    if row is None:
        row = db.get(GameplayDay, key)
        if row is None:
            row = GameplayDay(character_id=c.id, day=key[1], counters={})
            db.add(row)
        cache[key] = row
    row.counters = {
        **row.counters,
        **{k: row.counters.get(k, 0) + int(v) for k, v in values.items()},
    }


def finish_single(db, c, b):
    if b.encounter_id or b.metrics_recorded or b.status == "active":
        return
    b.metrics_recorded = True
    if b.monster == "dummy":
        add(db, c, training_finished=1, training_turns=b.turn)
        return
    elapsed = (
        max(0, int((utc_now() - b.started_at).total_seconds() * 1000))
        if b.started_at
        else 0
    )
    add(
        db,
        c,
        combats_finished=1,
        combat_turns=b.turn,
        combat_duration_ms=elapsed,
        combat_duration_known=int(b.started_at is not None),
        damage_dealt=b.damage_dealt,
        damage_received=b.damage_received,
        **{"combats_" + b.status: 1}
    )


def finish_group(db, c, g):
    if g.metrics_recorded:
        return
    g.metrics_recorded = True
    elapsed = max(0, int((g.finished_at - g.started_at).total_seconds() * 1000))
    add(
        db,
        c,
        combats_finished=1,
        groups_finished=1,
        combat_turns=g.turn,
        combat_duration_ms=elapsed,
        combat_duration_known=1,
        damage_dealt=g.damage_dealt,
        damage_received=g.damage_received,
        **{"combats_" + g.status.lower(): 1}
    )


def summary(db, character_id=None, days=30):
    since = utc_now().date() - timedelta(days=days - 1)
    where = " AND d.character_id=:character_id" if character_id is not None else ""
    rows = db.execute(
        text(
            "SELECT e.key,sum(e.value::numeric) FROM gameplay_days d CROSS JOIN LATERAL jsonb_each_text(d.counters::jsonb) e WHERE d.day>=:since"
            + where
            + " GROUP BY e.key"
        ),
        {"since": since, "character_id": character_id},
    ).all()
    totals = {key: int(value) for key, value in rows}
    n = totals.get("combats_finished", 0)
    known = totals.get("combat_duration_known", 0)
    resolved = totals.get("combats_won", 0) + totals.get("combats_lost", 0)
    return {
        "days": days,
        "timezone": "UTC",
        "totals": totals,
        "sample_size": n,
        "average_turns": round(totals.get("combat_turns", 0) / n, 2) if n else None,
        "average_combat_seconds": (
            round(totals.get("combat_duration_ms", 0) / known / 1000, 2)
            if known
            else None
        ),
        "win_rate": (
            round(totals.get("combats_won", 0) / resolved, 4) if resolved else None
        ),
        "defeat_rate": (
            round(totals.get("combats_lost", 0) / resolved, 4) if resolved else None
        ),
        "flee_rate": round(totals.get("combats_fled", 0) / n, 4) if n else None,
        "expedition_completion_rate": (
            round(
                totals.get("expeditions_completed", 0) / totals["expeditions_started"],
                4,
            )
            if totals.get("expeditions_started")
            else None
        ),
        "average_level_interval_seconds": (
            round(
                totals.get("level_interval_ms", 0)
                / totals["level_interval_samples"]
                / 1000,
                2,
            )
            if totals.get("level_interval_samples")
            else None
        ),
        "enemy_level_distribution": {
            k.removeprefix("spawn_level_"): v
            for k, v in totals.items()
            if k.startswith("spawn_level_")
        },
        "limitations": [
            "Only operations observed after instrumentation; no historical durations invented.",
            "Combat duration is wall time, including thinking and reconnects.",
            "Training excluded from real combat rates.",
            "These are observations, not controlled player experiments.",
        ],
    }
