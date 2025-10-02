import os
import sys
from pathlib import Path
from typing import List

import psycopg


def get_database_url() -> str:
    # Prefer full DATABASE_URL; otherwise build from parts
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("DB_USER", os.getenv("USER", "postgres"))
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "hom")

    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql://{auth}{host}:{port}/{dbname}"


def ensure_schema_migrations_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              filename TEXT PRIMARY KEY,
              applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    conn.commit()


def list_migration_files(migrations_dir: Path) -> List[Path]:
    return sorted([p for p in migrations_dir.glob("*.sql") if p.is_file()])


def already_applied(conn: psycopg.Connection, filename: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
        return cur.fetchone() is not None


def apply_migration(conn: psycopg.Connection, migration_path: Path) -> None:
    sql = migration_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
            (migration_path.name,),
        )
    conn.commit()


def main() -> int:
    root = Path(__file__).resolve().parent
    migrations_dir = root / "migrations"
    if not migrations_dir.exists():
        print(f"Migrations directory not found: {migrations_dir}", file=sys.stderr)
        return 2

    database_url = get_database_url()
    print(f"Connecting to: {database_url}")

    try:
        with psycopg.connect(database_url) as conn:
            ensure_schema_migrations_table(conn)
            files = list_migration_files(migrations_dir)
            if not files:
                print("No migration files found. Nothing to do.")
                return 0

            for path in files:
                if already_applied(conn, path.name):
                    print(f"Already applied: {path.name}")
                    continue
                print(f"Applying: {path.name} ...", end="", flush=True)
                apply_migration(conn, path)
                print(" done.")
    except psycopg.OperationalError as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        return 1

    print("Migrations complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


