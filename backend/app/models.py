from .clock import utc_now
from datetime import datetime, date
from sqlalchemy import (
    UniqueConstraint,
    Index,
    text,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Date,
    Boolean,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from .money import Gold


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password: Mapped[str] = mapped_column(String(256))
    discord_id: Mapped[str | None] = mapped_column(String(30), unique=True)


class AuthSession(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    expires: Mapped[datetime] = mapped_column(DateTime)


class LinkCode(Base):
    __tablename__ = "link_codes"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    expires: Mapped[datetime] = mapped_column(DateTime)


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (
        CheckConstraint(
            "coins >= -10000 AND hp >= 0 AND energy >= 0",
            name="character_health_balance",
        ),
        CheckConstraint(
            "level >= 1 AND unspent_attribute_points >= 0 AND attribute_point_debt >= 0",
            name="character_progression",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    level: Mapped[int] = mapped_column(default=1)
    xp: Mapped[int] = mapped_column(default=0)
    hp: Mapped[int] = mapped_column(default=30)
    energy: Mapped[int] = mapped_column(default=10)
    strength: Mapped[int] = mapped_column(default=5)
    defense: Mapped[int] = mapped_column(default=2)
    x: Mapped[int] = mapped_column(default=2)
    y: Mapped[int] = mapped_column(default=2)
    floor: Mapped[int] = mapped_column(default=1)
    coins: Mapped[int] = mapped_column(Gold(), default=0)
    unspent_attribute_points: Mapped[int] = mapped_column(default=0, server_default="0")
    attribute_point_debt: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utc_now)
    last_level_at: Mapped[datetime | None] = mapped_column(DateTime)
    adventure_streak: Mapped[int] = mapped_column(default=0, server_default="0")
    debt_accrued: Mapped[int] = mapped_column(Gold(), default=0, server_default="0")
    debt_next_collection: Mapped[int] = mapped_column(
        Gold(), default=0, server_default="0"
    )
    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms.id"), default="city1", server_default="city1"
    )


class ItemDefinition(Base):
    __tablename__ = "item_definitions"
    __table_args__ = (
        CheckConstraint("max_stack_size > 0"),
        CheckConstraint(
            "id != 'sword' OR NOT death_transferable", name="starter_sword_protected"
        ),
    )
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(20))
    power: Mapped[int] = mapped_column(default=0)
    base_value: Mapped[int | None] = mapped_column(Gold())
    death_transferable: Mapped[bool] = mapped_column(
        default=True, server_default="true"
    )
    rarity: Mapped[str] = mapped_column(
        String(20), default="common", server_default="common"
    )
    unique_item: Mapped[bool] = mapped_column(default=False, server_default="false")
    stackable: Mapped[bool] = mapped_column(default=False, server_default="false")
    max_stack_size: Mapped[int] = mapped_column(default=1, server_default="1")
    description: Mapped[str] = mapped_column(String(200), default="", server_default="")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint(
            "(location NOT IN ('auction','recovery','destroyed') OR (owner IS NULL AND NOT equipped)) AND (owner IS NOT NULL OR location IN ('auction','recovery','destroyed'))",
            name="item_custody",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[int | None] = mapped_column(ForeignKey("characters.id"))
    definition: Mapped[str] = mapped_column(ForeignKey("item_definitions.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    location: Mapped[str] = mapped_column(String(20), default="inventory")
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)


class Battle(Base):
    __tablename__ = "battles"
    __table_args__ = (
        Index(
            "uq_enemy_victory",
            "enemy_id",
            unique=True,
            postgresql_where=text("status = 'won' AND enemy_id IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    enemy_id: Mapped[int | None] = mapped_column(ForeignKey("enemy_instances.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=utc_now)
    damage_dealt: Mapped[int] = mapped_column(default=0, server_default="0")
    damage_received: Mapped[int] = mapped_column(default=0, server_default="0")
    metrics_recorded: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey("combat_encounters.id"), index=True
    )
    monster: Mapped[str] = mapped_column(String(20))
    hp: Mapped[int] = mapped_column()
    turn: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"))
    reward_amount: Mapped[int | None] = mapped_column(Gold())
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)


class Treasury(Base):
    __tablename__ = "treasury"
    __table_args__ = (CheckConstraint("balance >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column(Gold())


class Ledger(Base):
    __tablename__ = "ledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True)
    source: Mapped[str] = mapped_column(String(50))
    destination: Mapped[str] = mapped_column(String(50))
    amount: Mapped[int] = mapped_column(Gold())
    created: Mapped[datetime] = mapped_column(default=utc_now)


class WorldEvent(Base):
    __tablename__ = "world_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)


class Floor(Base):
    __tablename__ = "floors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))


class Room(Base):
    __tablename__ = "rooms"
    danger_tier: Mapped[int] = mapped_column(default=0, server_default="0")
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"))
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(30))
    seed: Mapped[int] = mapped_column(default=0)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id", use_alter=True, name="fk_room_owner")
    )
    data: Mapped[dict] = mapped_column(JSON)


class RoomConnection(Base):
    __tablename__ = "room_connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(ForeignKey("rooms.id"))
    target: Mapped[str] = mapped_column(ForeignKey("rooms.id"))
    x: Mapped[int] = mapped_column()
    y: Mapped[int] = mapped_column()
    __table_args__ = (UniqueConstraint("source", "target"),)


class RoomState(Base):
    __tablename__ = "room_states"
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"), primary_key=True
    )
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), primary_key=True)
    completed: Mapped[bool] = mapped_column(default=False)
    visits: Mapped[int] = mapped_column(default=0)
    generation: Mapped[int] = mapped_column(default=0, server_default="0")
    codex: Mapped[dict] = mapped_column(JSON, default=dict)


