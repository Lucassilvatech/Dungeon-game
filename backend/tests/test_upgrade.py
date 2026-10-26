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
            [exe, "upgrade", rev],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
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


@pytest.mark.skipif(
    os.getenv("TOWER_TEST_DATABASE") != "1", reason="requires disposable test server"
)
def test_existing_procedural_rooms_are_migrated_without_penalties():
    import sqlalchemy as sa
    from app.layouts import generate

    name = "tower_upgrade_" + uuid4().hex[:10]
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {name}"))
    url = engine.url.set(database=name)
    dbengine = create_engine(url)
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    exe = str(Path(__import__("sys").executable).parent / "alembic")

    def migrate(rev):
        subprocess.run(
            [exe, "upgrade", rev],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    try:
        migrate("11ac6a18a976")
        with dbengine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO accounts(id,username,password) VALUES(91,'explorer','unchanged')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO characters(id,account_id,name,level,xp,hp,energy,strength,defense,x,y,floor,coins,room_id) VALUES(91,91,'Explorer',4,27,21,7,9,3,4,5,1,321,'city1')"
                )
            )
            rooms = sa.table(
                "rooms",
                sa.column("id", sa.String),
                sa.column("floor_id", sa.Integer),
                sa.column("name", sa.String),
                sa.column("kind", sa.String),
                sa.column("owner_id", sa.Integer),
                sa.column("seed", sa.Integer),
                sa.column("data", sa.JSON),
            )
            for room in ("current-expedition", "past-expedition"):
                db.execute(
                    rooms.insert().values(
                        id=room,
                        floor_id=1,
                        name=room,
                        kind="PROCEDURAL",
                        owner_id=91,
                        seed=42,
                        data=generate("PROCEDURAL", 42),
                    )
                )
            db.execute(
                text("UPDATE characters SET room_id='current-expedition' WHERE id=91")
            )
            db.execute(
                text(
                    "INSERT INTO enemy_instances(id,character_id,room_id,generation,spawn_key,species,state,hp,max_hp,level,attack,defense,x,y,home_x,home_y,ai_state,moved_at,death_at) VALUES (91,91,'current-expedition',0,'slime','slime','DEAD',0,24,1,6,2,5,6,5,6,'DEAD',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO battles(id,character_id,monster,hp,turn,status,claimed,room_id,reward_amount,enemy_id) VALUES(91,91,'slime',0,4,'won',false,'current-expedition',101,91)"
                )
            )
        migrate("head")
        with dbengine.connect() as db:
            assert tuple(
                db.execute(
                    text(
                        "SELECT coins,xp,level,x,y,room_id FROM characters WHERE id=91"
                    )
                ).one()
            ) == (321, 27, 4, 4, 5, "current-expedition")
            assert (
                db.scalar(
                    text(
                        "SELECT status FROM expeditions WHERE room_id='current-expedition'"
                    )
                )
                == "ACTIVE"
            )
            assert (
                db.scalar(
                    text(
                        "SELECT status FROM expeditions WHERE room_id='past-expedition'"
                    )
                )
                == "FAILED"
            )
            assert (
                db.scalar(text("SELECT reward_amount FROM battles WHERE id=91")) == 101
            )
            assert (
                db.scalar(text("SELECT state FROM enemy_instances WHERE id=91"))
                == "DEAD"
            )
            assert (
                db.scalar(
                    text(
                        "SELECT seed FROM expeditions WHERE room_id='current-expedition'"
                    )
                )
                == 42
            )
    finally:
        dbengine.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()


def test_v04_upgrade_preserves_stats_inventory_balances_and_has_no_retroactive_points():
    name = "tower_upgrade_" + uuid4().hex[:10]
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {name}"))
    url = engine.url.set(database=name)
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    exe = str(Path(__import__("sys").executable).parent / "alembic")
    dbengine = create_engine(url)
    try:
        subprocess.run(
            [exe, "upgrade", "904ca715f282"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        with dbengine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO accounts(id,username,password) VALUES(91,'veteran','unchanged-hash')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO characters(id,account_id,name,level,xp,hp,energy,strength,defense,x,y,floor,coins,room_id) VALUES(91,91,'Veterano',37,150,21,7,41,5,4,5,1,12345,'city1')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO item_definitions(id,name,kind,power,stackable,max_stack_size,description) VALUES('sword','Espada','weapon',3,false,1,'preservada'),('unknown','Material','material',0,true,99,'legado')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO items(id,owner,definition,quantity,location,equipped) VALUES(91,91,'sword',1,'inventory',true),(92,91,'unknown',25,'inventory',false)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO battles(id,character_id,monster,hp,turn,status,claimed,room_id,reward_amount) VALUES(91,91,'slime',0,4,'won',false,'common_a',850)"
                )
            )
        subprocess.run(
            [exe, "upgrade", "head"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [exe, "check"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        with dbengine.connect() as db:
            assert tuple(
                db.execute(
                    text(
                        "SELECT level,xp,hp,strength,defense,coins,unspent_attribute_points,attribute_point_debt FROM characters WHERE id=91"
                    )
                ).one()
            ) == (37, 150, 21, 41, 5, 12345, 0, 0)
            assert list(
                db.execute(
                    text("SELECT id,quantity,equipped,location FROM items ORDER BY id")
                )
            ) == [(91, 1, True, "inventory"), (92, 25, False, "inventory")]
            assert (
                db.scalar(text("SELECT reward_amount FROM battles WHERE id=91")) == 850
            )
            assert db.scalar(text("SELECT COUNT(*) FROM death_events")) == 0
            assert db.scalar(text("SELECT COUNT(*) FROM auctions")) == 0
            assert (
                db.scalar(
                    text("SELECT base_value FROM item_definitions WHERE id='sword'")
                )
                == 100
            )
            assert (
                db.scalar(
                    text("SELECT base_value FROM item_definitions WHERE id='unknown'")
                )
                is None
            )
            assert db.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname='uq_auction_custody')"
                )
            )
        with dbengine.begin() as db:
            db.execute(text("UPDATE characters SET coins=-10000 WHERE id=91"))
        with pytest.raises(Exception):
            with dbengine.begin() as db:
                db.execute(text("UPDATE characters SET coins=-10001 WHERE id=91"))
    finally:
        dbengine.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()


