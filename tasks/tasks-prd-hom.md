## Relevant Files

- `backend/app/main.py` - FastAPI app factory and router registration.
- `backend/app/config/env.py` - Environment loading and DB URL helpers.
- `backend/app/integration/paycom_client.py` - Paycom client with mock HTTP fallback support.
- `backend/app/scheduler/sync_scheduler.py` - Daily sync scheduler (APScheduler) and jobs.
- `backend/src/db/migrations/2025_09_14_init.sql` - Initial schema for HR metrics + history.
- `backend/src/db/migrations/2025_09_20_enhanced_schema.sql` - Enhanced schema updates.
- `backend/src/db/run_migrations.py` - Lightweight migration runner.
- `backend/app/metrics/engine.py` - Metric calculations (headcount, absenteeism, turnover, overtime).
- `backend/app/api/routes/metrics.py` - FastAPI endpoints to fetch metrics and trends.
- `backend/app/api/routes/chat.py` - Chat SSE endpoint for AI orchestrator.
- `backend/app/ai/orchestrator.py` - AI orchestration: modes, context assembly, routing.
- `backend/app/ai/prompt_templates/` - Prompt templates for explanation, prediction, prescription.
- `backend/app/ai/ephemeral_ui.py` - Ephemeral visualization spec generation.
- `scripts/e2e_full_run.py` - Orchestrates migrations → API → ingestion → probes → chat.
- `scripts/e2e_metrics_probe.py` - Captures responses from metrics endpoints.
- `scripts/e2e_seeded_chat.py` - Runs seeded chat SSE for four metrics and saves transcripts.
- `frontend/vite.config.ts` - Vite config with API proxy to backend.
- `frontend/postcss.config.cjs` - PostCSS config (Tailwind v4 bridge + autoprefixer).
- `frontend/tailwind.config.ts` - Tailwind config.
- `frontend/src/index.css` - Tailwind layers, CSS variables, and design tokens.
- `frontend/src/components/dashboard/MetricCard.tsx` - Metric card UI with trend, target, sparkline, status, Ask AI.
- `frontend/src/components/dashboard/Sparkline.tsx` - Mini sparkline visualization.
- `frontend/src/components/chat/ChatInterface.tsx` - Conversational UI with streaming responses.
- `frontend/src/components/chat/EphemeralChart.tsx` - Renderer for AI-generated ephemeral charts.
- `frontend/src/state/ContextManager.ts` - Conversation state and context management.
- `frontend/src/components/dashboard/MetricCard.test.tsx` - Unit tests for metric card.
- `frontend/src/components/chat/EphemeralChart.test.tsx` - Unit tests for ephemeral chart.
- `backend/tests/metrics/test_engine.py` - Unit tests for metric calculations (pytest).
- `backend/tests/ai/test_orchestrator.py` - Unit tests for AI orchestration and context (pytest).
- `backend/tests/ai/test_chat_stream.py` - Unit tests for chat streaming endpoint (pytest).
 - `tasks/paycomPackage_CursorGuide.md` - Guide for installing and using `paycom_async`.
 - `tasks/e2e-synthetic.md` - Synthetic E2E guide and commands.
 - `README.md` - Monorepo scaffold overview and getting started pointers.
 - `.github/workflows/backend.yml` - Backend CI (pytest).
 - `.github/workflows/frontend.yml` - Frontend CI (jest).
 - `.gitignore` - Ignore rules for Python, Node, macOS, IDE artifacts.

### Notes

- Backend tests: use `pytest` (e.g., `pytest -q backend/tests`).
- Frontend tests: use `npx jest [optional/path/to/test/file]`.
- Unit tests can be placed alongside code or in `backend/tests` as shown.

#### Bootstrap Checklist (MVP)

1) Python and env
- Install Python 3.11+
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -e /Users/client/Documents/Dev/MaX/libs/paycom_async`

2) Backend deps and DB
- `pip install -r backend/requirements.txt` (or Poetry if used)
- Start PostgreSQL; create DB/schema
- Apply migrations in `backend/src/db/migrations/`

3) Env vars (choose mock or remote)
- `export PAYCOM_SID=...`
- `export PAYCOM_TOKEN=...`
- `export PAYCOM_BASE_URL=http://127.0.0.1:9000` (mock) or your Replit URL

4) Optional local mock
- `uvicorn mock.paycom_mock:app --port 9000 --reload`

5) Run services
- Start FastAPI: `uvicorn backend.app.main:app --reload`
- Start scheduler: `python -m backend.app.scheduler.sync_scheduler`

6) Quick verify
- OpenAPI docs at `http://localhost:8000/docs`
- `GET /api/metrics/health` returns 200
- `pytest -q backend/tests` passes

## Tasks

- [ ] 1.0 Foundation and data integration setup
  - [x] 1.1 Initialize project repo/CI (no MaX dependency)
  - [x] 1.2 Create Python env (3.11+) and install local `paycom_async` per guide
  - [x] 1.3 Set up PostgreSQL and create initial schema for employees, time, events, metrics_history
  - [x] 1.4 Implement `paycomClient.py` wrapper around `paycom_async` with fetch functions
  - [x] 1.5 Implement daily sync scheduler (APScheduler) with retries and rate limiting
  - [x] 1.6 Define metric data models and seed sample data for dev
  - [x] 1.7 Configure environment variables per guide: `PAYCOM_SID`, `PAYCOM_TOKEN`, `PAYCOM_BASE_URL`
  - [ ] 1.8 Add optional local mock support (uvicorn) behind a feature flag
  - [x] 1.9 Expose OpenAPI spec via FastAPI (contract-first, low-impact guardrail)

