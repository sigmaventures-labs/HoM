from __future__ import annotations

from datetime import date, timedelta

import psycopg

from backend.app.metrics.engine import MetricsEngine


def _ensure_company(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies LIMIT 1")
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT INTO companies (name) VALUES ('TestCo') RETURNING id")
        (cid,) = cur.fetchone()
        conn.commit()
        return cid


def _insert_employee(conn: psycopg.Connection, company_id: int, external_id: str, hire: date, term: date | None = None) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO employees (company_id, external_id, first_name, last_name, hire_date, termination_date, employment_status)
            VALUES (%s,%s,'T','User',%s,%s,'active')
            RETURNING id
            """,
            (company_id, external_id, hire, term),
        )
        (emp_id,) = cur.fetchone()
    conn.commit()
    return emp_id


def _insert_time_entry(
    conn: psycopg.Connection,
    company_id: int,
    employee_id: int,
    work_date: date,
    scheduled: int | None,
    regular: int,
    ot1: int,
    ot2: int,
    absence_minutes: int | None,
) -> None:
    worked = regular + ot1 + ot2
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO time_entries (
              company_id, employee_id, work_date,
              scheduled_minutes, worked_minutes, regular_minutes, ot1_minutes, ot2_minutes,
              absence_minutes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (company_id, employee_id, work_date) DO UPDATE SET
              scheduled_minutes=EXCLUDED.scheduled_minutes,
              worked_minutes=EXCLUDED.worked_minutes,
              regular_minutes=EXCLUDED.regular_minutes,
              ot1_minutes=EXCLUDED.ot1_minutes,
              ot2_minutes=EXCLUDED.ot2_minutes,
              absence_minutes=EXCLUDED.absence_minutes
            """,
            (company_id, employee_id, work_date, scheduled, worked, regular, ot1, ot2, absence_minutes),
        )
    conn.commit()


def test_headcount_basic(db_conn: psycopg.Connection) -> None:
    company_id = _ensure_company(db_conn)
    today = date.today()
    e1 = _insert_employee(db_conn, company_id, "E1", today - timedelta(days=10))
    e2 = _insert_employee(db_conn, company_id, "E2", today - timedelta(days=20), term=today + timedelta(days=5))
    e3 = _insert_employee(db_conn, company_id, "E3", today + timedelta(days=1))  # future hire

    hc_today = MetricsEngine.headcount(db_conn, company_id, today)
    assert hc_today == 2.0

    hc_yesterday = MetricsEngine.headcount(db_conn, company_id, today - timedelta(days=1))
    assert hc_yesterday == 2.0


def test_absenteeism_rate_basic(db_conn: psycopg.Connection) -> None:
    company_id = _ensure_company(db_conn)
    today = date.today()
    emp = _insert_employee(db_conn, company_id, "E10", today - timedelta(days=30))
    # 5 working days period: 4 full days scheduled 480min each, 1 day scheduled 480 with 60 absence
    start = today - timedelta(days=6)
    end = today
    for d in range(5):
        w = end - timedelta(days=d)
        _insert_time_entry(db_conn, company_id, emp, w, 480, 480, 0, 0, 0)
    # introduce absence on one day: 60 minutes
    _insert_time_entry(db_conn, company_id, emp, end - timedelta(days=2), 480, 420, 0, 0, 60)

    val = MetricsEngine.absenteeism_rate(db_conn, company_id, start, end)
    # total scheduled: 6 days considered? Our inserts cover only 5 days, one day untouched contributes 0
    # scheduled = 5*480 = 2400; absence = 60 -> 60/2400 = 0.025
    assert val is not None
    assert abs(val - 0.025) < 1e-6


def test_absenteeism_rate_denominator_zero_returns_none(db_conn: psycopg.Connection) -> None:
    company_id = _ensure_company(db_conn)
    today = date.today()
    emp = _insert_employee(db_conn, company_id, "E11", today - timedelta(days=30))
    # Insert a day with scheduled null or zero → excluded; denominator remains 0 → None
    _insert_time_entry(db_conn, company_id, emp, today - timedelta(days=1), None, 0, 0, 0, None)
    v = MetricsEngine.absenteeism_rate(db_conn, company_id, today - timedelta(days=7), today)
    assert v is None


def test_overtime_rate_basic(db_conn: psycopg.Connection) -> None:
    company_id = _ensure_company(db_conn)
    today = date.today()
    emp = _insert_employee(db_conn, company_id, "E20", today - timedelta(days=30))
    start = today - timedelta(days=6)
    end = today
    # 4 days worked 480 regular, 1 day with 60 OT1 (total 5 days)
    for d in range(5):
        w = end - timedelta(days=d)
        _insert_time_entry(db_conn, company_id, emp, w, 480, 480, 0, 0, 0)
    _insert_time_entry(db_conn, company_id, emp, end - timedelta(days=2), 480, 420, 60, 0, 0)

    v = MetricsEngine.overtime_rate(db_conn, company_id, start, end)
    # worked = 4*480 + (420+60) = 1920 + 480 = 2400; ot = 60 -> 60/2400 = 0.025
    assert v is not None
    assert abs(v - (60 / 2400)) < 1e-6


def test_overtime_rate_denominator_zero_returns_none(db_conn: psycopg.Connection) -> None:
    company_id = _ensure_company(db_conn)
    today = date.today()
    emp = _insert_employee(db_conn, company_id, "E21", today - timedelta(days=30))
    # worked 0 in range
    _insert_time_entry(db_conn, company_id, emp, today - timedelta(days=1), 0, 0, 0, 0, 0)
    v = MetricsEngine.overtime_rate(db_conn, company_id, today - timedelta(days=7), today)
    assert v is None


def test_turnover_rate_monthly_style(db_conn: psycopg.Connection) -> None:
    company_id = _ensure_company(db_conn)
    # Create employees with terms within month
    # Choose last month period
    today = date.today()
    start = today.replace(day=1)
    prev_month_end = start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    # Avg HC: 10 employees all month → 10
    employees = []
    for i in range(10):
        emp_id = _insert_employee(db_conn, company_id, f"T{i}", prev_month_start)
        employees.append(emp_id)

    # 2 terms within last month
    with db_conn.cursor() as cur:
        cur.execute("UPDATE employees SET termination_date = %s WHERE id IN (%s,%s)", (prev_month_start + timedelta(days=10), employees[0], employees[1]))
    db_conn.commit()

    v = MetricsEngine.turnover_rate(db_conn, company_id, prev_month_start, prev_month_end)
    # terms = 2; avg HC ≈ 10 (both termed after 10th still count most days). Our formula counts exact daily HC.
    assert v is not None
    assert 0.15 <= v <= 0.25  # loose band around 0.2


