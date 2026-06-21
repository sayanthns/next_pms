# Weekly Plan (next_pms) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Frappe work: keep the `frappe-erpnext-expert` skill active; verify any unfamiliar field/hook against the live app source or `mcp__frappe-brain__*` before coding — never guess field names.

**Goal:** A role-scoped Weekly Plan inside the next_pms SPA — developers see their own allocation + their projects + the week's global priorities; managers see everything and edit in-app; hybrid-prefilled from real PMS data.

**Architecture:** A `Weekly Plan` DocType (parent + 6 child tables) in the next_pms app (module "Next PMS") is the source of truth. A whitelisted API (`next_pms.api.weekly_plan`) reads it **role-scoped** and (later) prefills from PMS + saves edits. A Vue view (`/weekly-plan` route + sidebar nav) renders the existing `enfono-weekly-plan.html` design, scoped per the logged-in user; managers additionally get an in-app editor. Carry-forward = roll-forward from last week + PMS refresh.

**Tech Stack:** Frappe v15 (Python), Vue 3 + Vite SPA, `@/utils/frappe` `call()`, Pinia `settingsStore` (`isManager`/`isAdmin`/`isDeveloper`), reuse of `ai_report._build_user_metrics` / `_get_project_summary` for prefill.

**Supersedes:** the scratchpad spec `2026-06-21-weekly-plan-phase1-design.md` (enfono_internal / Jinja) — home is now **next_pms**, render is a **Vue tab**, access is **role-scoped**, data is **hybrid**.

---

## Design (locked via brainstorming)

| Decision | Choice |
|---|---|
| Home | **next_pms** app (internal PMS), module "Next PMS" |
| Surface | Native SPA view at `/weekly-plan` + sidebar nav item |
| Data source | **Hybrid** — PMS-prefilled draft + manager edits the judgment bits |
| Dev scope | Own allocation + their projects + global priorities + global checklist + their watch items |
| Manager scope | Everything |
| Customer | No access |
| Authoring | **In-app editor** in the SPA (managers) |
| Carry-forward | Roll-forward from prior week + refresh from PMS |
| Manager test | `is_admin` (System Manager/Administrator) or `is_manager` (PMS Manager); developer = `is_developer`; from `get_pms_settings()` |

### Data model — `Weekly Plan` (module "Next PMS", non-submittable, `autoname: field:week_start`)

Parent fields:

| Field | Type | Notes |
|---|---|---|
| `week_start` | Date | reqd, unique (Monday) |
| `week_end` | Date | read-only; controller = `add_days(week_start, 5)` |
| `title` | Data | read-only; controller = "Weekly Plan · 22–27 Jun" |
| `published` | Check | default 1; only published weeks shown to non-editors |
| `intro` | Small Text | hero subline |
| `headline_note` | Data | optional hero stat (e.g. "Jun 25 · Aqrar deadline") |
| `allocations` | Table → `Weekly Plan Allocation` | |
| `projects` | Table → `Weekly Plan Project` | |
| `closures` | Table → `Weekly Plan Closure` | |
| `priorities` | Table → `Weekly Plan Priority` | |
| `checklist` | Table → `Weekly Plan Checklist` | |
| `watch_list` | Table → `Weekly Plan Watch` | |
| `working_notes` | Text Editor | rich text |
| `week_shape` | Text Editor | rich text |
| `meetings_note` | Text Editor | rich text |

Child DocTypes (all `istable: 1`, module "Next PMS"):

