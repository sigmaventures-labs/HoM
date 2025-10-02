from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Literal, Dict, Any, List

import psycopg
from fastapi import APIRouter, Query, Path, HTTPException

from backend.app.config.env import load_env, get_db_url
from backend.app.metrics.engine import (
    headcount_with_status,
    absenteeism_rate_with_status,
    overtime_rate_with_status,
    turnover_rate_with_status,
    MetricPoint,
)
from backend.app.metrics.definitions import get_definitions, MetricDefinition
from backend.app.metrics.engine import MetricsEngine
from pydantic import BaseModel


router = APIRouter()

load_env()
DB_URL = get_db_url()


def _conn() -> psycopg.Connection:
    return psycopg.connect(DB_URL)


@router.get("/definitions", response_model=list[MetricDefinition])
def list_metric_definitions() -> list[MetricDefinition]:
    return get_definitions()


@router.get("/current", response_model=list[MetricPoint])
def current_metrics(company_id: int = Query(1)) -> list[MetricPoint]:
    today = date.today()
    week_start = today - timedelta(days=6)
    with _conn() as conn:
        return [
            headcount_with_status(conn, company_id, today),
            absenteeism_rate_with_status(conn, company_id, week_start, today),
            overtime_rate_with_status(conn, company_id, week_start, today),
            turnover_rate_with_status(conn, company_id, week_start, today),
        ]


@router.get("/trend", response_model=list[MetricPoint])
def metric_trend(
    metric_key: str,
    weeks: int = Query(12, ge=1, le=52),
    company_id: int = Query(1),
) -> list[MetricPoint]:
    """Back-compat weekly trend endpoint with safe cadence rules.

    Rules:
    - headcount: last N full weeks, value = end-of-week headcount (no averaging)
    - absenteeism_rate, overtime_rate: last N full weeks, recomputed from raw data per week
    - turnover_rate: last N full months (reject implicit weekly upsampling); compute per-month

    Note: "weeks" controls number of points returned; for turnover this maps to months.
    """
    today = date.today()
    points: list[MetricPoint] = []
    with _conn() as conn:
        if metric_key == "turnover_rate":
            # Use months instead of weeks to avoid unsupported upsampling
            num_months = weeks
            first_of_this_month = today.replace(day=1)
            month_cursor = first_of_this_month
            months: list[tuple[date, date]] = []
            for _ in range(num_months):
                # step back one full month each iteration
                if month_cursor.month == 1:
                    month_cursor = month_cursor.replace(year=month_cursor.year - 1, month=12)
                else:
                    month_cursor = month_cursor.replace(month=month_cursor.month - 1)
                start_m, end_m = _month_bounds(month_cursor)
                months.append((start_m, end_m))
            months.reverse()
            for start_m, end_m in months:
                points.append(turnover_rate_with_status(conn, company_id, start_m, end_m))
            return points

        # Default: align to last full weeks ending Sunday
        _, last_end = _week_bounds_ending(today)
        week_cursor_end = last_end
        weeks_list: list[tuple[date, date]] = []
        for _ in range(weeks):
            start_w = week_cursor_end - timedelta(days=6)
            weeks_list.append((start_w, week_cursor_end))
            week_cursor_end = start_w - timedelta(days=1)
        weeks_list.reverse()

        for start_w, end_w in weeks_list:
            if metric_key == "headcount":
                points.append(headcount_with_status(conn, company_id, end_w))
            elif metric_key == "absenteeism_rate":
                points.append(absenteeism_rate_with_status(conn, company_id, start_w, end_w))
            elif metric_key == "overtime_rate":
                points.append(overtime_rate_with_status(conn, company_id, start_w, end_w))
            elif metric_key == "turnover_rate":
                # Shouldn't reach here due to early return; keep for safety
                start_m, end_m = _month_bounds(end_w)
                points.append(turnover_rate_with_status(conn, company_id, start_m, end_m))
        return points


# -------- Metric-native trend endpoint with enriched buckets --------

class BucketStatus(str):
    ok = "ok"
    na = "na"
    partial = "partial"
    error = "error"


class TrendBucket(BaseModel):
    metric_key: str
    bucket_start: date
    bucket_end: date
    value: Optional[float] = None
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    status: Literal["ok", "na", "partial", "error"]
    meta: Optional[Dict[str, Any]] = None


def _month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    # next month start
    if start.month == 12:
        next_start = start.replace(year=start.year + 1, month=1)
    else:
        next_start = start.replace(month=start.month + 1)
    end = next_start - timedelta(days=1)
    return start, end


def _week_bounds_ending(d: date) -> tuple[date, date]:
    # Define weeks as Monday..Sunday; bucket ends on Sunday
    offset = (d.weekday() - 6) % 7  # days since last Sunday
    end = d - timedelta(days=offset)
    start = end - timedelta(days=6)
    return start, end


def _daterange_days(start: date, end: date) -> int:
    return (end - start).days + 1


def _is_partial_bucket(start: date, end: date, today: date) -> bool:
    return end > today


