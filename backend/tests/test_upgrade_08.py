"""All old columns/rows must survive a populated 0.7 → 0.8 migration, not just balances."""

import os, subprocess, sys, json
from uuid import uuid4
from pathlib import Path
from datetime import timedelta
from sqlalchemy import create_engine, MetaData, select, text
from app.database import engine
from app import models as m
from app.clock import utc_now


def test_populated_07_upgrade_preserves_all_original_columns_and_rights():
    assert os.getenv("TOWER_TEST_DATABASE") == "1"
    name = "tower08_upgrade_" + uuid4().hex[:10]
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin.connect() as db:
        db.execute(text(f"CREATE DATABASE {name}"))
    url = engine.url.set(database=name)
    copy = create_engine(url)
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}
    exe = str(Path(sys.executable).parent / "alembic")
    cwd = Path(__file__).resolve().parents[1]

    def migrate(revision):
        subprocess.run(
            [exe, "upgrade", revision],
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
        )

    try:
        migrate("d0fc148417a5")
        metadata = MetaData()
        metadata.reflect(copy)
        with copy.begin() as db:

            def put(cls, **values):
                table = metadata.tables[cls.__tablename__]
                if all(col.name in values for col in table.primary_key):
                    if db.execute(
                        select(table).where(
                            *[col == values[col.name] for col in table.primary_key]
                        )
                    ).first():
                        return
                # Resolve existing Python defaults only for columns actually present in 0.7.
                for col in table.columns:
                    model = cls.__table__.c[col.name]
                    if col.name not in values and model.default is not None:
                        values[col.name] = (
                            model.default.arg(None)
                            if model.default.is_callable
                            else model.default.arg
                        )
                db.execute(
                    table.insert(), {k: v for k, v in values.items() if k in table.c}
                )

            now = utc_now()
            put(m.Floor, id=1, name="Primeiro andar")
            for room in ["city1", "migration-active", "migration-dead"]:
                put(
                    m.Room,
                    id=room,
                    floor_id=1,
                    name=room,
                    kind="PROCEDURAL" if room != "city1" else "CITY",
                    data={"seed": 77, "frozen_stats": True},
                )
            for id in (991, 992):
                put(
                    m.Account,
                    id=id,
                    username=f"preserve{id}",
                    password="preserved-test-hash",
                    discord_id=str(id),
                )
                put(
                    m.Character,
                    id=id,
                    account_id=id,
                    name=f"Veterano{id}",
                    level=5,
                    xp=77,
                    coins=-321 if id == 991 else 111,
                    strength=13,
                    defense=9,
                    room_id="migration-active" if id == 991 else "city1",
                    unspent_attribute_points=3,
                    attribute_point_debt=1,
                    debt_accrued=321,
                    debt_next_collection=999,
                )
            put(
                m.AuthSession,
                token="a" * 64,
                account_id=991,
                expires=now + timedelta(days=1),
            )
            put(m.AdminRole, account_id=991, role="observer")
            put(
                m.AdminSession,
                token="b" * 64,
                account_id=991,
                expires=now + timedelta(minutes=20),
            )
            put(
                m.ItemDefinition,
                id="sword",
                name="Espada de Aprendiz",
                kind="weapon",
                power=3,
                death_transferable=False,
            )
            put(
                m.ItemDefinition,
                id="migration_mat",
                name="Material legado",
                kind="material",
                power=0,
                stackable=True,
                max_stack_size=99,
                base_value=50,
            )
            put(
                m.Item, id=991, owner=991, definition="sword", quantity=1, equipped=True
            )
            put(
                m.Item,
                id=992,
                owner=None,
                definition="migration_mat",
                quantity=9,
                location="auction",
            )
            put(
                m.Item,
                id=993,
                owner=None,
                definition="migration_mat",
                quantity=4,
                location="recovery",
            )
            put(
                m.RoomState,
                character_id=991,
                room_id="migration-active",
                visits=3,
                generation=2,
                codex={"slime": {"seen": True}},
            )
            for id, room, status in [
                (991, "migration-active", "ACTIVE"),
                (992, "migration-dead", "FAILED"),
            ]:
                put(
                    m.Expedition,
                    id=id,
                    character_id=991,
                    room_id=room,
                    seed=id,
                    boss_chance=177,
                    status=status,
                )
                put(
                    m.EnemyInstance,
                    id=id,
                    character_id=991,
                    room_id=room,
                    generation=2,
                    spawn_key="slime",
                    species="slime",
                    hp=7 if id == 991 else 0,
                    max_hp=40,
                    attack=9,
                    defense=4,
                    level=5,
                    x=7,
                    y=7,
                    home_x=7,
                    home_y=7,
                    state="IN_COMBAT" if id == 991 else "DEAD",
                )
                put(
                    m.Battle,
                    id=id,
                    character_id=991,
                    enemy_id=id,
                    monster="slime",
                    room_id=room,
                    hp=7 if id == 991 else 0,
                    turn=4,
                    status="active" if id == 991 else "lost",
                    reward_amount=51,
                )
            put(
                m.DeathEvent,
                id=991,
                character_id=991,
                expedition_id=992,
                battle_id=992,
                receipt={"medical_fee": 100, "pending": True},
            )
            put(
                m.Auction,
                id=991,
                item_id=992,
                quantity=9,
                death_event_id=991,
                former_owner_id=991,
                opening_price=10,
                highest_bid=29,
                highest_bidder_id=992,
                ends_at=now + timedelta(days=1),
            )
            put(
                m.AuctionBid,
                id=991,
                auction_id=991,
                bidder_id=992,
                request_id=str(uuid4()),
                amount=29,
            )
            put(
                m.RecoveryItem,
                id=991,
                character_id=991,
                item_id=993,
                death_event_id=991,
                price=19,
            )
            put(
                m.AdminOperation,
                id=str(uuid4()),
                actor_id=991,
                action="migration.fixture",
                target="991",
                params={},
                reason="Histórico preservado na migração",
                before={"coins": -321},
                after={"coins": -321},
                confirmation_hash="c" * 64,
                status="APPLIED",
                expires=now,
                finished_at=now,
            )
            put(
                m.Ledger,
                id=991,
                reference="migration-reserve",
                source="character:992",
                destination="auction:991",
                amount=29,
            )
            put(
                m.WorldEvent,
                id=991,
                key="migration-audit",
                kind="PRESERVED",
                payload={"character": 991, "debt": 321},
            )

        def snapshot():
            with copy.connect() as db:
                return {
                    name: sorted(
                        [
                            json.dumps(dict(row), sort_keys=True, default=str)
                            for row in db.execute(select(table)).mappings()
                        ]
                    )
                    for name, table in metadata.tables.items()
                    if name != "alembic_version"
                }

        before = snapshot()
        migrate("head")
        after = snapshot()
        # The recovery relocation adds village presentation metadata; all existing
        # world keys and all financial/progression rows must remain unchanged.
        assert {k: v for k, v in after.items() if k != "rooms"} == {
            k: v for k, v in before.items() if k != "rooms"
        }
        old_rooms = {json.loads(row)["id"]: json.loads(row) for row in before["rooms"]}
        new_rooms = {json.loads(row)["id"]: json.loads(row) for row in after["rooms"]}
        assert old_rooms.keys() == new_rooms.keys()
        for room_id, old in old_rooms.items():
            updated = new_rooms[room_id]
            if room_id == "city1":
                assert updated["data"]["npc"] == [5, 30]
                assert updated["data"]["npc_role"] == "recovery"
                assert updated["data"]["recovery_site_version"] == 1
                decorations = updated["data"]["decorations"]
                assert [d for d in decorations if d["kind"] == "recovery_tent"] == [
                    {"kind": "recovery_tent", "x": 3, "y": 27, "width": 5, "height": 5}
                ]
                assert [d for d in decorations if d["kind"] != "recovery_tent"] == [
                    d
                    for d in old["data"].get("decorations", [])
                    if d["kind"] != "recovery_tent"
                ]
                relocated = {
                    "npc",
                    "npc_name",
                    "npc_role",
                    "recovery_site_version",
                    "decorations",
                }
                assert {
                    k: v for k, v in updated["data"].items() if k not in relocated
                } == {k: v for k, v in old["data"].items() if k not in relocated}
                assert {k: v for k, v in updated.items() if k != "data"} == {
                    k: v for k, v in old.items() if k != "data"
                }
            else:
                assert updated == old
        with copy.connect() as db:
            assert (
                db.scalar(text("SELECT created_at FROM characters WHERE id=991"))
                is None
            )
            assert (
                db.scalar(text("SELECT started_at FROM battles WHERE id=991")) is None
            )
            assert db.scalar(text("SELECT count(*) FROM guild_contracts")) == 0
            assert db.scalar(text("SELECT count(*) FROM combat_encounters")) == 0
            assert db.scalar(text("SELECT count(*) FROM resource_nodes")) == 0
            assert db.scalar(text("SELECT coins FROM characters WHERE id=991")) == -321
    finally:
        copy.dispose()
        # This is the newly created disposable fixture DB, never a game database/volume.
        with admin.connect() as db:
            db.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()