1. **Weekly Plan Allocation** — `member` (Link User, reqd), `display_name` (Data), `role` (Data), `planned_hours` (Float), `tasks` (Small Text — one chip/line; optional prefixes `**`=key, `!`=deadline, `~`=provisional).
2. **Weekly Plan Project** — `project` (Link PMS Project, reqd), `focus` (Data), `team` (Table MultiSelect → User, fieldname `team_members`; child `Weekly Plan Project Member` with `user` Link User), `effort` (Data), `status_label` (Data), `status_color` (Select: `red\norange\ngreen\nblue\ngrey`).
3. **Weekly Plan Closure** — `project` (Data), `work` (Data, default "Final sign-off + handover"), `owner` (Data), `status_label` (Data, default "Closure").
4. **Weekly Plan Priority** — `rank` (Int), `project` (Data), `note` (Small Text), `badge_label` (Data), `badge_color` (Select: `red\norange\ngreen\nblue\ngrey`), `hot` (Check).
5. **Weekly Plan Checklist** — `who` (Data), `item` (Small Text).
6. **Weekly Plan Watch** — `item` (Small Text), `level` (Select: `High\nMed\nLow`), `mitigation` (Small Text), `owner` (Link User).

> Project `team_members` as Link-User rows (not the freeform initials of the HTML) is deliberate: it's the exact key for dev-scoping ("projects where I'm on the team"). The render derives initials/colors from the user.

### Role-scoping contract (`get_week`)

- **admin/manager** → full doc.
- **developer** → `allocations` filtered to `member == session user`; `projects` filtered to those whose `team_members` include the user (fallback: projects where the user has an assigned `PMS Task`); `priorities` + `checklist` returned whole (global); `watch_list` filtered to `owner == user`; `closures` returned whole; narrative fields returned whole.
- **customer / guest** → `frappe.throw(PermissionError)`.

### Stage decomposition (each shippable)

- **Stage 1 — model + role-scoped read view.** DocTypes + permissions + `get_week`/`list_weeks` API + `/weekly-plan` Vue view (read-only render, role-scoped) + nav. Manager authors in the Frappe **desk form** for now. **← this plan details Stage 1 fully.**
- **Stage 2 — hybrid PMS prefill.** `prefill_week(week_start)` + `roll_forward(from_week)` (manager-only) building a draft from PMS (reuse `_build_user_metrics`/`_get_project_summary`). Outlined below.
- **Stage 3 — in-app editor.** Vue child-table editing + `save_week` + publish + carry-forward button. Outlined below.

