-- Schema: initial HR metrics data model
-- Tables: employees, timecards, events, metrics_history

BEGIN;

CREATE TABLE IF NOT EXISTS employees (
  id SERIAL PRIMARY KEY,
  external_id TEXT UNIQUE NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT,
  department TEXT,
  location TEXT,
  title TEXT,
  hire_date DATE NOT NULL,
  termination_date DATE,
  employment_status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS timecards (
  id SERIAL PRIMARY KEY,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  work_date DATE NOT NULL,
  hours_worked NUMERIC(6,2) NOT NULL DEFAULT 0,
  overtime_hours NUMERIC(6,2) NOT NULL DEFAULT 0,
  absence_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timecards_emp_date ON timecards(employee_id, work_date);

CREATE TABLE IF NOT EXISTS events (
  id SERIAL PRIMARY KEY,
  employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL, -- hire, term, leave, promo, transfer
  event_date DATE NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_type_date ON events(event_type, event_date);

CREATE TABLE IF NOT EXISTS metrics_history (
  id SERIAL PRIMARY KEY,
  metric_key TEXT NOT NULL, -- headcount, absenteeism_rate, turnover_rate, overtime
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  value NUMERIC(10,4) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_metrics_history_key_period ON metrics_history(metric_key, period_start, period_end);

COMMIT;


