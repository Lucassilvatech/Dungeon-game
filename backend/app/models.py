from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

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
    __table_args__ = (CheckConstraint("coins >= 0 AND hp >= 0 AND energy >= 0"),)
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
    coins: Mapped[int] = mapped_column(default=0)

class ItemDefinition(Base):
    __tablename__ = "item_definitions"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(20))
    power: Mapped[int] = mapped_column(default=0)

class Item(Base):
    __tablename__ = "items"
    __table_args__ = (CheckConstraint("quantity > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    definition: Mapped[str] = mapped_column(ForeignKey("item_definitions.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    location: Mapped[str] = mapped_column(String(20), default="inventory")
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)

class Battle(Base):
    __tablename__ = "battles"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    monster: Mapped[str] = mapped_column(String(20))
    hp: Mapped[int] = mapped_column()
    turn: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)

class Treasury(Base):
    __tablename__ = "treasury"
    __table_args__ = (CheckConstraint("balance >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column()

class Ledger(Base):
    __tablename__ = "ledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True)
    source: Mapped[str] = mapped_column(String(50))
    destination: Mapped[str] = mapped_column(String(50))
    amount: Mapped[int] = mapped_column()
    created: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class WorldEvent(Base):
    __tablename__ = "world_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
