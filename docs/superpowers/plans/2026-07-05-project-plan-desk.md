# Project Plan (ERP desk) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement task-by-task. Steps use `- [ ]`. Frappe: keep frappe-erpnext-expert active; verify field names against live app source before coding. Tests run on `mysite.local`. Bench-installed app → work on `main` inline (worktrees detach the bench).

**Goal:** Desk-managed weekly Project Plan (person×project hours + per-project focus/target) with automatic daily tracking of plan-vs-actual (hours), task completion, and delivery-vs-target-date — surfaced in two reports + the daily email.

**Architecture:** Additive fields on existing doctypes (Weekly Plan Allocation gets `project`; Weekly Plan Project gets `target_hours`; PMS Project gets `target_close_date`) turn the current Weekly Plan into the Excel matrix. Two Script Reports + a daily-report block read the plan (Weekly Plan) vs actuals (PMS Time Log, PMS Task) vs `target_close_date`. Frappe desk only; the next_pms SPA tab becomes read-only.

**Tech Stack:** Frappe v15 (Python), Script Reports, existing PMS Time Log / PMS Task, ai_report.py.

Spec: `docs/superpowers/specs/2026-07-05-project-plan-desk-design.md`

---

## File map
- Modify: `next_pms/next_pms/doctype/pms_project/pms_project.json` (+target_close_date)
- Modify: `next_pms/next_pms/doctype/weekly_plan_allocation/weekly_plan_allocation.json` (+project)
- Modify: `next_pms/next_pms/doctype/weekly_plan_project/weekly_plan_project.json` (+target_hours)
- Modify: `next_pms/next_pms/api/weekly_plan.py` (+`get_plan_for_date` helper; SPA get_week rollup note)
- Create: `next_pms/next_pms/report/plan_vs_actual_hours/*`
- Create: `next_pms/next_pms/report/project_progress/*`
- Modify: `next_pms/next_pms/api/ai_report.py` (+`_get_plan_vs_actual`, wire into _build_report + email)
- Modify: `next_pms/next_pms/templates/emails/daily_ai_report.html` (plan-vs-actual block)
- Modify: `next_pms/frontend/src/components/WeeklyPlanEditor.vue` OR `WeeklyPlanView.vue` (edit → read-only)
- Test: `next_pms/next_pms/api/test_project_plan.py`

---

## Task 1: Durable + matrix fields

**Files:** the 3 doctype JSONs above.

- [ ] **Step 1: Add fields**
  - `pms_project.json`: add to `field_order` after `target_budget`/near status a field, and to `fields`:
    ```json
    { "fieldname": "target_close_date", "fieldtype": "Date", "label": "Target Close / Delivery Date" }
    ```
  - `weekly_plan_allocation.json`: add `project` as the FIRST field (before member) in field_order + fields:
    ```json
    { "fieldname": "project", "fieldtype": "Link", "label": "Project", "options": "PMS Project", "reqd": 1, "in_list_view": 1 }
    ```
  - `weekly_plan_project.json`: add after `focus`:
    ```json
    { "fieldname": "target_hours", "fieldtype": "Float", "label": "Target Hours", "in_list_view": 1 }
    ```

- [ ] **Step 2: Migrate + verify**
  Run: `/Users/sayanthns/.local/bin/bench --site mysite.local migrate`
  Then console: `frappe.get_meta("Weekly Plan Allocation").get_field("project")` and `frappe.get_meta("PMS Project").get_field("target_close_date")` — both non-None.
  Expected: migrate OK, both fields exist.

- [ ] **Step 3: Commit** (hold per session policy)

---

## Task 2: Shared helper — resolve the plan for a date

**Files:** Modify `next_pms/next_pms/api/weekly_plan.py`; Test `next_pms/next_pms/api/test_project_plan.py`

