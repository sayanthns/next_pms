# Department & Favorites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add department field to PMS Projects for scoped PM access, and per-user project favorites with star toggle and filter tab.

**Architecture:** Two independent features sharing the same project list UI. Department adds a Link field to PMS Project and a SQL filter in `permissions.py`. Favorites adds a new `PMS Favorite Project` doctype and toggle/list APIs in `crud.py`. Frontend changes are in `ProjectList.vue` (star icon + filter tabs), `CreateProjectModal.vue`, and `EditProjectModal.vue` (department dropdown).

**Tech Stack:** Frappe v15 (Python), Vue 3 (Composition API), MariaDB

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `next_pms/next_pms/doctype/pms_project/pms_project.json` | Modify | Add `department` field |
| `next_pms/next_pms/doctype/pms_favorite_project/` | Create (4 files) | New doctype for user↔project favorites |
| `next_pms/api/permissions.py` | Modify | Department filter in `project_query_conditions` and `get_user_projects` |
| `next_pms/api/crud.py` | Modify | Add `department` to create/update, add favorites APIs, add `get_departments` |
| `next_pms/api/dashboard.py` | Modify | Include `department` in project summary fields |
| `frontend/src/components/CreateProjectModal.vue` | Modify | Department dropdown |
| `frontend/src/components/EditProjectModal.vue` | Modify | Department dropdown |
| `frontend/src/views/ProjectList.vue` | Modify | Star icon, favorites filter tab |

---

### Task 1: Add `department` field to PMS Project doctype

**Files:**
- Modify: `next_pms/next_pms/doctype/pms_project/pms_project.json`

- [ ] **Step 1: Add `department` to `field_order` array**

In `pms_project.json`, add `"department"` after `"client"` in the `field_order` array:

```json
"field_order": [
  "project_name",
  "client",
  "department",
  "project_manager",
  "status",
  "column_break_mkew",
  ...
]
```

- [ ] **Step 2: Add `department` field object to `fields` array**

After the `client` field object (the one with `"fieldname": "client"`), add:

```json
{
  "fieldname": "department",
  "fieldtype": "Link",
  "label": "Department",
  "options": "Department"
}
```

- [ ] **Step 3: Verify JSON is valid**

Run: `cd /Users/sayanthns/frappe-bench && python3 -c "import json; json.load(open('apps/next_pms/next_pms/next_pms/doctype/pms_project/pms_project.json'))"`

Expected: No output (valid JSON)

- [ ] **Step 4: Run bench migrate to sync the schema**

Run: `cd /Users/sayanthns/frappe-bench && bench --site mysite.local migrate`

Expected: Migration completes. PMS Project table now has a `department` column.

- [ ] **Step 5: Verify column exists**

Run: `cd /Users/sayanthns/frappe-bench && bench --site mysite.local console` then:
```python
frappe.db.sql("DESCRIBE `tabPMS Project` department")
```

Expected: Returns a row showing the `department` column.

---

### Task 2: Create `PMS Favorite Project` doctype

**Files:**
- Create: `next_pms/next_pms/doctype/pms_favorite_project/__init__.py`
- Create: `next_pms/next_pms/doctype/pms_favorite_project/pms_favorite_project.json`
- Create: `next_pms/next_pms/doctype/pms_favorite_project/pms_favorite_project.py`
- Create: `next_pms/next_pms/doctype/pms_favorite_project/test_pms_favorite_project.py`

- [ ] **Step 1: Create the doctype directory**

Run: `mkdir -p /Users/sayanthns/frappe-bench/apps/next_pms/next_pms/next_pms/doctype/pms_favorite_project`

- [ ] **Step 2: Create `__init__.py`**

```python
# empty
```

- [ ] **Step 3: Create `pms_favorite_project.json`**

