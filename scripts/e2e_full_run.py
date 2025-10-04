from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> int:
    print("$", " ".join(cmd))
    proc = subprocess.Popen(cmd, env=env or os.environ.copy(), cwd=str(cwd or REPO_ROOT))
    return proc.wait()


def run_background(cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.Popen:
    print("$ (bg)", " ".join(cmd))
    return subprocess.Popen(cmd, env=env or os.environ.copy(), cwd=str(cwd or REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def wait_for_api(base_url: str, timeout_s: int = 45) -> None:
    import httpx

    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            r = httpx.get(base_url.rstrip("/") + "/api/metrics/health", timeout=5.0)
            if r.status_code == 200:
                print("API is up:", r.json())
                return
        except Exception as e:  # noqa: PERF203 - best-effort probe
            last_error = e
        time.sleep(1.0)
    raise RuntimeError(f"API did not become ready in {timeout_s}s: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full E2E: migrations -> API -> ingestion -> probes -> chat seeds")
    parser.add_argument("--paycom-base-url", required=True, help="Replit Paycom mock base URL")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="Postgres DATABASE_URL (or env)")
    parser.add_argument("--company-id", type=int, default=1)
    parser.add_argument("--days", type=int, default=28, help="Days of time entries to ingest")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--llm-provider", default=os.getenv("LLM_PROVIDER", "mock"))
    args = parser.parse_args()

    env = os.environ.copy()
    if args.database_url:
        env["DATABASE_URL"] = args.database_url
    # Minimal credentials accepted by mock; values are not validated by our client
    env.setdefault("PAYCOM_SID", env.get("PAYCOM_SID", "demo_sid"))
    env.setdefault("PAYCOM_TOKEN", env.get("PAYCOM_TOKEN", "demo_token"))
    env["PAYCOM_BASE_URL"] = args.paycom_base_url.rstrip("/")
    env["LLM_PROVIDER"] = args.llm_provider

    print("Repo root:", REPO_ROOT)
    print("PAYCOM_BASE_URL:", env["PAYCOM_BASE_URL"])

    # 1) Apply migrations
    rc = run([sys.executable, str(REPO_ROOT / "backend" / "src" / "db" / "run_migrations.py")], env=env)
    if rc != 0:
        return rc

    # 2) Start API
    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(args.api_port),
        "--reload",
    ]
    api_proc = run_background(api_cmd, env=env)

    try:
        # Wait until API is ready
        wait_for_api(f"http://127.0.0.1:{args.api_port}")

        # 3) Ingest employees and time entries
        rc = run([
            sys.executable,
            str(REPO_ROOT / "scripts" / "e2e_sync_once.py"),
            "--company-id",
            str(args.company_id),
            "--days",
            str(args.days),
            "--base-url",
            env["PAYCOM_BASE_URL"],
        ], env=env)
        if rc != 0:
            return rc

        # 4) Probe metrics endpoints and save outputs
        rc = run([
            sys.executable,
            str(REPO_ROOT / "scripts" / "e2e_metrics_probe.py"),
            "--base-url",
            f"http://127.0.0.1:{args.api_port}",
            "--out",
            str(REPO_ROOT / ".e2e" / "metrics"),
            "--company-id",
            str(args.company_id),
        ], env=env)
        if rc != 0:
            return rc

        # 5) Seed chat SSE for four metrics and save transcripts
        rc = run([
            sys.executable,
            str(REPO_ROOT / "scripts" / "e2e_seeded_chat.py"),
            "--base-url",
            f"http://127.0.0.1:{args.api_port}",
            "--out",
            str(REPO_ROOT / ".e2e" / "chat"),
            "--company-id",
            str(args.company_id),
        ], env=env)
        if rc != 0:
            return rc

        print("\nE2E complete. Outputs saved to:")
        print(" -", REPO_ROOT / ".e2e" / "metrics")
        print(" -", REPO_ROOT / ".e2e" / "chat")
        print("\nAPI is still running on:", f"http://127.0.0.1:{args.api_port}")
        print("You can now start the frontend dev server and demo the app.")

        # Keep API running until user interrupts
        print("\nPress Ctrl+C to stop the API server.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        # Terminate API process
        try:
            api_proc.send_signal(signal.SIGINT)
            try:
                api_proc.wait(timeout=5)
            except Exception:
                api_proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())