Tests run on local dev site `mysite.local`:
`bench --site mysite.local run-tests --module next_pms.api.test_weekly_plan`
Deploy = office bench, **migrate required** (`bench use office` first; restart web+workers per memory rule #6), maintenance window.

---

## STAGE 1 — model + role-scoped read view

### Task 1: Create the DocTypes

**Files (create under the same module dir as `pms_task` — resolve once):**
- Resolve dir: `MOD=$(dirname $(dirname $(find /Users/sayanthns/EFTPMS/next_pms/next_pms -type d -name pms_task)))` → e.g. `next_pms/next_pms/next_pms/doctype`. Create each doctype folder there.
- Create: `weekly_plan/weekly_plan.json`, `weekly_plan/weekly_plan.py`, `weekly_plan/__init__.py`
- Create child folders + JSON for the 6 children + `weekly_plan_project_member`.

- [ ] **Step 1: Create child + parent doctypes via bench (correct JSON + module wiring)**

Run (local), one per doctype — bench scaffolds JSON+py+__init__ in the right module dir:
```bash
cd /Users/sayanthns/frappe-bench
for d in "Weekly Plan Project Member" "Weekly Plan Allocation" "Weekly Plan Project" "Weekly Plan Closure" "Weekly Plan Priority" "Weekly Plan Checklist" "Weekly Plan Watch" "Weekly Plan"; do
  /Users/sayanthns/.local/bin/bench --site mysite.local new-doctype "$d" --module "Next PMS" || true
done
```
Then in the desk (or by editing the JSON), set `istable: 1` on the 7 child doctypes, add the fields from the Design tables above, and on `Weekly Plan` add the parent fields + Table fields pointing at the child doctypes (`options` = child doctype name). Set `Weekly Plan` `autoname` = `field:week_start`.

- [ ] **Step 2: Parent controller**

```python
# <module dir>/weekly_plan/weekly_plan.py
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, formatdate


class WeeklyPlan(Document):
    def validate(self):
        self.week_end = add_days(getdate(self.week_start), 5)
        start = formatdate(self.week_start, "d MMM")
        end = formatdate(self.week_end, "d MMM yyyy")
        self.title = f"Weekly Plan · {start} – {end}"
```

- [ ] **Step 3: Migrate + verify the doctype loads**

Run: `/Users/sayanthns/.local/bin/bench --site mysite.local migrate`
Then: `/Users/sayanthns/.local/bin/bench --site mysite.local console` → `frappe.get_meta("Weekly Plan").fields` lists the tables.
Expected: migrate succeeds; `Weekly Plan` + 7 child doctypes exist.

- [ ] **Step 4: Commit** (hold per session policy — skip until approved)

### Task 2: Permissions

**Files:** `weekly_plan.json` (`permissions` array)

- [ ] **Step 1: Set role permissions on `Weekly Plan`**

In `weekly_plan.json` `permissions`: System Manager (all), PMS Manager (read/write/create/delete), PMS Developer (read only). Children inherit via parent.

- [ ] **Step 2: Migrate + verify**

Run: `bench --site mysite.local migrate` then console: `frappe.get_doc("DocType","Weekly Plan").permissions` shows the 3 roles.
Expected: PMS Developer = read 1, write 0.

### Task 3: `get_week` + `list_weeks` API (role-scoped)

**Files:**
- Create: `next_pms/next_pms/api/weekly_plan.py`
- Test: `next_pms/next_pms/api/test_weekly_plan.py`

- [ ] **Step 1: Write the failing test**

```python
# next_pms/next_pms/api/test_weekly_plan.py
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from next_pms.api import weekly_plan as W


def _ctx(is_admin=False, is_manager=False, is_developer=False, is_customer=False, user="dev@x.com"):
    return {"is_admin": is_admin, "is_manager": is_manager,
            "is_developer": is_developer, "is_customer": is_customer, "user": user}


class TestWeeklyPlanScope(FrappeTestCase):
    def test_customer_denied(self):
        with patch.object(W, "_user_context", return_value=_ctx(is_customer=True)):
            with self.assertRaises(frappe.PermissionError):
                W.get_week()

    def test_developer_scopes_allocations_to_self(self):
        plan = {"allocations": [{"member": "dev@x.com"}, {"member": "other@x.com"}],
                "projects": [], "priorities": [{"rank": 1}], "watch_list": [],
                "checklist": [{"item": "x"}], "closures": []}
        with patch.object(W, "_user_context", return_value=_ctx(is_developer=True, user="dev@x.com")), \
             patch.object(W, "_load_week_dict", return_value=plan), \
             patch.object(W, "_user_project_names", return_value=set()):
            out = W.get_week()
        self.assertEqual([a["member"] for a in out["allocations"]], ["dev@x.com"])
        self.assertEqual(len(out["priorities"]), 1)   # global kept

    def test_manager_sees_all(self):
        plan = {"allocations": [{"member": "dev@x.com"}, {"member": "other@x.com"}],
                "projects": [], "priorities": [], "watch_list": [], "checklist": [], "closures": []}
        with patch.object(W, "_user_context", return_value=_ctx(is_manager=True)), \
             patch.object(W, "_load_week_dict", return_value=plan):
            out = W.get_week()
        self.assertEqual(len(out["allocations"]), 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_weekly_plan`
Expected: FAIL — `module 'next_pms.api.weekly_plan' has no attribute 'get_week'`.

- [ ] **Step 3: Implement the API**

```python
# next_pms/next_pms/api/weekly_plan.py
import frappe
from frappe import _


def _user_context():
    roles = set(frappe.get_roles(frappe.session.user))
    is_admin = bool({"System Manager", "Administrator"} & roles)
    is_manager = "PMS Manager" in roles
    is_developer = "PMS Developer" in roles
    is_customer = "PMS Customer" in roles and not (is_admin or is_manager or is_developer)
    return {"is_admin": is_admin, "is_manager": is_manager,
            "is_developer": is_developer, "is_customer": is_customer,
            "user": frappe.session.user}


def _resolve_name(week_start=None):
    if week_start:
        return frappe.db.get_value("Weekly Plan", {"week_start": week_start}, "name")
    return frappe.db.get_value("Weekly Plan", {"published": 1}, "name", order_by="week_start desc")


def _load_week_dict(name):
    return frappe.get_doc("Weekly Plan", name).as_dict()


def _user_project_names(user):
    """Projects the user is on: Weekly-plan team rows OR assigned PMS Tasks."""
    names = set(frappe.get_all("PMS Task", filters={"assigned_to": user},
                               pluck="project", ignore_permissions=True))
    return {n for n in names if n}


@frappe.whitelist()
def list_weeks():
    ctx = _user_context()
    if ctx["is_customer"] or frappe.session.user == "Guest":
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    pub = {} if (ctx["is_admin"] or ctx["is_manager"]) else {"published": 1}
    return frappe.get_all("Weekly Plan", filters=pub, fields=["name", "week_start", "title"],
                          order_by="week_start desc", ignore_permissions=True)


@frappe.whitelist()
def get_week(week_start=None):
    ctx = _user_context()
    if ctx["is_customer"] or frappe.session.user == "Guest":
        frappe.throw(_("You are not permitted to view the weekly plan."), frappe.PermissionError)

    name = _resolve_name(week_start)
    if not name:
        return None
    plan = _load_week_dict(name)

    if ctx["is_admin"] or ctx["is_manager"]:
        return plan

    # developer: scope to self
    user = ctx["user"]
    my_projects = _user_project_names(user)
    team_keyed = {p.get("project") for p in plan.get("projects", [])
                  if user in [m.get("user") for m in p.get("team_members", [])]}
    keep_projects = my_projects | team_keyed
    plan["allocations"] = [a for a in plan.get("allocations", []) if a.get("member") == user]
    plan["projects"] = [p for p in plan.get("projects", []) if p.get("project") in keep_projects]
    plan["watch_list"] = [w for w in plan.get("watch_list", []) if w.get("owner") == user]
    # priorities, checklist, closures, narrative = global (unchanged)
    return plan
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_weekly_plan`
Expected: PASS (3 tests).

### Task 4: Vue view + route + nav

**Files:**
- Create: `frontend/src/views/WeeklyPlanView.vue`
- Modify: `frontend/src/router/index.js` (add `/weekly-plan` route)
- Modify: `frontend/src/App.vue` (sidebar nav item, gated to non-customer)

- [ ] **Step 1: Build the view (read-only render, role-agnostic — API already scoped)**

Create `frontend/src/views/WeeklyPlanView.vue`: a week `<select>` populated from `list_weeks`, defaulting to latest; on change call `get_week({week_start})`; render the `enfono-weekly-plan.html` sections from the returned doc (people cards from `allocations`, project table from `projects`, closures, priority cards, checklist `<li>` with the localStorage tick JS, watch table, narrative via `v-html` of `working_notes`/`week_shape`/`meetings_note`); hero stats computed from array lengths; empty-state when `get_week` returns null. Port the CSS from the HTML into `<style scoped>`.

- [ ] **Step 2: Add the route**

```js
// frontend/src/router/index.js — add to the routes array
{
  path: "/weekly-plan",
  name: "WeeklyPlan",
  component: () => import("@/views/WeeklyPlanView.vue"),
},
```

- [ ] **Step 3: Add the sidebar nav item** in `frontend/src/App.vue`, next to "Reports", gated:
`v-if="!settingsStore.isCustomer"` → router-link to `/weekly-plan`, label "Weekly Plan".

- [ ] **Step 4: Build to verify it compiles**

Run: `cd frontend && yarn build`
Expected: build succeeds, no errors referencing `WeeklyPlanView.vue`.

### Task 5: Seed current week + manual verify (local)

- [ ] **Step 1:** In `mysite.local` desk, create a `Weekly Plan` for this Monday and fill a couple of allocations/projects (one allocation `member` = a test PMS Developer user, one project with that user in `team_members`).
- [ ] **Step 2:** Log in as that developer → `/weekly-plan` shows only their allocation + that project + global priorities. Log in as a PMS Manager → sees all. Customer → no nav item / API denied.

### Task 6: Deploy Stage 1 (after approval, maintenance window)

- [ ] Push next_pms. On office: `bench use office`; `git pull`; **`bench --site office migrate`** (new doctypes); `cd apps/next_pms/frontend && yarn build`; restart **web + workers** (`supervisorctl restart frappe-bench-web: frappe-bench-workers:`). Verify the tab for a manager + a developer. Update `LIVE_STATE.md`.

---

## STAGE 2 — hybrid PMS prefill (outline; detail when reached)

- `next_pms.api.weekly_plan.prefill_week(week_start)` (manager-only): build a **draft** `Weekly Plan` —
  - `allocations`: one row per active user from their assigned `PMS Task`s + planned hours (reuse the aggregation shape of `ai_report._build_user_metrics`; planned hours from `estimated_hours` of open tasks, not logged actuals).
  - `projects`: one row per `PMS Project` with `status in (Planning, Active, On Hold)` (reuse `ai_report._get_project_summary`); `status_color` mapped from status; `team_members` from `pms_project_member`.
  - `priorities`/`watch_list`: seed from near `due_date` tasks + stale tasks; manager curates.
- `roll_forward(from_week)`: copy the prior week, drop closed projects, refresh allocations/projects from PMS, keep narrative for manager edit.
- Tests: prefill builds expected row counts on a seeded fixture; manager-only gate.

## STAGE 3 — in-app editor (outline; detail when reached)

- `save_week(payload)` (manager-only, validated) — upsert parent + child tables.
- Vue: manager-only edit mode in `WeeklyPlanView.vue` (or `WeeklyPlanEditor.vue`) — add/remove/reorder child rows (allocations, projects, priorities, checklist, watch), edit narrative, `published` toggle, "Roll forward from last week" button.
- Tests: save round-trip; non-manager `save_week` → PermissionError.

---

## Self-Review

**Spec coverage (vs locked decisions):**
- next_pms home + SPA view → Tasks 1,4. ✓
- Hybrid data → Stage 2 (`prefill_week`/`roll_forward`). ✓ (Stage 1 ships with desk authoring; hybrid is Stage 2 by design.)
- Dev scope (own + projects + global priorities + own watch) → Task 3 `get_week` developer branch. ✓
- Manager sees all → Task 3. ✓ Customer denied → Task 3. ✓
- In-app editor → Stage 3. ✓
- Carry-forward → Stage 2 `roll_forward` + Stage 3 button. ✓

**Placeholder scan:** none — field tables enumerate every doctype field; API/controller code is complete; the one resolved-path command (`MOD=…`) is concrete, not a placeholder.

**Type consistency:** `get_week` returns the parent `as_dict()` shape; developer branch filters `allocations[].member`, `projects[].team_members[].user`, `watch_list[].owner` — all match the Design field names. `_user_context` keys (`is_admin/is_manager/is_developer/is_customer/user`) match the test's `_ctx`. Store refs (`isManager/isAdmin/isDeveloper/isCustomer`) match `settings.js`. Module string "Next PMS" matches `pms_task`.

**Verify at build:** exact module doctype dir (Task 1 resolves it); `PMS Project` has no `team` field → team scoping uses `pms_project_member` / assigned tasks (Task 3 `_user_project_names` uses `PMS Task.assigned_to`; extend to `pms_project_member` if richer membership needed).