```json
{
 "actions": [],
 "allow_rename": 0,
 "autoname": "hash",
 "creation": "2026-03-28 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["user", "project"],
 "fields": [
  {
   "fieldname": "user",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "User",
   "options": "User",
   "reqd": 1
  },
  {
   "fieldname": "project",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "Project",
   "options": "PMS Project",
   "reqd": 1
  }
 ],
 "index_web_pages_for_search": 0,
 "istable": 0,
 "links": [],
 "modified": "2026-03-28 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "Next PMS",
 "name": "PMS Favorite Project",
 "naming_rule": "Random",
 "owner": "Administrator",
 "permissions": [
  {
   "create": 1,
   "delete": 1,
   "read": 1,
   "role": "System Manager",
   "write": 1
  }
 ],
 "sort_field": "creation",
 "sort_order": "DESC",
 "track_changes": 0,
 "unique_together": [["user", "project"]]
}
```

- [ ] **Step 4: Create `pms_favorite_project.py`**

```python
# Copyright (c) 2026, Next PMS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PMSFavoriteProject(Document):
    pass
```

- [ ] **Step 5: Create `test_pms_favorite_project.py`**

```python
# Copyright (c) 2026, Next PMS and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase


class TestPMSFavoriteProject(FrappeTestCase):
    pass
```

- [ ] **Step 6: Run bench migrate**

Run: `cd /Users/sayanthns/frappe-bench && bench --site mysite.local migrate`

Expected: `PMS Favorite Project` table created with `user` and `project` columns.

---

### Task 3: Backend — Department in CRUD APIs + `get_departments`

**Files:**
- Modify: `next_pms/api/crud.py` (lines 235-238 and 458-484)

- [ ] **Step 1: Add `department` to `update_project` allowed fields**

In `crud.py` line 235-238, add `"department"` to the `allowed_fields` set:

```python
    allowed_fields = {
        "project_name", "status", "start_date", "end_date",
        "total_budget", "description", "client", "client_portal_enabled",
        "department",
    }
```

- [ ] **Step 2: Add `department` parameter to `create_project`**

In `crud.py` line 458-467, add `department=None` parameter:

```python
@frappe.whitelist()
def create_project(
    project_name,
    client,
    status="Planning",
    start_date=None,
    end_date=None,
    description=None,
    total_budget=0,
    project_manager=None,
    department=None,
):
```

Then in the doc dict (lines 473-484), add the department field:

```python
    doc = frappe.get_doc(
        {
            "doctype": "PMS Project",
            "project_name": project_name,
            "client": client,
            "status": status,
            "start_date": start_date or today(),
            "end_date": end_date,
            "description": description,
            "total_budget": total_budget or 0,
            "project_manager": project_manager or frappe.session.user,
            "department": department,
        }
    )
```

- [ ] **Step 3: Add `get_departments` API**

Add at the end of `crud.py`:

```python
@frappe.whitelist()
def get_departments():
    """Return all departments for dropdown."""
    return frappe.get_all(
        "Department",
        filters={"is_group": 0},
        fields=["name", "department_name"],
        order_by="department_name asc",
        ignore_permissions=True,
    )
```

- [ ] **Step 4: Add favorites toggle and list APIs**

Add at the end of `crud.py`:

```python
@frappe.whitelist()
def toggle_favorite_project(project):
    """Add or remove a project from the current user's favorites.
    Returns {"is_favorite": True/False}.
    """
    user = frappe.session.user
    existing = frappe.db.exists(
        "PMS Favorite Project", {"user": user, "project": project}
    )
    if existing:
        frappe.delete_doc("PMS Favorite Project", existing, ignore_permissions=True)
        frappe.db.commit()
        return {"is_favorite": False}
    else:
        doc = frappe.get_doc({
            "doctype": "PMS Favorite Project",
            "user": user,
            "project": project,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"is_favorite": True}


@frappe.whitelist()
def get_favorite_projects():
    """Return list of project names favorited by the current user."""
    return frappe.get_all(
        "PMS Favorite Project",
        filters={"user": frappe.session.user},
        pluck="project",
        ignore_permissions=True,
    )
```

- [ ] **Step 5: Verify APIs work via console**

Run: `cd /Users/sayanthns/frappe-bench && bench --site mysite.local console`

```python
frappe.set_user("Administrator")
from next_pms.api.crud import get_departments, get_favorite_projects, toggle_favorite_project
print(get_departments())
print(get_favorite_projects())
```

Expected: Returns lists (possibly empty if no departments/favorites exist yet).