def _compute_abs_bucket(conn: psycopg.Connection, company_id: int, start: date, end: date) -> tuple[Optional[float], float, float]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(absence_minutes),0) AS absent,
                   COALESCE(SUM(scheduled_minutes),0) AS scheduled
            FROM time_entries
            WHERE company_id = %s AND work_date BETWEEN %s AND %s
              AND scheduled_minutes IS NOT NULL AND scheduled_minutes > 0
            """,
            (company_id, start, end),
        )
        row = cur.fetchone()
        absent = float(row[0] or 0)
        scheduled = float(row[1] or 0)
        if scheduled <= 0:
            return None, absent, scheduled
        return absent / scheduled, absent, scheduled


def _compute_ot_bucket(conn: psycopg.Connection, company_id: int, start: date, end: date) -> tuple[Optional[float], float, float]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(ot1_minutes + ot2_minutes),0) AS ot,
                   COALESCE(SUM(worked_minutes),0) AS worked
            FROM time_entries
            WHERE company_id = %s AND work_date BETWEEN %s AND %s
            """,
            (company_id, start, end),
        )
        row = cur.fetchone()
        ot = float(row[0] or 0)
        worked = float(row[1] or 0)
        if worked <= 0:
            return None, ot, worked
        return ot / worked, ot, worked


def _compute_turnover_bucket(conn: psycopg.Connection, company_id: int, start: date, end: date) -> tuple[Optional[float], float, float]:
    # numerator: terms by termination_date in month
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM employees emp
            WHERE emp.company_id = %s
              AND emp.termination_date BETWEEN %s AND %s
            """,
            (company_id, start, end),
        )
        (terms,) = cur.fetchone()
    # denominator: average daily HC over month
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH days AS (
              SELECT generate_series(%s::date, %s::date, '1 day') AS d
            ), daily AS (
              SELECT d.d AS day,
                     (
                       SELECT COUNT(*)
                       FROM employees e
                       WHERE e.company_id = %s
                         AND e.is_deleted = FALSE
                         AND e.hire_date <= d.d
                         AND (e.termination_date IS NULL OR e.termination_date > d.d)
                     ) AS hc
              FROM days d
            )
            SELECT AVG(hc)::float
            FROM daily
            """,
            (start, end, company_id),
        )
        row = cur.fetchone()
        avg_hc = float(row[0] or 0)
    if avg_hc <= 0:
        return None, float(terms or 0), avg_hc
    return float(terms or 0) / avg_hc, float(terms or 0), avg_hc


