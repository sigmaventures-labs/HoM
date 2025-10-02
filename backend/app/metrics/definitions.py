from __future__ import annotations

from typing import Literal, Optional, List
from pydantic import BaseModel


MetricKey = Literal["headcount", "absenteeism_rate", "turnover_rate", "overtime_rate"]


class MetricDefinition(BaseModel):
    key: MetricKey
    name: str
    description: str
    orientation: Literal["higher", "lower"]
    unit: str  # internal unit (e.g., "count" or "ratio"); UI may format as %
    display_unit: Optional[str] = None  # e.g., "%" for ratios
    period: Literal["as_of_daily", "period", "monthly"]
    formula_markdown: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None
    edge_rules: Optional[List[str]] = None
    source_notes: Optional[List[str]] = None


DEFINITIONS: list[MetricDefinition] = [
    # 1) Headcount
    MetricDefinition(
        key="headcount",
        name="Headcount",
        description=(
            "Count employees where hire_date ≤ D and (termination_date is null or termination_date > D)."
        ),
        orientation="higher",
        unit="count",
        display_unit=None,
        period="as_of_daily",
        formula_markdown=(
            "HC(D) = count( employees with hire_date ≤ D and (termination_date is null or termination_date > D) )"
        ),
        numerator=None,
        denominator=None,
        edge_rules=[
            "Use department for location rollups only.",
            "Map Direct vs Indirect via Labor Allocation master, not department.",
        ],
        source_notes=[
            "Employee master (hire/term/status)",
            "Labor Allocation master for Direct/Indirect mapping",
            "Department master for location rollups",
        ],
    ),
    # 2) Absenteeism rate
    MetricDefinition(
        key="absenteeism_rate",
        name="Absenteeism Rate",
        description="Share of scheduled time not worked over a period.",
        orientation="lower",
        unit="ratio",
        display_unit="%",
        period="period",
        formula_markdown=(
            "Absenteeism = (Paid Absence Minutes + Unpaid Absence Minutes) / Scheduled Minutes"
        ),
        numerator=(
            "Paid absence minutes from earning codes (vacation, sick, floating holiday, holiday, bereavement, jury duty)"
            " + Unpaid absence minutes from Scheduling/Attendance events (post-Jun 2025); pre-Jun 2025: infer no-shows via roster minus worked"
        ),
        denominator=(
            "Scheduled minutes from official Scheduling module; pre-Jun 2025 fallback: roster rule table + overrides"
        ),
        edge_rules=[
            "If Scheduled = 0 → NULL (N/A).",
            "Do not clamp; flag if Paid+Unpaid > Scheduled.",
        ],
        source_notes=[
            "Post-Jun 2025: Scheduling/Attendance for unpaid absences and schedule.",
            "Paid absences from earning codes in time detail.",
            "Pre-Jun 2025: roster proxy for schedule; infer no-shows.",
        ],
    ),
    # 3) Overtime rate
    MetricDefinition(
        key="overtime_rate",
        name="Overtime Rate",
        description="Overtime minutes as a share of worked minutes over a period.",
        orientation="lower",
        unit="ratio",
        display_unit="%",
        period="period",
        formula_markdown=(
            "OT Rate = Overtime Minutes / Worked Minutes"
        ),
        numerator=(
            "Overtime minutes from OT earning codes (OT1, OT2, site-specific); if not coded, derive via rules against worked minutes"
        ),
        denominator=(
            "Worked minutes from punches minus unpaid meal periods; exclude minutes from paid absence earnings"
        ),
        edge_rules=[
            "If Worked = 0 → NULL (N/A).",
            "Do not clamp; OT ≤ Worked if sources are consistent.",
        ],
        source_notes=[
            "Use raw punches (in/out, lunch out/in) for precise worked time.",
            "Follow client rounding policies consistently (e.g., 6-min rounding).",
        ],
    ),
    # 4) Turnover rate (monthly)
    MetricDefinition(
        key="turnover_rate",
        name="Turnover Rate",
        description="Monthly separations relative to average daily headcount for the month.",
        orientation="lower",
        unit="ratio",
        display_unit="%",
        period="monthly",
        formula_markdown=(
            "Turnover_month = (# employees with termination_date in month) / (Average Daily Headcount in month)"
        ),
        numerator=(
            "Count employees whose termination_date falls within the month (exclude internal transfers)"
        ),
        denominator=(
            "Mean of daily headcount snapshots in that month"
        ),
        edge_rules=[
            "Validate with roll-forward: HC_t ≈ HC_{t-1} + Hires_t – Terms_t.",
        ],
        source_notes=[
            "Needs daily headcount snapshots to compute monthly average.",
            "Enable breakdowns by reason, supervisor, department, tenure buckets.",
        ],
    ),
]


def get_definitions() -> list[MetricDefinition]:
    return DEFINITIONS


