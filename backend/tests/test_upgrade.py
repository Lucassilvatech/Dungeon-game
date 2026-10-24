"""Exercise the real additive migration against a populated v1 database."""

import os, subprocess
from uuid import uuid4
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from app.database import engine


@pytest.mark.skipif(
    os.getenv("TOWER_TEST_DATABASE") != "1", reason="requires disposable test server"
)
def test_v1_upgrade_preserves_existing_data():
    name = "tower_upgrade_" + uuid4().hex[:10]
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {name}"))
    url = engine.url.set(database=name)
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    exe = str(Path(__import__("sys").executable).parent / "alembic")

    def migrate(rev):
        subprocess.run(
            [exe, "upgrade", rev], env=env, check=True, capture_output=True, text=True
        )

    dbengine = create_engine(url)
    try:
        migrate("234126160af2")
        with dbengine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO accounts (id,username,password) VALUES (91,'veteran','preserved-password-hash')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO characters (id,account_id,name,level,xp,hp,energy,strength,defense,x,y,floor,coins) VALUES (91,91,'Veterano',4,27,21,7,9,3,4,5,1,321)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO item_definitions(id,name,kind,power) VALUES ('old_sword','Relíquia','weapon',8)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO items(id,owner,definition,quantity,location,equipped) VALUES (91,91,'old_sword',1,'inventory',true)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO battles(id,character_id,monster,hp,turn,status,claimed) VALUES (91,91,'slime',6,2,'active',false)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO item_definitions(id,name,kind,power) VALUES ('old_material','Madeira','material',0)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO items(id,owner,definition,quantity,location,equipped) VALUES (92,91,'old_material',90,'inventory',false),(93,91,'old_material',20,'inventory',false)"
                )
            )
        migrate("head")
        with dbengine.connect() as db:
            c = db.execute(
                text("SELECT coins,xp,hp,x,y,room_id FROM characters WHERE id=91")
            ).one()
            assert tuple(c) == (321, 27, 21, 4, 5, "common_a")
            assert list(
                db.scalars(
                    text(
                        "SELECT quantity FROM items WHERE definition='old_material' ORDER BY id"
                    )
                )
            ) == [99, 11]
            assert db.scalar(text("SELECT equipped FROM items WHERE id=91"))
            assert tuple(
                db.execute(
                    text("SELECT hp,turn,room_id FROM battles WHERE id=91")
                ).one()
            ) == (6, 2, "common_a")
            assert (
                db.scalar(text("SELECT password FROM accounts WHERE id=91"))
                == "preserved-password-hash"
            )
    finally:
        dbengine.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()
