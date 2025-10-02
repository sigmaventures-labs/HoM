# **Updated Implementation Guide for HoM – HR‑Analytics MVP**

# **What changes (TL;DR)**

* **Direct vs. Indirect** can be determined **authoritatively** from each employee’s **labor allocation code** (not department). Use Dept only for plant/location rollups.

* **Worked time** should be built from **punches** (in/out, lunch out/in) and must **exclude** the listed paid absence earnings (vacation, sick, floating holiday, holiday, bereavement, jury duty).

* **Absences** split into:

  * **Unpaid**: use Paycom **Scheduling/Attendance** module events (available from **June 2025 onward**).

  * **Paid**: derive from **earning codes posted** in time detail (e.g., sick).

* **Turnover** is tracked monthly by clients; compute your KPI **monthly** with average daily headcount for the month; enable deeper slices (reason, supervisor, department, tenure).

---

# **Refined metric specs (wireable now)**

## **1\) Headcount (HC)**

**Definition (as-of D):** Count employees where `hire_date ≤ D` and (`termination_date` is null or `termination_date > D`).

**Direct/Indirect:**

* Join employees to **LaborAllocationCode → {Direct|Indirect}** via a client-maintained mapping table seeded from Paycom labor allocation master.

* Use **Department** only for **location**/site rollups.

**Data you need**

* Employee master (hire/term/status), Labor Allocation master (for your DI mapping), Department master.

**Storage & cadence**

* Create a **daily snapshot** table `fact_headcount_daily(plant, direct_flag, …, as_of_date, headcount)` to support:

  * point-in-time HC

  * average HC for turnover

  * consistent historical reporting

**QA checks**

* HC roll-forward: `HC_t = HC_{t-1} + Hires_t – Terms_t` (tolerate small diffs due to late data).

---

## **2\) Absenteeism rate**

**What clients can provide**

* **Unpaid absences** via **Scheduling/Attendance** (since **Jun 2025**).

* **Paid absences** via **earning codes in time detail** (sick, PTO, etc.). Paycom’s native report doesn’t include paid unplanned—your calculation should.

**MVP definition (period P)**  
 \[  
 \\text{Absenteeism} \= \\frac{\\text{Paid Absence Minutes} \+ \\text{Unpaid Absence Minutes}}{\\text{Scheduled Minutes}}  
 \]

**Numerator**

* **Paid absence minutes**: sum hours from time detail where `earning_code ∈ {vacation, sick, floating holiday, holiday, bereavement, jury duty}` (your exact code set from `cl/earning`), convert to minutes.

* **Unpaid absence minutes**:

  * **Post-Jun 2025**: pull from Scheduling/Attendance events (full/partial day) → minutes.

  * **Pre-Jun 2025 (fallback)**: infer no-shows via roster (see Denominator) minus worked minutes on expected workdays (exclude approved unpaid leave if you can detect it).

**Denominator (Scheduled Minutes)**

* **Post-Jun 2025**: prefer **official schedule** from Scheduling module for each employee/day.

* **Pre-Jun 2025 fallback**: use a **Roster Rule** table (e.g., FT=8h Mon–Fri; PT patterns) \+ `custom_standard_hours` overrides.

**Edge rules**

* If Scheduled=0 → **NULL** (not 0\) for that slice.

* Don’t clamp; paid+unpaid can’t exceed scheduled if sources are clean—flag if it does.

**QA checks**

* Sanity: PaidAbs \+ UnpaidAbs ≤ Scheduled (alert if violated).

* Coverage: % of employees with schedule source available per period.

---

## **3\) Overtime rate**

**punch style:** in/out, lunch out/in → you can compute worked time precisely from raw punches.

**Definition (period P)**  
 Recommend the operationally intuitive version:  
 \[  
 \\text{OT Rate} \= \\frac{\\text{Overtime Minutes}}{\\text{Worked Minutes}}  
 \]

* **Worked Minutes** \= minutes from punches **minus** unpaid meal periods, **excluding** minutes from paid absence earnings (vacation, sick, floating holiday, holiday, bereavement, jury duty).

* **Overtime Minutes** \= sum of minutes posted with **OT earning codes** (OT1, OT2, site-specific). If OT is not explicitly coded, derive from rule-based calc you run against worked minutes—but prefer the codes actually paid.

