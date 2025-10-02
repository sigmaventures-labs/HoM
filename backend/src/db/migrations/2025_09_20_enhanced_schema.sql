-- Enhanced schema migration implementing multi-tenancy, SCD, minute-precision time, configs, AI, actions, and logging
-- Includes: extensions, enums, new tables, alters, constraints, triggers, and indexes

BEGIN;

-- Extensions
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for digest()
CREATE EXTENSION IF NOT EXISTS btree_gist; -- for exclusion constraints on ranges

-- Enums (create if missing)
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employment_status_enum') THEN
  CREATE TYPE employment_status_enum AS ENUM ('active','terminated','leave');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'labor_type_enum') THEN
  CREATE TYPE labor_type_enum AS ENUM ('direct','indirect','contractor');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type_enum') THEN
  CREATE TYPE event_type_enum AS ENUM ('hire','term','leave','promo','transfer','other');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ai_role_enum') THEN
  CREATE TYPE ai_role_enum AS ENUM ('user','assistant','system');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_status_enum') THEN
  CREATE TYPE action_status_enum AS ENUM ('open','in_progress','done','blocked');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_priority_enum') THEN
  CREATE TYPE action_priority_enum AS ENUM ('low','medium','high');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sync_status_enum') THEN
  CREATE TYPE sync_status_enum AS ENUM ('success','partial','failed');
END IF; END $$;

-- Companies (tenant root)
CREATE TABLE IF NOT EXISTS companies (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  external_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ensure a default company for backfilling existing rows
INSERT INTO companies (name)
SELECT 'Default Company'
WHERE NOT EXISTS (SELECT 1 FROM companies);

-- Departments
CREATE TABLE IF NOT EXISTS departments (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  code TEXT,
  name TEXT NOT NULL,
  parent_id INTEGER REFERENCES departments(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_departments_company_name UNIQUE (company_id, name)
);

-- Employees alterations: add company, enums, soft-delete, dept FK, email CITEXT
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'employees' AND column_name = 'company_id'
  ) THEN
    ALTER TABLE employees ADD COLUMN company_id INTEGER;
  END IF;
END $$;

UPDATE employees SET company_id = (SELECT id FROM companies LIMIT 1) WHERE company_id IS NULL;

ALTER TABLE employees ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE employees ADD CONSTRAINT fk_employees_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Email to CITEXT
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='email'
  ) THEN
    ALTER TABLE employees ALTER COLUMN email TYPE CITEXT USING email::citext;
  END IF;
END $$;

-- Department FK and soft delete fields
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='department_id'
  ) THEN
    ALTER TABLE employees ADD COLUMN department_id INTEGER REFERENCES departments(id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='is_deleted'
  ) THEN
    ALTER TABLE employees ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='deleted_at'
  ) THEN
    ALTER TABLE employees ADD COLUMN deleted_at TIMESTAMPTZ;
  END IF;
END $$;

-- employment_status to enum if currently TEXT
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='employees' AND column_name='employment_status'
  ) THEN
    -- drop existing default to allow type cast
    BEGIN
      ALTER TABLE employees ALTER COLUMN employment_status DROP DEFAULT;
    EXCEPTION WHEN others THEN NULL; END;
    BEGIN
      ALTER TABLE employees ALTER COLUMN employment_status TYPE employment_status_enum USING employment_status::employment_status_enum;
    EXCEPTION WHEN others THEN
      -- fallback: set unknowns to 'active'
      UPDATE employees SET employment_status = 'active' WHERE employment_status IS NULL OR employment_status NOT IN ('active','terminated','leave');
      ALTER TABLE employees ALTER COLUMN employment_status TYPE employment_status_enum USING employment_status::employment_status_enum;
    END;
    -- restore a safe default
    BEGIN
      ALTER TABLE employees ALTER COLUMN employment_status SET DEFAULT 'active'::employment_status_enum;
    EXCEPTION WHEN others THEN NULL; END;
  END IF;
END $$;

-- labor_type column
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='labor_type'
  ) THEN
    ALTER TABLE employees ADD COLUMN labor_type labor_type_enum;
  END IF;
END $$;

-- Hire/term date check and created_at default
ALTER TABLE employees ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE employees ADD CONSTRAINT chk_employees_dates CHECK (termination_date IS NULL OR termination_date >= hire_date);

-- Unique external id scoped by company
DO $$ BEGIN
  -- drop old unique if present
  IF EXISTS (
    SELECT 1 FROM pg_indexes WHERE tablename='employees' AND indexname LIKE '%external_id%'
  ) THEN
    -- attempt drop constraint by name if standard
    BEGIN
      ALTER TABLE employees DROP CONSTRAINT IF EXISTS employees_external_id_key;
    EXCEPTION WHEN others THEN NULL; END;
  END IF;
