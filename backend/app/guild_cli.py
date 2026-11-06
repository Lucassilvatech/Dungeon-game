"""Operator CLI: read state, create preview, explicitly confirm with fingerprint/token."""

import argparse, json
from uuid import uuid4
from sqlalchemy import select
from fastapi import HTTPException
from . import models as m, finance, guild_admin, guild_commerce, admin_service
from .database import Session
from .admin_security import Principal, require
from .admin import OperationInput


def main():
    p = argparse.ArgumentParser(
        description="Inspecionar Guilda e aplicar troca manual auditada; nunca refaz cutover"
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    sub.add_parser("audit")
    preview = sub.add_parser("preview")
    preview.add_argument("--username", required=True)
    preview.add_argument("--reason", required=True)
    preview.add_argument("--request-id", default=None)
    preview.add_argument(
        "--manual",
        action="store_true",
        help="Novo rebalanceamento manual; sem este argumento usa V1 idempotente",
    )
    apply = sub.add_parser("apply")
    apply.add_argument("--username", required=True)
    apply.add_argument("--operation-id", required=True)
    apply.add_argument("--fingerprint", required=True)
    apply.add_argument("--confirmation-token", required=True)
    apply.add_argument("--confirm", action="store_true", required=True)
    args = p.parse_args()
    try:
        with Session.begin() as db:
            if args.command == "inspect":
                result = {
                    "cutover_active": finance.active(db),
                    "cash": finance.cash(db, "guild"),
                    "proposal": guild_admin.rebalance_denominations(
                        finance.coin_mg(db, "guild")
                    ),
                    "prices": guild_commerce.admin_catalog(db),
                    "mineral": guild_commerce.mineral_policy(db),
                }
            elif args.command == "audit":
                result = finance.reconcile(db)
                if (
                    result["gap_mg"] != "0"
                    or result["metadata_mismatches"]
                    or result["ledger_mismatches"]
                ):
                    raise RuntimeError(
                        "Auditoria divergente; nenhuma correção automática"
                    )
            else:
                account = db.scalar(
                    select(m.Account).where(m.Account.username == args.username.lower())
                )
                role = db.get(m.AdminRole, account.id) if account else None
                if not role:
                    raise RuntimeError(
                        "Usuário administrativo existente exigido; não há conta padrão"
                    )
                actor = Principal(account.id, role.role)
                require(actor, "economy.manage")
                if args.command == "preview":
                    body = OperationInput(
                        operation_id=args.request_id or str(uuid4()),
                        action="guild.rebalance",
                        target="guild",
                        params={"initial": not args.manual},
                        reason=args.reason,
                    )
                    result = admin_service.preview(db, actor, body)
                else:
                    op = db.get(m.AdminOperation, args.operation_id)
                    if (
                        not op
                        or op.action != "guild.rebalance"
                        or op.before.get("fingerprint") != args.fingerprint
                    ):
                        raise RuntimeError("Fingerprint/identidade de prévia inválido")
                    result = admin_service.confirm(
                        db, actor, args.operation_id, args.confirmation_token
                    )
                    result["audit"] = finance.reconcile(db)
            print(json.dumps(result, ensure_ascii=False, default=str))
    except (HTTPException, RuntimeError) as error:
        p.exit(1, str(getattr(error, "detail", error)) + "\n")


if __name__ == "__main__":
    main()
