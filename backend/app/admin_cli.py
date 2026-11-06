"""Local operator bootstrap. No default administrator or password is created."""

import argparse
from sqlalchemy import select
from .database import Session
from .models import Account, AdminRole, AdminSession, WorldEvent
from .admin_security import ROLES
from .clock import utc_now
import secrets


def main():
    p = argparse.ArgumentParser(
        description="Grant/revoke an admin role to an EXISTING account, with audit"
    )
    p.add_argument("username")
    p.add_argument("role", choices=[*ROLES, "revoke"])
    p.add_argument("--reason", required=True)
    args = p.parse_args()
    if len(args.reason) < 10:
        p.error("Use a reason with at least 10 characters")
    with Session.begin() as db:
        a = db.scalar(
            select(Account)
            .where(Account.username == args.username.lower())
            .with_for_update()
        )
        if not a:
            p.error("Account does not exist; register normally first")
        old = db.get(AdminRole, a.id)
        before = old.role if old else None
        if args.role == "revoke":
            if old:
                db.delete(old)
        elif old:
            old.role = args.role
        else:
            db.add(AdminRole(account_id=a.id, role=args.role))
        for s in db.scalars(
            select(AdminSession).where(AdminSession.account_id == a.id)
        ):
            db.delete(s)
        db.add(
            WorldEvent(
                key="admin-role:" + secrets.token_hex(16),
                kind="ADMIN_ROLE_CHANGED",
                payload={
                    "actor": "local_operator",
                    "account_id": a.id,
                    "before": before,
                    "after": args.role,
                    "reason": args.reason,
                    "timestamp": utc_now().isoformat() + "Z",
                },
                processed=True,
            )
        )
        print("Role updated; administrative sessions revoked; audit recorded.")


if __name__ == "__main__":
    main()