- [ ] **Step 1: Write the failing test**
```python
# next_pms/next_pms/api/test_project_plan.py
import frappe
from frappe.tests.utils import FrappeTestCase
from next_pms.api import weekly_plan as W

class TestPlanForDate(FrappeTestCase):
    def test_returns_none_when_no_plan(self):
        self.assertIsNone(W.get_plan_for_date("1999-01-04"))
```

- [ ] **Step 2: Run → fail**
Run: `/Users/sayanthns/.local/bin/bench --site mysite.local run-tests --module next_pms.api.test_project_plan`
Expected: FAIL — `get_plan_for_date` missing.

- [ ] **Step 3: Implement**
Add to `weekly_plan.py`:
```python
def get_plan_for_date(date=None):
    """Return the Weekly Plan name whose week contains `date` (else latest <= date)."""
    from frappe.utils import getdate, nowdate
    d = getdate(date or nowdate())
    name = frappe.db.get_value("Weekly Plan",
        {"week_start": ["<=", str(d)], "week_end": [">=", str(d)]}, "name")
    if not name:
        name = frappe.db.get_value("Weekly Plan", {"week_start": ["<=", str(d)]},
            "name", order_by="week_start desc")
    return name
```

- [ ] **Step 4: Run → pass**

---

## Task 3: Report — Plan vs Actual (Hours)

**Files:** Create `next_pms/next_pms/report/plan_vs_actual_hours/{plan_vs_actual_hours.json, plan_vs_actual_hours.py, __init__.py}`; Test append to `test_project_plan.py`

- [ ] **Step 1: report json**
```json
{
 "add_total_row": 1, "columns": [], "creation": "2026-07-05 00:00:00.000000",
 "disabled": 0, "docstatus": 0, "doctype": "Report", "filters": [], "idx": 0,
 "is_standard": "Yes", "letter_head": "", "modified": "2026-07-05 00:00:00.000000",
 "modified_by": "Administrator", "module": "Next PMS", "name": "Plan vs Actual Hours",
 "owner": "Administrator", "prepared_report": 0, "ref_doctype": "Weekly Plan",
 "report_name": "Plan vs Actual Hours", "report_type": "Script Report",
 "roles": [{"role": "System Manager"}, {"role": "PMS Manager"}]
}
```

- [ ] **Step 2: report py** — `plan_vs_actual_hours.py`
```python
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt
from next_pms.api.weekly_plan import get_plan_for_date

def execute(filters=None):
    filters = filters or {}
    plan_name = filters.get("weekly_plan") or get_plan_for_date(filters.get("as_on") or nowdate())
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 180},
        {"label": _("Person"), "fieldname": "person", "fieldtype": "Data", "width": 160},
        {"label": _("Planned"), "fieldname": "planned", "fieldtype": "Float", "width": 90},
        {"label": _("Actual"), "fieldname": "actual", "fieldtype": "Float", "width": 90},
        {"label": _("Deviation"), "fieldname": "deviation", "fieldtype": "Float", "width": 100},
        {"label": _("% Consumed"), "fieldname": "pct", "fieldtype": "Percent", "width": 100},
    ]
    if not plan_name:
        return columns, []
    wp = frappe.get_doc("Weekly Plan", plan_name)
    ws, we = str(wp.week_start), str(getdate(nowdate()))
    if getdate(we) > getdate(wp.week_end):
        we = str(wp.week_end)
    planned = {}
    names = {}
    for a in wp.allocations:
        if not a.get("project"):
            continue
        key = (a.project, a.member)
        planned[key] = planned.get(key, 0) + flt(a.planned_hours)
    # actuals: hours by project+user in [week_start, we]
    rows = frappe.db.sql("""
        select t.project as project, tl.user as person, round(sum(tl.duration_hours),2) h
        from `tabPMS Time Log` tl join `tabPMS Task` t on t.name = tl.task
        where tl.is_running=0 and DATE(tl.start_time) between %s and %s and t.project is not null
        group by t.project, tl.user""", (ws, we), as_dict=True)
    actual = {(r.project, r.person): flt(r.h) for r in rows}
    keys = set(planned) | set(actual)
    for pid, uid in keys:
        names.setdefault(pid, frappe.db.get_value("PMS Project", pid, "project_name") or pid)
        names.setdefault(uid, frappe.db.get_value("User", uid, "full_name") or uid)
    data = []
    for (pid, uid) in sorted(keys, key=lambda k: (names.get(k[0], k[0]), names.get(k[1], k[1]))):
        p = planned.get((pid, uid), 0); a = actual.get((pid, uid), 0)
        data.append({"project": names.get(pid, pid), "person": names.get(uid, uid),
                     "planned": p, "actual": a, "deviation": round(a - p, 2),
                     "pct": (a / p * 100) if p else 0})
    return columns, data
```

