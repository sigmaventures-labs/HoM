from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.ai.orchestrator import (
    AIOrchestrator,
    OrchestratorMode,
    OrchestratorRequest,
)


router = APIRouter()


class ChatStreamRequest(BaseModel):
    message: str = Field(...)
    metric: str = Field(..., description="metric key like 'absenteeism_rate'")
    mode: Optional[OrchestratorMode] = Field(None, description="explanation|prediction|prescription")
    sessionId: Optional[str] = Field(None)
    options: Dict[str, Any] = Field(default_factory=dict)


@router.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest, request: Request) -> StreamingResponse:
    orchestrator = AIOrchestrator()
    response = orchestrator.run(
        mode=(req.mode or OrchestratorMode.EXPLANATION),
        request=OrchestratorRequest(
            user_query=req.message,
            metric_ref=req.metric,
            session_id=req.sessionId,
            options=req.options,
        ),
    )

    text = response.message or ""
    ui_spec = (response.extras.ui_spec if response.extras else None) if hasattr(response, "extras") else None

    async def event_generator():
        # naive tokenization by sentences/clauses
        chunks = [c.strip() for c in text.replace("\n", " ").split(". ") if c.strip()]
        for chunk in chunks:
            if await request.is_disconnected():
                break
            payload = {"delta": (chunk + (". " if not chunk.endswith(".") else " "))}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        # emit ui_spec if available
        if ui_spec is not None:
            yield "data: " + json.dumps({"ui_spec": ui_spec}, ensure_ascii=False) + "\n\n"
        # done
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


