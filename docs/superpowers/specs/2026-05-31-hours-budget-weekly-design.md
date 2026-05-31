# Design — Working-Hours Baseline, Mandatory Budget, Saturday Weekly Summary

**Date:** 2026-05-31
**App:** next_pms (Frappe v15.68.1)
**Scope:** Features 2, 3, 4. APK mobile app deferred to its own spec/plan cycle.

## Problem

Reports disagree on "hours worked" because three different sources coexist:

- `office_hours` — from **PMS Checkin** `total_hours` (checkin/checkout in-out).
- `logged_hours` — from **PMS Time Log** `duration_hours` (the timer).
- `actual_hours` / `estimated_hours` — task fields.

`productivity.py` computes `avg_hours_per_day` from checkin in-out; `ai_report.py _build_user_metrics` also pulls `office_hours` from checkin while logging timer hours separately; productivity % is `actual/estimated`. No single baseline → numbers differ between the Employee Productivity report, AI daily report, project status emails, and weekly summary.

## Decisions (locked with user)

1. **APK** — deferred. Separate spec/plan, reuse fatehhr Capacitor pattern.
2. **Baseline** — fixed daily working hours, **configurable, default 8**, stored in a settings single. Reports compare **timer hours vs (8 × working days)** as utilization %. Checkin in-out dropped as the work-hours baseline.
3. **Budget** — `total_budget` required and **> 0 on new projects only**. Existing projects grandfathered.
4. **Weekly summary** — Saturday. Per active member: own stats. `sayanth@enfono.in`: all-members table.
5. **Settings home** — reuse **PMS AI Settings** single (no new doctype).

## Feature 3 — Mandatory budget

- Field: `total_budget` (Currency) on **PMS Project**.
- `next_pms/next_pms/doctype/pms_project/pms_project.py` `validate()`:
  ```python
  if self.is_new() and flt(self.total_budget) <= 0:
      frappe.throw(_("Total Budget is required and must be greater than 0"))
  ```
- Doctype JSON: `total_budget` gets `"reqd": 1`.
- Frontend create dialog `frontend/src/components/CreateProjectModal.vue`: mark `total_budget` input required, block submit if empty/≤0. (`EditProjectModal.vue` left unchanged — grandfathering.)
- Grandfather: `is_new()` guard → edits/saves on existing budget-less projects still pass.

## Feature 2 — Fixed 8h baseline, consistent everywhere

### New shared module: `next_pms/api/_hours.py`
Single source of truth for working-day + target math. Lift these out of `productivity.py`:
- `working_days_in_range(from_date, to_date)` — non-Sunday dates.
- `get_holiday_dates(holiday_list, from_date, to_date)`.
- `get_leave_dates(employee, from_date, to_date)` — approved leaves.
- `get_employee_for_user(user)`.

Add:
- `get_working_hours_per_day()` → reads `PMS AI Settings.working_hours_per_day`, falls back to `8.0`.
- `effective_working_days(user, from_date, to_date)` → working_days minus holidays minus approved-leave days.
- `compute_target_hours(user, from_date, to_date)` → `len(effective_working_days) × get_working_hours_per_day()`.
- `compute_utilization(logged_hours, target_hours)` → `round(logged/target*100, 1)` (0 if target 0).

`productivity.py` re-imports these (keep its thin wrappers or update call sites) so there is no duplicate logic.

### New setting on PMS AI Settings
- `working_hours_per_day` — Float, default `8`.

### Report changes (timer = `PMS Time Log.duration_hours` is the only hours source for comparison)
- **`productivity.py` `get_employee_productivity`** — replace `avg_hours_per_day` (checkin-derived) headline with **utilization vs target** (`total_logged_hours / compute_target_hours`). Day-wise rows: keep `logged_hours`; `office_hours` (checkin) becomes informational/optional, not the baseline.
- **`ai_report.py _build_user_metrics`** — utilization computed against target hours, not `office_hours`. Checkin times may still display as info; they no longer drive productivity.
- **`project_report.py`** — any per-member hours shown use the same helper for target/utilization.
- **Weekly summary** (Feature 4) — uses the same helper.

## Feature 4 — Saturday weekly summary

- **Schedule:** remove `send_weekly_summary` from `scheduler_events["weekly"]`; add cron `"0 7 * * 6"` → `next_pms.tasks.send_weekly_summary` (Saturday 07:00).
- **New setting:** `weekly_summary_recipient` on PMS AI Settings, default `sayanth@enfono.in`.
- **Rewrite `send_weekly_summary`** from per-manager-per-project to **per active member**:
  - **Week window (explicit):** Monday 00:00:00 of the current week → the run moment (Saturday 07:00). Captures Mon–Fri fully plus early Saturday. Uses `frappe.utils.get_first_day_of_week`/`getdate` math, not in-out.
  - **Active member** = PMS user with ≥1 `PMS Time Log` this week, unioned with active `PMS Project Member` users.
  - **Per member email:** hours logged this week, target (`compute_target_hours`), utilization %, tasks completed, tasks in-progress, projects touched.
  - **All-team email** to `weekly_summary_recipient`: table with one row per member (name, logged, target, util%, tasks done).
- HTML builders: `_build_member_weekly_html(member, stats)` and `_build_team_weekly_html(rows)`.

## Cross-cutting

- `next_pms/api/_hours.py` is the root fix — all reports derive working days + target from it.
- PMS AI Settings (Single): doctype JSON gains `working_hours_per_day` + `weekly_summary_recipient`. Values are site data, not fixtures.
- `hooks.py scheduler_events` cron block updated.

## Testing

- `next_pms/api/test_hours.py` — `compute_target_hours` with Sundays + holidays + approved leaves; `get_working_hours_per_day` fallback; `compute_utilization` zero-target.
- `pms_project` test — new project with budget ≤ 0 throws; existing budget-less project saves; new project with budget > 0 passes.
- Weekly summary test — recipient split (member gets own; configured recipient gets all-team rows); active-member detection.

## Out of scope

- APK / Capacitor / native mobile (separate cycle).
- Migrating historical checkin data.
- Changing how the timer itself records `duration_hours`.

## Files touched

| File | Change |
|------|--------|
| `next_pms/api/_hours.py` | NEW — shared working-days + target-hours helpers |
| `next_pms/api/productivity.py` | Use `_hours.py`; utilization vs target replaces checkin-based avg |
| `next_pms/api/ai_report.py` | `_build_user_metrics` utilization vs target |
| `next_pms/api/project_report.py` | Per-member hours via shared helper |
| `next_pms/tasks.py` | Rewrite `send_weekly_summary` (per-member + all-team) |
| `next_pms/hooks.py` | Move weekly → cron `0 7 * * 6` |
| `next_pms/next_pms/doctype/pms_ai_settings/pms_ai_settings.json` | + `working_hours_per_day`, `weekly_summary_recipient` |
| `next_pms/next_pms/doctype/pms_project/pms_project.py` | budget reqd>0 on new |
| `next_pms/next_pms/doctype/pms_project/pms_project.json` | `total_budget` reqd |
| `frontend/src/components/CreateProjectModal.vue` | budget required in UI |
| `next_pms/api/test_hours.py` + project/weekly tests | NEW tests |
