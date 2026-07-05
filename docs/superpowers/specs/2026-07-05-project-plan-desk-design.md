# Project Plan (ERP desk) — design spec

**Date:** 2026-07-05
**App:** next_pms (Frappe v15), office bench
**Status:** Approved for planning
**Goal:** Bring the weekly allocation Excel into the ERP as a desk-managed **Project Plan**, then **automatically track daily deviation & progress** against it (hours, tasks, delivery date) and surface it in reports + the daily email.

## Locked decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Plan atomic unit | **Person × Project × planned hours** per week (the Excel Allocations/Matrix) |
| Home | **Frappe desk** (no SPA editing). SPA Weekly Plan tab → read-only viewer |
| Project attributes | **Hybrid**: durable on project master + weekly override |
| Daily tracking measures | (1) planned vs actual **hours**, (2) **task/milestone** completion, (3) **delivery vs target date**. All **automatic** — no manual % entry |

## Data model

### A. Durable — `PMS Project` (persists week to week)
- `meeting_days` (Table MultiSelect → Weekday) + `meeting_coordinator` — **exist**.
- `target_close_date` (Date) — **new**. Committed delivery/closure date (ties to finance closure).
- `status` — exists.

### B. Weekly plan (desk) — evolve the existing `Weekly Plan` doctype
`Weekly Plan` (parent): `week_start` (Mon, unique), `week_end`, `title`, `published`. (exists)

Two child grids:
1. **Weekly Plan Allocation** (RESTRUCTURE) → the person×project matrix. Fields:
   - `project` (Link PMS Project, reqd) — **new**
   - `member` (Link User, reqd) — exists
   - `planned_hours` (Float) — exists
   - drop `tasks`, `capacity_hours` no longer needed here (capacity → By Person report from user master/40 default)
   - One row per project+person. Rolls up per-person (sum over projects) + per-project (sum over people).
2. **Weekly Plan Project** (per project this week). Fields:
   - `project` (Link PMS Project, reqd), `project_name` (fetch), `focus` (Data, weekly), `target_hours` (Float, weekly), `status` (Data/Select, defaults from master, weekly override).
   - drop `team` (now derived from allocations), `effort`→`target_hours`, keep health optional.

> Migration: the seeded 22-Jun plan uses the old allocation shape (member/hours/tasks, no project). It's historical — a patch backfills `project=NULL` rows as-is (they still sum per-person). New weeks use the matrix. No data loss.

### C. Actuals source (existing)
`PMS Time Log` (user, task→project, duration_hours, start_time) → actual hours per project+person. `PMS Task` (project, status, assigned_to) → task completion.

## Daily tracking — 2 desk reports + daily email

### Report 1 — **Plan vs Actual (Hours)** (Script Report)
Filter: week (default current). For the week's `Weekly Plan`:
- Rows: per **project × person**. Columns: Planned (from Allocation) · Actual (Time Logs sum, `week_start`..today, cumulative) · Deviation (Actual−Planned) · % consumed.
- Rollups: per-person total (overload flag if Σactual or Σplanned > capacity), per-project total.
- "Unplanned actuals" surfaced: logged hours on project/person with no plan row.

### Report 2 — **Project Progress** (Script Report)
Per active project:
- Planned target hours vs actual (this week) · % of target consumed.
- Tasks: done vs open (from PMS Task) → **% complete**.
- **Delivery:** `target_close_date` vs today → days remaining / overdue → **On track / At risk / Overdue** (at-risk if overdue, or ≤3 days with <80% tasks done).

### Report 3 — Daily AI report (extend `ai_report._build_report`)
Add a **Plan vs Actual** block to `full_data` + email: top hours deviations (over/under vs plan) + projects **at risk by target date**. (Meeting summary already added.)

## Desk surfacing
- `Weekly Plan` form: enter the two grids (Allocations matrix + Projects). Duplicate last week to carry forward.
- The 2 reports under the module.
- **Workspace** "Next PMS" (or add shortcuts): Weekly Plan, Plan vs Actual (Hours), Project Progress, PMS Meeting.

## SPA (next_pms) — read-only, don't break
- `get_week` API: adapt to new allocation shape — return allocations grouped **per person** (sum over projects) so the existing WeeklyPlanView cards still render; add a per-project rollup. Editor (`WeeklyPlanEditor`) → make read-only or hide the edit button (desk is the editor now).
- Keep the `/weekly-plan` tab as a read-only viewer.

## Testing
- Weekly Plan controller (week_end/title) — exists.
- Report 1: planned vs actual math on a seeded week (plan rows + time logs) → deviation correct; rollups.
- Report 2: task % + delivery status (on-track/at-risk/overdue) on seeded data.
- ai_report plan-vs-actual block: shape + values with a seeded plan.

## Deploy
Office: reload_doc changed doctypes (weekly_plan_allocation, weekly_plan_project, pms_project) + 2 new reports + patch for target_close_date; git reset for ai_report.py; restart web+workers. New doctypes/fields via reload_doc (full `bench migrate` still blocked by the job-application web-form dup — separate fix). Maintenance window for the restart.

## Out of scope (YAGNI)
- Manual daily % entry (rejected).
- SPA editing (desk only).
- Auto-generation of meeting occurrences (manual, chosen earlier).
