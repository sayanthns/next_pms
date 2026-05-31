# Working-Hours Baseline, Mandatory Budget, Saturday Weekly Summary — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize all reports on a configurable fixed daily working-hours baseline (default 8h) compared against timer hours, make project budget mandatory (>0) on new projects, and send a per-member + all-team weekly summary every Saturday.

**Architecture:** A new shared module `next_pms/api/_hours.py` becomes the single source of truth for working-day and target-hour math (timer hours vs `8 × effective working days`, excluding Sundays/holidays/approved leaves). Reports (`productivity.py`, `ai_report.py`, weekly summary in `tasks.py`) all derive numbers from it, killing the current inconsistency where checkin in/out, timer, and task-estimate hours disagree. Budget enforcement lives in the `PMS Project` controller (new-only). Two new fields on the existing `PMS AI Settings` single hold the configurable hours/day and the team-summary recipient.

**Tech Stack:** Frappe v15.68.1 (Python), `frappe.tests.utils.FrappeTestCase`, Vue 3 SPA frontend. Local dev site = `mysite.local`.

**Spec:** `docs/superpowers/specs/2026-05-31-hours-budget-weekly-design.md`

**Conventions (from skill Section 1):** use `flt`/`cint`/`getdate` from `frappe.utils`, never `int()/float()` on stored values; wrap user-facing strings in `_()`; no f-string SQL; `frappe.db.get_single_value` for single doctypes.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `next_pms/api/_hours.py` (NEW) | Working-day + target-hour + utilization helpers. Pure-ish functions, the root fix. |
| `next_pms/api/test_hours.py` (NEW) | Tests for `_hours.py`. |
| `next_pms/next_pms/doctype/pms_ai_settings/pms_ai_settings.json` | + `working_hours_per_day`, `weekly_summary_recipient` fields. |
| `next_pms/next_pms/doctype/pms_project/pms_project.py` | Budget reqd>0 on new projects. |
| `next_pms/next_pms/doctype/pms_project/pms_project.json` | `total_budget` `reqd: 1`. |
| `next_pms/next_pms/doctype/pms_project/test_pms_project.py` | Budget enforcement tests. |
| `frontend/src/components/CreateProjectModal.vue` | Budget required in create UI. |
| `next_pms/api/productivity.py` | Use `_hours.py`; utilization vs target. |
| `next_pms/api/ai_report.py` | `_build_user_metrics` gets target + utilization. |
| `next_pms/tasks.py` | Rewrite `send_weekly_summary` (per-member + all-team). |
| `next_pms/hooks.py` | Weekly → cron `0 7 * * 6`. |

`project_report.py` is **not** touched — it reports project-level aggregates only, no per-member hours.

---

## Task 1: Add settings fields to PMS AI Settings

**Files:**
- Modify: `next_pms/next_pms/doctype/pms_ai_settings/pms_ai_settings.json`

- [ ] **Step 1: Add fields to `field_order`**

In `field_order`, after `"report_detail_level"`, add the two new fieldnames:

```json
    "field_order": [
        "ai_provider",
        "ai_api_key",
        "ai_model",
        "column_break_1",
        "daily_report_enabled",
        "daily_report_recipient",
        "section_break_report",
        "daily_report_recipients",
        "report_detail_level",
        "section_break_hours",
        "working_hours_per_day",
        "weekly_summary_recipient"
    ],
```

- [ ] **Step 2: Add the field definitions**

In the `fields` array, after the `report_detail_level` field object, add:

```json
        {
            "fieldname": "section_break_hours",
            "fieldtype": "Section Break",
            "label": "Working Hours & Weekly Summary"
        },
        {
            "fieldname": "working_hours_per_day",
            "fieldtype": "Float",
            "label": "Working Hours Per Day",
            "default": "8",
            "description": "Fixed daily target hours used by all productivity reports."
        },
        {
            "fieldname": "weekly_summary_recipient",
            "fieldtype": "Data",
            "label": "Weekly Team Summary Recipient",
            "default": "sayanth@enfono.in",
            "description": "Email that receives the all-members weekly summary (sent Saturdays)."
        }
```