class Raid(Base):
    __tablename__ = "raids"
    id: Mapped[int] = mapped_column(primary_key=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    invite: Mapped[str] = mapped_column(String(32), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="forming")


class RaidMember(Base):
    __tablename__ = "raid_members"
    raid_id: Mapped[int] = mapped_column(ForeignKey("raids.id"), primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"), primary_key=True
    )


class EnemyInstance(Base):
    __tablename__ = "enemy_instances"
    __table_args__ = (
        UniqueConstraint("character_id", "room_id", "generation", "spawn_key"),
        CheckConstraint("hp >= 0 AND max_hp > 0"),
        CheckConstraint("state IN ('ALIVE','IN_COMBAT','DYING','DEAD')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"))
    generation: Mapped[int] = mapped_column(default=0)
    spawn_key: Mapped[str] = mapped_column(String(40))
    species: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(
        String(20), default="common", server_default="common"
    )
    state: Mapped[str] = mapped_column(String(20), default="ALIVE")
    hp: Mapped[int] = mapped_column()
    max_hp: Mapped[int] = mapped_column()
    xp_reward: Mapped[int] = mapped_column(default=0, server_default="0")
    level: Mapped[int] = mapped_column(default=1)
    attack: Mapped[int] = mapped_column(default=6)
    defense: Mapped[int] = mapped_column(default=2)
    x: Mapped[int] = mapped_column()
    y: Mapped[int] = mapped_column()
    home_x: Mapped[int] = mapped_column()
    home_y: Mapped[int] = mapped_column()
    ai_state: Mapped[str] = mapped_column(String(20), default="IDLE")
    moved_at: Mapped[datetime] = mapped_column(default=utc_now)
    death_at: Mapped[datetime | None] = mapped_column(DateTime)


class Expedition(Base):
    __tablename__ = "expeditions"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','COMPLETED','FLED','FAILED')"),
        Index(
            "uq_active_expedition",
            "character_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), unique=True)
    seed: Mapped[int] = mapped_column()
    boss_chance: Mapped[int] = mapped_column(default=100, server_default="100")
    boss_rolled: Mapped[bool] = mapped_column(default=False, server_default="false")
    special_boss: Mapped[bool] = mapped_column(default=False, server_default="false")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    result: Mapped[dict | None] = mapped_column(JSON)


class DeathEvent(Base):
    __tablename__ = "death_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    expedition_id: Mapped[int] = mapped_column(
        ForeignKey("expeditions.id"), unique=True
    )
    battle_id: Mapped[int] = mapped_column(ForeignKey("battles.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    receipt: Mapped[dict] = mapped_column(JSON)
    acknowledged: Mapped[bool] = mapped_column(default=False, server_default="false")


class Auction(Base):
    __tablename__ = "auctions"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','CLOSED','CANCELLED','SETTLED','UNSOLD')"),
        CheckConstraint("opening_price > 0 AND highest_bid >= 0"),
        UniqueConstraint("death_event_id", "item_id"),
        Index(
            "uq_auction_custody",
            "item_id",
            unique=True,
            postgresql_where=text("status IN ('OPEN','CLOSED','UNSOLD')"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    quantity: Mapped[int] = mapped_column()
    death_event_id: Mapped[int | None] = mapped_column(ForeignKey("death_events.id"))
    hidden: Mapped[bool] = mapped_column(default=False, server_default="false")
    archived: Mapped[bool] = mapped_column(default=False, server_default="false")
    origin: Mapped[str] = mapped_column(
        String(30), default="expedition_death", server_default="expedition_death"
    )
    assessed_value: Mapped[int] = mapped_column(Gold(), default=0, server_default="0")
    former_owner_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    opening_price: Mapped[int] = mapped_column(Gold())
    highest_bid: Mapped[int] = mapped_column(Gold(), default=0)
    highest_bidder_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id"))
    started_at: Mapped[datetime] = mapped_column(default=utc_now)
    ends_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    proceeds_destination: Mapped[str] = mapped_column(String(20), default="treasury")


class AuctionBid(Base):
    __tablename__ = "auction_bids"
    __table_args__ = (
        UniqueConstraint("bidder_id", "request_id"),
        CheckConstraint("amount > 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), index=True)
    bidder_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    request_id: Mapped[str] = mapped_column(String(36))
    amount: Mapped[int] = mapped_column(Gold())
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class AdminRole(Base):
    __tablename__ = "admin_roles"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    expires: Mapped[datetime] = mapped_column(DateTime)


class AdminLoginAttempt(Base):
    __tablename__ = "admin_login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(default=0)
    window_start: Mapped[datetime] = mapped_column(default=utc_now)


class AdminOperation(Base):
    __tablename__ = "admin_operations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(80))
    params: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    confirmation_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="PREVIEW")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    expires: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class CentralBank(Base):
    __tablename__ = "central_bank"
    __table_args__ = (CheckConstraint("balance >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column(Gold(), default=0)


class AdminTestCredit(Base):
    __tablename__ = "admin_test_credits"
    __table_args__ = (CheckConstraint("balance >= 0"),)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    balance: Mapped[int] = mapped_column(Gold(), default=0)


class GameSetting(Base):
    __tablename__ = "game_settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class MonsterDefinition(Base):
    __tablename__ = "monster_definitions"
    __table_args__ = (
        CheckConstraint(
            "hp > 0 AND attack >= 0 AND defense >= 0 AND level >= 1 AND xp >= 0"
        ),
    )
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    procedural_config: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default="{}"
    )
    hp: Mapped[int] = mapped_column()
    attack: Mapped[int] = mapped_column()
    defense: Mapped[int] = mapped_column()
    level: Mapped[int] = mapped_column()
    xp: Mapped[int] = mapped_column()


class RecoveryItem(Base):
    __tablename__ = "recovery_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    death_event_id: Mapped[int] = mapped_column(ForeignKey("death_events.id"))
    price: Mapped[int] = mapped_column(Gold())
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime)
    request_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (
        UniqueConstraint("death_event_id", "item_id"),
        CheckConstraint("price >= 0"),
    )


class DebtCollection(Base):
    __tablename__ = "debt_collections"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    accrued_checkpoint: Mapped[int] = mapped_column(Gold())
    debt_before: Mapped[int] = mapped_column(Gold())
    debt_after: Mapped[int] = mapped_column(Gold())
    assessed: Mapped[int] = mapped_column(Gold())
    surplus: Mapped[int] = mapped_column(Gold())
    items: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class ScheduledWorldEvent(Base):
    __tablename__ = "scheduled_world_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    region: Mapped[str] = mapped_column(String(80))
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"))
    effect: Mapped[str] = mapped_column(String(30))
    intensity: Mapped[int] = mapped_column()
    conditions: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    operation_id: Mapped[str] = mapped_column(
        ForeignKey("admin_operations.id"), unique=True
    )


class CombatEncounter(Base):
    __tablename__ = "combat_encounters"
    __table_args__ = (
        UniqueConstraint("character_id", "request_id"),
        CheckConstraint("turn >= 0 AND size >= 2 AND size <= 3"),
        CheckConstraint("status IN ('ACTIVE','WON','LOST','FLED')"),
        Index(
            "uq_active_combat_encounter",
            "character_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"))
    request_id: Mapped[str] = mapped_column(String(36))
    enemy_ids: Mapped[list] = mapped_column(JSON)
    selected_enemy_id: Mapped[int] = mapped_column()
    size: Mapped[int] = mapped_column()
    turn: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    metrics_recorded: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    damage_dealt: Mapped[int] = mapped_column(default=0)
    damage_received: Mapped[int] = mapped_column(default=0)
    last_round: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class GameplayDay(Base):
    __tablename__ = "gameplay_days"
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    counters: Mapped[dict] = mapped_column(JSON, default=dict)


class ResourceNode(Base):
    __tablename__ = "resource_nodes"
    __table_args__ = (
        UniqueConstraint("character_id", "room_id", "generation", "node_key"),
        CheckConstraint("capacity > 0 AND remaining >= 0 AND remaining <= capacity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True)
    generation: Mapped[int] = mapped_column(default=0)
    node_key: Mapped[str] = mapped_column(String(40))
    definition: Mapped[str] = mapped_column(ForeignKey("item_definitions.id"))
    x: Mapped[int] = mapped_column()
    y: Mapped[int] = mapped_column()
    capacity: Mapped[int] = mapped_column()
    remaining: Mapped[int] = mapped_column()
    enabled: Mapped[bool] = mapped_column(default=True, server_default="true")


class GuildContract(Base):
    __tablename__ = "guild_contracts"
    __table_args__ = (
        CheckConstraint(
            "required > 0 AND reward > 0 AND reserved >= 0 AND slots > 0 AND taken >= 0 AND taken <= slots"
        ),
        CheckConstraint("kind IN ('kill','collect','deliver')"),
        CheckConstraint("status IN ('OPEN','CANCELLED','COMPLETED')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(String(30))
    required: Mapped[int] = mapped_column()
    reward: Mapped[int] = mapped_column(Gold())
    slots: Mapped[int] = mapped_column()
    taken: Mapped[int] = mapped_column(default=0)
    reserved: Mapped[int] = mapped_column(Gold(), default=0)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    operation_id: Mapped[str | None] = mapped_column(ForeignKey("admin_operations.id"))


class CharacterContract(Base):
    __tablename__ = "character_contracts"
    __table_args__ = (
        UniqueConstraint("character_id", "contract_id"),
        UniqueConstraint("character_id", "request_id"),
        CheckConstraint("progress >= 0"),
        CheckConstraint("status IN ('ACTIVE','PAID','CANCELLED')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("guild_contracts.id"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(36))
    progress: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    accepted_at: Mapped[datetime] = mapped_column(default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    claim_request_id: Mapped[str | None] = mapped_column(String(36))


class DiscordOperation(Base):
    __tablename__ = "discord_operations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    discord_id: Mapped[str] = mapped_column(String(30))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    equipped: Mapped[bool] = mapped_column(Boolean)
    before: Mapped[dict] = mapped_column(JSON)
    confirmation_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="PREVIEW")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    __table_args__ = (CheckConstraint("status IN ('PREVIEW','APPLIED')"),)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column()
    count: Mapped[int] = mapped_column()
    __table_args__ = (CheckConstraint("count > 0"),)


Index("ix_battles_character_status", Battle.character_id, Battle.status, Battle.claimed)
Index("ix_items_owner_location", Item.owner, Item.location)
Index(
    "ix_world_events_character_recent",
    WorldEvent.payload["character"].as_integer(),
    WorldEvent.id,
)
Index(
    "ix_contract_acceptance_active",
    CharacterContract.character_id,
    CharacterContract.status,
    CharacterContract.contract_id,
)


class LunarAsset(Base):
    __tablename__ = "lunar_assets"
    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    weight_mg: Mapped[int] = mapped_column(Gold())
    __table_args__ = (
        CheckConstraint("kind IN ('nugget','coin')"),
        CheckConstraint("weight_mg > 0"),
    )


class LunarAccount(Base):
    __tablename__ = "lunar_accounts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id"), unique=True
    )
    __table_args__ = (
        CheckConstraint(
            "kind IN ('player','npc','guild','treasury','escrow','expedition')"
        ),
    )


class LunarHolding(Base):
    __tablename__ = "lunar_holdings"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("lunar_accounts.id"), primary_key=True
    )
    asset_code: Mapped[str] = mapped_column(
        ForeignKey("lunar_assets.code"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Gold(), default=0)
    __table_args__ = (CheckConstraint("quantity >= 0"),)


class LunarEntry(Base):
    __tablename__ = "lunar_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(160), unique=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(500))
    fingerprint: Mapped[str] = mapped_column(String(64))
    postings: Mapped[list] = mapped_column(JSON)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class LunarSupply(Base):
    __tablename__ = "lunar_supply"
    id: Mapped[int] = mapped_column(primary_key=True)
    discovered_mg: Mapped[int] = mapped_column(Gold(), default=0)
    legacy_backing_mg: Mapped[int] = mapped_column(Gold(), default=0)
    destroyed_mg: Mapped[int] = mapped_column(Gold(), default=0)
    minted_mg: Mapped[int] = mapped_column(Gold(), default=0)
    coin_burned_mg: Mapped[int] = mapped_column(Gold(), default=0)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint("id = 1"),
        CheckConstraint(
            "discovered_mg >= 0 AND legacy_backing_mg >= 0 AND destroyed_mg >= 0 AND minted_mg >= 0 AND coin_burned_mg >= 0"
        ),
    )
