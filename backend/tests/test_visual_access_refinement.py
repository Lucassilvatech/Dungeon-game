"""Conservative city-only geometry repair and real populated migration preservation."""

import os
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as DBSession
from app.models import Account, Character
from app.database import engine
from app.visual_access import repair_city_access
from app.layouts import generate, reachable


def test_city_repair_removes_only_named_decorative_collisions():
    original = {
        "width": 20,
        "height": 20,
        "walls": [[0, 0], [7, 4], [10, 10], [12, 12], [15, 15]],
        "buildings": [{"x": 7, "y": 4, "width": 3, "height": 3}],
        "decorations": [
            {"kind": "barrel", "x": 10, "y": 10, "solid": True},
            {"kind": "tree", "x": 7, "y": 4, "solid": True},
            {"kind": "custom_structure", "x": 12, "y": 12, "solid": True},
        ],
        "npc": [4, 8],
        "frozen_stats": {"hp": 90},
        "resources": [[5, 9]],
    }
    fixed, removed = repair_city_access(original)
    assert removed == [[10, 10]]
    assert (
        [7, 4] in fixed["walls"]
        and [12, 12] in fixed["walls"]
        and [15, 15] in fixed["walls"]
        and [0, 0] in fixed["walls"]
    )
    assert original["decorations"][0]["solid"] is True
    assert fixed["decorations"][0]["solid"] is False
    assert (
        fixed["npc"] == original["npc"]
        and fixed["resources"] == original["resources"]
        and fixed["frozen_stats"] == original["frozen_stats"]
    )
    assert repair_city_access(fixed) == (fixed, [])


def test_incomplete_historical_room_is_not_reconstructed():
    original = {"seed": 77, "frozen_stats": True}
    assert repair_city_access(original) == (original, [])


def test_new_villages_have_no_scatter_collision_on_main_paths():
    for seed in range(50):
        data = generate("CITY", seed)
        assert data["visual_access_version"] == 1
        structures = {
            (x, y)
            for b in data["buildings"]
            for x in range(b["x"], b["x"] + b["width"])
            for y in range(b["y"], b["y"] + b["height"])
        }
        assert all(
            tuple(p) in structures
            or p[0] in (0, data["width"] - 1)
            or p[1] in (0, data["height"] - 1)
            for p in data["walls"]
        )
        assert (9, 7) in reachable(data) and (50, 18) in reachable(data)


def test_real_populated_visual_upgrade_changes_no_financial_or_actor_rows():
    assert os.getenv("TOWER_TEST_DATABASE") == "1"
    name = "art_upgrade_" + uuid4().hex[:12]
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text("CREATE DATABASE " + name))
    target = create_engine(engine.url.set(database=name))
    env = {
        **os.environ,
        "DATABASE_URL": target.url.render_as_string(hide_password=False),
    }
    root = Path(__file__).resolve().parents[1]

    def migrate(rev):
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", rev],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
        )

    migrate("7167b684d5f7")
    subprocess.run(
        [sys.executable, "-m", "app.seed"],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
    )
    with target.begin() as c:
        data = c.execute(
            text("SELECT data FROM rooms WHERE id='city1' FOR UPDATE")
        ).scalar()
        data.pop("visual_access_version", None)
        data["walls"].append([10, 18])
        data["decorations"].append({"kind": "crate", "x": 10, "y": 18, "solid": True})
        c.execute(
            text("UPDATE rooms SET data=CAST(:d AS json) WHERE id='city1'"),
            {"d": json.dumps(data)},
        )
    with DBSession(target) as session:
        session.add(
            Account(id=880, username="art-preserve", password="private-test-hash")
        )
        session.flush()
        session.add(
            Character(
                id=880,
                account_id=880,
                name="Preserved",
                coins=123,
                hp=27,
                xp=41,
                level=4,
                strength=8,
                defense=7,
                room_id="city1",
                x=2,
                y=2,
                floor=1,
            )
        )
        session.commit()

    # Hash every old table/column row except the one explicitly repaired room and migration metadata.
    def snapshot():
        with target.connect() as c:
            tables = list(
                c.scalars(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                    )
                )
            )
            return {
                t: sorted(
                    json.dumps(dict(r), sort_keys=True, default=str)
                    for r in c.execute(text('SELECT * FROM "' + t + '"')).mappings()
                )
                for t in tables
                if t not in ("alembic_version", "rooms", "world_events")
            }

    before = snapshot()
    with target.connect() as c:
        rooms = {r.id: r.data for r in c.execute(text("SELECT id,data FROM rooms"))}
        events = list(
            c.execute(
                text(
                    "SELECT id,key,kind,payload,processed FROM world_events ORDER BY id"
                )
            )
        )
    migrate("head")
    assert snapshot() == before
    with target.connect() as c:
        current = {r.id: r.data for r in c.execute(text("SELECT id,data FROM rooms"))}
        assert [10, 18] not in current["city1"]["walls"]
        assert current["city1"]["visual_access_version"] == 1
        for room in rooms:
            if room != "city1":
                assert rooms[room] == current[room]
        assert (
            list(
                c.execute(
                    text(
                        "SELECT id,key,kind,payload,processed FROM world_events WHERE kind!='VISUAL_ACCESS_REPAIRED' ORDER BY id"
                    )
                )
            )
            == events
        )
        assert (
            c.scalar(
                text(
                    "SELECT count(*) FROM world_events WHERE kind='VISUAL_ACCESS_REPAIRED'"
                )
            )
            == 1
        )
    migrate("head")
    assert snapshot() == before
    subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
    )
    target.dispose()
    admin.dispose()  # Keep this private database as preservation evidence.
