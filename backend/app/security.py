from .clock import utc_now
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .database import get_db
from .models import AuthSession, Account

bearer = HTTPBearer()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.pbkdf2_hmac(
            "sha256", value.encode(), bytes.fromhex(salt), 600000
        ).hex()
    )


def password_matches(value, stored):
    return hmac.compare_digest(password_hash(value, stored.split(":")[0]), stored)


def issue_token(db, account):
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token=digest(token),
            account_id=account.id,
            expires=utc_now() + timedelta(days=7),
        )
    )
    return {"token": token}


def current_account(
    auth: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)
):
    session = db.get(AuthSession, digest(auth.credentials))
    if not session or session.expires < utc_now():
        raise HTTPException(401, "Sessão inválida ou expirada")
    return db.get(Account, session.account_id)
