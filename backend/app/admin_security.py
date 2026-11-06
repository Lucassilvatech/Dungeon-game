"""Independent short-lived admin sessions; normal player/bot tokens never grant access."""

from dataclasses import dataclass
from datetime import timedelta
import secrets
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from .models import Account, AdminRole, AdminSession, AdminLoginAttempt
from .security import bearer, digest, password_matches
from .database import get_db
from .clock import utc_now

READ = {
    "overview.read",
    "economy.read",
    "guilds.read",
    "players.read",
    "items.read",
    "monsters.read",
    "auctions.read",
    "world.read",
    "audit.read",
    "encounters.read",
    "collection.read",
    "contracts.read",
    "metrics.read",
}
ROLES = {
    "observer": READ,
    "operator": READ
    | {
        "players.manage",
        "items.manage",
        "monsters.manage",
        "auctions.manage",
        "world.manage",
        "collection.manage",
    },
    "economist": READ | {"economy.manage", "contracts.manage"},
    "owner": READ
    | {
        "players.manage",
        "items.manage",
        "monsters.manage",
        "auctions.manage",
        "world.manage",
        "collection.manage",
        "economy.manage",
        "contracts.manage",
    },
}


@dataclass
class Principal:
    id: int
    role: str

    @property
    def permissions(self):
        return ROLES.get(self.role, set())


def login(db, username, password, ip):
    # Persist failed attempts: return a response rather than raising/rolling them back.
    db.execute(text("SELECT pg_advisory_xact_lock(7312028)"))
    now = utc_now()
    buckets = []
    for key in (digest("adm-ip:" + ip), digest("adm-user:" + username.lower())):
        row = db.get(AdminLoginAttempt, key)
        if not row:
            row = AdminLoginAttempt(key=key, failures=0, window_start=now)
            db.add(row)
        if now - row.window_start >= timedelta(minutes=10):
            row.failures = 0
            row.window_start = now
        buckets.append(row)
    if any(r.failures >= 5 for r in buckets):
        return JSONResponse(
            status_code=429,
            content={"detail": "Muitas tentativas. Aguarde 10 minutos."},
        )
    a = db.scalar(select(Account).where(Account.username == username.lower()))
    valid = (
        password_matches(password, a.password)
        if a
        else password_matches(password, "0" * 32 + ":" + "0" * 64)
    )
    role = db.get(AdminRole, a.id) if a else None
    if not valid or not role or role.role not in ROLES:
        for row in buckets:
            row.failures += 1
        return JSONResponse(
            status_code=403, content={"detail": "Credenciais administrativas inválidas"}
        )
    buckets[1].failures = 0
    token = secrets.token_urlsafe(48)
    db.add(
        AdminSession(
            token=digest(token), account_id=a.id, expires=now + timedelta(hours=1)
        )
    )
    return {
        "token": token,
        "expires_in": 3600,
        "role": role.role,
        "permissions": sorted(ROLES[role.role]),
    }


def principal(auth=Depends(bearer), db=Depends(get_db)):
    session = db.get(AdminSession, digest(auth.credentials))
    if not session or session.expires <= utc_now():
        raise HTTPException(401, "Sessão administrativa inválida ou expirada")
    role = db.get(AdminRole, session.account_id)
    if not role or role.role not in ROLES:
        raise HTTPException(403, "Permissão administrativa revogada")
    return Principal(session.account_id, role.role)


def require(actor, permission):
    if permission not in actor.permissions:
        raise HTTPException(403, "Permissão administrativa insuficiente: " + permission)