---

### Task 4: Backend — Department filter in permissions

**Files:**
- Modify: `next_pms/api/permissions.py` (lines 19-46 and 62-82)

- [ ] **Step 1: Update `get_user_projects` to include department scope for managers**

Replace `get_user_projects()` (lines 19-46) with:

```python
def get_user_projects():
    """Return list of project names user has access to.
    Returns None if user is admin (no filter needed).
    For PMS Manager: projects where user is PM, team member, OR project's
    department matches user's department.
    """
    if is_admin_user():
        return None

    user = frappe.session.user

    # Projects where user is the project manager
    manager_projects = frappe.get_all(
        "PMS Project",
        filters={"project_manager": user},
        pluck="name",
    )

    # Projects where user is a team member
    member_projects = frappe.db.get_all(
        "PMS Project Member",
        filters={"user": user},
        pluck="parent",
    )

    # For PMS Manager: also include projects matching their department
    dept_projects = []
    if is_manager_user():
        user_dept = frappe.db.get_value("User", user, "department")
        if user_dept:
            dept_projects = frappe.get_all(
                "PMS Project",
                filters={"department": user_dept},
                pluck="name",
            )

    allowed = list(set(manager_projects + member_projects + dept_projects))

    # Return a sentinel value if no projects found so filters don't return all
    return allowed if allowed else ["__none__"]
```

- [ ] **Step 2: Update `project_query_conditions` to add department clause for managers**

Replace `project_query_conditions()` (lines 62-82) with:

```python
def project_query_conditions(user):
    """Permission query conditions for PMS Project list."""
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return ""

    escaped_user = frappe.db.escape(user)

    # Base conditions: PM or team member
    conditions = [
        f"`tabPMS Project`.project_manager = {escaped_user}",
        f"""`tabPMS Project`.name IN (
            SELECT parent FROM `tabPMS Project Member`
            WHERE user = {escaped_user}
        )""",
    ]

    # PMS Manager: also sees projects in their department
    if "PMS Manager" in roles:
        user_dept = frappe.db.get_value("User", user, "department")
        if user_dept:
            escaped_dept = frappe.db.escape(user_dept)
            conditions.append(
                f"`tabPMS Project`.department = {escaped_dept}"
            )
        # Also include projects with no department set
        conditions.append(
            "`tabPMS Project`.department IS NULL OR `tabPMS Project`.department = ''"
        )

    return "(" + " OR ".join(conditions) + ")"
```

---

### Task 5: Backend — Include `department` in dashboard query

**Files:**
- Modify: `next_pms/api/dashboard.py` (line 134-145)

- [ ] **Step 1: Add `department` to the fields list in `get_all_projects_summary`**

In `dashboard.py` line 131-147, add `"department"` to the fields list:

```python
    projects = frappe.get_all(
        "PMS Project",
        filters=filters,
        fields=[
            "name",
            "project_name",
            "client",
            "project_manager",
            "status",
            "start_date",
            "end_date",
            "total_budget",
            "calculated_cost",
            "budget_utilization",
            "department",
        ],
        order_by="modified desc",
    )
```

---

### Task 6: Frontend — Department dropdown in CreateProjectModal

**Files:**
- Modify: `frontend/src/components/CreateProjectModal.vue`

- [ ] **Step 1: Add department dropdown to template**

After the Client `</div>` (line 35) and before the Status form-group, add:

```vue
      <div class="form-group">
        <label class="form-label">Department</label>
        <select v-model="form.department" class="form-input">
          <option value="">No Department</option>
          <option v-for="d in departments" :key="d.name" :value="d.name">
            {{ d.department_name || d.name }}
          </option>
        </select>
      </div>
```

- [ ] **Step 2: Add departments ref and loader**

After the `customers` ref (line 96), add:

```javascript
const departments = ref([])
```

Add loader function after `loadCustomers()`:

```javascript
async function loadDepartments() {
  try {
    const result = await call('next_pms.api.crud.get_departments')
    departments.value = result || []
  } catch (e) {
    console.error('Failed to load departments:', e)
    departments.value = []
  }
}
```

