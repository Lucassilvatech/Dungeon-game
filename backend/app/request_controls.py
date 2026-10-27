"""PostgreSQL-backed fixed windows, independent of game rollback; secret-free request logs."""

import json, logging, math, secrets, time
from sqlalchemy.dialects.postgresql import insert
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from .database import Session
from . import models as m
from .config import settings
from .clock import utc_now
from .security import digest

logger = logging.getLogger("dungeon.requests")
logger.setLevel(logging.INFO)
if not logging.getLogger().handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def policy(path, method):
    if path == "/health" or method == "OPTIONS":
        return None
    if path in ("/auth/login", "/auth/register"):
        return ("authentication", 15, 600)
    if path.startswith("/discord/"):
        return (
            ("discord-query", 120, 60)
            if method == "GET"
            else ("discord-action", 20, 60)
        )
    if path.startswith("/admin/operations"):
        return ("administration", 30, 60)
    if method == "GET":
        return ("read", 300, 60)
    if path == "/move":
        return ("move", 240, 60)
    if path.startswith(("/battles", "/encounters")):
        return ("combat", 90, 60)
    if "/lunar-resources/" in path or path.startswith("/lunar/") and method != "GET":
        return ("lunar-finance", 30, 60)
    if path.startswith("/resources/"):
        return ("gather", 45, 60)
    if path.startswith("/contracts/"):
        return ("contracts", 30, 60)
    if path.startswith(("/auctions/", "/guild/", "/recovery/")):
        return ("finance", 30, 60)
    return ("write", 120, 60)


def consume(path, method, headers, ip):
    group, limit, seconds = policy(path, method)
    actor = "ip:" + ip
    with Session.begin() as db:
        authorization = headers.get("authorization", "")
        if authorization.startswith("Bearer ") and len(authorization) < 300:
            model = m.AdminSession if path.startswith("/admin/") else m.AuthSession
            session = db.get(model, digest(authorization[7:]))
            if session and session.expires >= utc_now():
                actor = f"account:{session.account_id}"
        if (
            path.startswith("/discord/")
            and settings.discord_service_key
            and secrets.compare_digest(
                headers.get("x-bot-key", ""), settings.discord_service_key
            )
        ):
            parts = path.split("/")
            actor = (
                "discord:" + parts[2]
                if len(parts) > 2 and parts[2].isdigit() and len(parts[2]) <= 30
                else "bot-link:" + ip
            )
        now = int(time.time())
        window = now // seconds
        key = digest(group + ":" + actor)
        table = m.RateLimitBucket
        statement = insert(table).values(key=key, window=window, count=1)
        from sqlalchemy import case, func

        # Saturation bounds the counter even under a sustained attack.
        statement = statement.on_conflict_do_update(
            index_elements=[table.key],
            set_={
                "window": window,
                "count": case(
                    (table.window == window, func.least(table.count + 1, 1000000)),
                    else_=1,
                ),
            },
        ).returning(table.count)
        count = db.scalar(statement)
    limit = max(1, math.ceil(limit * settings.rate_limit_scale))
    return seconds - now % seconds if count > limit else 0


class RequestControls:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = time.perf_counter()
        request_id = secrets.token_hex(12)
        status = 500

        async def tracked_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode())
                ]
            await send(message)

        try:
            path = scope["path"]
            method = scope["method"]
            if settings.rate_limits_enabled and policy(path, method):
                headers = {
                    k.decode("latin1").lower(): v.decode("latin1")
                    for k, v in scope.get("headers", [])
                }
                retry = await run_in_threadpool(
                    consume,
                    path,
                    method,
                    headers,
                    (scope.get("client") or ("unknown",))[0],
                )
                if retry:
                    response = JSONResponse(
                        {
                            "detail": "Muitas requisições. Aguarde e tente novamente.",
                            "retry_after": retry,
                        },
                        status_code=429,
                        headers={"Retry-After": str(retry)},
                    )
                    return await response(scope, receive, tracked_send)
            await self.app(scope, receive, tracked_send)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": scope["method"],
                        "route": route,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    },
                    separators=(",", ":"),
                )
            )