- [ ] **Step 3: Migrate so the single doctype schema updates**

Run: `bench --site mysite.local migrate`
Expected: completes; "Updating DocType" for PMS AI Settings, no errors on next_pms.

- [ ] **Step 4: Verify the field reads with default**

Run: `bench --site mysite.local console` then:
```python
import frappe
print(frappe.db.get_single_value("PMS AI Settings", "working_hours_per_day"))
```
Expected: `8.0` (or `8`).

- [ ] **Step 5: Commit**

```bash
git add next_pms/next_pms/doctype/pms_ai_settings/pms_ai_settings.json
git commit -m "feat: add working_hours_per_day + weekly_summary_recipient to PMS AI Settings"
```

---

## Task 2: Shared working-hours module `_hours.py` (TDD)

**Files:**
- Create: `next_pms/api/_hours.py`
- Test: `next_pms/api/test_hours.py`

- [ ] **Step 1: Write the failing tests**

Create `next_pms/api/test_hours.py`:

```python
# apps/next_pms/next_pms/api/test_hours.py
import frappe
from frappe.tests.utils import FrappeTestCase

from next_pms.api import _hours


class TestHours(FrappeTestCase):
    def test_working_days_excludes_sunday(self):
        # 2026-06-01 (Mon) .. 2026-06-07 (Sun) inclusive -> 6 non-Sunday days
        days = _hours.working_days_in_range("2026-06-01", "2026-06-07")
        self.assertEqual(len(days), 6)
        self.assertTrue(all(d.weekday() != 6 for d in days))

    def test_compute_utilization_zero_target(self):
        self.assertEqual(_hours.compute_utilization(10, 0), 0.0)

    def test_compute_utilization_basic(self):
        self.assertEqual(_hours.compute_utilization(20, 40), 50.0)

    def test_working_hours_per_day_default(self):
        # A 0/blank stored value falls back to the 8h default
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 0)
        self.assertEqual(_hours.get_working_hours_per_day(), 8.0)

    def test_working_hours_per_day_configured(self):
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 7.5)
        self.assertEqual(_hours.get_working_hours_per_day(), 7.5)
        frappe.db.set_single_value("PMS AI Settings", "working_hours_per_day", 8)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_hours`
Expected: FAIL — `ModuleNotFoundError: No module named 'next_pms.api._hours'`.

- [ ] **Step 3: Write `_hours.py`**

Create `next_pms/api/_hours.py`:

