HoM
====

Monorepo scaffold for HR metrics dashboard, AI chat, and action engine.

Getting Started
---------------

See `tasks/tasks-prd-hom.md` for the PRD task list and bootstrap checklist.

Data ingestion
--------------

- Ingestion order matters:
  - Sync `employees` first, then `time entries`.
  - Reason: time entries are matched by `external_id` to employees; if an employee doesn’t exist yet, time-entry ingestion may be partial or fail.

- E2E (against mock Paycom):
  1. Export env vars: `PAYCOM_SID`, `PAYCOM_TOKEN`, optional `PAYCOM_BASE_URL` (mock URL), and database settings (or `DATABASE_URL`).
  2. Run migrations: `python backend/src/db/run_migrations.py`.
  3. Trigger syncs in order:
     - Employees: call the scheduler helpers to run `sync_employees(company_id)`.
     - Time entries: then run `sync_time_entries(company_id, days=N)`.
  4. Verify: check `employees`, `time_entries`, and `sync_logs` tables.

Directory Structure
-------------------

- `backend/` — FastAPI services, schedulers, metrics engine, AI orchestrator
- `frontend/` — React app with dashboard, chat, action board
- `.github/workflows/` — CI workflows for backend pytest and frontend jest
- `tasks/` — PRD and task lists