- [ ] **Step 3: Test** (append)
```python
class TestPlanVsActual(FrappeTestCase):
    def test_executes(self):
        from next_pms.next_pms.report.plan_vs_actual_hours import plan_vs_actual_hours as R
        cols, data = R.execute({})
        self.assertTrue(any(c["fieldname"] == "deviation" for c in cols))
        self.assertIsInstance(data, list)
```

- [ ] **Step 4: migrate (register report) + run tests → pass**
Run: `bench --site mysite.local migrate` then `run-tests --module next_pms.api.test_project_plan`

---

## Task 4: Report — Project Progress

**Files:** Create `next_pms/next_pms/report/project_progress/{project_progress.json, .py, __init__.py}`

- [ ] **Step 1: json** — same shape as Task 3 json, `name`/`report_name` = "Project Progress", `ref_doctype`="PMS Project".

- [ ] **Step 2: py** — `project_progress.py`
```python
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt, date_diff
from next_pms.api.weekly_plan import get_plan_for_date

ACTIVE = ("Planning", "Active", "On Hold")

def execute(filters=None):
    filters = filters or {}
    today = getdate(nowdate())
    plan_name = get_plan_for_date(today)
    target = {}
    if plan_name:
        wp = frappe.get_doc("Weekly Plan", plan_name)
        ws = str(wp.week_start)
        for p in wp.projects:
            if p.get("project"):
                target[p.project] = flt(p.get("target_hours"))
    else:
        ws = str(today)
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "PMS Project", "width": 180},
        {"label": _("Target h"), "fieldname": "target", "fieldtype": "Float", "width": 80},
        {"label": _("Actual h"), "fieldname": "actual", "fieldtype": "Float", "width": 80},
        {"label": _("Tasks Done"), "fieldname": "done", "fieldtype": "Int", "width": 90},
        {"label": _("Tasks Open"), "fieldname": "open", "fieldtype": "Int", "width": 90},
        {"label": _("% Complete"), "fieldname": "pct", "fieldtype": "Percent", "width": 100},
        {"label": _("Close Date"), "fieldname": "close_date", "fieldtype": "Date", "width": 100},
        {"label": _("Delivery"), "fieldname": "delivery", "fieldtype": "Data", "width": 120},
    ]
    projects = frappe.get_all("PMS Project", filters={"status": ["in", ACTIVE]},
                              fields=["name", "project_name", "target_close_date"], ignore_permissions=True)
    data = []
    for p in projects:
        actual = flt(frappe.db.sql("""select round(sum(tl.duration_hours),2) from `tabPMS Time Log` tl
            join `tabPMS Task` t on t.name=tl.task where tl.is_running=0 and t.project=%s
            and DATE(tl.start_time) between %s and %s""", (p.name, ws, str(today)))[0][0] or 0)
        done = frappe.db.count("PMS Task", {"project": p.name, "status": "Done"})
        openc = frappe.db.count("PMS Task", {"project": p.name, "status": ["not in", ["Done"]]})
        total = done + openc
        pct = (done / total * 100) if total else 0
        delivery = "—"
        if p.get("target_close_date"):
            dd = date_diff(p.target_close_date, today)
            if dd < 0:
                delivery = "Overdue %sd" % (-dd)
            elif dd <= 3 and pct < 80:
                delivery = "At risk (%sd)" % dd
            else:
                delivery = "On track (%sd)" % dd
        data.append({"project": p.name, "target": target.get(p.name, 0), "actual": actual,
                     "done": done, "open": openc, "pct": pct,
                     "close_date": p.get("target_close_date"), "delivery": delivery})
    return columns, data
```

