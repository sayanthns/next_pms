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
