from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_series(trend: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for p in trend or []:
        # Prefer period_end; fall back to period_start
        ts_str: Optional[str] = p.get("period_end") or p.get("period_start")
        try:
            x_val = ts_str or ""
        except Exception:
            x_val = ""
        points.append({
            "x": x_val,
            "y": p.get("value"),
        })
    return points


def _format_title(metric: Dict[str, Any]) -> str:
    name = metric.get("name") or metric.get("key") or "Metric"
    return f"{name} Trend"


def _target_annotation(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not current:
        return None
    target = current.get("target_value")
    if target is None:
        return None
    return {
        "type": "horizontal_line",
        "y": target,
        "label": "Target",
    }


def _summary_rows(metric: Dict[str, Any], current: Optional[Dict[str, Any]], trend: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    unit = metric.get("display_unit") or ("%" if metric.get("unit") == "ratio" else None)
    def _fmt(v: Optional[float]) -> Optional[str]:
        if v is None:
            return None
        if unit == "%":
            return f"{v * 100:.1f}%"
        return f"{v:.2f}"

    current_value = (current or {}).get("value")
    rows.append({"label": "Current", "value": _fmt(current_value)})

    # Week-over-week / month-over-month change from last 2 points
    if len(trend) >= 2:
        last = trend[-1].get("value")
        prev = trend[-2].get("value")
        if last is not None and prev is not None and prev != 0:
            delta = last - prev
            pct = delta / abs(prev)
            rows.append({"label": "Change", "value": (f"{pct*100:.1f}%" if unit == "%" else f"{delta:.2f}")})

    status = (current or {}).get("status")
    if status:
        rows.append({"label": "Status", "value": str(status).upper()})

    return rows


def build_ephemeral_spec(*, context: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """Return a lightweight UI spec for inline rendering.

    The consumer (frontend) can interpret this generic schema to render a chart
    and an optional summary table.
    """
    metric: Dict[str, Any] = context.get("metric") or {}
    current: Optional[Dict[str, Any]] = context.get("current")
    trend: List[Dict[str, Any]] = context.get("trend") or []

    series = _parse_series(trend)
    title = _format_title(metric)
    annotation = _target_annotation(current)
    rows = _summary_rows(metric, current, trend)

    spec: Dict[str, Any] = {
        "version": 1,
        "mode": mode,
        "components": [
            {
                "type": "chart",
                "kind": "line",
                "title": title,
                "data": series,
                "yFormat": "%" if (metric.get("unit") == "ratio" or metric.get("display_unit") == "%") else "number",
                "annotations": [a for a in [annotation] if a],
            },
            {
                "type": "table",
                "title": "Summary",
                "rows": rows,
            },
        ],
        "meta": {
            "metric_key": metric.get("key"),
        },
    }

    return spec