- [ ] **Step 3: Test** (append) — executes, returns delivery column.
- [ ] **Step 4: migrate + run tests → pass**

---

## Task 5: Daily report — Plan vs Actual block

**Files:** Modify `next_pms/next_pms/api/ai_report.py`; `next_pms/next_pms/templates/emails/daily_ai_report.html`

- [ ] **Step 1: Write failing test** (append to test_project_plan.py)
```python
class TestPlanVsActualSummary(FrappeTestCase):
    def test_shape(self):
        from next_pms.api import ai_report as R
        out = R._get_plan_vs_actual("2026-06-24")
        for k in ("deviations", "at_risk"):
            self.assertIn(k, out)
```

- [ ] **Step 2: Run → fail** (`_get_plan_vs_actual` missing)

- [ ] **Step 3: Implement** — add to `ai_report.py`:
```python
def _get_plan_vs_actual(report_date):
    from next_pms.api.weekly_plan import get_plan_for_date
    rd = getdate(report_date)
    plan_name = get_plan_for_date(rd)
    deviations = []
    if plan_name:
        wp = frappe.get_doc("Weekly Plan", plan_name)
        planned = {}
        for a in wp.allocations:
            if a.get("project"):
                planned[(a.project, a.member)] = planned.get((a.project, a.member), 0) + flt(a.planned_hours)
        rows = frappe.db.sql("""select t.project pj, tl.user u, round(sum(tl.duration_hours),2) h
            from `tabPMS Time Log` tl join `tabPMS Task` t on t.name=tl.task
            where tl.is_running=0 and DATE(tl.start_time) between %s and %s and t.project is not null
            group by t.project, tl.user""", (str(wp.week_start), str(rd)), as_dict=True)
        actual = {(r.pj, r.u): flt(r.h) for r in rows}
        for k in set(planned) | set(actual):
            p = planned.get(k, 0); a = actual.get(k, 0)
            if abs(a - p) >= 4:  # only material deviations
                deviations.append({"project": k[0], "person": k[1], "planned": p, "actual": a, "deviation": round(a - p, 2)})
        deviations.sort(key=lambda x: abs(x["deviation"]), reverse=True)
    at_risk = []
    for p in frappe.get_all("PMS Project", filters={"status": ["in", ("Planning", "Active", "On Hold")], "target_close_date": ["is", "set"]},
                            fields=["name", "project_name", "target_close_date"], ignore_permissions=True):
        dd = (getdate(p.target_close_date) - rd).days
        if dd < 0 or dd <= 3:
            at_risk.append({"project": p.project_name or p.name, "close_date": str(p.target_close_date), "days": dd})
    return {"deviations": deviations[:10], "at_risk": at_risk}
```
Then in `_build_report`: `pva = _get_plan_vs_actual(report_date)`, add `full_data["plan_vs_actual"] = pva`, add `"plan_vs_actual": pva` to the return dict; in `get_daily_report_data` return add `"plan_vs_actual": r["plan_vs_actual"]`; in `_send_report_email` template context add `"plan_vs_actual": full_data.get("plan_vs_actual")`.

