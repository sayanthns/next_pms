# Design — SO Mandatory, 95% Budget Guard, Working-Hours in UI

**Date:** 2026-05-31
**App:** next_pms (Frappe v15 + Vue 3 SPA). ERPNext installed (Sales Order available).
**Scope:** Three related additions, to ship + deploy before the Android APK work.
Builds on the 2026-05-31 hours/budget/weekly batch (already deployed to office.enfonoerp.com).

## Decisions (locked with user)

| # | Decision |
|---|----------|
| SO field | Link → ERPNext `Sales Order`, `reqd:1`, enforced **new projects only** (grandfather existing). Compare against SO **grand_total** (incl. tax). |
| SO comparison shown in | Project status email + Project dashboard (in-app) + Multi-project report (all three). |
| 95% block | Block **new time entries** (timer start AND manual log insert) when `budget_utilization >= 95`. Running timer can still stop/save; task details editable. |
| Approval | "Request budget increase" → emails **sayanth@enfono.in** (fixed). Unblock is **automatic** when sayanth raises `total_budget` → utilisation drops < 95%. No override doctype. |
| Hours-in-UI | Surface `working_hours_per_day` + `weekly_summary_recipient` (added to PMS AI Settings doctype last batch but NOT in the SPA) in the Team → AI Settings tab. |

## A. Working-hours setting in the UI (fixes deployed gap)

Last batch added `working_hours_per_day` + `weekly_summary_recipient` to the **PMS AI Settings doctype**, but the SPA "AI Settings" tab is a hand-built form (`TeamView.vue` + `settings.py` get/save) — doctype fields don't auto-appear. So the setting is live in backend, not editable in-app.

- **`next_pms/api/settings.py`**:
  - `get_ai_settings`: add `working_hours_per_day` (default 8) + `weekly_summary_recipient` (default sayanth@enfono.in) to the returned dict (+ the except fallback).
  - `save_ai_settings`: add `working_hours_per_day=None`, `weekly_summary_recipient=None` params; `if not None: doc.<field> = ...` (guard with `hasattr`). Coerce hours via `flt`.
- **`frontend/src/views/TeamView.vue`** AI Settings tab: add a **"Working Hours & Weekly Summary"** subsection — number input (`working_hours_per_day`, min 1, step 0.5, default 8) + email input (`weekly_summary_recipient`), included in the existing Save AI Settings call payload.

## B. Sales Order mandatory + 3-way comparison

### Field + enforcement
- **`pms_project.json`**: new field `sales_order`, Fieldtype `Link`, Options `Sales Order`, `reqd:1`, placed in/near the budget section.
- **`pms_project.py`** `validate()`: add `validate_sales_order()` —
  ```python
  if self.is_new() and not self.sales_order:
      frappe.throw(_("Sales Order is required"))
  ```
  (new-only; existing projects grandfathered, same as budget). The Link field already enforces existence.
- **`CreateProjectModal.vue`**: add a required Sales Order field (link-search via `frappe.client.get_list`/existing link-picker pattern), passed to `create_project`. `crud.create_project` must accept + set `sales_order`.

### Financials helper
- **`next_pms/api/project_report.py`** (or a small shared `_financials` fn): `get_project_financials(project)` returns:
  ```
  { so_value: Sales Order.grand_total (0 if no SO),
    budget: total_budget,
    actual: calculated_cost,
    budget_util: budget_utilization,          # actual/budget %
    so_util: round(actual/so_value*100,1) }   # actual vs SO value %
  ```
  Read SO value with `frappe.db.get_value("Sales Order", project.sales_order, "grand_total")`.

### Surfaces (all three)
- **Project status email** (`project_report.py` `get_project_report_data` + its HTML): add an SO / Budget / Actual / Util row.
- **Multi-project report** (`get_multi_project_report_data` + HTML): add SO, Budget, Actual columns per project.
- **Project dashboard in-app**: `ProjectDashboard.vue` (or project detail financial card) shows SO value vs Budget vs Actual + both util %s. New/extended whitelisted reader if needed (e.g. add fields to existing project fetch).

## C. 95% budget guard + approval