```python
# apps/next_pms/next_pms/api/_hours.py
"""Shared working-hours + target-hours helpers — single source of truth.

All reports (Employee Productivity, AI daily, weekly summary) derive
"how many hours should this user have worked" from here, so numbers stay
consistent. Target = effective working days x configurable hours/day
(default 8). The timer (PMS Time Log.duration_hours) is the only "actual
hours" source; PMS Checkin in/out is NOT used as a baseline.
"""

from datetime import timedelta

import frappe
from frappe.utils import flt, getdate

DEFAULT_WORKING_HOURS_PER_DAY = 8.0


def get_working_hours_per_day():
    """Configured fixed working hours per day. Defaults to 8 when unset/zero."""
    value = frappe.db.get_single_value("PMS AI Settings", "working_hours_per_day")
    hours = flt(value)
    return hours if hours > 0 else DEFAULT_WORKING_HOURS_PER_DAY


def working_days_in_range(from_date, to_date):
    """All non-Sunday dates in [from_date, to_date] (inclusive) as date objects."""
    days = []
    d = getdate(from_date)
    end = getdate(to_date)
    while d <= end:
        if d.weekday() != 6:  # 6 = Sunday
            days.append(d)
        d += timedelta(days=1)
    return days


def get_employee_for_user(user):
    """Active Employee for a user (falls back to any Employee, else None)."""
    employees = frappe.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fields=["name", "holiday_list"],
        limit=1,
    )
    if not employees:
        employees = frappe.get_all(
            "Employee",
            filters={"user_id": user},
            fields=["name", "holiday_list"],
            limit=1,
        )
    return employees[0] if employees else None


def get_holiday_dates(holiday_list_name, from_date, to_date):
    """Non-weekly-off holiday dates (str) in range for a holiday list."""
    if not holiday_list_name:
        return set()
    holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": holiday_list_name,
            "holiday_date": ["between", [str(getdate(from_date)), str(getdate(to_date))]],
            "weekly_off": 0,
        },
        fields=["holiday_date"],
    )
    return {str(h.holiday_date) for h in holidays}


def get_leave_dates(employee_name, from_date, to_date):
    """Approved-leave dates (str) within range for an employee."""
    if not employee_name:
        return set()
    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee_name,
            "status": "Approved",
            "from_date": ["<=", str(getdate(to_date))],
            "to_date": [">=", str(getdate(from_date))],
        },
        fields=["from_date", "to_date"],
    )
    fd = getdate(from_date)
    td = getdate(to_date)
    leave_dates = set()
    for leave in leaves:
        ld = getdate(leave.from_date)
        lt = getdate(leave.to_date)
        while ld <= lt:
            if fd <= ld <= td:
                leave_dates.add(str(ld))
            ld += timedelta(days=1)
    return leave_dates


def effective_working_days(user, from_date, to_date):
    """Non-Sunday days minus holidays minus approved leave, as sorted str list."""
    all_days = {str(d) for d in working_days_in_range(from_date, to_date)}
    employee = get_employee_for_user(user)
    employee_name = employee.name if employee else None
    holiday_list = employee.holiday_list if employee else None
    excused = get_holiday_dates(holiday_list, from_date, to_date) | get_leave_dates(
        employee_name, from_date, to_date
    )
    return sorted(all_days - excused)


def compute_target_hours(user, from_date, to_date):
    """Target hours over a range = effective working days x configured hours/day."""
    days = len(effective_working_days(user, from_date, to_date))
    return round(days * get_working_hours_per_day(), 2)


def compute_utilization(logged_hours, target_hours):
    """Utilization % = logged / target * 100. Returns 0.0 when target <= 0."""
    target = flt(target_hours)
    if target <= 0:
        return 0.0
    return round(flt(logged_hours) / target * 100, 1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_hours`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add next_pms/api/_hours.py next_pms/api/test_hours.py
git commit -m "feat: add shared _hours module (working days + target hours + utilization)"
```

---

## Task 3: Mandatory budget on new projects (TDD)

**Files:**
- Modify: `next_pms/next_pms/doctype/pms_project/pms_project.py:9-13`
- Modify: `next_pms/next_pms/doctype/pms_project/pms_project.json` (total_budget field)
- Test: `next_pms/next_pms/doctype/pms_project/test_pms_project.py`

- [ ] **Step 1: Write the failing tests**

Replace the body of `next_pms/next_pms/doctype/pms_project/test_pms_project.py`:

```python
# apps/next_pms/next_pms/next_pms/doctype/pms_project/test_pms_project.py
# Copyright (c) 2024, Next PMS and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPMSProject(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _new_project(self, **kwargs):
        doc = frappe.get_doc({
            "doctype": "PMS Project",
            "project_name": kwargs.get("project_name", "ZZ Test Project"),
            "status": "Active",
            "total_budget": kwargs.get("total_budget", 1000),
        })
        return doc

    def test_new_project_requires_positive_budget(self):
        doc = self._new_project(total_budget=0)
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_new_project_with_budget_passes(self):
        doc = self._new_project(total_budget=5000)
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.total_budget, 5000)

    def test_existing_project_without_budget_can_save(self):
        # Simulate a legacy project created before the rule (bypass validate on create)
        doc = self._new_project(total_budget=5000)
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("PMS Project", doc.name, "total_budget", 0)
        reloaded = frappe.get_doc("PMS Project", doc.name)
        reloaded.description = "edited"
        reloaded.save(ignore_permissions=True)  # must NOT throw (grandfathered)