- [ ] **Step 4: email block** — in `daily_ai_report.html`, after the Client Meetings block:
```html
  {% if plan_vs_actual %}
  <div style="border:1px solid #e5e7eb; border-top:none; padding:24px 32px;">
    <div style="font-size:14px; font-weight:700; color:#1a1a2e; margin-bottom:12px;">Plan vs Actual (Hours)</div>
    {% for d in plan_vs_actual.deviations %}
    <div style="font-size:13px; color:#374151;">{{ d.project }} · {{ d.person }} — planned {{ d.planned }}h, actual {{ d.actual }}h
      (<b style="color:{% if d.deviation > 0 %}#b45309{% else %}#b91c1c{% endif %};">{{ '%+g' % d.deviation }}h</b>)</div>
    {% endfor %}
    {% if plan_vs_actual.at_risk %}
    <div style="margin-top:10px; font-size:12.5px; color:#9a3412; background:#fff7ed; border:1px solid #fcd9b6; border-radius:8px; padding:8px 12px;">
      Delivery at risk: {% for r in plan_vs_actual.at_risk %}{{ r.project }} ({{ r.close_date }}, {{ r.days }}d){% if not loop.last %} · {% endif %}{% endfor %}
    </div>{% endif %}
  </div>
  {% endif %}
```

- [ ] **Step 5: Run → pass**

---

## Task 6: SPA read-only (don't break)

**Files:** Modify `next_pms/frontend/src/views/WeeklyPlanView.vue`

- [ ] **Step 1:** Hide the manager edit path so desk is the editor:
  Change the edit buttons gate from `v-if="canEdit && !editing"` → remove the buttons (or wrap `v-if="false"`). Keep the read-only render. `get_week` still returns allocations (now with a `project` field, but the per-person cards sum fine).
- [ ] **Step 2: build** — `cd frontend && yarn build`; expect success.

---

## Task 7: Workspace shortcuts (desk discoverability)

**Files:** the "Next PMS" Workspace fixture (if present) or create one.

- [ ] **Step 1:** Ensure a desk Workspace for module "Next PMS" has shortcuts: Weekly Plan, Plan vs Actual Hours, Project Progress, PMS Meeting, Meeting Compliance. If no workspace exists, create one (per frappe-erpnext-expert §5b) + `bench export-fixtures --app next_pms`.
- [ ] **Step 2:** migrate + verify shortcuts appear in `/app/next-pms`.

---

## Task 8: Deploy office (maintenance window, after approval)

- [ ] Push. On office: `bench use office`; `git reset --hard origin/main`; **reload_doc** for pms_project, weekly_plan_allocation, weekly_plan_project + the 2 new reports; frontend `yarn build`; restart web + workers. (Full `bench migrate` still blocked by the job-application web-form dup — reload_doc creates the added columns; for the new `target_close_date`/`project`/`target_hours` columns confirm `bench --site office migrate-doctype`? No — reload_doc runs the schema sync for that doctype only, which adds columns.) Verify the 2 reports run + Weekly Plan form shows the project column in allocations.

---

## Self-Review

**Spec coverage:** durable fields (T1) · person×project matrix (T1 allocation.project) · weekly target (T1 project.target_hours) · plan-for-date helper (T2) · Plan vs Actual hours report (T3) · Project Progress incl tasks% + delivery-vs-date (T4) · daily-report block (T5) · SPA read-only (T6) · desk workspace (T7) · deploy (T8). All covered.

**Placeholder scan:** none — full report + ai_report code inline; field JSON snippets exact.

**Type consistency:** `get_plan_for_date` used by T3/T4/T5 (same signature). Allocation key `(project, member)` consistent across report + summary. `target_close_date` used in T4 + T5. `plan_vs_actual` keys `deviations`/`at_risk` match test + template.

**Verify at build:** confirm reload_doc adds the new columns on office (Frappe `reload_doc` runs `sync` which alters the table); if a column doesn't appear, run `bench --site office migrate` is blocked → use `frappe.model.sync.sync_for` or add the column via a patch. Confirm PMS Task open-status set (`["not in",["Done"]]`) matches the status list.