END $$;
ALTER TABLE employees ADD CONSTRAINT uq_employees_company_external UNIQUE (company_id, external_id);

-- Employee Assignment History (SCD) with half-open ranges
CREATE TABLE IF NOT EXISTS employee_assignment_history (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
  department_id INTEGER REFERENCES departments(id),
  location TEXT,
  title TEXT,
  effective_start DATE NOT NULL,
  effective_end DATE,
  effective_range DATERANGE GENERATED ALWAYS AS (
    daterange(effective_start, COALESCE(effective_end, 'infinity'::date), '[)')
  ) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE employee_assignment_history
  ADD CONSTRAINT ex_employee_assignment_no_overlap
  EXCLUDE USING gist (
    company_id WITH =,
    employee_id WITH =,
    effective_range WITH &&
  );

CREATE INDEX IF NOT EXISTS gist_employee_assignment_range ON employee_assignment_history USING gist (effective_range);
CREATE INDEX IF NOT EXISTS idx_employee_assignment_emp_start ON employee_assignment_history (company_id, employee_id, effective_start);
CREATE INDEX IF NOT EXISTS idx_employee_assignment_dept_start ON employee_assignment_history (company_id, department_id, effective_start);

-- Replace timecards with time_entries (if timecards exists, drop it)
DROP TABLE IF EXISTS timecards CASCADE;

CREATE TABLE IF NOT EXISTS time_entries (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
  employee_external_id TEXT,
  work_date DATE NOT NULL,
  scheduled_minutes INTEGER,
  worked_minutes INTEGER NOT NULL DEFAULT 0,
  regular_minutes INTEGER NOT NULL DEFAULT 0,
  ot1_minutes INTEGER NOT NULL DEFAULT 0,
  ot2_minutes INTEGER NOT NULL DEFAULT 0,
  absence_code TEXT,
  absence_category TEXT,
  absence_minutes INTEGER,
  is_paid BOOLEAN,
  labor_type labor_type_enum,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_time_entries_daily UNIQUE (company_id, employee_id, work_date),
  CONSTRAINT chk_minutes_nonneg CHECK (
    worked_minutes >= 0 AND regular_minutes >= 0 AND ot1_minutes >= 0 AND ot2_minutes >= 0
    AND (scheduled_minutes IS NULL OR scheduled_minutes >= 0)
    AND (absence_minutes IS NULL OR absence_minutes >= 0)
  ),
  CONSTRAINT chk_minutes_consistency CHECK (
    worked_minutes = regular_minutes + ot1_minutes + ot2_minutes
  ),
  CONSTRAINT chk_absenteeism_bounds CHECK (
    scheduled_minutes IS NULL OR (absence_minutes IS NOT NULL AND absence_minutes <= scheduled_minutes)
  )
);

CREATE INDEX IF NOT EXISTS idx_time_entries_emp_date ON time_entries (company_id, employee_id, work_date);
CREATE INDEX IF NOT EXISTS idx_time_entries_company_date ON time_entries (company_id, work_date);
CREATE INDEX IF NOT EXISTS idx_time_entries_company_external ON time_entries (company_id, employee_external_id);
-- Optional as table grows
CREATE INDEX IF NOT EXISTS brin_time_entries_company_date ON time_entries USING brin (company_id, work_date);

-- Events: add company_id, external_id copy, enforce RESTRICT, enum type, timestamp
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='company_id'
  ) THEN
    ALTER TABLE events ADD COLUMN company_id INTEGER;
    UPDATE events SET company_id = (SELECT id FROM companies LIMIT 1) WHERE company_id IS NULL;
    ALTER TABLE events ALTER COLUMN company_id SET NOT NULL;
    ALTER TABLE events ADD CONSTRAINT fk_events_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
  END IF;
END $$;

-- event_type enum
ALTER TABLE events ALTER COLUMN event_type TYPE event_type_enum USING event_type::event_type_enum;

-- switch FK behavior to RESTRICT
ALTER TABLE events DROP CONSTRAINT IF EXISTS events_employee_id_fkey;
ALTER TABLE events ADD CONSTRAINT events_employee_fk FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT;

-- employee_external_id copy and created_at default
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='employee_external_id'
  ) THEN
    ALTER TABLE events ADD COLUMN employee_external_id TEXT;
  END IF;
END $$;
ALTER TABLE events ALTER COLUMN created_at SET DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_events_type_date ON events (company_id, event_type, event_date);
CREATE INDEX IF NOT EXISTS idx_events_company_external ON events (company_id, employee_external_id);

-- Metrics history: add company_id, tighten unique, created_at default
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='metrics_history' AND column_name='company_id'
  ) THEN
    ALTER TABLE metrics_history ADD COLUMN company_id INTEGER;
    UPDATE metrics_history SET company_id = (SELECT id FROM companies LIMIT 1) WHERE company_id IS NULL;
    ALTER TABLE metrics_history ALTER COLUMN company_id SET NOT NULL;
    ALTER TABLE metrics_history ADD CONSTRAINT fk_metrics_history_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
  END IF;