@router.get("/{metric}/trend", response_model=list[TrendBucket])
def metric_trend_native(
    metric: Literal["headcount", "absenteeism_rate", "overtime_rate", "turnover_rate"] = Path(...),
    cadence: Literal["auto", "day", "week", "month"] = Query("auto"),
    company_id: int = Query(1),
    include_partial: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=365),
) -> list[TrendBucket]:
    today = date.today()
    buckets: List[TrendBucket] = []

    def add_bucket(metric_key: str, start: date, end: date, value: Optional[float], num: Optional[float], den: Optional[float], partial: bool):
        status: Literal["ok", "na", "partial", "error"]
        if den is not None and den <= 0:
            status = "na"
            v = None
        else:
            v = value
            status = "partial" if partial else ("ok" if v is not None else "na")
        days_expected = _daterange_days(start, end)
        days_with_data = min(days_expected, _daterange_days(start, min(end, today))) if partial else days_expected
        coverage = days_with_data / days_expected if days_expected > 0 else 0.0
        buckets.append(
            TrendBucket(
                metric_key=metric_key,
                bucket_start=start,
                bucket_end=end,
                value=v,
                numerator=num,
                denominator=den,
                status=status,
                meta={
                    "days_expected": days_expected,
                    "days_with_data": days_with_data,
                    "coverage_pct": coverage,
                    "notes": ("partial period" if partial else "last full period"),
                },
            )
        )

    with _conn() as conn:
        if metric == "turnover_rate":
            # Only monthly is supported
            if cadence in ("day", "week"):
                raise HTTPException(status_code=400, detail="Turnover supports only month cadence.")
            # default: last 12 full months (exclude current partial unless include_partial)
            cadence = "month"
            num_months = limit or 12
            # Determine last full month end
            first_of_this_month = today.replace(day=1)
            month_cursor = first_of_this_month
            months = []
            # collect previous full months
            for _ in range(num_months):
                # move back one month
                if month_cursor.month == 1:
                    month_cursor = month_cursor.replace(year=month_cursor.year - 1, month=12)
                else:
                    month_cursor = month_cursor.replace(month=month_cursor.month - 1)
                start_m, end_m = _month_bounds(month_cursor)
                months.append((start_m, end_m, False))
            months.reverse()
            # Optionally include partial current month as MTD
            if include_partial:
                start_m, end_m = _month_bounds(today)
                months.append((start_m, end_m, True))
            for start_m, end_m, is_partial in months:
                val, num, den = _compute_turnover_bucket(conn, company_id, start_m, end_m)
                add_bucket("turnover_rate", start_m, end_m, val, num, den, is_partial)

        elif metric in ("absenteeism_rate", "overtime_rate"):
            # default: last 13 weeks rolling; allow day or month
            if cadence == "auto":
                cadence = "week"
            if cadence not in ("day", "week", "month"):
                raise HTTPException(status_code=400, detail="Unsupported cadence for this metric.")
            if cadence == "week":
                num_weeks = limit or 13
                # last full week ending last Sunday
                _, last_end = _week_bounds_ending(today)
                week_cursor_end = last_end
                weeks = []
                for _ in range(num_weeks):
                    start_w = week_cursor_end - timedelta(days=6)
                    weeks.append((start_w, week_cursor_end, False))
                    week_cursor_end = start_w - timedelta(days=1)
                weeks.reverse()
                if include_partial:
                    start_p, end_p = _week_bounds_ending(today)
                    if end_p > weeks[-1][1]:
                        weeks.append((start_p, end_p, True))
                for start_w, end_w, is_partial in weeks:
                    if metric == "absenteeism_rate":
                        val, num, den = _compute_abs_bucket(conn, company_id, start_w, end_w)
                    else:
                        val, num, den = _compute_ot_bucket(conn, company_id, start_w, end_w)
                    add_bucket(metric, start_w, end_w, val, num, den, is_partial)
            elif cadence == "day":
                num_days = limit or 90
                start_d = today - timedelta(days=num_days - 1)
                for offset in range(num_days):
                    d = start_d + timedelta(days=offset)
                    if metric == "absenteeism_rate":
                        val, num, den = _compute_abs_bucket(conn, company_id, d, d)
                    else:
                        val, num, den = _compute_ot_bucket(conn, company_id, d, d)
                    partial = _is_partial_bucket(d, d, today) and include_partial
                    add_bucket(metric, d, d, val, num, den, partial)
            else:  # month
                num_months = limit or 12
                # last full months
                first_of_this_month = today.replace(day=1)
                month_cursor = first_of_this_month
                months = []
                for _ in range(num_months):
                    if month_cursor.month == 1:
                        month_cursor = month_cursor.replace(year=month_cursor.year - 1, month=12)
                    else:
                        month_cursor = month_cursor.replace(month=month_cursor.month - 1)
                    start_m, end_m = _month_bounds(month_cursor)
                    months.append((start_m, end_m, False))
                months.reverse()
                if include_partial:
                    start_m, end_m = _month_bounds(today)
                    months.append((start_m, end_m, True))
                for start_m, end_m, is_partial in months:
                    if metric == "absenteeism_rate":
                        val, num, den = _compute_abs_bucket(conn, company_id, start_m, end_m)
                    else:
                        val, num, den = _compute_ot_bucket(conn, company_id, start_m, end_m)
                    add_bucket(metric, start_m, end_m, val, num, den, is_partial)

        elif metric == "headcount":
            # default: last 90 days daily; allow week cadence returning end-of-week HC
            if cadence == "auto":
                cadence = "day"
            if cadence not in ("day", "week"):
                raise HTTPException(status_code=400, detail="Headcount supports day or week cadence.")
            if cadence == "day":
                num_days = limit or 90
                start_d = today - timedelta(days=num_days - 1)
                for offset in range(num_days):
                    d = start_d + timedelta(days=offset)
                    v = MetricsEngine.headcount(conn, company_id, d)
                    add_bucket("headcount", d, d, v, v, None, False)
            else:
                num_weeks = limit or 13
                _, last_end = _week_bounds_ending(today)
                week_cursor_end = last_end
                weeks = []
                for _ in range(num_weeks):
                    start_w = week_cursor_end - timedelta(days=6)
                    v = MetricsEngine.headcount(conn, company_id, week_cursor_end)
                    add_bucket("headcount", start_w, week_cursor_end, v, v, None, False)
                    week_cursor_end = start_w - timedelta(days=1)
                buckets.sort(key=lambda b: b.bucket_start)

    return buckets


# -------- Headcount breakdown (Direct vs Indirect) --------

@router.get("/headcount/breakdown", response_model=dict[str, float])
def headcount_breakdown(
    company_id: int = Query(1),
    as_of: Optional[date] = None,
) -> dict[str, float]:
    """Return headcount breakdown for Direct vs Indirect as-of date.

    Uses `employees.labor_type` when available; otherwise maps departments:
    'Operations' -> direct; others -> indirect.
    """
    if as_of is None:
        as_of = date.today()
    buckets: Dict[str, float] = {"Direct Labor": 0.0, "Indirect Labor": 0.0}
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT CASE
                     WHEN labor_type IS NOT NULL THEN labor_type::text
                     WHEN department ILIKE 'Operations' THEN 'direct'
                     ELSE 'indirect'
                   END AS bucket,
                   COUNT(*)::float AS cnt
            FROM employees
            WHERE company_id = %s
              AND is_deleted = FALSE
              AND hire_date <= %s::date
              AND (termination_date IS NULL OR termination_date > %s::date)
            GROUP BY 1
            """,
            (company_id, as_of, as_of),
        )
        for bucket, cnt in cur.fetchall():
            if bucket == "direct":
                buckets["Direct Labor"] += float(cnt or 0)
            else:
                buckets["Indirect Labor"] += float(cnt or 0)
    return buckets
