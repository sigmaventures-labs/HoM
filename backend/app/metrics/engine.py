from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional, Dict, Any

import psycopg
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class MetricValue:
    metric_key: str
    value: float
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class MetricsEngine:
    """Computes core HR metrics against the Postgres schema.

    Metrics (MVP): headcount, absenteeism_rate, turnover_rate, overtime_rate
    """

    @staticmethod
    def headcount(conn: psycopg.Connection, company_id: int, as_of: date) -> float:
        """Headcount as-of D using hire/termination dates per implementation guide."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM employees emp
                WHERE emp.company_id = %s
                  AND emp.is_deleted = FALSE
                  AND emp.hire_date <= %s::date
                  AND (emp.termination_date IS NULL OR emp.termination_date > %s::date)
                """,
                (company_id, as_of, as_of),
            )
            (count,) = cur.fetchone()
            return float(count or 0)

    @staticmethod
    def absenteeism_rate(
        conn: psycopg.Connection, company_id: int, start: date, end: date
    ) -> Optional[float]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(absence_minutes),0) AS absent,
                       COALESCE(SUM(scheduled_minutes),0) AS scheduled
                FROM time_entries
                WHERE company_id = %s
                  AND work_date BETWEEN %s AND %s
                  AND scheduled_minutes IS NOT NULL AND scheduled_minutes > 0
                """,
                (company_id, start, end),
            )
            row = cur.fetchone()
            absent = float(row[0] or 0)
            scheduled = float(row[1] or 0)
            if scheduled <= 0:
                return None
            return absent / scheduled

    @staticmethod
    def overtime_rate(
        conn: psycopg.Connection, company_id: int, start: date, end: date
    ) -> Optional[float]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(ot1_minutes + ot2_minutes),0) AS ot,
                       COALESCE(SUM(worked_minutes),0) AS worked
                FROM time_entries
                WHERE company_id = %s
                  AND work_date BETWEEN %s AND %s
                """,
                (company_id, start, end),
            )
            row = cur.fetchone()
            ot = float(row[0] or 0)
            worked = float(row[1] or 0)
            if worked <= 0:
                return None
            return ot / worked

    @staticmethod
    def turnover_rate(
        conn: psycopg.Connection, company_id: int, start: date, end: date
    ) -> Optional[float]:
        """Turnover over a period using monthly-style definition: terms / average daily HC.

        Numerator: count employees whose termination_date falls within the period.
        Denominator: average daily headcount computed from hire/termination dates.
        """
        # Count terms using employees.termination_date
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

        # Average daily headcount across the period (inclusive)
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
            return None
        return float(terms or 0) / avg_hc

    @staticmethod
    def write_metrics_history(
        conn: psycopg.Connection,
        company_id: int,
        metric_key: str,
        value: Optional[float],
        period_start: date,
        period_end: date,
    ) -> None:
        # Skip writing if value is None; history table requires non-null value
        if value is None:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metrics_history (company_id, metric_key, period_start, period_end, value)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (company_id, metric_key, period_start, period_end)
                DO UPDATE SET value = EXCLUDED.value, created_at = now()
                """,
                (company_id, metric_key, period_start, period_end, float(value)),
            )
            conn.commit()


# ---------- Status mapping using metric_configs ----------

class MetricStatusEnum(str, Enum):
    red = "red"
    yellow = "yellow"
    green = "green"


class MetricPoint(BaseModel):
    key: str = Field(alias="metric_key")
    value: Optional[float]
    status: Optional[MetricStatusEnum] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    target_value: Optional[float] = None
    thresholds: Optional[Dict[str, float]] = None  # expects keys: red,yellow,green


# Orientation: whether lower values are better or higher values are better
METRIC_ORIENTATION: Dict[str, str] = {
    "absenteeism_rate": "lower",
    "overtime_rate": "lower",
    "turnover_rate": "lower",
    "headcount": "higher",
}


def _fetch_metric_config(
    conn: psycopg.Connection,
    company_id: int,
    metric_key: str,
    as_of: date,
    scope: Optional[Dict[str, Any]] = None,
) -> tuple[Optional[float], Optional[Dict[str, float]]]:
    """Return (target_value, thresholds) for a metric as of a date.

    MVP: uses company-level defaults (scope omitted). Add scoped matching later.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT target_value, thresholds
            FROM metric_configs
            WHERE company_id = %s
              AND metric_key = %s
              AND effective_range @> %s::date
            ORDER BY effective_from DESC
            LIMIT 1
            """,
            (company_id, metric_key, as_of),
        )
        row = cur.fetchone()
        if not row:
            return None, None
        tgt, thr = row
        # psycopg returns dict for jsonb automatically
        return (float(tgt) if tgt is not None else None, thr or None)


def _map_value_to_status(
    metric_key: str,
    value: Optional[float],
    thresholds: Optional[Dict[str, float]],
) -> Optional[MetricStatusEnum]:
    if value is None or not thresholds:
        return None
    orientation = METRIC_ORIENTATION.get(metric_key, "lower")
    red = float(thresholds.get("red")) if thresholds.get("red") is not None else None
    yellow = float(thresholds.get("yellow")) if thresholds.get("yellow") is not None else None
    green = float(thresholds.get("green")) if thresholds.get("green") is not None else None

    # Expect monotonic thresholds according to orientation
    try:
        if orientation == "lower":
            # e.g., absenteeism: green <= green_thr, yellow <= yellow_thr, else red
            if green is not None and value <= green:
                return MetricStatusEnum.green
            if yellow is not None and value <= yellow:
                return MetricStatusEnum.yellow
            return MetricStatusEnum.red
        else:  # higher is better
            # interpret thresholds as minimums
            if green is not None and value >= green:
                return MetricStatusEnum.green
            if yellow is not None and value >= yellow:
                return MetricStatusEnum.yellow
            return MetricStatusEnum.red
    except Exception:
        return None


def metric_with_status(
    conn: psycopg.Connection,
    company_id: int,
    metric_key: str,
    value: Optional[float],
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    scope: Optional[Dict[str, Any]] = None,
) -> MetricPoint:
    as_of = period_end or period_start or date.today()
    target_value, thresholds = _fetch_metric_config(conn, company_id, metric_key, as_of, scope)
    status = _map_value_to_status(metric_key, value if value is not None else None, thresholds)
    return MetricPoint(metric_key=metric_key, value=value if value is not None else None, status=status, period_start=period_start, period_end=period_end, target_value=target_value, thresholds=thresholds)


# Convenience wrappers that compute the metric and attach status
def headcount_with_status(conn: psycopg.Connection, company_id: int, as_of: date) -> MetricPoint:
    v = MetricsEngine.headcount(conn, company_id, as_of)
    return metric_with_status(conn, company_id, "headcount", v, period_start=as_of, period_end=as_of)


def absenteeism_rate_with_status(
    conn: psycopg.Connection, company_id: int, start: date, end: date
) -> MetricPoint:
    v = MetricsEngine.absenteeism_rate(conn, company_id, start, end)
    return metric_with_status(conn, company_id, "absenteeism_rate", v, period_start=start, period_end=end)


def overtime_rate_with_status(
    conn: psycopg.Connection, company_id: int, start: date, end: date
) -> MetricPoint:
    v = MetricsEngine.overtime_rate(conn, company_id, start, end)
    return metric_with_status(conn, company_id, "overtime_rate", v, period_start=start, period_end=end)


def turnover_rate_with_status(
    conn: psycopg.Connection, company_id: int, start: date, end: date
) -> MetricPoint:
    v = MetricsEngine.turnover_rate(conn, company_id, start, end)
    return metric_with_status(conn, company_id, "turnover_rate", v, period_start=start, period_end=end)


