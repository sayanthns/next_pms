# Next PMS - IT Project Management System

A comprehensive project management system built on the Frappe Framework, designed for IT services companies. Inspired by Zoho Sprints.

## Features

### Project Management
- Project creation with budget tracking, team management, and client settings
- Sprint-based workflow (Planning → Active → Completed)
- Task management with Kanban board (Backlog → To Do → In Progress → In Review → Done)
- Gantt chart visualization with drag-to-reschedule
- Sprint backlog planning with drag-and-drop

### Time Tracking
- One-click timer start/stop on any task
- Live elapsed time display with localStorage persistence
- Automatic cost calculation based on hourly rates
- Timer running alerts (4+ hours)
- Keyboard shortcut: Press `T` to toggle timer

### Budget & Cost Management
- Automatic cost calculation: task cost = actual hours x hourly rate
- Project budget tracking with utilization percentage
- Budget alerts at 80%+ utilization
- Cost breakdown by team member, task type, and sprint
- Budget forecast based on burn rate

### Client Portal
- Token-based access (no ERPNext login required)
- Project progress overview, sprint status, task list
- View-only timeline
- Client can post comments on tasks
- No internal cost/budget data exposed
- Mobile responsive

### Real-time Updates
- Live Kanban board updates via Socket.io
- Task assignment notifications
- Budget alert notifications
- Client comment notifications
- Timer reminders

### Reports & Analytics
- Project dashboard with task status breakdown
- Budget utilization reports
- Team workload and utilization view
- Cost per developer analysis
- Sprint progress tracking

## Tech Stack

- **Backend:** Python 3, Frappe Framework v15
- **Frontend:** Vue 3 + Vite + Pinia
- **Database:** MariaDB (via Frappe ORM)
- **Real-time:** Frappe Socket.io
- **Charts:** frappe-gantt, Frappe Charts

## Installation

### Prerequisites
- Frappe Bench installed and configured
- ERPNext v15 (optional - Next PMS has no module dependencies)
- Node.js 18+
- Python 3.10+

### Install

```bash
# Get the app
bench get-app https://github.com/your-org/next_pms.git

# Install on your site
bench --site your-site.local install-app next_pms

# Build assets
bench build --app next_pms

# Build Vue frontend
cd apps/next_pms/frontend
npm install
npm run build

# Rebuild bench assets
cd ../../../
bench build --app next_pms
```

### Create Demo Data (Optional)

```bash
bench --site your-site.local console
>>> from next_pms.setup.demo_data import create_demo_data
>>> create_demo_data()
```

## Access Points

| URL | Description |
|-----|-------------|
| `/next-pms` | Vue 3 SPA (main frontend) |
| `/app/pms-dashboard` | Frappe Desk dashboard |
| `/app/pms-project` | Project list (Desk) |
| `/app/pms-task` | Task list (Desk) |
| `/pms-portal?token=XXX` | Client portal (no login needed) |

## DocTypes

| DocType | Description |
|---------|-------------|
| PMS Project | Projects with budget, team, client portal settings |
| PMS Project Member | Child table - team members with hourly rates |
| PMS Sprint | Sprint planning with date ranges |
| PMS Task | Tasks with Kanban status, cost tracking |
| PMS Time Log | Timer entries with duration auto-calculation |
| PMS Comment | Task comments with @mentions |
| PMS Activity Rate | Billing rates per activity |
| PMS Client Portal Access | Token-based client portal access |

## Roles

| Role | Access |
|------|--------|
| PMS Manager | Full CRUD on all PMS doctypes |
| PMS Developer | Own tasks, own time logs, read project |
| PMS Viewer | Read-only on assigned projects |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `T` | Start/stop timer on current task |
| `D` | Mark current task as Done |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `next_pms.api.timer.start_timer` | Start a timer for a task |
| `next_pms.api.timer.stop_timer` | Stop a running timer |
| `next_pms.api.timer.get_running_timer` | Get current user's running timer |
| `next_pms.api.dashboard.get_project_dashboard` | Project dashboard data |
| `next_pms.api.dashboard.get_all_projects_summary` | All projects overview |
| `next_pms.api.gantt.get_gantt_data` | Gantt chart data |
| `next_pms.api.gantt.update_task_dates` | Update task dates from Gantt |
| `next_pms.api.portal.get_client_portal_data` | Client portal data (guest) |
| `next_pms.api.portal.post_client_comment` | Client comment (guest) |
| `next_pms.api.budget.recalculate_project_budget` | Force budget recalculation |
| `next_pms.api.budget.get_budget_forecast` | Budget forecast |
| `next_pms.api.budget.get_cost_breakdown` | Detailed cost breakdown |
| `next_pms.api.notifications.get_notifications` | Get unread notifications |

## Development

### Frontend Development

```bash
cd apps/next_pms/frontend
npm install
npm run dev   # Starts Vite dev server on port 8081
```

### Build for Production

```bash
cd apps/next_pms/frontend
npm run build
cd ../../../
bench build --app next_pms
```

## License

MIT
