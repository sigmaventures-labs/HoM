from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import AsyncIterator, Optional, Dict, Any, List

try:
    # Local library installed via editable path per tasks/paycomPackage_CursorGuide.md
    from paycom_async import PaycomConnector  # type: ignore
except Exception:
    # Soft-degrade: allow HTTP fallback when PAYCOM_BASE_URL is provided
    PaycomConnector = None  # type: ignore[assignment]


ENV_SID = "PAYCOM_SID"
ENV_TOKEN = "PAYCOM_TOKEN"
ENV_BASE_URL = "PAYCOM_BASE_URL"
from backend.app.config.env import load_env
import httpx


@dataclass(frozen=True)
class PaycomConfig:
    sid: str
    token: str
    base_url: Optional[str] = None


def _read_config_from_env() -> PaycomConfig:
    load_env()
    sid = os.getenv(ENV_SID)
    token = os.getenv(ENV_TOKEN)
    base_url = os.getenv(ENV_BASE_URL)

    missing = [name for name, val in [(ENV_SID, sid), (ENV_TOKEN, token)] if not val]
    if missing:
        raise RuntimeError(
            "Missing required environment variables for Paycom client: "
            + ", ".join(missing)
        )
    return PaycomConfig(sid=sid or "", token=token or "", base_url=base_url)


class PaycomClient:
    """Thin wrapper around paycom_async.PaycomConnector.

    - Reads credentials from env by default
    - Provides typed async helpers for common fetches
    - Manages connector lifetime via async context manager
    """

    def __init__(self, config: Optional[PaycomConfig] = None) -> None:
        self._config = config or _read_config_from_env()
        # Initialize connector if library is available; otherwise rely on HTTP fallback when base_url is set
        if 'PaycomConnector' in globals() and PaycomConnector is not None:  # type: ignore[name-defined]
            # PaycomConnector accepts sid, token, and optional base_url for mock/alt endpoints
            self._connector = PaycomConnector(  # type: ignore[call-arg]
                sid=self._config.sid, token=self._config.token, base_url=self._config.base_url
            )
        else:
            self._connector = None
        self._httpx: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "PaycomClient":
        # If the underlying connector needs startup, put it here.
        if self._config.base_url:
            self._httpx = httpx.AsyncClient(
                base_url=self._config.base_url.rstrip("/"),
                auth=(self._config.sid, self._config.token),
                timeout=30.0,
            )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # If the underlying connector exposes close() or aclient.close(), call it here.
        close = getattr(self._connector, "aclose", None)
        if callable(close):
            await close()
        if self._httpx is not None:
            await self._httpx.aclose()
            self._httpx = None

    # Employees
    async def fetch_employees(self, active_only: bool = True):
        """Return list of employees from Paycom.

        Mirrors paycom_async semantics; returns pydantic models or dicts depending on library internals.
        """
        # Preferred: library call
        try:
            if self._connector is None:
                raise RuntimeError("connector_unavailable")
            return await self._connector.fetch_employees(active_only=active_only)
        except Exception:
            # Fallback to direct HTTP for Replit-based mock
            if not self._httpx:
                raise
            resp = await self._httpx.get("/api/v1/employeedirectory")
            resp.raise_for_status()
            data: List[Dict[str, Any]] = resp.json()
            # Normalize fields to expected keys
            norm: List[Dict[str, Any]] = []
            for e in data:
                norm.append(
                    {
                        "id": e.get("eecode") or e.get("id") or e.get("external_id"),
                        "external_id": e.get("eecode") or e.get("external_id"),
                        "first_name": e.get("firstname") or e.get("first_name"),
                        "last_name": e.get("lastname") or e.get("last_name"),
                        "email": e.get("email") or f"{(e.get('firstname') or 'user').lower()}@example.com",
                        "department": e.get("deptname") or e.get("department"),
                        "department_code": e.get("deptcode"),
                        "labor_type": e.get("labor_type"),
                        "status": e.get("status"),
                        "hiredate": e.get("hiredate"),
                        "termdate": e.get("termdate"),
                    }
                )
            return norm

    # Timecards / time entries
    async def iter_timecards(
        self, start_date: date, end_date: date, *, active_only: bool = True
    ) -> AsyncIterator[dict]:
        """Async-iterate timecards between start_date and end_date (inclusive).

        Yields provider records one-by-one to support streaming ingestion.
        """
        # Preferred: library call
        try:
            if self._connector is None:
                raise RuntimeError("connector_unavailable")
            async for tc in self._connector.fetch_timecards(  # type: ignore[union-attr]
                start_date=start_date, end_date=end_date, active_only=active_only
            ):
                yield tc
            return
        except Exception:
            if not self._httpx:
                raise
            # Fallback: iterate employees from mock and fetch punch history per employee
            resp = await self._httpx.get("/api/v1/employeedirectory")
            resp.raise_for_status()
            employees = resp.json()
            for e in employees:
                eecode = e.get("eecode") or e.get("id") or e.get("external_id")
                if not eecode:
                    continue
                pr = await self._httpx.get(
                    f"/api/v1/employee/{eecode}/punchhistory",
                    params={
                        # canonical Paycom-style params
                        "startdate": start_date.isoformat(),
                        "enddate": end_date.isoformat(),
                        # compatibility with alternate mocks
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )
                if pr.status_code >= 400:
                    continue
                punches = pr.json()
                for p in punches:
                    # Accept either minute fields or fallback from hours
                    work_date = p.get("work_date") or p.get("date")
                    if not work_date:
                        continue
                    record: Dict[str, Any] = {
                        "employee_id": eecode,
                        "work_date": work_date,
                    }
                    if "worked_minutes" in p:
                        record.update(
                            {
                                "worked_minutes": int(p.get("worked_minutes") or 0),
                                "regular_minutes": int(p.get("regular_minutes") or 0),
                                "ot1_minutes": int(p.get("ot1_minutes") or 0),
                                "ot2_minutes": int(p.get("ot2_minutes") or 0),
                                "scheduled_minutes": p.get("scheduled_minutes"),
                                "absence_code": p.get("absence_code"),
                                "absence_minutes": p.get("absence_minutes"),
                            }
                        )
                    else:
                        # hours fallback
                        hours = float(p.get("hours_worked") or 0)
                        ot_hours = float(p.get("overtime_hours") or 0)
                        mins = int(round(hours * 60))
                        otm = int(round(ot_hours * 60))
                        record.update(
                            {
                                "hours_worked": hours,
                                "overtime_hours": ot_hours,
                                "worked_minutes": mins + otm,
                                "regular_minutes": mins,
                                "ot1_minutes": otm,
                                "ot2_minutes": 0,
                                "scheduled_minutes": p.get("scheduled_minutes"),
                                "absence_code": p.get("absence_code"),
                                "absence_minutes": p.get("absence_minutes"),
                            }
                        )
                    yield record

    # Health / readiness
    async def ping(self) -> bool:
        """Lightweight readiness probe using a minimal call if available.

        Falls back to credential presence when no ping endpoint is available.
        """
        try:
            # Prefer a cheap call if library exposes it in future; for now, just check creds present.
            return bool(self._config.sid and self._config.token)
        except Exception:
            return False


__all__ = ["PaycomClient", "PaycomConfig"]