**Why this denominator?** It matches shop-floor intuition (“of what we worked, how much was OT?”) and avoids inflating/deflating with PTO.

**Edge rules**

* Worked=0 → **NULL**.

* Do **not** clamp (OT/Worked is naturally ≤1 if sources are consistent).

**QA checks**

* OT minutes ≤ Worked minutes per employee/day.

* Cross-foot: Regular \+ OT (+ other paid-work types) equals total paid work hours (excluding absences).

**Punch stitching details (important)**

* Pair IN/OUT and LUNCH OUT/IN per day; handle out-of-order/missing pairs:

  * If one lunch punch missing → assume default lunch length (e.g., 30 min) only if policy allows; else mark day “needs review” and exclude from metric until corrected.

  * Round rules (e.g., 6-min rounding) should follow clients policy—document and apply consistently.

---

## **4\) Turnover rate**

**recommended practice:** monthly manual calc \= terms ÷ average employees.

**Definition (monthly)**  
 \[  
 \\text{Turnover}\_{\\text{month}} \= \\frac{\#\\text{Employees with termination\_date in month}}{\\text{Average Daily HC in month}}  
 \]

* **Numerator**: count employees whose `termination_date` falls within the month (exclude internal transfers).

* **Denominator**: mean of **daily headcount snapshots** in that month (already defined in HC).

**Breakdowns (enable from day 1\)**

* By **termination reason**, **supervisor**, **department (location)**, **tenure buckets** (e.g., \<90d, 90–365d, \>1y). All are available in Paycom or can be stored alongside employee master at term time.

**QA checks**

* Recompute (Start HC \+ Hires – Terms ≈ End HC).

* Compare to client’s monthly spreadsheet for initial validation.

---

# **Data model & pipeline updates**

## **Reference dictionaries**

* `dim_earning_code` → classify each code: `{regular_work, overtime, paid_absence, unpaid_absence, other}` with subtypes (sick, vacation…).

* `dim_labor_allocation` → `{direct_flag (Y/N), location, …}`.

* `dim_department` → plant/location rollups.

* `dim_supervisor`, `dim_termination_reason`.

## **Facts**

* `fact_headcount_daily(employee_id, date, direct_flag, plant, …)`

* `fact_time_punch(employee_id, punch_id, ts, type {in/out/lunch_out/lunch_in}, source)`

* `fact_time_day(employee_id, date, worked_minutes, ot_minutes, paid_abs_minutes, unpaid_abs_minutes, anomalies)`

* `fact_schedule_day(employee_id, date, scheduled_minutes, source {scheduling|roster})`

* `fact_terms_month(plant, direct_flag, month, terms)` (or derive on the fly from employee master \+ snapshots)

## **Pipelines**

1. **Directory & attributes** (nightly): employees, supervisors, labor allocation, departments, termination reasons.

2. **Punch history** (daily windows): stitch to `fact_time_day`.

3. **Earning codes** (on change): refresh `dim_earning_code` and mapping.

4. **Scheduling/Attendance**:

   * **Post-Jun 2025**: import official schedules \+ unpaid absence events → `fact_schedule_day` and unpaid absence minutes.

   * **Pre-Jun 2025**: materialize roster rules into `fact_schedule_day`.

5. **HC snapshot** (nightly): compute as-of for all employees → `fact_headcount_daily`.

---

# **Dashboard behavior & UX guardrails**

* Show **method badges** on Absenteeism and OT: “Source: Scheduling+Earnings (since Jun 2025)” or “Source: Roster proxy (pre-Jun 2025)”.

* If denominator=0 → display **N/A** with hover explaining why.

* Add **drill-downs** clients want: turnover by reason/supervisor/department/tenure; OT by department and supervisor; absenteeism by absence type.

---

# **Validation plan (first 2 sprints)**

1. **Parallel run** one recent month with client’s spreadsheet: match turnover %, absenteeism days, OT hours ±1–2%.

2. **Spot-check** 10 employees across plants: punches → worked → OT; schedules vs. paid/unpaid absences.

3. **Exception queue**: list of days with punch anomalies, schedule missing, code unmapped.

