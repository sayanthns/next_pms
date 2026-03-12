# Next PMS - Permissions & Role Management

This document explains how roles, permissions, and feature access work in Next PMS.

## Roles

Next PMS uses a layered role system built on top of Frappe's role framework.

### Base Role

| Role | Purpose |
|------|---------|
| **Next PMS** | Base role assigned to every PMS user. Required to appear in team settings and access the app. |

Every user who needs PMS access must have the "Next PMS" role. It is automatically assigned when PMS access is toggled on.

### Functional Roles

| Role | Access Level |
|------|-------------|
| **PMS Manager** | Full CRUD on assigned projects, team management, budget visibility, reports |
| **PMS Developer** | Work on assigned tasks, own time logs, restricted defaults |
| **PMS Viewer** | Read-only access to assigned projects |
| **PMS Customer** | Client portal access to assigned projects |

Role hierarchy: **Administrator > System Manager > PMS Manager > PMS Developer > PMS Viewer / PMS Customer**

- **Administrator / System Manager** can see and manage everything (all projects, all users, all timelogs).
- **PMS Manager** has project-scoped full access (only projects they manage or are a member of).
- **PMS Developer** has the most restricted defaults (see Feature Permissions below).

## Enabling PMS Access for a User

1. Go to **Settings > Team > User Management** (admin only)
2. Find the user and toggle **PMS Access** ON
3. The user receives the **Next PMS** base role + **PMS Developer** as the default functional role
4. Change the functional role using the role dropdown (Manager, Developer, Viewer, Customer)

When PMS access is toggled OFF, all PMS roles (including "Next PMS") are removed.

## Permission Categories

There are three categories of per-user permissions, all configurable from the **User Detail > Permissions** tab (admin only).

### 1. Sidebar Menu Access

Controls which sidebar navigation items the user can see.

| Key | Default (Manager) | Default (Developer) |
|-----|-------------------|---------------------|
| `projects` | Visible | Visible |
| `my_tasks` | Visible | Visible |
| `settings` | Visible | Hidden |
| `timelogs` | Visible | Visible |
| `reports` | Visible | Hidden |

### 2. Project Tab Access

Controls which tabs are visible inside a project detail page.

| Key | Default (Manager) | Default (Developer) |
|-----|-------------------|---------------------|
| `overview` | Visible | Visible |
| `tasks` | Visible | Visible |
| `backlog` | Visible | Visible |
| `team` | Visible | Hidden |
| `files` | Visible | Visible |
| `timelogs` | Visible | Hidden |
| `analytics` | Visible | Hidden |

### 3. Feature Access

Controls what actions the user can perform. These are enforced on both the frontend (buttons hidden) and the backend (API throws PermissionError).

| Key | Description | Default (Manager) | Default (Developer) |
|-----|-------------|-------------------|---------------------|
| `view_all_timelogs` | See other users' time logs | Enabled | Disabled |
| `view_all_projects` | See projects they are not a member of | Enabled | Disabled |
| `edit_project` | Edit project details (name, dates, budget, etc.) | Enabled | Disabled |
| `edit_task` | Edit task details (title, status, priority, etc.) | Enabled | Disabled |
| `create_project` | Create new projects | Enabled | Disabled |
| `create_task` | Create new tasks in any project | Enabled | Disabled |

**How defaults work:**
- Users with the **PMS Developer** role (without Manager/Admin) get the restricted defaults shown above.
- All other roles (Manager, Viewer, Customer, Admin) get permissive defaults.
- Once an admin explicitly saves permissions for a user, those saved values override the defaults.

## Configuring Permissions

### Via the UI

1. Navigate to **Settings > Team** or click on a team member
2. Open the user's detail page
3. Go to the **Permissions** tab (visible to admins only)
4. Toggle individual permissions ON/OFF in each section:
   - **Sidebar Menu Access** - which menu items to show
   - **Project Tab Access** - which project tabs to show
   - **Feature Access** - what actions the user can perform
5. Click **Save Permissions**

### Via the API

```python
# Read permissions
from next_pms.api.permissions import get_user_permissions
perms = get_user_permissions("user@example.com")
# Returns: {"sidebar_permissions": {...}, "project_tab_permissions": {...}, "feature_permissions": {...}}

# Save permissions (admin only)
import frappe
frappe.call(
    "next_pms.api.permissions.save_user_permissions",
    user="user@example.com",
    feature_permissions='{"view_all_timelogs": true, "edit_task": false, "create_task": true, "create_project": false, "view_all_projects": false, "edit_project": false}'
)
```

### Storage

Permissions are stored per-user using Frappe's defaults system:

| Key | Storage |
|-----|---------|
| `pms_sidebar_permissions` | `frappe.db.get_default(..., parent=user)` |
| `pms_project_tab_permissions` | `frappe.db.get_default(..., parent=user)` |
| `pms_feature_permissions` | `frappe.db.get_default(..., parent=user)` |

Values are JSON strings. If no value is stored, role-appropriate defaults are used.

## Backend Enforcement

Feature permissions are enforced at the API level, not just the UI:

| Feature | Backend Enforcement |
|---------|-------------------|
| `view_all_timelogs` | `get_all_timelogs()` forces `user=self` filter; `get_timelog_filters()` returns only self |
| `view_all_projects` | `get_all_projects_summary()` filters to team-member projects only |
| `edit_project` | Frontend-only (Frappe document permissions handle backend) |
| `edit_task` | Frontend-only (Frappe document permissions handle backend) |
| `create_project` | `create_project()` throws PermissionError if disabled |
| `create_task` | `create_task()` throws PermissionError if disabled |

## Example: Restricting a Developer

A typical developer setup:

1. Toggle PMS access ON (gets "Next PMS" + "PMS Developer")
2. Developer defaults automatically apply:
   - Can only see own timelogs
   - Can only see projects they are a member of
   - Cannot edit projects or tasks
   - Cannot create projects or tasks
   - Cannot see Settings, Reports, Team, Timelogs tab, or Analytics tab
3. To selectively grant access (e.g., allow task creation):
   - Open User Detail > Permissions
   - Toggle "Create Tasks" ON
   - Save

## Example: Restricting a Manager

Managers get full defaults, but you can restrict individual features:

1. User has PMS Manager role
2. Open User Detail > Permissions
3. Toggle "View All Time Logs" OFF
4. Save
5. Manager can now only see their own timelogs (enforced on backend too)

## Files Reference

| File | Purpose |
|------|---------|
| `next_pms/api/permissions.py` | Permission defaults, storage, query conditions, feature permission helper |
| `next_pms/api/settings.py` | Returns all permissions to the frontend via `get_pms_settings()` |
| `next_pms/api/users.py` | Role management (toggle access, set role) |
| `next_pms/api/timer.py` | Backend enforcement for timelog visibility |
| `next_pms/api/dashboard.py` | Backend enforcement for project visibility |
| `next_pms/api/crud.py` | Backend enforcement for create task/project |
| `frontend/src/store/settings.js` | Pinia store holding all permissions for the frontend |
| `frontend/src/views/UserDetailView.vue` | Admin UI for managing per-user permissions |
