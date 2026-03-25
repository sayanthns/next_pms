# Next PMS — System Architecture

## Overview

Next PMS is a project management system built as a **Frappe v15 custom app** with a **Vue 3 SPA frontend** and **PWA support**. It serves two audiences:
1. **Internal team** (managers, developers, viewers) — full PMS dashboard at `/next-pms/`
2. **External customers** — read-only client portal at `/next-pms/portal`

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend Framework | Frappe | v15 |
| Backend Language | Python | 3.10+ (local), 3.12 (server) |
| Frontend Framework | Vue | 3.x (Composition API) |
| State Management | Pinia | Latest |
| Routing | Vue Router | 4.x (history mode, base: `/next-pms/`) |
| Build Tool | Vite | Latest |
| Database | MariaDB | 10.6+ |
| Cache | Redis | Queue + Cache |
| Web Server | gunicorn (behind nginx) | |
| Process Manager | Supervisor | |
| PWA | Service Worker + Web Push (VAPID) | |

## End-to-End Request Flow

```
Browser → nginx → gunicorn (Frappe) → Python API → MariaDB
                                    ↑
Vue SPA (static assets served by nginx/Frappe)
```

1. User visits `office.enfono.com/next-pms/dashboard`
2. Frappe serves `index.html` from `next_pms/public/frontend/`
3. Vue Router loads the DashboardView component
4. Component calls `call('next_pms.api.dashboard.get_dashboard_data')` via `utils/frappe.js`
5. Frappe routes to whitelisted Python function
6. Python queries MariaDB, returns JSON
7. Vue renders the data

## File Structure Map

```
next_pms/
├── CLAUDE.md                          # Project memory for Claude Code
├── skills/                            # Agent handoff documentation
├── frontend/                          # Vue 3 SPA
│   ├── index.html                     # SPA entry point
│   ├── package.json                   # Node dependencies
│   ├── vite.config.js                 # Build + dev proxy config
│   └── src/
│       ├── main.js                    # Vue app bootstrap
│       ├── App.vue                    # Root component (admin sidebar layout)
│       ├── router/index.js            # ALL routes + guards (portal redirect, token auth)
│       ├── store/                     # Pinia stores
│       │   ├── settings.js            # Roles, permissions, user flags (CRITICAL)
│       │   ├── projects.js            # Project list/detail state
│       │   ├── tasks.js               # Task list/detail state
│       │   ├── notifications.js       # Notification polling + browser notifs
│       │   ├── timer.js               # Time tracking state
│       │   └── checkin.js             # Check-in/out state
│       ├── utils/
│       │   └── frappe.js              # API wrapper with dedup, TTL cache, CSRF
│       ├── views/                     # Page-level components
│       │   ├── DashboardView.vue      # Home dashboard
│       │   ├── ProjectDetailView.vue  # Project detail (tabs: overview, tasks, backlog, team, files)
│       │   ├── TaskDetailView.vue     # Task detail + comments + files
│       │   ├── TeamView.vue           # Settings: Team, Users, Client Portal, AI
│       │   ├── SupportTicketsView.vue # Admin support tickets table
│       │   ├── PortalAnalyticsView.vue# Portal analytics dashboard (admin)
│       │   └── portal/               # Customer portal views
│       │       ├── PortalLayout.vue   # Left sidebar layout for portal
│       │       ├── PortalDashboard.vue# Customer dashboard with project cards
│       │       ├── PortalProject.vue  # Project detail (milestones, tasks, kanban)
│       │       ├── PortalTickets.vue  # Support tickets (list + kanban + drawer)
│       │       └── PortalReports.vue  # Weekly/monthly progress reports
│       └── components/               # Reusable components
│           ├── KanbanCard.vue         # Kanban board task card
│           ├── SprintBacklog.vue      # Sprint management component
│           ├── CommentThread.vue      # Comment thread with @mentions
│           ├── RichTextEditor.vue     # Description editor
│           └── Timer.vue              # Time tracking widget
├── next_pms/                          # Python backend
│   ├── hooks.py                       # Frappe hooks (doc_events, scheduler, routes)
│   ├── tasks.py                       # Scheduled tasks (reminders, alerts, summaries)
│   ├── api/                           # Whitelisted API endpoints
│   │   ├── portal.py                  # Portal APIs (20+ endpoints, ~1400 lines)
│   │   ├── crud.py                    # Project/task CRUD + cascade delete
│   │   ├── dashboard.py               # Dashboard aggregation
│   │   ├── users.py                   # User/role management
│   │   ├── settings.py                # PMS settings + AI config
│   │   ├── permissions.py             # Permission queries + UI permissions
│   │   ├── timer.py                   # Time log management
│   │   ├── checkin.py                 # Check-in/out
│   │   ├── files.py                   # File + link attachments
│   │   ├── push.py                    # Web Push notifications (VAPID)
│   │   ├── budget.py                  # Budget tracking + forecasting
│   │   ├── gantt.py                   # Gantt chart data
│   │   ├── notifications.py           # In-app notifications
│   │   └── ai_report.py              # AI-powered daily report
│   ├── next_pms/doctype/             # DocType definitions
│   │   ├── pms_project/              # Project model
│   │   ├── pms_task/                 # Task model (includes Support Ticket type)
│   │   ├── pms_sprint/              # Sprint/milestone (approval_status)
│   │   ├── pms_comment/             # Comments (fields: comment, user, task, mentions)
│   │   ├── pms_client_portal_access/ # Portal access tokens
│   │   ├── pms_time_log/            # Time tracking logs
│   │   ├── pms_project_member/      # Project team members (with hourly_rate)
│   │   ├── pms_task_assignee/       # Task assignee child table
│   │   ├── pms_checkin/             # Attendance check-ins
│   │   ├── pms_push_subscription/   # Push notification subscriptions
│   │   ├── pms_link_attachment/     # URL link attachments
│   │   ├── pms_activity_rate/       # Activity-based billing rates
│   │   └── pms_ai_settings/         # AI report configuration
│   └── public/
│       ├── frontend/                 # Built Vue SPA assets (DO NOT edit directly)
│       ├── js/sw.js                  # Service worker for PWA
│       └── manifest.json             # PWA manifest
```

