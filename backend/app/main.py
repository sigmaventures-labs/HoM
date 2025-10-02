from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.metrics import router as metrics_router
from backend.app.api.routes.chat import router as chat_router


app = FastAPI(title="HoM API", version="0.1.0")

# CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/metrics/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
app.include_router(chat_router, prefix="/api/ai", tags=["ai"]) 


