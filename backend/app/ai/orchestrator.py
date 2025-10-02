from __future__ import annotations

import json
import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from tenacity import Retrying, stop_after_attempt, wait_exponential_jitter
import psycopg
from datetime import date, timedelta

from backend.app.config.env import load_env, get_db_url
from backend.app.metrics.engine import (
    headcount_with_status,
    absenteeism_rate_with_status,
    overtime_rate_with_status,
    turnover_rate_with_status,
    MetricPoint,
)
from backend.app.metrics.definitions import get_definitions
from backend.app.ai.ephemeral_ui import build_ephemeral_spec


class OrchestratorMode(str, Enum):
    EXPLANATION = "explanation"
    PREDICTION = "prediction"
    PRESCRIPTION = "prescription"


class ActionSuggestion(BaseModel):
    title: str
    impact: Optional[str] = None
    effort: Optional[str] = None
    timeline: Optional[str] = None
    first_step: Optional[str] = None


class OrchestratorExtras(BaseModel):
    explanation: Optional[str] = None
    prediction: Optional[str] = None
    prescription: Optional[list[ActionSuggestion]] = None
    ui_spec: Optional[Dict[str, Any]] = None


class OrchestratorRequest(BaseModel):
    user_query: str = Field(..., description="End-user question or instruction")
    metric_ref: str = Field(..., description="Metric identifier or key, e.g., 'absenteeism_rate'")
    session_id: Optional[str] = Field(None, description="Conversation/session identifier for tracing")
    time_range: Optional[str] = Field(None, description="Optional time window descriptor, e.g., 'last_12_weeks'")
    options: Dict[str, Any] = Field(default_factory=dict, description="Provider/model overrides and runtime options")


