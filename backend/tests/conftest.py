from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Iterator, List

import psycopg
import pytest


def _find_repo_root(start: Path) -> Path:
    cur = start
    while cur != cur.parent:
        candidate = cur / "backend" / "src" / "db" / "migrations"
        if candidate.exists():
            return cur
        cur = cur.parent
    # Fallback to start
    return start


def _migration_paths(repo_root: Path) -> List[Path]:
    mig_dir = repo_root / "backend" / "src" / "db" / "migrations"
    return sorted([p for p in mig_dir.glob("*.sql") if p.is_file()])


def _apply_migrations(conn: psycopg.Connection, migrations: List[Path]) -> None:
    with conn.cursor() as cur:
        for path in migrations:
            sql = path.read_text(encoding="utf-8")
            cur.execute(sql)
    conn.commit()


# Ensure repo root is on sys.path so tests can import the backend package
_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("DB_USER", os.getenv("USER", "client"))
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "hom")
    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql://{auth}{host}:{port}/{name}"


@pytest.fixture(scope="session")
def migrated_db(database_url: str) -> Iterator[str]:
    # Use project's migration runner which skips already-applied files
    # Ensure repo root on path for relative imports (already handled above)
    from backend.src.db.run_migrations import main as run_migrations_main  # local import after sys.path
    run_migrations_main()
    yield database_url


def _truncate_for_test(conn: psycopg.Connection) -> None:
    # Clean relevant tables between tests, keeping companies (default tenant) intact
    with conn.cursor() as cur:
        cur.execute(
            """
            DO $$ BEGIN
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='ai_messages') THEN TRUNCATE ai_messages RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='ai_conversations') THEN TRUNCATE ai_conversations RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='action_status_history') THEN TRUNCATE action_status_history RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='actions') THEN TRUNCATE actions RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='sync_logs') THEN TRUNCATE sync_logs RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='metric_configs') THEN TRUNCATE metric_configs RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='metrics_history') THEN TRUNCATE metrics_history RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='time_entries') THEN TRUNCATE time_entries RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='employee_assignment_history') THEN TRUNCATE employee_assignment_history RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='events') THEN TRUNCATE events RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='employees') THEN TRUNCATE employees RESTART IDENTITY CASCADE; END IF;
              IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='departments') THEN TRUNCATE departments RESTART IDENTITY CASCADE; END IF;
            END $$;
            """
        )
    conn.commit()


@pytest.fixture()
def db_conn(migrated_db: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(migrated_db) as conn:
        _truncate_for_test(conn)
        yield conn