```

Note: `project_name` may not be the autoname; if `PMS Project` autonames by series this still works. If your install requires `client`, add a throwaway client in `_new_project`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site mysite.local run-tests --module next_pms.next_pms.doctype.pms_project.test_pms_project`
Expected: FAIL — `test_new_project_requires_positive_budget` does not raise (no enforcement yet).

- [ ] **Step 3: Add enforcement to the controller**

In `next_pms/next_pms/doctype/pms_project/pms_project.py`, update imports and `validate`:

```python
# apps/next_pms/next_pms/next_pms/doctype/pms_project/pms_project.py
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PMSProject(Document):
	def validate(self):
		self.validate_budget()
		self.calculate_project_cost()
		self.validate_dates()

	def validate_budget(self):
		# Mandatory only on new projects; existing budget-less projects are grandfathered.
		if self.is_new() and flt(self.total_budget) <= 0:
			frappe.throw(_("Total Budget is required and must be greater than 0"))
```

(Leave `validate_dates`, `after_insert`, `calculate_project_cost`, etc. unchanged.)

- [ ] **Step 4: Mark the field required in the JSON**

In `next_pms/next_pms/doctype/pms_project/pms_project.json`, the `total_budget` field object becomes:

```json
  {
   "fieldname": "total_budget",
   "fieldtype": "Currency",
   "label": "Total Budget",
   "reqd": 1
  },
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `bench --site mysite.local run-tests --module next_pms.next_pms.doctype.pms_project.test_pms_project`
Expected: PASS (3 tests). Then `bench --site mysite.local migrate` to apply the `reqd` schema change.

- [ ] **Step 6: Commit**

```bash
git add next_pms/next_pms/doctype/pms_project/pms_project.py next_pms/next_pms/doctype/pms_project/pms_project.json next_pms/next_pms/doctype/pms_project/test_pms_project.py
git commit -m "feat: require Total Budget > 0 on new PMS Projects (existing grandfathered)"
```

---

## Task 4: Budget required in the create-project UI

**Files:**
- Modify: `frontend/src/components/CreateProjectModal.vue` (budget input ~line 69-78, `handleSubmit` ~line 160-180)

- [ ] **Step 1: Mark the budget field required in the template**

Replace the Total Budget form-group (around line 68-78):

```html
      <div class="form-group">
        <label class="form-label">Total Budget <span class="required">*</span></label>
        <input
          v-model.number="form.total_budget"
          type="number"
          class="form-input"
          placeholder="0.00"
          min="0.01"
          step="0.01"
          required
        />
      </div>
