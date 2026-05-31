# Next PMS - Project Memory

> **READ `skills/` BEFORE ANY OPERATION.** The skills directory contains critical safety rules, architecture docs, operations guides, and troubleshooting patterns that prevent production incidents.

## Skill Index

| Skill | Path | Read When |
|-------|------|-----------|
| **Safety Rules** | `skills/safety/SKILL.md` | BEFORE making ANY change |
| **Architecture** | `skills/architecture/SKILL.md` | When you need to understand how the system works |
| **Operations** | `skills/operations/SKILL.md` | When building, deploying, or debugging |
| **Troubleshooting** | `skills/troubleshooting/SKILL.md` | When something breaks |
| **Session Logs** | `skills/session-logs/` | To see what was done in previous sessions |

## Top 5 Rules That Prevent Production Incidents

1. **PMS Comment fields are `comment` and `user`** — NOT `content` and `author`. This has caused multiple production bugs.
2. **All portal `frappe.get_all()` calls need `ignore_permissions=True`** — PMS Customer users lack doctype read permissions.
3. **Never use `frappe.get_doc()` in portal APIs** — use `frappe.db.get_value()` or `frappe.get_all()` with ignore_permissions.
4. **Always `bench use office` before migrate on server** — 4 sites exist, wrong site = wrong database.
5. **Frontend deploy = `cd frontend && yarn build`** — NOT `bench build`. They are completely different.

## Confirmed Features (Deployed & Tested on Server)

### March 2026

- **Web Push Notifications** (Mar 15) — VAPID-based push for task events (assignment, status change, comments). Service worker handles display + click navigation. Config in site_config.json.

- **Push Notification Enable Banner** (Mar 15) — Banner for new/iOS users + "Enable Push Notifications" option in mobile More menu.

- **Task Header Mobile Layout Fix** (Mar 16) — 3-row layout for task detail header on mobile (priority+status, title, actions).

- **@Mention in Comments** (Mar 17) — Type `@` in comment textarea to search/select project team members. Tagged users get push + email notifications. Uses `mentions` field on PMS Comment (comma-separated emails). Keyboard nav with arrow keys, Enter, Escape.

- **Link Attachments in Tasks** (Mar 17) — "File" and "Link" buttons in task attachments section. Link form has URL + optional Title. Saved as PMS Link Attachment doctype. Fixed null title issue (conditional arg inclusion).

- **Link Attachments in Projects** (Mar 17) — Same link attachment feature in project Files tab. Added `project` field to PMS Link Attachment doctype. Separate APIs: `save_project_link`, `get_project_links`, `delete_project_link`.

- **Customer Portal Phase 1** (Mar 17) — Token-based client portal with left sidebar layout, dashboard (project cards with progress), project detail (milestones, tasks, team, files tabs), support tickets page. Portal routes under `/portal` with PortalLayout.vue wrapper. Token login via `portal_token_login()` API + router guard.

- **Customer Portal Phase 2** (Mar 18) — Client Portal management tab in TeamView (role-based invite using PMS Customer users from dropdown), sprint approval badges in ProjectBacklog/SprintBacklog, Support Ticket task type styling, Portal Analytics admin dashboard.

- **Customer Portal Phase 3** (Mar 18) — Notification polling (60s) with badge indicators, email notification wiring for ticket responses via PMS Comment after_insert, clickable milestones with mini kanban boards, task/ticket detail drawers with comments, kanban view toggle for tasks and tickets, file attachment support for new tickets (drag & drop), customer Reports page (weekly/monthly project progress), dedicated Support Tickets admin page in PMS sidebar, route guard redirecting PMS Customer users from admin routes to portal.

### Late March 2026

- **Portal toggle moved to Edit Project dialog** (Mar 19) — Client Portal enable toggle relocated from project header to the Edit Project dialog. Portal access now auto-enables BEFORE creating the access record (the doctype `validate()` checks the flag pre-insert). Grant Access dropdown shows ALL projects and auto-enables portal on grant.

