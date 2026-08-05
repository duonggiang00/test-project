import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


os.environ["ENV"] = "test"

from app.core.security import get_password_hash  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.user import User  # noqa: E402
from scripts.test_database import build_manager  # noqa: E402


FRONTEND_ROOT = Path(__file__).resolve().parents[2] / "frontend"
BACKEND_ORIGIN = "http://127.0.0.1:8765"
BACKEND_HEALTH_URL = f"{BACKEND_ORIGIN}/"


def seed_users() -> None:
    session = SessionLocal()
    try:
        session.add_all(
            [
                User(
                    email="admin@example.com",
                    password_hash=get_password_hash("12345678"),
                    full_name="E2E Admin",
                    role="admin",
                ),
                User(
                    email="student@example.com",
                    password_hash=get_password_hash("12345678"),
                    full_name="E2E Student",
                    role="student",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()


def wait_for_backend(process: subprocess.Popen, timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend exited before readiness with {process.returncode}")
        try:
            with urllib.request.urlopen(BACKEND_HEALTH_URL, timeout=1) as response:
                if response.status == 200:
                    print("REAL_E2E_BACKEND_READY", flush=True)
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("Backend did not become ready within 30 seconds")


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    command = sys.argv[1:]
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise ValueError("A frontend E2E command is required after `--`")

    manager = build_manager()
    backend_process = None
    manager.create()
    try:
        Base.metadata.create_all(bind=engine)
        seed_users()
        backend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
            ],
            env={**os.environ, "ENV": "test"},
        )
        wait_for_backend(backend_process)
        completed = subprocess.run(
            command,
            cwd=FRONTEND_ROOT,
            env={
                **os.environ,
                "BACKEND_API_URL": BACKEND_ORIGIN,
            },
            check=False,
        )
        return completed.returncode
    finally:
        if backend_process is not None:
            stop_process(backend_process)
        engine.dispose()
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