```

- [ ] **Step 2: Block submit on missing/zero budget**

In `handleSubmit`, after the existing `client` guard, add a budget guard:

```javascript
async function handleSubmit() {
  if (!form.value.project_name.trim()) return
  if (!form.value.client) return
  if (!form.value.total_budget || form.value.total_budget <= 0) {
    alert('Total Budget is required and must be greater than 0')
    return
  }
  saving.value = true
```

(Keep the rest of `handleSubmit` unchanged. `alert` matches existing lightweight UX; if the file already imports a toast helper, use that instead.)

- [ ] **Step 3: Build the frontend**

Run: `cd frontend && yarn build`
Expected: build succeeds, no type/compile errors.

- [ ] **Step 4: Manual verify**

Open the app, click New Project, leave budget at 0 → submit blocked with the message. Enter a budget > 0 with name+client → project creates. (Backend also enforces via Task 3, so the API rejects a 0 budget even if the UI is bypassed.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CreateProjectModal.vue
git commit -m "feat: require Total Budget in create-project modal"
```

---

## Task 5: Productivity report uses shared baseline

**Files:**
- Modify: `next_pms/api/productivity.py` (imports, remove local helpers, `get_employee_productivity`)

- [ ] **Step 1: Import shared helpers and drop the duplicated local ones**

At the top of `productivity.py`, add:

```python
from next_pms.api._hours import (
    working_days_in_range as _working_days_in_range,
    get_employee_for_user as _get_employee_for_user,
    get_holiday_dates as _get_holiday_dates,
    get_leave_dates as _get_leave_dates,
    compute_target_hours,
    compute_utilization,
)
```

Then **delete** the now-duplicated local function definitions in this file: `_working_days_in_range`, `_get_employee_for_user`, `_get_holiday_dates`, `_get_leave_dates` (the bodies shown at `productivity.py:24-90`). Keep `_strip_html`, `_get_date_range`, and everything else. The import aliases preserve all existing call sites.

- [ ] **Step 2: Compute target + utilization and stop using checkin as the baseline**

In `get_employee_productivity`, right after `total_logged_hours` is computed (currently `productivity.py:61`), add:

```python
    # Fixed-baseline target (8h x effective working days) — replaces checkin in/out
    target_hours = compute_target_hours(user, from_date, to_date)
    utilization_pct = compute_utilization(total_logged_hours, target_hours)
```

- [ ] **Step 3: Surface the new metric in the response**

In the dict returned by `get_employee_productivity`, near the existing `total_logged_hours` / `avg_hours_per_day` keys, add:

```python
        "target_hours": target_hours,
        "utilization_pct": utilization_pct,
```

Leave `total_office_hours` / `avg_hours_per_day` in the payload as informational (checkin data still shown), but they are no longer the productivity baseline.

- [ ] **Step 4: Smoke-test the endpoint**

Run: `bench --site mysite.local console`
```python
import frappe
frappe.set_user("Administrator")
from next_pms.api.productivity import get_employee_productivity
r = get_employee_productivity("Administrator", 30)
print(r.get("target_hours"), r.get("utilization_pct"))
```
Expected: a numeric `target_hours` (e.g. ~> 0) and a `utilization_pct` float; no exception.

- [ ] **Step 5: Re-run the hours tests (regression)**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_hours`
Expected: PASS (imports via productivity still resolve).

- [ ] **Step 6: Commit**

```bash
git add next_pms/api/productivity.py
git commit -m "refactor: productivity report uses shared 8h-baseline target + utilization"
```

---

## Task 6: AI daily report metrics use shared baseline

**Files:**
- Modify: `next_pms/api/ai_report.py` (`_build_user_metrics`, `ai_report.py:201-289`)

- [ ] **Step 1: Import shared helpers**

At the top of `ai_report.py`, add:

```python
from next_pms.api._hours import compute_target_hours, compute_utilization
```

- [ ] **Step 2: Compute per-day target + utilization per user**

In `_build_user_metrics`, inside the `for user in user_list:` loop, after `time_today` is computed (`ai_report.py:256-260`), add:

```python
        # Fixed-baseline daily target (8h if an effective working day, else 0)
        day_target = compute_target_hours(user, report_date, report_date)
        day_utilization = compute_utilization(time_today, day_target)
```

- [ ] **Step 3: Add to the metrics dict**

In the `metrics.append({...})` dict, add (alongside `hours_logged_today`):

```python
            "target_hours": day_target,
            "utilization_pct": day_utilization,
```

(Leave `office_hours`, `checkin_time`, `checkout_time` as informational. The LLM prompt builder consumes `full_data`, so it now sees timer-vs-target utilization consistently with the other reports.)

- [ ] **Step 4: Smoke-test**

Run: `bench --site mysite.local console`
```python
import frappe
from next_pms.api.ai_report import _build_user_metrics
from frappe.utils import today
m = _build_user_metrics(today())
print(m[0] if m else "no activity today")
```
Expected: each metric dict contains `target_hours` and `utilization_pct`; no exception.

- [ ] **Step 5: Commit**

```bash
git add next_pms/api/ai_report.py
git commit -m "refactor: AI daily report user metrics include 8h-baseline target + utilization"
```

---

## Task 7: Saturday weekly summary — per-member + all-team (TDD where testable)

**Files:**
- Modify: `next_pms/tasks.py` (rewrite `send_weekly_summary`, replace `_build_weekly_summary_html`)
- Modify: `next_pms/hooks.py` (`scheduler_events`)
- Test: `next_pms/api/test_hours.py` (add a week-window test) — keeps weekly logic testable without sending mail

- [ ] **Step 1: Write a failing test for the week-start helper**

Append to `next_pms/api/test_hours.py`:

```python
    def test_week_start_is_monday(self):
        from next_pms.tasks import get_week_start
        # 2026-06-06 is a Saturday; its week starts Monday 2026-06-01
        self.assertEqual(str(get_week_start("2026-06-06")), "2026-06-01")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_hours`
Expected: FAIL — `ImportError: cannot import name 'get_week_start'`.

- [ ] **Step 3: Rewrite `send_weekly_summary` and helpers in `tasks.py`**

Replace the entire `send_weekly_summary` function AND `_build_weekly_summary_html` (`tasks.py:167-310`) with:

```python
def get_week_start(d):
    """Monday of the week containing date d."""
    d = getdate(d)
    return add_days(d, -d.weekday())  # weekday(): Monday=0


def _get_active_members(from_dt, to_dt):
    """Enabled users who logged time this week OR are members of an Active project."""
    logged = frappe.get_all(
        "PMS Time Log",
        filters={"start_time": ["between", [from_dt, to_dt]], "is_running": 0},
        fields=["user"],
        group_by="user",
    )
    members = {l.user for l in logged if l.user}

    active_projects = frappe.get_all("PMS Project", filters={"status": "Active"}, fields=["name"])
    active_proj_names = [p.name for p in active_projects]
    if active_proj_names:
        project_members = frappe.get_all(
            "PMS Project Member",
            filters={"parenttype": "PMS Project", "parent": ["in", active_proj_names]},
            fields=["user"],
        )
        members |= {m.user for m in project_members if m.user}

    if not members:
        return []
    enabled = frappe.get_all(
        "User",
        filters={"name": ["in", list(members)], "enabled": 1},
        fields=["name"],
    )
    return [u.name for u in enabled]


def _member_week_stats(user, week_start, week_end, from_dt, to_dt):
    """Per-member weekly stats dict (no email). Uses shared 8h-baseline target."""
    from next_pms.api._hours import compute_target_hours, compute_utilization

    full_name = frappe.db.get_value("User", user, "full_name") or user

    logs = frappe.get_all(
        "PMS Time Log",
        filters={"user": user, "start_time": ["between", [from_dt, to_dt]], "is_running": 0},
        fields=["duration_hours", "task"],
    )
    logged_hours = round(sum(l.duration_hours or 0 for l in logs), 2)
    target_hours = compute_target_hours(user, week_start, week_end)
    utilization = compute_utilization(logged_hours, target_hours)

    tasks_completed = frappe.db.sql(
        """
        SELECT COUNT(*) FROM `tabPMS Task`
        WHERE assigned_to = %s AND status = 'Done'
          AND DATE(modified) BETWEEN %s AND %s
        """,
        (user, str(week_start), str(week_end)),
    )[0][0] or 0
    tasks_in_progress = frappe.db.count(
        "PMS Task", {"assigned_to": user, "status": ["in", ["In Progress", "In Review"]]}
    )

    task_names = list({l.task for l in logs if l.task})
    projects_touched = set()
    if task_names:
        for row in frappe.get_all(
            "PMS Task", filters={"name": ["in", task_names]}, fields=["project"]
        ):
            if row.project:
                projects_touched.add(row.project)

    return {
        "user": user,
        "full_name": full_name,
        "logged_hours": logged_hours,
        "target_hours": target_hours,
        "utilization": utilization,
        "tasks_completed": tasks_completed,
        "tasks_in_progress": tasks_in_progress,
        "project_count": len(projects_touched),
    }


def send_weekly_summary():
    """Saturday 07:00 — per active member: own weekly stats email.
    Configured recipient (default sayanth@enfono.in): all-members table.
    """
    week_end = getdate()
    week_start = get_week_start(week_end)
    from_dt = str(week_start) + " 00:00:00"
    to_dt = str(week_end) + " 23:59:59"

    members = _get_active_members(from_dt, to_dt)
    team_rows = []

    for user in members:
        stats = _member_week_stats(user, week_start, week_end, from_dt, to_dt)
        team_rows.append(stats)
        frappe.sendmail(
            recipients=[user],
            subject=_("Your Weekly Work Summary"),
            message=_build_member_weekly_html(stats, str(week_start), str(week_end)),
            now=True,
        )

    recipient = (
        frappe.db.get_single_value("PMS AI Settings", "weekly_summary_recipient")
        or "sayanth@enfono.in"
    )
    if team_rows:
        frappe.sendmail(
            recipients=[recipient],
            subject=_("Team Weekly Work Summary"),
            message=_build_team_weekly_html(team_rows, str(week_start), str(week_end)),
            now=True,
        )

    frappe.db.commit()


def _util_color(util):
    if util >= 90:
        return "#10B981"
    if util >= 60:
        return "#F59E0B"
    return "#EF4444"


def _build_member_weekly_html(stats, from_str, to_str):
    color = _util_color(stats["utilization"])
    return f"""
    <h3>Your Weekly Work Summary</h3>
    <p>Hi {stats['full_name']},</p>
    <p>Summary for <strong>{from_str}</strong> to <strong>{to_str}</strong>:</p>
    <table style="border-collapse:collapse; max-width:520px;">
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Hours Logged</td>
            <td style="padding:8px; border:1px solid #e5e7eb;"><strong>{stats['logged_hours']:.1f}h</strong></td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Target Hours</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['target_hours']:.1f}h</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Utilization</td>
            <td style="padding:8px; border:1px solid #e5e7eb; color:{color}; font-weight:600;">{stats['utilization']:.0f}%</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Tasks Completed</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['tasks_completed']}</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Tasks In Progress</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['tasks_in_progress']}</td></tr>
        <tr><td style="padding:8px; border:1px solid #e5e7eb;">Projects Worked On</td>
            <td style="padding:8px; border:1px solid #e5e7eb;">{stats['project_count']}</td></tr>
    </table>
    <p style="margin-top:16px; color:#6b7280; font-size:13px;">
        Target = 8h x working days (excludes Sundays, holidays, approved leave).
        Automated weekly summary from Next PMS.
    </p>
    """


def _build_team_weekly_html(team_rows, from_str, to_str):
    rows = ""
    for s in sorted(team_rows, key=lambda x: x["utilization"], reverse=True):
        color = _util_color(s["utilization"])
        rows += f"""
        <tr>
            <td style="padding:10px; border:1px solid #e5e7eb;">{s['full_name']}</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['logged_hours']:.1f}h</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['target_hours']:.1f}h</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center; color:{color}; font-weight:600;">{s['utilization']:.0f}%</td>
            <td style="padding:10px; border:1px solid #e5e7eb; text-align:center;">{s['tasks_completed']}</td>
        </tr>
        """
    return f"""
    <h3>Team Weekly Work Summary</h3>
    <p>Week <strong>{from_str}</strong> to <strong>{to_str}</strong> — {len(team_rows)} active member(s):</p>
    <table style="border-collapse:collapse; width:100%; max-width:760px;">
        <thead>
            <tr style="background:#f3f4f6;">
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:left;">Member</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Logged</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Target</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Utilization</th>
                <th style="padding:10px; border:1px solid #e5e7eb; text-align:center;">Tasks Done</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:16px; color:#6b7280; font-size:13px;">
        Target = 8h x working days (excludes Sundays, holidays, approved leave).
        Automated weekly summary from Next PMS.
    </p>
    """
```

- [ ] **Step 4: Add `_` import in tasks.py**

Ensure the top of `tasks.py` imports the translator (it currently does not):

```python
import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, getdate, date_diff, get_datetime
from next_pms.utils import get_pms_url
```

- [ ] **Step 5: Move the schedule to Saturday cron in `hooks.py`**

In `next_pms/hooks.py` `scheduler_events`, remove the `weekly` block:

```python
    "weekly": [
        "next_pms.tasks.send_weekly_summary",
    ],
```

and add to the existing `cron` dict (alongside the 3 AM and 8 AM entries):

```python
        "0 7 * * 6": [
            "next_pms.tasks.send_weekly_summary",
        ],
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_hours`
Expected: PASS including `test_week_start_is_monday`.

- [ ] **Step 7: Dry-run the job (sends real email — use a test recipient or Administrator only)**

Run: `bench --site mysite.local console`
```python
import frappe
from next_pms.tasks import _get_active_members, _member_week_stats, get_week_start
from frappe.utils import getdate
we = getdate(); ws = get_week_start(we)
fd = str(ws)+" 00:00:00"; td = str(we)+" 23:59:59"
ms = _get_active_members(fd, td)
print("active members:", ms)
if ms:
    print(_member_week_stats(ms[0], ws, we, fd, td))
```
Expected: a member list and a stats dict with `logged_hours`, `target_hours`, `utilization`. (Do not call `send_weekly_summary()` directly unless you accept it emailing every active member.)

- [ ] **Step 8: Commit**

```bash
git add next_pms/tasks.py next_pms/hooks.py next_pms/api/test_hours.py
git commit -m "feat: Saturday weekly summary — per-member email + all-team table (8h baseline)"
```

---

## Task 8: Update project memory

**Files:**
- Modify: `CLAUDE.md`
- Create: `skills/session-logs/2026-05-31-features.md`

- [ ] **Step 1: Add a Confirmed Features entry**

Under the most recent month in `CLAUDE.md` "Confirmed Features", add a May 31 entry summarizing: configurable 8h working-hours baseline (PMS AI Settings), reports standardized to timer-vs-target utilization (`api/_hours.py`), mandatory budget >0 on new projects, Saturday weekly summary (per-member + all-team).

- [ ] **Step 2: Note the new setting + schedule**

In the Scheduled Jobs table, change the weekly row to the `0 7 * * 6` Saturday cron. Add `working_hours_per_day` + `weekly_summary_recipient` to the PMS AI Settings description.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md skills/session-logs/2026-05-31-features.md
git commit -m "docs: record hours-baseline, mandatory-budget, Saturday weekly summary"
```

---

## Deployment (after local verification — server is separate, ask before deploying)

Per CLAUDE.md deploy checklist on the server (`office` site):
1. `cd apps/next_pms && git pull`
2. `bench use office`
3. `bench migrate` (applies PMS AI Settings + PMS Project schema)
4. `bench build --app next_pms`
5. `cd apps/next_pms/frontend && yarn && yarn build`
6. `sudo supervisorctl restart all`
7. In the app, open PMS AI Settings → set `working_hours_per_day` (default 8) and confirm `weekly_summary_recipient`.

---

## Self-Review

**Spec coverage:**
- F2 baseline (configurable 8h, utilization vs target, drop checkin baseline) → Tasks 1, 2, 5, 6. ✓
- F3 mandatory budget (new-only, >0, grandfather, UI) → Tasks 3, 4. ✓
- F4 Saturday weekly (per-member + all-team, configurable recipient, week window) → Task 7. ✓
- Settings home = PMS AI Settings → Task 1. ✓
- Shared `_hours.py` root fix → Task 2, consumed by 5/6/7. ✓
- `project_report.py` — spec said "if per-member hours"; confirmed none exist → correctly omitted. ✓

**Type/name consistency:** `compute_target_hours`, `compute_utilization`, `get_working_hours_per_day`, `working_days_in_range`, `get_employee_for_user`, `get_holiday_dates`, `get_leave_dates`, `effective_working_days` — defined in Task 2, imported identically in Tasks 5/6/7. `get_week_start`, `_get_active_members`, `_member_week_stats`, `_build_member_weekly_html`, `_build_team_weekly_html`, `_util_color` — all defined and referenced within Task 7. Stats dict keys (`logged_hours`, `target_hours`, `utilization`, `tasks_completed`, `tasks_in_progress`, `project_count`, `full_name`) consistent between `_member_week_stats` and both HTML builders. ✓

**Placeholders:** none — every code step shows full content.