def test_v05_starter_custody_bids_and_money_are_preserved_for_individual_recovery():
    name = "tower_upgrade_" + uuid4().hex[:10]
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {name}"))
    url = engine.url.set(database=name)
    dbengine = create_engine(url)
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    exe = str(Path(__import__("sys").executable).parent / "alembic")

    def migrate(rev):
        subprocess.run(
            [exe, "upgrade", rev],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    try:
        migrate("039105b3ae1a")
        with dbengine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO accounts(id,username,password) VALUES(91,'legacy_owner','unchanged'),(92,'legacy_bidder','unchanged')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO characters(id,account_id,name,level,xp,hp,energy,strength,defense,x,y,floor,coins,room_id) VALUES(91,91,'Owner',9,150,30,10,13,2,2,2,1,-85,'city1'),(92,92,'Buyer',2,5,35,10,6,2,2,2,1,950,'city1')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO item_definitions(id,name,kind,power,stackable,max_stack_size,description,death_transferable,base_value) VALUES('sword','Espada de Aprendiz','weapon',3,false,1,'Original',true,100),('other_sword','Espada comum','weapon',4,false,1,'Transferível',true,200)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO items(id,owner,definition,quantity,location,equipped) VALUES(91,NULL,'sword',1,'auction',false)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO rooms(id,floor_id,name,kind,seed,owner_id,data) VALUES('oldproc',1,'Histórico','PROCEDURAL',42,91,'{}')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO expeditions(id,character_id,room_id,seed,status,started_at,finished_at,result) VALUES(91,91,'oldproc',42,'FAILED',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,json_build_object('legacy',true))"
                )
            )
            db.execute(
                text(
                    "INSERT INTO battles(id,character_id,monster,hp,turn,status,claimed,room_id,reward_amount) VALUES(91,91,'slime',20,5,'lost',false,'oldproc',0)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO death_events(id,character_id,expedition_id,battle_id,created_at,receipt,acknowledged) VALUES(91,91,91,91,CURRENT_TIMESTAMP,json_build_object('legacy',true),true)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO auctions(id,item_id,quantity,death_event_id,former_owner_id,opening_price,highest_bid,highest_bidder_id,started_at,ends_at,status,proceeds_destination) VALUES(91,91,1,91,91,20,50,92,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+interval '1 day','OPEN','treasury')"
                )
            )
            db.execute(
                text(
                    "INSERT INTO auction_bids(id,auction_id,bidder_id,request_id,amount,created_at) VALUES(91,91,92,'legacy-bid-unchanged',50,CURRENT_TIMESTAMP)"
                )
            )
            db.execute(
                text(
                    "INSERT INTO ledger(id,reference,source,destination,amount,created) VALUES(91,'legacy-escrow','character:92','auction:91',50,CURRENT_TIMESTAMP)"
                )
            )
        migrate("head")
        subprocess.run(
            [exe, "check"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        with dbengine.connect() as db:
            assert tuple(
                db.execute(
                    text(
                        "SELECT owner,location,quantity,equipped FROM items WHERE id=91"
                    )
                ).one()
            ) == (None, "auction", 1, False)
            assert tuple(
                db.execute(
                    text(
                        "SELECT status,highest_bid,highest_bidder_id FROM auctions WHERE id=91"
                    )
                ).one()
            ) == ("OPEN", 50, 92)
            assert list(
                db.execute(text("SELECT id,coins,level,xp FROM characters ORDER BY id"))
            ) == [(91, -85, 9, 150), (92, 950, 2, 5)]
            assert (
                db.scalar(
                    text(
                        "SELECT death_transferable FROM item_definitions WHERE id='sword'"
                    )
                )
                is False
            )
            assert (
                db.scalar(
                    text(
                        "SELECT death_transferable FROM item_definitions WHERE id='other_sword'"
                    )
                )
                is True
            )
            assert db.scalar(text("SELECT COUNT(*) FROM ledger")) == 1
            assert db.scalar(text("SELECT balance FROM central_bank WHERE id=1")) == 0
        with pytest.raises(Exception):
            with dbengine.begin() as db:
                db.execute(
                    text(
                        "UPDATE item_definitions SET death_transferable=true WHERE id='sword'"
                    )
                )
    finally:
        dbengine.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()
