from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Any, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from backend.app.integration.paycom_client import PaycomClient
from backend.app.config.env import load_env, get_db_url
import psycopg


load_env()
DB_URL = get_db_url()


@asynccontextmanager
async def pg_conn():
    conn = await psycopg.AsyncConnection.connect(DB_URL)
    try:
        yield conn
    finally:
        await conn.close()


async def log_sync(conn: psycopg.AsyncConnection, company_id: int, source: str, status: str, details: Dict[str, Any]) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO sync_logs (company_id, source, job_id, status, details)
            VALUES (%s, %s, gen_random_uuid()::text, %s, %s)
            """,
            (company_id, source, status, psycopg.types.json.Json(details)),
        )
        await conn.commit()


async def upsert_employee(conn: psycopg.AsyncConnection, company_id: int, emp: Dict[str, Any]) -> int:
    # Minimal mapping; adjust to real fields offered by paycom_async models
    external_id = emp.get("id") or emp.get("external_id") or emp.get("eecode")
    first_name = emp.get("first_name") or emp.get("firstname")
    last_name = emp.get("last_name") or emp.get("lastname")
    email = emp.get("email") or f"{(first_name or 'user').lower()}@example.com"
    department = emp.get("department") or emp.get("deptname")
    # status mapping: 'A' -> active, else terminated/leave fallbacks
    raw_status = (emp.get("status") or "active").lower()
    if raw_status in ("a", "active"):
        employment_status = "active"
    else:
        employment_status = "terminated"
    # hire date
    hire_raw = emp.get("hiredate") or emp.get("hire_date")
    try:
        hire_date = date.fromisoformat(hire_raw) if hire_raw else date.today()
    except Exception:
        hire_date = date.today()

    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO employees (company_id, external_id, first_name, last_name, email, employment_status, department, hire_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, external_id) DO UPDATE
            SET first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                email = EXCLUDED.email,
                department = EXCLUDED.department,
                employment_status = EXCLUDED.employment_status,
                hire_date = EXCLUDED.hire_date,
                updated_at = now()
            RETURNING id
            """,
            (company_id, external_id, first_name, last_name, email, employment_status, department, hire_date),
        )
        row = await cur.fetchone()
        await conn.commit()
        return int(row[0])


async def upsert_time_entry(
    conn: psycopg.AsyncConnection,
    company_id: int,
    employee_id: int,
    work_date: date,
    worked_minutes: int,
    regular_minutes: int,
    ot1_minutes: int,
    ot2_minutes: int,
    scheduled_minutes: int | None,
    absence_code: str | None,
    absence_minutes: int | None,
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO time_entries (
              company_id, employee_id, work_date,
              worked_minutes, regular_minutes, ot1_minutes, ot2_minutes,
              scheduled_minutes, absence_code, absence_minutes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (company_id, employee_id, work_date) DO UPDATE SET
              worked_minutes = EXCLUDED.worked_minutes,
              regular_minutes = EXCLUDED.regular_minutes,
              ot1_minutes = EXCLUDED.ot1_minutes,
              ot2_minutes = EXCLUDED.ot2_minutes,
              scheduled_minutes = COALESCE(EXCLUDED.scheduled_minutes, time_entries.scheduled_minutes),
              absence_code = EXCLUDED.absence_code,
              absence_minutes = EXCLUDED.absence_minutes
            """,
            (
                company_id,
                employee_id,
                work_date,
                worked_minutes,
                regular_minutes,
                ot1_minutes,
                ot2_minutes,
                scheduled_minutes,
                absence_code,
                absence_minutes,
            ),
        )
        await conn.commit()


async def sync_employees(company_id: int) -> None:
    async with pg_conn() as conn:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(5),
                wait=wait_exponential_jitter(initial=1, max=30),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    async with PaycomClient() as client:
                        emps = await client.fetch_employees(active_only=True)
                        count = 0
                        for emp in emps:
                            await upsert_employee(conn, company_id, emp)
                            count += 1
                        await log_sync(conn, company_id, "paycom:employees", "success", {"count": count})
                        return
        except Exception as e:  # log failure
            try:
                await conn.rollback()
            except Exception:
                pass
            await log_sync(conn, company_id, "paycom:employees", "failed", {"error": str(e)})


async def sync_time_entries(company_id: int, days: int = 1) -> None:
    start = date.today() - timedelta(days=days)
    end = date.today()

    async with pg_conn() as conn:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(5),
                wait=wait_exponential_jitter(initial=1, max=30),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    async with PaycomClient() as client:
                        # Minimal: we need employee_id mapping; assume upsert_emp was run
                        processed = 0
                        async for tc in client.iter_timecards(start, end):
                            external_id = tc.get("employee_id") or tc.get("employee_external_id")
                            if not external_id:
                                continue
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    "SELECT id FROM employees WHERE company_id=%s AND external_id=%s",
                                    (company_id, external_id),
                                )
                                row = await cur.fetchone()
                                if not row:
                                    # ensure employee exists
                                    await log_sync(conn, company_id, "paycom:timecards", "partial", {"missing_employee_external_id": external_id})
                                    continue
                                emp_id = int(row[0])

                            worked = int(tc.get("worked_minutes") or round(float(tc.get("hours_worked", 0)) * 60))
                            regular = int(tc.get("regular_minutes") or round(float(tc.get("hours_worked", 0)) * 60))
                            ot1 = int(tc.get("ot1_minutes") or round(float(tc.get("overtime_hours", 0)) * 60))
                            ot2 = int(tc.get("ot2_minutes") or 0)
                            scheduled = tc.get("scheduled_minutes")
                            absence_code = tc.get("absence_code")
                            absence_minutes = tc.get("absence_minutes")
                            wdate = tc.get("work_date")
                            if isinstance(wdate, str):
                                wdate = date.fromisoformat(wdate)

                            await upsert_time_entry(
                                conn,
                                company_id,
                                emp_id,
                                wdate,
                                worked,
                                regular,
                                ot1,
                                ot2,
                                scheduled,
                                absence_code,
                                absence_minutes,
                            )
                            processed += 1

                        await log_sync(conn, company_id, "paycom:timecards", "success", {"processed": processed})
                        return
        except Exception as e:
            try:
                await conn.rollback()
            except Exception:
                pass
            await log_sync(conn, company_id, "paycom:timecards", "failed", {"error": str(e)})


def main() -> None:
    company_id = int(os.getenv("COMPANY_ID", "1"))
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Daily at 02:15 UTC: employees
    scheduler.add_job(lambda: asyncio.create_task(sync_employees(company_id)), CronTrigger(hour=2, minute=15))
    # Daily at 02:30 UTC: time entries (yesterday)
    scheduler.add_job(lambda: asyncio.create_task(sync_time_entries(company_id, days=2)), CronTrigger(hour=2, minute=30))

    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()