class OrchestratorResponse(BaseModel):
    message: str
    mode: OrchestratorMode
    extras: Optional[OrchestratorExtras] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class PromptTemplateLoader:
    """Loads text prompt templates from the local prompt_templates directory."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), "prompt_templates")

    def load(self, name: str) -> str:
        path = os.path.join(self.base_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class BaseLLMClient:
    """Abstracts the LLM provider. Default implementation is a safe, deterministic mock.

    Implementations should override `generate` to call a real provider.
    """

    def __init__(self, *, timeout_s: float = 15.0, temperature: float = 0.2) -> None:
        self.timeout_s = timeout_s
        self.temperature = temperature

    def generate(self, *, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Safe default that crafts a short, bounded response without external calls.

    This allows the orchestrator to function in development and tests
    without requiring provider credentials.
    """

    def generate(self, *, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        # Produce a concise, deterministic response using the last instruction lines.
        # Clip to a reasonable length to simulate token limits.
        tail = user_prompt.strip().splitlines()[-10:]
        summary_hint = " ".join(line.strip() for line in tail if line.strip())
        base = summary_hint[:600]
        return f"{base}\n\n[Simulated response — replace with provider]"


class OpenAIClient(BaseLLMClient):
    """OpenAI Chat Completions client using the official SDK.

    Requires OPENAI_API_KEY and supports LLM_MODEL.
    """

    def __init__(self, *, timeout_s: float = 15.0, temperature: float = 0.2) -> None:
        super().__init__(timeout_s=timeout_s, temperature=temperature)
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("openai package not installed") from exc
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY for OpenAI provider")
        # Create client; rely on env var for key
        self._client = OpenAI(api_key=api_key)

    def generate(self, *, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        try:
            # Defer import type to runtime to avoid global dependency
            completion = self._client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
            )
            content = completion.choices[0].message.content or ""
            return content.strip()
        except Exception as exc:  # pragma: no cover - provider errors surfaced upstream
            raise


class AzureOpenAIClient(BaseLLMClient):
    """Azure OpenAI client using the official SDK wrapper.

    Requires AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION.
    Uses LLM_MODEL as the deployment name.
    """

    def __init__(self, *, timeout_s: float = 15.0, temperature: float = 0.2) -> None:
        super().__init__(timeout_s=timeout_s, temperature=temperature)
        try:
            from openai import AzureOpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openai package not installed (AzureOpenAI)") from exc

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        if not api_key or not endpoint:
            raise RuntimeError("Missing Azure OpenAI envs: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT")

        self._client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

    def generate(self, *, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        deployment = model or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not deployment:
            raise RuntimeError("Missing Azure OpenAI deployment name (LLM_MODEL or AZURE_OPENAI_DEPLOYMENT)")
        result = self._client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
        )
        return (result.choices[0].message.content or "").strip()


class AnthropicClient(BaseLLMClient):
    """Anthropic Messages API client.

    Requires ANTHROPIC_API_KEY. Uses Messages API with system + user content.
    """

    def __init__(self, *, timeout_s: float = 15.0, temperature: float = 0.2) -> None:
        super().__init__(timeout_s=timeout_s, temperature=temperature)
        try:
            import anthropic  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("anthropic package not installed") from exc
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY for Anthropic provider")
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, *, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        import anthropic  # type: ignore
        response = self._client.messages.create(
            model=model or "claude-3-5-sonnet-latest",
            max_tokens=600,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Messages API returns a list of content blocks
        parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
        return "\n\n".join(part for part in parts if part).strip()


class AIOrchestrator:
    """Main entry point for conversational orchestration across modes.

    Usage:
        orchestrator = AIOrchestrator()
        response = orchestrator.run(mode="explanation", request=OrchestratorRequest(...))
    """

    def __init__(
        self,
        *,
        llm_client: Optional[BaseLLMClient] = None,
        template_loader: Optional[PromptTemplateLoader] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.template_loader = template_loader or PromptTemplateLoader()

        # Choose LLM client based on env; default to OpenAI for production-like behavior
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        timeout_s = float(os.getenv("LLM_TIMEOUT_S", "15"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        model_env = os.getenv("LLM_MODEL")
        if model_env:
            self.model_name = model_env
        else:
            self.model_name = {
                "openai": "gpt-4o-mini",
                "azure": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                "azure_openai": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                "azure-openai": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                "anthropic": "claude-3-5-sonnet-latest",
            }.get(provider, "mock-001")

        if llm_client is not None:
            self.llm = llm_client
        else:
            self.llm = self._build_llm_client(provider=provider, timeout_s=timeout_s, temperature=temperature)

        self.retrying = Retrying(
            stop=stop_after_attempt(int(os.getenv("LLM_RETRY_ATTEMPTS", "2"))),
            wait=wait_exponential_jitter(initial=0.2, max=2.0),
            reraise=True,
        )

    def run(self, *, mode: OrchestratorMode | str, request: OrchestratorRequest) -> OrchestratorResponse:
        try:
            mode_enum = mode if isinstance(mode, OrchestratorMode) else OrchestratorMode(mode.lower())
        except Exception:
            return OrchestratorResponse(
                message="Unsupported mode. Try one of: explanation, prediction, prescription.",
                mode=OrchestratorMode.EXPLANATION,
                error="invalid_mode",
            )

        system_prompt = self._render_system_prompt(request=request)
        context = self._assemble_context(request=request)
        user_prompt = self._render_mode_prompt(mode=mode_enum, request=request, context=context)

        try:
            for attempt in self.retrying:
                with attempt:
                    text = self.llm.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=self.model_name,
                    )
                    break
        except Exception as exc:
            self.logger.exception("AIOrchestrator LLM failure: %s", exc, extra={"mode": mode_enum.value})
            return OrchestratorResponse(
                message=(
                    "I ran into a temporary issue generating a response. Please try again. "
                    "If this persists, contact support with this session id."
                ),
                mode=mode_enum,
                error="llm_error",
                meta={"session_id": request.session_id or "", "mode": mode_enum.value},
            )

        extras = self._build_extras(mode=mode_enum, text=text)
        try:
            ui_spec = build_ephemeral_spec(context=context, mode=mode_enum.value)
            if extras is None:
                extras = OrchestratorExtras()
            extras.ui_spec = ui_spec
        except Exception as _exc:
            # UI spec is best-effort; ignore failures
            pass
        return OrchestratorResponse(
            message=text,
            mode=mode_enum,
            extras=extras,
            meta={
                "session_id": request.session_id or "",
                "mode": mode_enum.value,
                "model": self.model_name,
            },
        )

    # Internal helpers
    def _render_system_prompt(self, *, request: OrchestratorRequest) -> str:
        tpl = self.template_loader.load("system.md")
        return tpl.format(
            session_id=request.session_id or "",
        )

    def _render_mode_prompt(self, *, mode: OrchestratorMode, request: OrchestratorRequest, context: Dict[str, Any]) -> str:
        name = {
            OrchestratorMode.EXPLANATION: "explanation.md",
            OrchestratorMode.PREDICTION: "prediction.md",
            OrchestratorMode.PRESCRIPTION: "prescription.md",
        }[mode]
        tpl = self.template_loader.load(name)
        return tpl.format(
            user_query=request.user_query,
            metric_ref=request.metric_ref,
            time_range=request.time_range or "",
            context_json=json.dumps(context, ensure_ascii=False),
        )

    def _build_extras(self, *, mode: OrchestratorMode, text: str) -> OrchestratorExtras:
        if mode is OrchestratorMode.EXPLANATION:
            return OrchestratorExtras(explanation=text)
        if mode is OrchestratorMode.PREDICTION:
            return OrchestratorExtras(prediction=text)
        if mode is OrchestratorMode.PRESCRIPTION:
            # Placeholder parse: real extraction will be added later
            suggestions = [
                ActionSuggestion(title=line.strip("- "))
                for line in text.splitlines()
                if line.strip().startswith("-") and len(line.strip()) > 2
            ]
            return OrchestratorExtras(prescription=suggestions or None)
        return OrchestratorExtras()

    def _build_llm_client(self, *, provider: str, timeout_s: float, temperature: float) -> BaseLLMClient:
        provider = provider.lower()
        if provider == "openai":
            try:
                return OpenAIClient(timeout_s=timeout_s, temperature=temperature)
            except Exception as exc:
                self.logger.error("Failed to init OpenAI client: %s; falling back to mock", exc)
                return MockLLMClient(timeout_s=timeout_s, temperature=temperature)
        if provider in ("azure", "azure_openai", "azure-openai"):
            try:
                return AzureOpenAIClient(timeout_s=timeout_s, temperature=temperature)
            except Exception as exc:
                self.logger.error("Failed to init Azure OpenAI client: %s; falling back to mock", exc)
                return MockLLMClient(timeout_s=timeout_s, temperature=temperature)
        if provider == "anthropic":
            try:
                return AnthropicClient(timeout_s=timeout_s, temperature=temperature)
            except Exception as exc:
                self.logger.error("Failed to init Anthropic client: %s; falling back to mock", exc)
                return MockLLMClient(timeout_s=timeout_s, temperature=temperature)
        # default mock
        if provider != "mock":
            self.logger.warning("Unknown LLM_PROVIDER=%s; using mock", provider)
        return MockLLMClient(timeout_s=timeout_s, temperature=temperature)

    # -------- Context assembly (Task 3.4) --------
    def _assemble_context(self, *, request: OrchestratorRequest) -> Dict[str, Any]:
        """Fetch metric definition, current value, and a recent trend window.

        Falls back to empty context on any failure.
        """
        try:
            load_env()
            db_url = get_db_url()
            company_id = int(request.options.get("company_id", 1))
            metric_key = request.metric_ref
            today = date.today()
            # Trend window defaults
            weeks = int(request.options.get("weeks", 12))
            week_end = today
            week_start = week_end - timedelta(days=6)

            def _points_to_dict(mp: MetricPoint) -> Dict[str, Any]:
                return {
                    "metric_key": mp.key,
                    "value": mp.value,
                    "status": getattr(mp.status, "value", None) if mp.status is not None else None,
                    "period_start": mp.period_start.isoformat() if mp.period_start else None,
                    "period_end": mp.period_end.isoformat() if mp.period_end else None,
                    "target_value": mp.target_value,
                    "thresholds": mp.thresholds,
                }

            definitions = get_definitions()
            definition = next((d.model_dump() for d in definitions if d.key == metric_key), None)

            with psycopg.connect(db_url) as conn:
                if metric_key == "headcount":
                    current = headcount_with_status(conn, company_id, today)
                    # last N weeks end-of-week
                    trend: list[Dict[str, Any]] = []
                    cursor_end = today - timedelta(days=(today.weekday() - 6) % 7)
                    for _ in range(weeks):
                        start_w = cursor_end - timedelta(days=6)
                        trend.append(_points_to_dict(headcount_with_status(conn, company_id, cursor_end)))
                        cursor_end = start_w - timedelta(days=1)
                    trend.reverse()
                elif metric_key == "absenteeism_rate":
                    current = absenteeism_rate_with_status(conn, company_id, week_start, week_end)
                    # last N full weeks
                    trend = []
                    cursor_end = today - timedelta(days=(today.weekday() - 6) % 7)
                    for _ in range(weeks):
                        start_w = cursor_end - timedelta(days=6)
                        trend.append(_points_to_dict(absenteeism_rate_with_status(conn, company_id, start_w, cursor_end)))
                        cursor_end = start_w - timedelta(days=1)
                    trend.reverse()
                elif metric_key == "overtime_rate":
                    current = overtime_rate_with_status(conn, company_id, week_start, week_end)
                    trend = []
                    cursor_end = today - timedelta(days=(today.weekday() - 6) % 7)
                    for _ in range(weeks):
                        start_w = cursor_end - timedelta(days=6)
                        trend.append(_points_to_dict(overtime_rate_with_status(conn, company_id, start_w, cursor_end)))
                        cursor_end = start_w - timedelta(days=1)
                    trend.reverse()
                elif metric_key == "turnover_rate":
                    # Use months; map weeks param to months count
                    months = weeks
                    # current = month-to-date
                    start_m = today.replace(day=1)
                    end_m = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    current = turnover_rate_with_status(conn, company_id, start_m, end_m)
                    # last full months
                    trend = []
                    month_cursor = today.replace(day=1)
                    for _ in range(months):
                        if month_cursor.month == 1:
                            month_cursor = month_cursor.replace(year=month_cursor.year - 1, month=12)
                        else:
                            month_cursor = month_cursor.replace(month=month_cursor.month - 1)
                        start_b = month_cursor
                        next_start = (start_b.replace(day=28) + timedelta(days=4)).replace(day=1)
                        end_b = next_start - timedelta(days=1)
                        trend.append(_points_to_dict(turnover_rate_with_status(conn, company_id, start_b, end_b)))
                    trend.reverse()
                else:
                    # Unknown metric; return minimal context
                    return {
                        "metric": {"key": metric_key},
                        "error": "unknown_metric",
                    }

            return {
                "metric": definition or {"key": metric_key},
                "current": _points_to_dict(current),
                "trend": trend,
                "params": {
                    "company_id": company_id,
                    "weeks": weeks,
                },
            }
        except Exception as exc:
            self.logger.warning("Context assembly failed: %s", exc)
            return {
                "metric": {"key": request.metric_ref},
                "current": None,
                "trend": [],
                "warning": "context_unavailable",
            }