### Block (covers timer + manual)
- **`PMS Time Log` controller** (`pms_time_log.py`) `before_insert`:
  ```python
  # Block NEW time entries (timer start or manual) when the project budget is exhausted.
  # Stopping/updating an existing running timer is an UPDATE, not insert → not blocked.
  if self.task:
      project = frappe.db.get_value("PMS Task", self.task, "project")
      if project:
          util = flt(frappe.db.get_value("PMS Project", project, "budget_utilization"))
          if util >= 95:
              frappe.throw(_("Project budget at {0}% (>= 95%). New time entries are blocked until the budget is increased. Use 'Request budget increase'.").format(round(util)), title=_("Budget Exhausted"))
  ```
  This single guard covers `start_timer` (inserts a running log) and any manual log insert. `stop_timer` updates the existing log → unaffected.
- `budget_utilization` is kept fresh by the existing `on_time_log_change` doc_event (recomputes project cost). At `before_insert` it reflects state before this entry — correct for a threshold gate.

### Approval request
- **`next_pms/api/budget.py`** (existing) new whitelisted `request_budget_increase(project)`:
  - Reads project name, `total_budget`, `calculated_cost`, `budget_utilization`, requester (`frappe.session.user`).
  - `frappe.sendmail(recipients=["sayanth@enfono.in"], subject=_("Budget increase request: <project>"), message=<html with figures + requester + link>, now=True)`.
  - Returns `{success:True}`.
- **Frontend**: when a timer-start / time-log call throws the "Budget Exhausted" error, show a "Request budget increase" button → calls `request_budget_increase` → toast/alert "Request sent to sayanth@enfono.in".

### Unblock
- Automatic. sayanth raises `total_budget` (desk or in-app project edit) → `calculate_project_cost` recomputes `budget_utilization < 95` → next insert passes. No flag, no doctype.

## Testing

- **SO:** new project without `sales_order` throws; with SO inserts; existing project (sales_order empty) still saves (grandfather). `get_project_financials` math (so_value/budget/actual/utils; 0-SO safe).
- **Budget guard:** PMS Time Log insert blocked when project `budget_utilization=95` (and 96), allowed at 94; updating an existing running log (stop) at 96% still works.
- **Approval:** `request_budget_increase` calls sendmail to sayanth@enfono.in with the figures (assert recipients/subject via a mail-capture or monkeypatch).
- **Settings:** `get_ai_settings`/`save_ai_settings` round-trip `working_hours_per_day` + `weekly_summary_recipient`.
- Web build still compiles (TeamView + CreateProjectModal changes).

## Files

| File | Change |
|------|--------|
| `next_pms/api/settings.py` | get/save AI settings: + working_hours_per_day, weekly_summary_recipient |
| `frontend/src/views/TeamView.vue` | AI Settings tab: Working Hours & Weekly Summary section |
| `next_pms/next_pms/doctype/pms_project/pms_project.json` | + `sales_order` Link(Sales Order) reqd |
| `next_pms/next_pms/doctype/pms_project/pms_project.py` | `validate_sales_order` (new-only) |
| `next_pms/api/crud.py` | `create_project` accepts + sets `sales_order` |
| `frontend/src/components/CreateProjectModal.vue` | required Sales Order picker |
| `next_pms/api/project_report.py` | `get_project_financials` + SO row in project + multi-project reports |
| `frontend/src/views/ProjectDashboard.vue` (or project detail) | SO vs Budget vs Actual card |
| `next_pms/next_pms/doctype/pms_time_log/pms_time_log.py` | `before_insert` 95% budget guard |
| `next_pms/api/budget.py` | `request_budget_increase(project)` endpoint |
| `frontend` timer/error handling | "Request budget increase" button on Budget Exhausted error |
| tests | pms_project (SO), pms_time_log (guard), budget (request), settings round-trip |

## Out of scope
- Changing how budget_utilization is computed (reuse existing calculate_project_cost).
- Multi-SO per project (single Link).
- SO auto-sync of budget from SO value (budget stays manual).
- APK (next cycle — spec already written: `2026-05-31-android-apk-design.md`).