- **AI Daily Report skips weekends/holidays** (Mar 26) — `generate_daily_report` (3 AM cron) skips Sundays and holidays via `_should_skip_report()`. Weekend logic = Sunday-only skip (KSA work week). PMS Task import enabled.

- **Department field + Project Favorites** (Mar 28–30) — `department` field on PMS user profile (looked up via Employee, not direct). Per-user project favorites via **PMS Favorite Project** doctype (favorites persist; permission fixes so each user manages own). Project list has a department filter showing only enabled departments. Design spec: `docs/superpowers/specs/2026-03-28-department-favorites-design.md`.

- **Urgent + Normal priorities** (Mar 31) — PMS Task `priority` options now: `Low / Normal / Medium / High / Urgent / Critical`.

### April 2026

- **Daily Project Status Report email** (Apr 2) — Per-project status report emailed to configured recipients. APIs in `next_pms/api/project_report.py`: `get_project_report_data`, `send_project_report`, `get_project_report_recipients`. Sent by `send_scheduled_project_reports` cron (8 AM, Mon–Sat).

- **Multi-Project Combined Report + saved configs** (Apr 2) — Combine multiple projects into one report with named, reusable configs (**PMS Report Config** + child **PMS Report Config Project**). APIs: `get_multi_project_report_data`, `send_multi_project_report`, `get_report_configs`, `save_report_config`, `delete_report_config`. Auto-send via `send_scheduled_multi_project_reports` cron. UI: `ReportConfigModal.vue`, `SendReportModal.vue`.

- **Fix: admin/manager with PMS Customer role redirect** (Apr 6) — Users holding BOTH admin and PMS Customer roles no longer wrongly redirected to portal.

- **Employee Productivity Report** (Apr 27–28) — New tab in Task Report (`EmployeeProductivityTab.vue`, `TaskReportView.vue`). API `get_employee_productivity(user, period_days)` in `next_pms/api/productivity.py`: day-wise hours, overall summary row, working-days calc that **excludes approved leaves and public holidays** (reads Employee → Holiday List + Leave Application). `get_productivity_users` lists reportable users.

## Customer Portal Architecture

- **Dual access**: Session-based (PMS Customer role login) + Token-based (allow_guest URLs with access_token)
- **PMS Client Portal Access** doctype: maps client_email → project with unique access_token + is_active flag
- **Portal APIs** (`next_pms/api/portal.py`): 20+ whitelisted endpoints with `_verify_portal_access()` guard and `ignore_permissions=True` on all customer-facing queries
- **Support Tickets**: PMS Tasks with `task_type = "Support Ticket"` and `created_by_customer = 1`
- **Milestones**: PMS Sprints with `approval_status` field (Pending/Ready for Review/Approved/Changes Requested)
- **Route guard**: `router.beforeEach` checks `settingsStore.isCustomer` and redirects non-portal routes to `/portal`
- **PMS Roles**: Manager, Developer, Viewer, Customer — Customer role blocks access to admin dashboard

## Architecture Notes

- **Backend**: Frappe v15, Python, bench CLI
- **Frontend**: Vue 3 SPA, Pinia stores, Vue Router (base `/next-pms/`)
- **PWA**: Service worker with cache strategies, Web Push API
- **Build**: `bench build --app next_pms` (Frappe bundle) + `cd frontend && yarn build` (Vue SPA)
- **Deploy**: git pull → bench migrate → bench build → yarn build → supervisorctl restart

### Scheduled Jobs (`hooks.py`)

| Schedule | Method | Purpose |
|----------|--------|---------|
| daily | `next_pms.tasks.send_deadline_reminders` / `check_budget_alerts` | Deadline + budget alerts |
| hourly | `next_pms.tasks.check_long_running_timers` | 4h+ timer warnings |
| weekly | `next_pms.tasks.send_weekly_summary` | Weekly summary |
| `0 3 * * *` | `api.ai_report.generate_daily_report` | LLM daily work summary (skips Sun/holidays) |
| `0 8 * * 1-6` | `api.project_report.send_scheduled_project_reports` + `send_scheduled_multi_project_reports` | Project status emails, Mon–Sat |