- [ ] 2.0 Dashboard adaptation for HR metrics with "Ask AI" triggers
  - [x] 2.1 Define 4 MVP metrics: headcount, absenteeism rate, turnover rate, overtime
  - [x] 2.2 Implement Python metrics engine (`backend/app/metrics/engine.py`) and pytest unit tests
  - [x] 2.3 Build/modify `MetricCard` to show value, target, trend arrow, sparkline, status
- [x] 2.4 Add "Ask AI" button that passes metric context and opens chat
  - [x] 2.5 Create FastAPI metrics endpoints for current values and last-12-weeks trends
  - [x] 2.6 Integrate sample data and verify visual accuracy of cards
  - [x] 2.7 Add component tests for `MetricCard` and sparkline rendering
  - [x] 2.8 Add safe resampling rules and cadence validation for trend API (weighted averages for rates; counts sum; reject unsupported upsampling)

- [ ] 3.0 Conversational module and AI orchestration service
  - [x] 3.1 Implement `ChatInterface` with message history, streaming, and loading states
  - [x] 3.2 Pre-populate first message from "Ask AI" with metric context ("Tell me about [Metric]")
  - [x] 3.3 Build Python AI orchestrator with modes: explanation, prediction, prescription
  - [x] 3.4 Implement context injection: fetch metric data and trends for prompts
  - [x] 3.5 Add ephemeral UI spec: support chart/table/annotation render instructions
  - [x] 3.6 Create `EphemeralChart` renderer to display AI-proposed visuals inline
  - [x] 3.7 Implement `ContextManager` to persist conversation state per metric/session
  - [x] 3.8 Externalize prompt templates to `backend/app/ai/prompt_templates/` (guardrail)
  - [x] 3.9 Write pytest unit tests for orchestrator, context injection, and chat flows
  - [ ] 3.10 Orchestrator context enrichment (post-3.9)
    - [ ] 3.10.1 Add `time_range` parsing and cadence options (day/week/month)
    - [ ] 3.10.2 Compute trend descriptors (slope, WoW/MoM, volatility, target delta)
    - [ ] 3.10.3 Include numerator/denominator and partial-period coverage for rate metrics
    - [ ] 3.10.4 Support scope filters (department/location) in context assembly
  - [ ] 3.11 Ephemeral UI polish (post-3.9)
  - [ ] 3.11.1 Add yFormat-aware formatting (percent vs number) and malformed spec guards (deferred from 3.6d)
  - [ ] 3.11.2 Expand EphemeralChart edge-case tests (empty/invalid data, unknown kinds/annotations, yFormat cases)

- [ ] 4.0 Action generation and management module
  - [ ] 4.1 Implement Python `ActionGenerator` producing 3–5 actions with impact, difficulty, timeline, first step
  - [ ] 4.2 Create FastAPI routes to list/create/update actions and link to metrics/conversations
  - [ ] 4.3 Build `ActionBoard` view with statuses and priority matrix (impact vs effort)
  - [ ] 4.4 Add basic playbook entries for common HR actions
  - [ ] 4.5 Track action outcomes against metrics over time
  - [ ] 4.6 Add pytest tests for generator logic and action API

- [ ] 5.0 Integration, end-to-end testing, performance, and deployment preparation
  - [ ] 5.1 Complete Paycom sync E2E using `paycom_async` with CSV/mock fallback and reconciliation
- NOTE: Ingestion order matters — run employee sync before time-entry syncs. Time entries are matched by `external_id` to employees; running time entries first may lead to partial or failed ingestion.
  - [ ] 5.2 Create E2E test covering dashboard → chat → actions flow with seeded data
  - [ ] 5.3 Add simple caching/indices for metrics and chat context queries; perf budget checks
  - [ ] 5.4 Implement error handling, audit logs, and basic analytics
  - [ ] 5.5 Prepare deployment: Dockerfile, envs, migrations, CI pipeline
  - [ ] 5.6 Smoke test in staging and fix critical issues


- [ ] 6.0 Observability
  - [ ] 6.1 Define SLOs/SLIs: availability, p95 latency, sync freshness
  - [ ] 6.2 Add structured JSON logging with correlation IDs across API, jobs, Paycom client
  - [ ] 6.3 Expose Prometheus metrics on backend (/metrics): HTTP, DB, APScheduler, Paycom
  - [ ] 6.4 Instrument frontend Web Vitals and error monitoring (Sentry) with performance tracing
  - [ ] 6.5 Create Grafana dashboards for APIs, scheduler jobs, DB health, AI flows
  - [ ] 6.6 Configure alerts: 5xx/error rate, p95 latency, job failures, sync lag
  - [ ] 6.7 Implement OpenTelemetry tracing (API, DB, Paycom, jobs) to OTLP collector
  - [ ] 6.8 Add Postgres exporter and slow query/index hit dashboards; tune hotspots
  - [ ] 6.9 Extend AI orchestration metrics: latency, timeouts, token usage, cost anomalies
  - [ ] 6.10 Write incident runbooks, map ownership, and set error budgets per SLOs
  - [ ] 6.11 Enforce PII-safe telemetry: redaction, sampling, and retention policies
  - [ ] 6.12 Add synthetic probes and E2E checks for dashboard → chat → actions


