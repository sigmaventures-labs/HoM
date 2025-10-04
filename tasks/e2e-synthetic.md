## Synthetic E2E Test Plan (Replit Paycom mock)

### Prereqs
- Python 3.11+, virtualenv activated
- Postgres running; env `DATABASE_URL` or `DB_*` set
- Install deps: `pip install -r backend/requirements.txt`
- Install local paycom lib (if available): `pip install -e /Users/client/Documents/Dev/MaX/libs/paycom_async`

### Env
```
export PAYCOM_SID=your_sid
export PAYCOM_TOKEN=your_token
export PAYCOM_BASE_URL=https://<your-replit-host>/
export LLM_PROVIDER=mock        # or openai with OPENAI_API_KEY set
```

### Migrations
```
python backend/src/db/run_migrations.py
```

### One-off sync from mock
```
python scripts/e2e_sync_once.py --company-id 1 --days 28 --base-url "$PAYCOM_BASE_URL"
```

### Start API (separate terminal)
```
uvicorn backend.app.main:app --reload
```

### Probe metrics endpoints
```
python scripts/e2e_metrics_probe.py --base-url http://127.0.0.1:8000 --out .e2e/metrics
```

Artifacts written under `.e2e/metrics/*`.

### Seeded chat SSE for four metrics
```
python scripts/e2e_seeded_chat.py --base-url http://127.0.0.1:8000 --out .e2e/chat
```

Artifacts written under `.e2e/chat/{metric}.json` including events and timing.

### Optional: Live OpenAI smoke
```
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
python scripts/e2e_seeded_chat.py --base-url http://127.0.0.1:8000 --out .e2e/chat-openai
```

### Observability (lightweight suggestions)
- Correlate: pass `x-session-id` header from frontend; include in logs.
- Measure: log request durations, DB query timings, orchestrator latency.
- Expose: add `/metrics` endpoint (Prometheus) when ready.


