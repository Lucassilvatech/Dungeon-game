from concurrent.futures import ThreadPoolExecutor
import json
from sqlalchemy import select, text
from test_game import clean, client, player, state
from app.database import Session
from app.config import settings
from app.security import issue_token
from app import models as m
from app.request_controls import consume


def enable(monkeypatch):
    monkeypatch.setattr(settings, "rate_limits_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_scale", 0.01)


def test_rate_limit_failed_financial_requests_survive_rollback(client, monkeypatch):
    h = player(client)
    enable(monkeypatch)
    r = client.post(
        "/contracts/99999/accept",
        headers=h,
        json={"request_id": "db13a1f4-5a39-4469-834f-e865151923db"},
    )
    assert r.status_code == 409
    r = client.post(
        "/contracts/99999/accept",
        headers=h,
        json={"request_id": "db13a1f4-5a39-4469-834f-e865151923db"},
    )
    assert r.status_code == 429 and 0 < int(r.headers["Retry-After"]) <= 60
    assert r.json()["retry_after"] > 0
    with Session() as db:
        assert db.scalar(select(m.RateLimitBucket.count)) == 2


def test_rate_limits_follow_account_across_tokens_not_shared_proxy_ip(
    client, monkeypatch
):
    h = player(client)
    other = player(client, "other")
    with Session.begin() as db:
        a = db.scalar(select(m.Account).where(m.Account.username == "alice"))
        token = issue_token(db, a)["token"]
    h2 = {"Authorization": "Bearer " + token}
    enable(monkeypatch)
    for headers in [h, h2, h]:
        assert client.get("/state", headers=headers).status_code == 200
    assert client.get("/state", headers=h2).status_code == 429
    assert client.get("/state", headers=other).status_code == 200
    assert client.get("/health").status_code == 200


def test_concurrent_rate_counter_and_window_reset(client, monkeypatch):
    h = player(client)
    enable(monkeypatch)
    headers = {"authorization": h["Authorization"]}
    with ThreadPoolExecutor(8) as pool:
        results = list(
            pool.map(
                lambda _: consume(
                    "/resources/1/collect", "POST", headers, "same-proxy"
                ),
                range(10),
            )
        )
    assert results.count(0) == 1
    with Session.begin() as db:
        row = db.scalar(select(m.RateLimitBucket))
        assert row.count == 10
        row.window -= 1
    assert consume("/resources/1/collect", "POST", headers, "same-proxy") == 0


def test_login_throttled_after_failed_attempt_and_logs_do_not_include_credentials(
    client, monkeypatch, caplog
):
    h = player(client)
    enable(monkeypatch)
    with caplog.at_level("INFO", logger="dungeon.requests"):
        first = client.post(
            "/auth/login",
            json={"username": "alice", "password": "never-log-this-password"},
        )
        assert first.status_code == 401
        assert (
            client.post(
                "/auth/login",
                json={"username": "alice", "password": "never-log-this-password"},
            ).status_code
            == 429
        )
        assert (
            client.get(
                "/discord/123456789/queries/character",
                headers={"X-Bot-Key": "never-log-this-service-key"},
            ).status_code
            == 403
        )
    logs = [
        json.loads(r.message) for r in caplog.records if r.name == "dungeon.requests"
    ]
    assert logs and all("duration_ms" in r and len(r["request_id"]) == 24 for r in logs)
    assert any(r["route"] == "/discord/{discord_id}/queries/{section}" for r in logs)
    joined = json.dumps(logs)
    assert all(
        secret not in joined
        for secret in [
            "never-log-this-password",
            "never-log-this-service-key",
            h["Authorization"],
            "123456789",
        ]
    )


def test_malformed_websocket_auth_is_closed_and_query_indexes_exist(client):
    with client.websocket_connect("/ws/rooms") as ws:
        ws.send_json([])
        assert ws.receive()["code"] == 4401
    with Session() as db:
        names = set(
            db.scalars(
                text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
            )
        )
        assert {
            "ix_battles_character_status",
            "ix_items_owner_location",
            "ix_world_events_character_recent",
            "ix_contract_acceptance_active",
        } <= names