- [ ] **Step 3: Add `department` to form defaults**

In `getDefaultForm()` (line 99-108), add `department: ''`:

```javascript
function getDefaultForm() {
  return {
    project_name: '',
    client: '',
    department: '',
    status: 'Planning',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    total_budget: 0,
    description: '',
  }
}
```

- [ ] **Step 4: Load departments on modal open**

In the `watch` handler (line 121-129), add `loadDepartments()` alongside `loadCustomers()`:

```javascript
watch(() => props.show, (val) => {
  if (val) {
    form.value = getDefaultForm()
    if (!customers.value.length) {
      loadCustomers()
    }
    if (!departments.value.length) {
      loadDepartments()
    }
    nextTick(() => nameInput.value?.focus())
  }
})
```

- [ ] **Step 5: Include department in API call**

In `handleSubmit()` (line 136-144), add `department`:

```javascript
    const result = await call('next_pms.api.crud.create_project', {
      project_name: form.value.project_name.trim(),
      client: form.value.client,
      status: form.value.status,
      start_date: form.value.start_date || null,
      end_date: form.value.end_date || null,
      total_budget: form.value.total_budget || 0,
      description: form.value.description || null,
      department: form.value.department || null,
    })
```

---

### Task 7: Frontend — Department dropdown in EditProjectModal

**Files:**
- Modify: `frontend/src/components/EditProjectModal.vue`

- [ ] **Step 1: Add department dropdown to template**

After the Client `</div>` (line 35) and before the Status form-group, add:

```vue
      <div class="form-group">
        <label class="form-label">Department</label>
        <select v-model="form.department" class="form-input">
          <option value="">No Department</option>
          <option v-for="d in departments" :key="d.name" :value="d.name">
            {{ d.department_name || d.name }}
          </option>
        </select>
      </div>
```

- [ ] **Step 2: Add departments ref and loader**

After the `customers` ref (line 98), add:

```javascript
const departments = ref([])

async function loadDepartments() {
  try {
    const result = await call('next_pms.api.crud.get_departments')
    departments.value = result || []
  } catch (e) {
    console.error('Failed to load departments:', e)
    departments.value = []
  }
}
```

- [ ] **Step 3: Add `department` to form defaults and watch**

In `getDefaultForm()` (line 101-111), add `department: ''`.

In the `watch` handler (line 124-141), add department to form population:

```javascript
    form.value = {
      project_name: props.project.project_name || '',
      client: props.project.client || '',
      department: props.project.department || '',
      status: props.project.status || 'Planning',
      start_date: props.project.start_date || '',
      end_date: props.project.end_date || '',
      total_budget: props.project.total_budget || 0,
      description: props.project.description || '',
      client_portal_enabled: !!props.project.client_portal_enabled,
    }
```

Add `loadDepartments()` call:

```javascript
    if (!departments.value.length) {
      loadDepartments()
    }
```

- [ ] **Step 4: Include department in update API call**

In `handleSubmit()` (line 147-158), add `department`:

```javascript
      fields: JSON.stringify({
        project_name: form.value.project_name.trim(),
        client: form.value.client || null,
        department: form.value.department || null,
        status: form.value.status,
        start_date: form.value.start_date || null,
        end_date: form.value.end_date || null,
        total_budget: form.value.total_budget || 0,
        description: form.value.description || '',
        client_portal_enabled: form.value.client_portal_enabled ? 1 : 0,
      }),
```

---

### Task 8: Frontend — Star icon + Favorites filter in ProjectList

**Files:**
- Modify: `frontend/src/views/ProjectList.vue`

- [ ] **Step 1: Add state variables**

After line 215 (`const viewMode = ref('grid')`), add:

```javascript
const favoriteProjects = ref([])
const favoriteFilter = ref(false)
```

- [ ] **Step 2: Load favorites on mount**

Update `onMounted` (line 217-219):

```javascript
onMounted(() => {
  projectStore.fetchProjects()
  loadFavorites()
})

async function loadFavorites() {
  try {
    const result = await call('next_pms.api.crud.get_favorite_projects')
    favoriteProjects.value = result || []
  } catch (e) {
    console.error('Failed to load favorites:', e)
  }
}
```