## Key Subsystems

### 1. Role & Permission System
**Roles:** System Manager, Administrator, PMS Manager, PMS Developer, PMS Viewer, PMS Customer
**Base role:** "Next PMS" (required for any PMS access)

```
System Manager / Administrator
    └── Full access to everything
PMS Manager
    └── CRUD on projects, tasks, sprints. Can manage team, budgets, portal.
PMS Developer
    └── Create/edit tasks. Limited to assigned projects. No finance data.
PMS Viewer
    └── Read-only. Can view projects and tasks.
PMS Customer
    └── Portal-only. Redirected from admin routes. Token-based or session access.
```

**Settings store** (`frontend/src/store/settings.js`): Central authority for role checks. Exposes `isAdmin`, `isManager`, `isDeveloper`, `isCustomer`, `canViewFinance`, etc.

### 2. Customer Portal
**Dual access model:**
- **Session-based:** User has `PMS Customer` role, logs in normally, gets redirected to `/portal`
- **Token-based:** URL like `/next-pms/portal?token=XYZ` → `portal_token_login()` creates session

**Key doctype:** `PMS Client Portal Access` — maps `client_email` → `project` with unique `access_token`
**Validation:** `validate_project_portal()` checks `client_portal_enabled` on the project before insert.
**Auto-enable:** `invite_client()` API auto-enables portal on the project before creating access record.

**Portal features:**
- Dashboard with project cards and progress
- Project detail: milestones (clickable with mini kanban), tasks (list + kanban), team, files
- Support tickets: list + kanban, detail drawer with comments, file attachments
- Reports: weekly/monthly project progress

### 3. Support Ticket System
Support tickets are **PMS Tasks** with `task_type = "Support Ticket"` and `created_by_customer = 1`.
- Created via portal's "New Ticket" dialog
- Filtered OUT of the regular Tasks tab in portal project view
- Shown in dedicated Support Tickets page (both portal and admin)
- Admin view: `/next-pms/support-tickets` with stats, filters, table

### 4. Sprint/Milestone Approval Workflow
**Field:** `PMS Sprint.approval_status` (Pending → Ready for Review → Approved/Changes Requested)
**Flow:**
1. Manager marks sprint "Ready for Review" (from ProjectBacklog.vue)
2. Customer sees approval buttons in portal (PortalProject.vue)
3. Customer clicks Approve or Request Changes (with comment)
4. Status updates visible to both sides

### 5. Time Tracking
- Timer widget in header (start/stop per task)
- Time logs stored in PMS Time Log doctype
- Auto-calculates `actual_hours` on PMS Task via doc_event hooks
- Cost calculation: `actual_hours × hourly_rate` from PMS Project Member

### 6. Notification System
- **In-app:** PMS Notification doctype, polled by frontend
- **Web Push:** VAPID-based, stored in PMS Push Subscription, sent via `pywebpush`
- **Email:** Task deadline reminders, budget alerts, weekly summary, AI daily report
- **Portal polling:** 60-second interval for notification badges in portal sidebar

## External Dependencies

| Service | Purpose | Connection Method |
|---------|---------|-------------------|
| MariaDB | Database | Local socket (Frappe manages) |
| Redis | Cache + Queue | Local socket (Frappe manages) |
| SMTP | Email notifications | Configured in Frappe Email Account |
| OpenAI/AI API | Daily AI report | API key in PMS AI Settings doctype |
| Web Push Service | Push notifications | VAPID keys in site_config.json |

## Credential Locations (never values, just locations)

| Credential | Location |
|------------|----------|
| Database password | `frappe-bench/sites/common_site_config.json` |
| VAPID keys | `frappe-bench/sites/office/site_config.json` |
| AI API key | PMS AI Settings doctype (encrypted field) |
| Portal access tokens | PMS Client Portal Access doctype (`access_token` field) |
| SSH (production server) | IP: 156.67.105.6, User: root |
| Frappe admin password | Set via `bench set-admin-password` |

## Production Server Details

| Item | Value |
|------|-------|
| Server IP | 156.67.105.6 |
| SSH User | root |
| App User | v15 (su - v15) |
| Bench Path | /home/v15/frappe-bench |
| Frappe Version | v15 |
| Python Version | 3.12 |
| Sites | office, katcherp, enfono-office-new, spice |
| PMS Site | office |
| Domain | office.enfono.com |
| Process Manager | Supervisor |
| Web Server | nginx → gunicorn |
