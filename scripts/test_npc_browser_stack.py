"""Run the real NPC worker/Chromium against a newly created, isolated PostgreSQL DB.
Never resets or migrates the DATABASE_URL database itself. Requires test authorization.
"""

import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from uuid import uuid4
from sqlalchemy import create_engine, text

assert (
    os.getenv("TOWER_TEST_DATABASE") == "1"
), "Explicit disposable-test authorization required"
assert os.getenv("DATABASE_URL"), "Use an explicit test PostgreSQL server"
root = Path(__file__).resolve().parents[1]
name = "npc_browser_" + uuid4().hex[:10]
source = create_engine(os.environ["DATABASE_URL"], isolation_level="AUTOCOMMIT")
assert source.url.get_backend_name() == "postgresql", "PostgreSQL test server required"
with source.connect() as connection:
    connection.execute(
        text("CREATE DATABASE " + name)
    )  # generated identifier, never user text
url = source.url.set(database=name).render_as_string(hide_password=False)
source.dispose()
env = {
    **os.environ,
    "DATABASE_URL": url,
    "RATE_LIMIT_SCALE": "10",
    "NPC_ECONOMY_TICK_SECONDS": "2",
    "SECRET_CHANCE": "0",
}
alembic = str(Path(sys.executable).parent / "alembic")
for args in [("upgrade", "head"), ("check",)]:
    subprocess.run([alembic, *args], cwd=root / "backend", env=env, check=True)
subprocess.run(
    [sys.executable, "-m", "app.seed"], cwd=root / "backend", env=env, check=True
)
os.environ.update(DATABASE_URL=url)
sys.path.insert(0, str(root / "backend"))
from app.database import Session
from app import lunar, cutover, finance, models as m

with Session.begin() as db:
    lunar.initialize(db)
    preview = cutover.preview(db)
    cutover.confirm(
        db,
        preview["fingerprint"],
        str(uuid4()),
        "private-browser-fixture",
        "Authorized isolated HTTP test database only",
    )
    # Explicit TEST exchange, no normalization hidden in a purchase.
    cash = finance.cash(db, "treasury")
    lunar.exchange(
        db,
        "treasury",
        {k: int(v) for k, v in cash["coins"].items() if int(v)},
        {"coin_small": int(cash["total_weight_mg"]) // 1000},
        "test-physical-change",
    )
    for profile in db.query(m.NpcProfile):
        if profile.id != "guild":
            profile.production_enabled = False
            profile.purchase_enabled = False


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


api_port, web_port = port(), port()
private = Path(tempfile.mkdtemp(prefix="dungeon-npc-e2e-"))
processes, logs = [], []
try:
    server_env = dict(env)
    server_env.pop(
        "TOWER_TEST_DATABASE", None
    )  # Exercise the actual background worker.
    for command, cwd, variables, label in [
        (
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--workers",
                "1",
            ],
            root / "backend",
            server_env,
            "api",
        ),
        (
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(web_port)],
            root / "frontend",
            {**env, "API_URL": f"http://127.0.0.1:{api_port}"},
            "web",
        ),
    ]:
        log = (private / (label + ".log")).open("w")
        logs.append(log)
        processes.append(
            subprocess.Popen(
                command,
                cwd=cwd,
                env=variables,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        )
    for attempt in range(60):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{web_port}/api/health", timeout=1
            ) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.5)
    else:
        raise RuntimeError("Private HTTP stack not ready; logs in " + str(private))
    subprocess.run(
        ["node", "tests/npc-economy.cjs"],
        cwd=root / "frontend",
        env={
            **env,
            "NPC_TEST_DATABASE_URL": url,
            "BASE_URL": f"http://127.0.0.1:{web_port}",
        },
        check=True,
    )
finally:
    for process in reversed(processes):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for process in processes:
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    for log in logs:
        log.close()
    # Retain the newly created private DB for diagnosis; never delete a game DB.