Add the `call` import — check if it's already imported. If not, add:

```javascript
import { call } from '@/utils/frappe'
```

- [ ] **Step 3: Add favorites toggle function**

```javascript
async function toggleFavorite(e, projectName) {
  e.stopPropagation()
  try {
    const result = await call('next_pms.api.crud.toggle_favorite_project', {
      project: projectName,
    })
    if (result.is_favorite) {
      favoriteProjects.value.push(projectName)
    } else {
      favoriteProjects.value = favoriteProjects.value.filter(p => p !== projectName)
    }
  } catch (err) {
    console.error('Failed to toggle favorite:', err)
  }
}

function isFavorite(projectName) {
  return favoriteProjects.value.includes(projectName)
}
```

- [ ] **Step 4: Update `filteredProjects` computed to handle favorites filter**

Replace the `filteredProjects` computed (lines 221-246):

```javascript
const filteredProjects = computed(() => {
  let projects = projectStore.projects || []

  // Favorites filter
  if (favoriteFilter.value) {
    projects = projects.filter(p => favoriteProjects.value.includes(p.name))
  }

  // Search filter
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    projects = projects.filter(p =>
      (p.project_name || '').toLowerCase().includes(q) ||
      (p.client || '').toLowerCase().includes(q)
    )
  }

  // Status filter
  if (statusFilter.value !== 'all') {
    const filterMap = {
      'active': ['Active', 'In Progress'],
      'planning': ['Planning', 'Planned', 'Open'],
      'on-hold': ['On Hold'],
      'completed': ['Completed'],
    }
    const allowed = filterMap[statusFilter.value] || []
    projects = projects.filter(p => allowed.includes(p.status))
  }

  return projects
})
```

- [ ] **Step 5: Add favorites toggle button in toolbar**

In the toolbar-left div (after the status filter `</select>`, around line 34), add:

```vue
        <button
          :class="['filter-btn', { active: favoriteFilter }]"
          @click="favoriteFilter = !favoriteFilter"
          title="Show favorites only"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" :fill="favoriteFilter ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          Favorites
        </button>
```

- [ ] **Step 6: Add star icon to project cards in grid view**

In the grid view card-header (around line 87-91), add a star button before the status badge:

```vue
        <div class="card-header">
          <div class="card-header-left">
            <button
              class="star-btn"
              :class="{ active: isFavorite(project.name) }"
              @click="toggleFavorite($event, project.name)"
              :title="isFavorite(project.name) ? 'Remove from favorites' : 'Add to favorites'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" :fill="isFavorite(project.name) ? '#f59e0b' : 'none'" stroke="#f59e0b" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            </button>
            <h3 class="project-name">{{ project.project_name }}</h3>
          </div>
          <span class="status-badge" :class="statusClass(project.status)">
            {{ project.status }}
          </span>
        </div>
```

- [ ] **Step 7: Add CSS for star button and favorites filter**

Add at the end of the `<style scoped>` section:

```css
.star-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  opacity: 0.4;
  transition: opacity 0.15s;
}
.star-btn:hover,
.star-btn.active {
  opacity: 1;
}
.card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.card-header-left .project-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 6px;
  background: white;
  font-size: 13px;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover {
  border-color: var(--primary, #3b82f6);
  color: var(--primary, #3b82f6);
}
.filter-btn.active {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #b45309;
}
```

- [ ] **Step 8: Build and verify**

Run: `cd /Users/sayanthns/frappe-bench/apps/next_pms/frontend && yarn build`

Expected: Build succeeds with no errors.

---

### Task 9: Final verification and commit

- [ ] **Step 1: Start bench and test locally**

Run: `cd /Users/sayanthns/frappe-bench && bench start` (if not already running)

Navigate to `localhost:8000/next-pms/` and verify:
1. Project list shows star icons on each card
2. Clicking star toggles favorite (turns gold)
3. "Favorites" button filters to only favorited projects
4. Create Project modal has Department dropdown
5. Edit Project modal has Department dropdown
6. Department value persists after save

- [ ] **Step 2: Commit all changes**

Stage and commit (wait for user confirmation before committing).
