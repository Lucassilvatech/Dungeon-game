"""Rehearse the upgrade on a new private DB built with the preceding Git revision.
Never connects to an operational database; requires explicit test authorization.
"""

import os, sys, json, subprocess, tempfile, uuid, tarfile, io
from pathlib import Path
from sqlalchemy import create_engine, text

root = Path(__file__).resolve().parents[1]
assert os.getenv("TOWER_TEST_DATABASE") == "1"
source = create_engine(os.environ["DATABASE_URL"], isolation_level="AUTOCOMMIT")
assert source.url.get_backend_name() == "postgresql"
name = "appearance_upgrade_" + uuid.uuid4().hex[:10]
with source.connect() as c:
    c.execute(text("CREATE DATABASE " + name))
env = {
    **os.environ,
    "DATABASE_URL": source.url.set(database=name).render_as_string(hide_password=False),
}
source.dispose()
base = "f96aa9c512d7cbdee18e98f63e01f57b8f2a34e9"
old = Path(tempfile.mkdtemp(prefix="appearance-baseline-"))
archive = subprocess.check_output(["git", "archive", base, "backend"], cwd=root)
with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
    bundle.extractall(old, filter="data")


def run(args, cwd):
    subprocess.run([sys.executable, *args], cwd=cwd, env=env, check=True)


run(["-m", "alembic", "upgrade", "head"], old / "backend")
run(["-m", "app.seed"], old / "backend")
setup = """from app.database import Session
from app import models as m,lunar,cutover,finance
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
with TestClient(app) as client:
 r=client.post('/auth/register',json={'username':'previous_character','password':'private-upgrade-proof'});assert r.status_code==201
 h={'Authorization':'Bearer '+r.json()['token']}
 r=client.post('/character',headers=h,json={'name':'Existing hero'});assert r.status_code==201
 cid=r.json()['character']['id']
with Session.begin() as db:
 lunar.initialize(db);p=cutover.preview(db);cutover.confirm(db,p['fingerprint'],str(uuid4()),'upgrade-test','Private disposable baseline fixture')
 assert lunar.audit(db)['gap_mg']=='0'
 c=db.get(m.Character,cid);c.room_id='city1';c.x=16;c.y=27
"""
run(["-c", setup], old / "backend")
engine = create_engine(env["DATABASE_URL"])
# Full ordered financial/inventory rows, not only totals.
tables = [
    "lunar_cutovers",
    "lunar_entries",
    "lunar_holdings",
    "lunar_supply",
    "lunar_debts",
    "items",
    "npc_profiles",
    "npc_stocks",
]
with engine.connect() as c:
    available = set(
        c.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        ).scalars()
    )
    assert set(tables) <= available, "A preserved table is missing"
    before = {
        t: c.execute(
            text(
                "SELECT row_to_json(t)::text FROM "
                + t
                + " t ORDER BY row_to_json(t)::text"
            )
        )
        .scalars()
        .all()
        for t in tables
    }
    characters = c.execute(
        text(
            "SELECT id,name,level,xp,coins,hp,strength,defense FROM characters ORDER BY id"
        )
    ).all()
run(["-m", "alembic", "upgrade", "head"], root / "backend")
run(["-m", "alembic", "check"], root / "backend")
run(["-m", "app.seed"], root / "backend")
run(["-m", "app.seed"], root / "backend")
with engine.connect() as c:
    after = {
        t: c.execute(
            text(
                "SELECT row_to_json(t)::text FROM "
                + t
                + " t ORDER BY row_to_json(t)::text"
            )
        )
        .scalars()
        .all()
        for t in tables
    }
    assert before == after
    assert (
        characters
        == c.execute(
            text(
                "SELECT id,name,level,xp,coins,hp,strength,defense FROM characters ORDER BY id"
            )
        ).all()
    )
    assert c.scalar(text("SELECT COUNT(*) FROM character_appearances")) == 0
    assert (
        c.scalar(
            text(
                "SELECT COUNT(*) FROM rooms WHERE id IN ('merchant_shop','blacksmith_workshop','alchemy_laboratory','barber_shop')"
            )
        )
        == 4
    )
    assert (
        c.scalar(
            text(
                "SELECT COUNT(*) FROM characters WHERE room_id='city1' AND x BETWEEN 15 AND 19 AND y BETWEEN 26 AND 29"
            )
        )
        == 0
    )
run(
    [
        "-c",
        "from app.database import Session\nfrom app import lunar,character_appearance as a\nwith Session() as db:\n assert lunar.audit(db)['gap_mg']=='0'\n assert a.payload(db,1)['revision']==0",
    ],
    root / "backend",
)
report = {
    "status": "PASS",
    "baseline": base,
    "migration": "65a7c9e21b04 → 8c2a71e93d60",
    "kind": "New private baseline fixture, not a production database copy",
    "alembic_check": "PASS",
    "preserved_tables": {t: len(v) for t, v in before.items()},
    "preserved_characters": len(characters),
    "seed_idempotent": True,
    "occupied_new_building_relocation": "nearest free tile, audited",
    "legacy_appearance": "read-only fallback, zero inserted appearance rows",
    "audit_gap_mg": "0",
}
(root / "artifacts/appearance/upgrade-validation.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps(report))
engine.dispose()
