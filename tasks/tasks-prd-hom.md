## Relevant Files

- `backend/app/integration/paycom_client.py` - Python wrapper using local `paycom_async` package.
- `backend/app/scheduler/sync_scheduler.py` - Daily sync scheduler (APScheduler) and jobs.
- `backend/src/db/migrations/2025_09_14_init.sql` - Initial schema for HR metrics + history.
- `backend/app/metrics/engine.py` - Metric calculations (headcount, absenteeism, turnover, overtime).
- `backend/app/api/routes/metrics.py` - FastAPI endpoints to fetch metrics and trends.
- `backend/app/ai/orchestrator.py` - AI orchestration: modes, context assembly, routing.
- `backend/app/ai/prompt_templates/` - Prompt templates for explanation, prediction, prescription.
- `backend/app/ai/ephemeral_ui.py` - Ephemeral visualization spec generation.
- `backend/app/actions/generator.py` - Prescriptive action generation pipeline.
- `backend/app/api/routes/actions.py` - CRUD and listing routes for actions and status updates.
- `frontend/src/components/dashboard/MetricCard.tsx` - Metric card UI with trend, target, sparkline, status, Ask AI.
- `frontend/src/components/dashboard/Sparkline.tsx` - Mini sparkline visualization.
- `frontend/src/components/chat/ChatInterface.tsx` - Conversational UI with streaming responses.
- `frontend/src/components/chat/EphemeralChart.tsx` - Renderer for AI-generated ephemeral charts.
- `frontend/src/state/ContextManager.ts` - Conversation state and context management.
- `frontend/src/utils/ResponseFormatter.ts` - Formatting AI responses into UI-friendly structures.
- `frontend/src/views/ActionBoard.tsx` - Action board view with status and priority matrix.
- `frontend/src/lib/playbooks/index.md` - Playbook library entries (starter content).
- `frontend/src/components/dashboard/MetricCard.test.tsx` - Unit tests for metric card.
- `frontend/src/components/chat/ChatInterface.test.tsx` - Unit tests for chat interface.
- `backend/tests/metrics/test_engine.py` - Unit tests for metric calculations (pytest).
- `backend/tests/ai/test_orchestrator.py` - Unit tests for AI orchestration and context (pytest).
- `backend/tests/actions/test_generator.py` - Unit tests for action generation (pytest).
 - `tasks/paycomPackage_CursorGuide.md` - Guide for installing and using `paycom_async`.

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
  - [ ] 1.1 Initialize project repo/CI (no MaX dependency)
  - [ ] 1.2 Create Python env (3.11+) and install local `paycom_async` per guide
  - [ ] 1.3 Set up PostgreSQL and create initial schema for employees, time, events, metrics_history
  - [ ] 1.4 Implement `paycomClient.py` wrapper around `paycom_async` with fetch functions
  - [ ] 1.5 Implement daily sync scheduler (APScheduler) with retries and rate limiting
  - [ ] 1.6 Define metric data models and seed sample data for dev
  - [ ] 1.7 Configure environment variables per guide: `PAYCOM_SID`, `PAYCOM_TOKEN`, `PAYCOM_BASE_URL`
  - [ ] 1.8 Add optional local mock support (uvicorn) behind a feature flag
  - [ ] 1.9 Expose OpenAPI spec via FastAPI (contract-first, low-impact guardrail)

- [ ] 2.0 Dashboard adaptation for HR metrics with "Ask AI" triggers
  - [ ] 2.1 Define 4 MVP metrics: headcount, absenteeism rate, turnover rate, overtime
  - [ ] 2.2 Implement Python metrics engine (`backend/app/metrics/engine.py`) and pytest unit tests
  - [ ] 2.3 Build/modify `MetricCard` to show value, target, trend arrow, sparkline, status
  - [ ] 2.4 Add "Ask AI" button that passes metric context and opens chat
  - [ ] 2.5 Create FastAPI metrics endpoints for current values and last-12-weeks trends
  - [ ] 2.6 Integrate sample data and verify visual accuracy of cards
  - [ ] 2.7 Add component tests for `MetricCard` and sparkline rendering

- [ ] 3.0 Conversational module and AI orchestration service
  - [ ] 3.1 Implement `ChatInterface` with message history, streaming, and loading states
  - [ ] 3.2 Pre-populate first message from "Ask AI" with metric context ("Tell me about [Metric]")
  - [ ] 3.3 Build Python AI orchestrator with modes: explanation, prediction, prescription
  - [ ] 3.4 Implement context injection: fetch metric data and trends for prompts
  - [ ] 3.5 Add ephemeral UI spec: support chart/table/annotation render instructions
  - [ ] 3.6 Create `EphemeralChart` renderer to display AI-proposed visuals inline
  - [ ] 3.7 Implement `ContextManager` to persist conversation state per metric/session
  - [ ] 3.8 Externalize prompt templates to `backend/app/ai/prompt_templates/` (guardrail)
  - [ ] 3.9 Write pytest unit tests for orchestrator, context injection, and chat flows

- [ ] 4.0 Action generation and management module
  - [ ] 4.1 Implement Python `ActionGenerator` producing 3–5 actions with impact, difficulty, timeline, first step
  - [ ] 4.2 Create FastAPI routes to list/create/update actions and link to metrics/conversations
  - [ ] 4.3 Build `ActionBoard` view with statuses and priority matrix (impact vs effort)
  - [ ] 4.4 Add basic playbook entries for common HR actions
  - [ ] 4.5 Track action outcomes against metrics over time
  - [ ] 4.6 Add pytest tests for generator logic and action API

- [ ] 5.0 Integration, end-to-end testing, performance, and deployment preparation
  - [ ] 5.1 Complete Paycom sync E2E using `paycom_async` with CSV/mock fallback and reconciliation
  - [ ] 5.2 Create E2E test covering dashboard → chat → actions flow with seeded data
  - [ ] 5.3 Add simple caching/indices for metrics and chat context queries; perf budget checks
  - [ ] 5.4 Implement error handling, audit logs, and basic analytics
  - [ ] 5.5 Prepare deployment: Dockerfile, envs, migrations, CI pipeline
  - [ ] 5.6 Smoke test in staging and fix critical issues