`doc_events`: PMS Time Log (after_insert/on_update/on_trash → cost recalc), PMS Task (on_update). `permission_query_conditions`: PMS Project, PMS Task.

### DocTypes (`next_pms/next_pms/doctype/`)

Core: PMS Project, PMS Task, PMS Sprint, PMS Time Log, PMS Project Member, PMS Task Assignee, PMS Comment, PMS Link Attachment.
Portal: PMS Client Portal Access.
Reporting: PMS Report Config (+ child PMS Report Config Project).
Other: PMS Favorite Project, PMS Checkin, PMS Activity Rate, PMS AI Settings, PMS Push Subscription.

## Key Files

| Area | Path |
|------|------|
| Vue Entry | `frontend/src/main.js` |
| Router | `frontend/src/router/index.js` |
| Frappe API Wrapper | `frontend/src/utils/frappe.js` |
| Stores | `frontend/src/store/*.js` |
| Backend APIs | `next_pms/api/*.py` |
| DocTypes | `next_pms/next_pms/doctype/` |
| Hooks | `next_pms/hooks.py` |
| Service Worker | `next_pms/public/js/sw.js` |
| PWA Manifest | `next_pms/public/manifest.json` |
| Portal APIs | `next_pms/api/portal.py` |
| Portal Layout | `frontend/src/views/portal/PortalLayout.vue` |
| Portal Dashboard | `frontend/src/views/portal/PortalDashboard.vue` |
| Portal Project | `frontend/src/views/portal/PortalProject.vue` |
| Portal Tickets | `frontend/src/views/portal/PortalTickets.vue` |
| Portal Reports | `frontend/src/views/portal/PortalReports.vue` |
| Portal Analytics (Admin) | `frontend/src/views/PortalAnalyticsView.vue` |
| Support Tickets (Admin) | `frontend/src/views/SupportTicketsView.vue` |
| Reports View | `frontend/src/views/ReportsView.vue` |
| Task / Productivity Report | `frontend/src/views/TaskReportView.vue` + `components/EmployeeProductivityTab.vue` |
| Report Config / Send modals | `frontend/src/components/ReportConfigModal.vue`, `SendReportModal.vue` |
| Productivity API | `next_pms/api/productivity.py` |
| Project Report API | `next_pms/api/project_report.py` |
| AI Daily Report API | `next_pms/api/ai_report.py` |
| Check-in API | `next_pms/api/checkin.py` |

## Deployment Checklist

1. `cd apps/next_pms && git pull`
2. `bench use <site>` (if multi-site — server has: office, katcherp, enfono-office-new, spice)
3. `bench migrate`
4. `bench build --app next_pms`
5. `cd apps/next_pms/frontend && yarn && yarn build`
6. `sudo supervisorctl restart all`

## Standing Rules

- **No commits without user confirmation** — always ask before committing
- **Git branch**: `feature/customer-portal` for testing, merge to `main` when confirmed
- **Server deployment**: `cd apps/next_pms/frontend && yarn build` (NOT `bench build`)
- **Multi-site Frappe**: must use `bench use office` before migrate on production server
- **Local dev site**: `mysite.local` (NOT `office`)
- **Admin login**: Administrator / admin
- **Customer test**: `client@example.com` (PMS Customer role, token-based portal access)

## Known Issues / Gotchas

- Server has multiple sites — always `bench use office` before migrate
- `bench migrate` may fail on unrelated apps (HRMS duplicate route, frappe_appointment form tour) — next_pms doctypes usually sync before the error
- Frappe API doesn't handle `null` params well — use conditional arg inclusion instead
- Browser may cache old Vue bundle — hard refresh (Cmd+Shift+R) after deploy
- Portal APIs need `ignore_permissions=True` for all `frappe.get_all` calls accessed by PMS Customer users
- PMS Comment table uses `comment` and `user` fields (NOT `content` and `author`)
- Preview dev server (port 8081) can't authenticate with Frappe — test via production build at `localhost:8000`
