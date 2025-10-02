from __future__ import annotations

import os
from datetime import date, timedelta
from random import Random

import psycopg


from backend.app.config.env import load_env, get_db_url

load_env()
DB_URL = get_db_url()


def seed() -> None:
    rng = Random(42)
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        # company id 1 exists from migration
        company_id = 1

        # Departments
        cur.execute(
            """
            INSERT INTO departments (company_id, name)
            VALUES (%s, 'Operations'), (%s, 'HR'), (%s, 'Sales')
            ON CONFLICT (company_id, name) DO NOTHING
            RETURNING id, name
            """,
            (company_id, company_id, company_id),
        )
        conn.commit()

        # Employees
        employees = [
            ("E1001", "Alice", "Nguyen", "alice@example.com", "Operations"),
            ("E1002", "Bob", "Lee", "bob@example.com", "Operations"),
            ("E1003", "Cara", "Kim", "cara@example.com", "Sales"),
            ("E1004", "Dan", "Singh", "dan@example.com", "HR"),
        ]
        for ext, first, last, email, dept in employees:
            cur.execute(
                """
                INSERT INTO employees (company_id, external_id, first_name, last_name, email, department, hire_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (company_id, external_id) DO UPDATE SET first_name=EXCLUDED.first_name,
                                                                   last_name=EXCLUDED.last_name,
                                                                   email=EXCLUDED.email,
                                                                   department=EXCLUDED.department,
                                                                   hire_date=EXCLUDED.hire_date
                RETURNING id
                """,
                (company_id, ext, first, last, email, dept, date.today() - timedelta(days=365)),
            )
        conn.commit()

        # Assignment history (current)
        cur.execute("SELECT id, external_id FROM employees WHERE company_id=%s", (company_id,))
        emp_rows = cur.fetchall()
        for emp_id, external in emp_rows:
            cur.execute(
                """
                INSERT INTO employee_assignment_history (company_id, employee_id, effective_start)
                VALUES (%s,%s,%s)
                ON CONFLICT DO NOTHING
                """,
                (company_id, emp_id, date.today() - timedelta(days=90)),
            )
        conn.commit()

        # Time entries for last 30 days
        for d in range(30, 0, -1):
            wdate = date.today() - timedelta(days=d)
            for emp_id, _ in emp_rows:
                scheduled = 8 * 60
                ot1 = 0 if rng.random() < 0.7 else 60
                ot2 = 0
                absence = 0 if rng.random() < 0.9 else 60
                # Regular is scheduled minus absence; worked equals regular + OT tiers
                regular = max(0, scheduled - absence)
                worked = regular + ot1 + ot2
                cur.execute(
                    """
                    INSERT INTO time_entries (
                      company_id, employee_id, work_date,
                      worked_minutes, regular_minutes, ot1_minutes, ot2_minutes,
                      scheduled_minutes, absence_minutes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (company_id, employee_id, work_date) DO UPDATE SET
                      worked_minutes=EXCLUDED.worked_minutes,
                      regular_minutes=EXCLUDED.regular_minutes,
                      ot1_minutes=EXCLUDED.ot1_minutes,
                      ot2_minutes=EXCLUDED.ot2_minutes,
                      scheduled_minutes=EXCLUDED.scheduled_minutes,
                      absence_minutes=EXCLUDED.absence_minutes
                    """,
                    (company_id, emp_id, wdate, worked, regular, ot1, ot2, scheduled, absence),
                )
        conn.commit()

        # Metric configs
        cur.execute(
            """
            INSERT INTO metric_configs (company_id, metric_key, target_value, thresholds, effective_from)
            VALUES
              (%s,'absenteeism_rate',0.03,'{"red":0.08,"yellow":0.05,"green":0.03}'::jsonb, CURRENT_DATE),
              (%s,'overtime_rate',0.10,'{"red":0.20,"yellow":0.12,"green":0.08}'::jsonb, CURRENT_DATE),
              (%s,'headcount',15,'{"red":8,"yellow":12,"green":15}'::jsonb, CURRENT_DATE),
              (%s,'turnover_rate',0.12,'{"red":0.25,"yellow":0.15,"green":0.12}'::jsonb, CURRENT_DATE)
            ON CONFLICT DO NOTHING
            """,
            (company_id, company_id, company_id, company_id),
        )
        conn.commit()

        # Simple metrics_history for the last 4 weeks
        from backend.app.metrics.engine import MetricsEngine

        for w in range(4, 0, -1):
            start = date.today() - timedelta(days=w * 7)
            end = start + timedelta(days=6)
            hc = MetricsEngine.headcount(conn, company_id, end)
            abs_rate = MetricsEngine.absenteeism_rate(conn, company_id, start, end)
            ot_rate = MetricsEngine.overtime_rate(conn, company_id, start, end)
            turn_rate = MetricsEngine.turnover_rate(conn, company_id, start, end)

            MetricsEngine.write_metrics_history(conn, company_id, 'headcount', hc, start, end)
            MetricsEngine.write_metrics_history(conn, company_id, 'absenteeism_rate', abs_rate, start, end)
            MetricsEngine.write_metrics_history(conn, company_id, 'overtime_rate', ot_rate, start, end)
            MetricsEngine.write_metrics_history(conn, company_id, 'turnover_rate', turn_rate, start, end)


if __name__ == "__main__":
    seed()