END $$;

ALTER TABLE metrics_history ALTER COLUMN created_at SET DEFAULT now();

-- Replace old unique with company-scoped unique
DO $$ BEGIN
  BEGIN
    DROP INDEX IF EXISTS uq_metrics_history_key_period;
  EXCEPTION WHEN others THEN NULL; END;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_metrics_history_company_key_period ON metrics_history (company_id, metric_key, period_start, period_end);

-- metric_configs with half-open range and scope hash
CREATE TABLE IF NOT EXISTS metric_configs (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  target_value NUMERIC(12,4),
  thresholds JSONB NOT NULL,
  scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  scope_canonical JSONB GENERATED ALWAYS AS (jsonb_strip_nulls(scope)) STORED,
  scope_hash BYTEA GENERATED ALWAYS AS (digest(jsonb_strip_nulls(scope)::text, 'sha256')) STORED,
  effective_from DATE NOT NULL,
  effective_to DATE,
  effective_range DATERANGE GENERATED ALWAYS AS (
    daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)')
  ) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE metric_configs
  ADD CONSTRAINT ex_metric_configs_no_overlap
  EXCLUDE USING gist (
    company_id WITH =,
    metric_key WITH =,
    scope_hash WITH =,
    effective_range WITH &&
  );

CREATE INDEX IF NOT EXISTS idx_metric_configs_lookup ON metric_configs (company_id, metric_key, effective_from);

-- AI conversations/messages
CREATE TABLE IF NOT EXISTS ai_conversations (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  metric_key TEXT,
  initiator CITEXT,
  initial_context JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_messages (
  id SERIAL PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
  role ai_role_enum NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_messages_convo_created ON ai_messages (conversation_id, created_at);

-- Actions and status history
CREATE TABLE IF NOT EXISTS actions (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE SET NULL,
  metric_key TEXT,
  title TEXT NOT NULL,
  description TEXT,
  priority action_priority_enum,
  status action_status_enum NOT NULL DEFAULT 'open',
  impact_score NUMERIC(4,2),
  effort_score NUMERIC(4,2),
  first_step TEXT,
  checklist JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_by CITEXT,
  assignee CITEXT,
  due_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_actions_closed_after_created CHECK (closed_at IS NULL OR closed_at >= created_at)
);

CREATE INDEX IF NOT EXISTS idx_actions_status ON actions (company_id, status);
CREATE INDEX IF NOT EXISTS idx_actions_metric ON actions (company_id, metric_key);
CREATE INDEX IF NOT EXISTS idx_actions_priority ON actions (company_id, priority);

CREATE TABLE IF NOT EXISTS action_status_history (
  id SERIAL PRIMARY KEY,
  action_id INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  old_status action_status_enum,
  new_status action_status_enum NOT NULL,
  changed_by CITEXT,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  note TEXT
);

CREATE INDEX IF NOT EXISTS idx_action_status_history ON action_status_history (action_id, changed_at);

-- Sync logs
CREATE TABLE IF NOT EXISTS sync_logs (
  id SERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  job_id TEXT,
  status sync_status_enum NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_sync_logs_source_started ON sync_logs (company_id, source, started_at);
CREATE INDEX IF NOT EXISTS idx_sync_logs_job ON sync_logs (job_id);

-- Triggers to populate/validate employee_external_id for time_entries and events
CREATE OR REPLACE FUNCTION set_employee_external_id() RETURNS trigger AS $$
DECLARE emp_external TEXT; emp_company INTEGER;
BEGIN
  SELECT external_id, company_id INTO emp_external, emp_company FROM employees WHERE id = NEW.employee_id;
  IF emp_external IS NULL THEN
    RAISE EXCEPTION 'Employee % not found or missing external_id', NEW.employee_id;
  END IF;
  IF NEW.company_id IS NOT NULL AND emp_company IS NOT NULL AND NEW.company_id <> emp_company THEN
    RAISE EXCEPTION 'Company mismatch: row company % vs employee company %', NEW.company_id, emp_company;
  END IF;
  NEW.company_id := COALESCE(NEW.company_id, emp_company);
  NEW.employee_external_id := emp_external;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_external_time_entries ON time_entries;
CREATE TRIGGER trg_set_external_time_entries
BEFORE INSERT OR UPDATE ON time_entries
FOR EACH ROW EXECUTE FUNCTION set_employee_external_id();

DROP TRIGGER IF EXISTS trg_set_external_events ON events;
CREATE TRIGGER trg_set_external_events
BEFORE INSERT OR UPDATE ON events
FOR EACH ROW EXECUTE FUNCTION set_employee_external_id();

COMMIT;


