"""Local controlled HTTP/SQL latency samples; only runs against an explicitly disposable test DB."""

import os, sys, time, json, statistics, logging
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import settings

assert (
    os.getenv("TOWER_TEST_DATABASE") == "1" and "_test" in settings.database_url
), "Disposable test DB required"
from app.database import engine
from app.main import app
from app.seed import seed
from fastapi.testclient import TestClient
from sqlalchemy import event

logging.getLogger("dungeon.requests").disabled = True
settings.wander_interval = 100000
seed()
queries = 0


@event.listens_for(engine, "before_cursor_execute")
def count(*args):
    global queries
    queries += 1


def percentile(values, p):
    return round(sorted(values)[int((len(values) - 1) * p)], 2)


report = {
    "method": "TestClient HTTP + real PostgreSQL, single sequential user, no network/browser/production load claim",
    "samples_per_endpoint": 50,
    "results": [],
}
with TestClient(app) as c:
    name = "benchmark" + uuid4().hex[:15]
    r = c.post(
        "/auth/register",
        json={"username": name, "password": "benchmark-disposable-pass"},
    )
    assert r.status_code == 201
    h = {"Authorization": "Bearer " + r.json()["token"]}
    assert c.post("/character", headers=h, json={"name": name}).status_code == 201
    for enabled in (False, True):
        settings.rate_limits_enabled = enabled
        for path in ("/state", "/metrics", "/resources", "/contracts"):
            times = []
            counts = []
            sizes = []
            for i in range(52):
                before = queries
                start = time.perf_counter()
                r = c.get(path, headers=h)
                elapsed = (time.perf_counter() - start) * 1000
                assert r.status_code == 200, (path, r.status_code)
                if i >= 2:
                    times.append(elapsed)
                    counts.append(queries - before)
                    sizes.append(len(r.content))
            report["results"].append(
                {
                    "path": path,
                    "rate_limits": enabled,
                    "p50_ms": percentile(times, 0.5),
                    "p95_ms": percentile(times, 0.95),
                    "p99_ms": percentile(times, 0.99),
                    "mean_sql_queries": round(statistics.mean(counts), 1),
                    "mean_response_bytes": round(statistics.mean(sizes)),
                }
            )
Path("docs/performance-0.8.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
