# SO Mandatory, 95% Budget Guard, Working-Hours in UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sales Order mandatory on new projects with SO-vs-Budget-vs-Actual comparison in reports + dashboard, block new time entries at ≥95% budget with an email approval flow to sayanth@enfono.in, and expose the working-hours/weekly-recipient settings in the SPA AI Settings tab.

**Architecture:** Backend enforcement in Frappe controllers (`pms_project.py` validate, `pms_time_log.py` before_insert), a shared `get_project_financials` reader, an email endpoint in `budget.py`, and matching Vue fields in `TeamView.vue`, `CreateProjectModal.vue`, `ProjectDashboard.vue`, `store/timer.js`. ERPNext is installed → `Sales Order` Link is valid.

**Tech Stack:** Frappe v15.68.1 (Python), FrappeTestCase, Vue 3 SPA. Local site `mysite.local`; `bench` from `/Users/sayanthns/frappe-bench`.

**Spec:** `docs/superpowers/specs/2026-05-31-so-budgetguard-hours-ui-design.md`

**Conventions:** `flt`/`cint`/`getdate` from `frappe.utils`; `_()` on user strings; no f-string SQL; reuse the `is_new()` grandfather pattern from `validate_budget`.

---

## File Structure

| File | Change |
|------|--------|
| `next_pms/api/settings.py` | get/save AI settings: + working_hours_per_day, weekly_summary_recipient |
| `frontend/src/views/TeamView.vue` | AI Settings tab: Working Hours & Weekly Summary inputs |
| `next_pms/next_pms/doctype/pms_project/pms_project.json` | + `sales_order` Link(Sales Order) reqd |
| `next_pms/next_pms/doctype/pms_project/pms_project.py` | `validate_sales_order` (new-only) |
| `next_pms/api/crud.py` | `create_project` accepts + sets `sales_order` |
| `frontend/src/components/CreateProjectModal.vue` | required Sales Order picker |
| `next_pms/api/project_report.py` | `get_project_financials` + SO rows in project & multi-project reports |
| `frontend/src/views/ProjectDashboard.vue` | SO vs Budget vs Actual card |
| `next_pms/next_pms/doctype/pms_time_log/pms_time_log.py` | `before_insert` 95% budget guard |
| `next_pms/api/budget.py` | `request_budget_increase(project)` endpoint |
| `frontend/src/store/timer.js` | catch Budget-Exhausted → offer request-increase |
| tests | settings round-trip, pms_project SO, pms_time_log guard, budget request |

---

## Task 1: Expose working-hours settings in the AI Settings API

**Files:**
- Modify: `next_pms/api/settings.py` (`get_ai_settings` ~line 71-87, `save_ai_settings` ~line 92-130)
- Test: `next_pms/api/test_settings.py` (new)

- [ ] **Step 1: Write the failing test**

Create `next_pms/api/test_settings.py`:
```python
# apps/next_pms/next_pms/api/test_settings.py
import frappe
from frappe.tests.utils import FrappeTestCase

from next_pms.api import settings


class TestSettings(FrappeTestCase):
    def test_ai_settings_roundtrip_hours(self):
        frappe.set_user("Administrator")
        settings.save_ai_settings(working_hours_per_day=7, weekly_summary_recipient="x@example.com")
        data = settings.get_ai_settings()
        self.assertEqual(data["working_hours_per_day"], 7.0)
        self.assertEqual(data["weekly_summary_recipient"], "x@example.com")
        # restore defaults
        settings.save_ai_settings(working_hours_per_day=8, weekly_summary_recipient="sayanth@enfono.in")
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_settings`
Expected: FAIL — `save_ai_settings() got an unexpected keyword argument 'working_hours_per_day'`.

- [ ] **Step 3: Add fields to `get_ai_settings`**

In `next_pms/api/settings.py` `get_ai_settings`, add to BOTH the success return dict and the `except` fallback dict:
```python
            "working_hours_per_day": flt(getattr(doc, "working_hours_per_day", 8)) or 8,
            "weekly_summary_recipient": getattr(doc, "weekly_summary_recipient", "") or "sayanth@enfono.in",
```
(except-fallback values: `8` and `"sayanth@enfono.in"`.) Ensure `from frappe.utils import flt` is imported at top of the file (add if missing).

- [ ] **Step 4: Add params to `save_ai_settings`**

Change the signature to add two kwargs:
```python
def save_ai_settings(provider=None, api_key=None, model=None, enabled=None,
                      recipient=None, additional_recipients=None, detail_level=None,
                      working_hours_per_day=None, weekly_summary_recipient=None):
```
Before `doc.save(...)`, add:
```python
    if working_hours_per_day is not None and hasattr(doc, "working_hours_per_day"):
        doc.working_hours_per_day = flt(working_hours_per_day) or 8
    if weekly_summary_recipient is not None and hasattr(doc, "weekly_summary_recipient"):
        doc.weekly_summary_recipient = weekly_summary_recipient
```

- [ ] **Step 5: Run test, expect PASS**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_settings`
Expected: PASS.

- [ ] **Step 6: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/api/settings.py next_pms/api/test_settings.py
git commit -m "feat: working_hours_per_day + weekly_summary_recipient in AI settings API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Working-hours fields in the AI Settings tab UI

**Files:**
- Modify: `frontend/src/views/TeamView.vue` (template ~line 449-468; `aiSettings` ref ~line 731; load ~line 752-760; save ~line 771-779)

- [ ] **Step 1: Add fields to the `aiSettings` ref**

In `TeamView.vue`, the `const aiSettings = ref({ ... })` object — add:
```javascript
  workingHoursPerDay: 8,
  weeklySummaryRecipient: 'sayanth@enfono.in',
```

- [ ] **Step 2: Populate them on load**

In the `get_ai_settings` load block (after `aiSettings.value.detailLevel = ...`):
```javascript
      aiSettings.value.workingHoursPerDay = data.working_hours_per_day || 8
      aiSettings.value.weeklySummaryRecipient = data.weekly_summary_recipient || 'sayanth@enfono.in'
```

- [ ] **Step 3: Send them on save**

In the `save_ai_settings` call payload (after `detail_level: ...`):
```javascript
      working_hours_per_day: aiSettings.value.workingHoursPerDay || 8,
      weekly_summary_recipient: aiSettings.value.weeklySummaryRecipient || 'sayanth@enfono.in',
```

- [ ] **Step 4: Add the inputs to the template**

After the Report Detail Level form-group (the `<select v-model="aiSettings.detailLevel">` block, ~line 467), add a new section:
```html
            <div class="ai-field" style="margin-top:20px;">
              <h4 style="margin:0 0 12px;">Working Hours & Weekly Summary</h4>
              <label class="ai-label">Working Hours Per Day</label>
              <input v-model.number="aiSettings.workingHoursPerDay" type="number" min="1" step="0.5"
                     class="ai-input" placeholder="8" />
              <label class="ai-label" style="margin-top:12px;">Weekly Summary Recipient (all-team email)</label>
              <input v-model="aiSettings.weeklySummaryRecipient" type="email" class="ai-input"
                     placeholder="sayanth@enfono.in" />
            </div>
```
(Match the existing class names used by neighbouring fields — verify `ai-field`/`ai-label`/`ai-input` exist in this file; if the labels use a different wrapper, mirror the Report Detail Level block's exact markup.)

- [ ] **Step 5: Build**

Run: `cd frontend && yarn build`
Expected: builds clean.

- [ ] **Step 6: Commit (source only; dist rebuilt in Task 9)**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add frontend/src/views/TeamView.vue
git commit -m "feat: working hours + weekly recipient inputs in AI Settings tab

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Sales Order mandatory on PMS Project

**Files:**
- Modify: `next_pms/next_pms/doctype/pms_project/pms_project.json` (add field)
- Modify: `next_pms/next_pms/doctype/pms_project/pms_project.py` (validate)
- Test: `next_pms/next_pms/doctype/pms_project/test_pms_project.py` (extend)

- [ ] **Step 1: Write failing tests**

Append to `TestPMSProject` in `test_pms_project.py`:
```python
    def test_new_project_requires_sales_order(self):
        doc = frappe.get_doc({
            "doctype": "PMS Project",
            "project_name": "ZZ SO Test",
            "status": "Active",
            "total_budget": 1000,
            # no sales_order
        })
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)
```
(Note: `_new_project` helper from earlier tests sets client/project_manager. If the SO validation fires before those, this still raises ValidationError — acceptable. If the helper exists, reuse it and just omit sales_order.)

- [ ] **Step 2: Run, expect FAIL**

Run: `bench --site mysite.local run-tests --module next_pms.next_pms.doctype.pms_project.test_pms_project`
Expected: `test_new_project_requires_sales_order` FAILS (no SO enforcement; insert may succeed or fail for other missing fields — ensure it fails specifically on SO by giving the helper its other required fields).

- [ ] **Step 3: Add the field to JSON**

In `pms_project.json`, add to `field_order` (near `budget_section`) the entry `"sales_order"`, and add the field object:
```json
  {
   "fieldname": "sales_order",
   "fieldtype": "Link",
   "options": "Sales Order",
   "label": "Sales Order",
   "reqd": 1
  },
```
Validate: `python3 -m json.tool pms_project.json >/dev/null`.

- [ ] **Step 4: Add controller validation**

In `pms_project.py`, add to `validate()` (after `validate_budget()`):
```python
		self.validate_sales_order()
```
and the method:
```python
	def validate_sales_order(self):
		# Mandatory only on new projects; existing projects grandfathered.
		if self.is_new() and not self.sales_order:
			frappe.throw(_("Sales Order is required"))
```

- [ ] **Step 5: Run, expect PASS** (+ migrate)

Run: `bench --site mysite.local run-tests --module next_pms.next_pms.doctype.pms_project.test_pms_project`
Expected: PASS. Then `bench --site mysite.local migrate` to sync the field.

- [ ] **Step 6: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/next_pms/doctype/pms_project/pms_project.py next_pms/next_pms/doctype/pms_project/pms_project.json next_pms/next_pms/doctype/pms_project/test_pms_project.py
git commit -m "feat: require Sales Order on new PMS Projects (grandfather existing)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: create_project accepts Sales Order + create-modal picker

**Files:**
- Modify: `next_pms/api/crud.py` (`create_project` ~line 459-489)
- Modify: `frontend/src/components/CreateProjectModal.vue`

- [ ] **Step 1: Backend — accept `sales_order`**

In `crud.py` `create_project`, add `sales_order=None` to the signature (after `department=None`), and add `"sales_order": sales_order,` to the `frappe.get_doc({...})` dict.

- [ ] **Step 2: Smoke the backend arg**

Run: `cd /Users/sayanthns/frappe-bench && python3 -c "import ast; ast.parse(open('apps/next_pms/next_pms/api/crud.py').read()); print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Frontend — load Sales Orders + field**

In `CreateProjectModal.vue`:
- Add to `getDefaultForm()`/form: `sales_order: ''`.
- Add a ref + loader (mirror how clients are loaded; if clients come from a prop/list, fetch SOs via the Frappe client API). In `<script setup>`:
```javascript
const salesOrders = ref([])
async function loadSalesOrders() {
  try {
    const rows = await call('frappe.client.get_list', {
      doctype: 'Sales Order', filters: { docstatus: 1 },
      fields: ['name', 'grand_total', 'customer'], limit_page_length: 0, order_by: 'creation desc',
    })
    salesOrders.value = Array.isArray(rows) ? rows : (rows?.message || [])
  } catch (e) { console.error('Failed to load sales orders', e) }
}
```
Call `loadSalesOrders()` where the modal initialises (the same place clients load, e.g. a `watch(() => props.show, ...)` or `onMounted`).
- Template — add after the Client field group:
```html
      <div class="form-group">
        <label class="form-label">Sales Order <span class="required">*</span></label>
        <select v-model="form.sales_order" class="form-input" required>
          <option value="" disabled>Select a sales order</option>
          <option v-for="so in salesOrders" :key="so.name" :value="so.name">
            {{ so.name }} — {{ so.customer }} ({{ so.grand_total }})
          </option>
        </select>
      </div>
```

- [ ] **Step 4: Guard submit + pass arg**

In `handleSubmit`, after the budget guard:
```javascript
  if (!form.value.sales_order) {
    alert('Sales Order is required')
    return
  }
```
And add to the `create_project` call payload: `sales_order: form.value.sales_order,`.

- [ ] **Step 5: Build**

Run: `cd frontend && yarn build` → clean.

- [ ] **Step 6: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/api/crud.py frontend/src/components/CreateProjectModal.vue
git commit -m "feat: Sales Order picker in create-project (required) + backend arg

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: get_project_financials + SO comparison in reports

**Files:**
- Modify: `next_pms/api/project_report.py` (add helper + use in `get_project_report_data` and `get_multi_project_report_data`)
- Test: `next_pms/api/test_project_financials.py` (new)

- [ ] **Step 1: Write the failing test**

Create `next_pms/api/test_project_financials.py`:
```python
# apps/next_pms/next_pms/api/test_project_financials.py
import frappe
from frappe.tests.utils import FrappeTestCase

from next_pms.api.project_report import get_project_financials


class TestProjectFinancials(FrappeTestCase):
    def test_financials_shape(self):
        # Use any existing project, or skip if none
        proj = frappe.db.get_value("PMS Project", {}, "name")
        if not proj:
            self.skipTest("no PMS Project in test db")
        f = get_project_financials(proj)
        for k in ("so_value", "budget", "actual", "budget_util", "so_util"):
            self.assertIn(k, f)

    def test_so_util_zero_safe(self):
        from next_pms.api.project_report import _financials_dict
        f = _financials_dict(so_value=0, budget=0, actual=10)
        self.assertEqual(f["so_util"], 0)
        self.assertEqual(f["budget_util"], 0)
```

- [ ] **Step 2: Run, expect FAIL**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_project_financials`
Expected: FAIL — `cannot import name 'get_project_financials'`.

- [ ] **Step 3: Implement the helper**

In `next_pms/api/project_report.py`, add (ensure `from frappe.utils import flt` is imported):
```python
def _financials_dict(so_value, budget, actual):
    so_value = flt(so_value); budget = flt(budget); actual = flt(actual)
    return {
        "so_value": round(so_value, 2),
        "budget": round(budget, 2),
        "actual": round(actual, 2),
        "budget_util": round(actual / budget * 100, 1) if budget > 0 else 0,
        "so_util": round(actual / so_value * 100, 1) if so_value > 0 else 0,
    }


@frappe.whitelist()
def get_project_financials(project):
    """SO value vs budget vs actual cost for a project."""
    proj = frappe.db.get_value(
        "PMS Project", project,
        ["sales_order", "total_budget", "calculated_cost"], as_dict=True,
    ) or {}
    so_value = 0
    if proj.get("sales_order"):
        so_value = frappe.db.get_value("Sales Order", proj["sales_order"], "grand_total") or 0
    return _financials_dict(so_value, proj.get("total_budget"), proj.get("calculated_cost"))
```

- [ ] **Step 4: Add to project status report data**

In `get_project_report_data`, before the `return {...}`, add:
```python
    financials = get_project_financials(project)
```
and add to the returned dict: `"financials": financials,`. In the report's HTML builder (the function that renders `get_project_report_data` into email HTML — find it in this file, e.g. `_build_project_report_html` / inside `send_project_report`), add a block rendering SO / Budget / Actual / Util:
```python
    f = data["financials"]
    financials_html = f"""
    <table style="border-collapse:collapse; margin:12px 0;">
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Sales Order Value</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{f['so_value']:,.2f}</td></tr>
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Budget</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{f['budget']:,.2f}</td></tr>
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Actual Cost</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{f['actual']:,.2f} ({f['budget_util']:.0f}% of budget)</td></tr>
    </table>"""
```
and inject `financials_html` into the email body template where appropriate (near the progress section).

- [ ] **Step 5: Add to multi-project report**

In `get_multi_project_report_data`, for each project row include `get_project_financials(p)` values (so_value, budget, actual, budget_util). In its HTML builder add columns: SO, Budget, Actual, Util%. (Mirror the existing per-project row construction in that function.)

- [ ] **Step 6: Run test, expect PASS + smoke**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_project_financials`
Expected: PASS.
Smoke: `bench --site mysite.local execute next_pms.api.project_report.get_project_financials --kwargs "{'project':'<any project name>'}"` → prints the dict.

- [ ] **Step 7: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/api/project_report.py next_pms/api/test_project_financials.py
git commit -m "feat: get_project_financials + SO/Budget/Actual in project & multi-project reports

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: SO vs Budget vs Actual card on the project dashboard

**Files:**
- Modify: `frontend/src/views/ProjectDashboard.vue`

- [ ] **Step 1: Fetch financials**

In `ProjectDashboard.vue` `<script setup>`, add a ref + loader keyed to the current project id (mirror how the view already loads project data):
```javascript
const financials = ref(null)
async function loadFinancials(projectName) {
  try {
    const r = await call('next_pms.api.project_report.get_project_financials', { project: projectName })
    financials.value = r?.message || r
  } catch (e) { console.error('financials load failed', e) }
}
```
Call `loadFinancials(<projectName>)` wherever the dashboard loads its project (same lifecycle hook / watch as existing data load).

- [ ] **Step 2: Render the card**

In the template, near the existing budget display, add:
```html
      <div v-if="financials" class="financials-card" style="display:flex; gap:24px; padding:16px; border:1px solid #e5e7eb; border-radius:8px; margin:16px 0;">
        <div><div style="font-size:12px; color:#6b7280;">Sales Order</div><div style="font-weight:600;">{{ financials.so_value.toLocaleString() }}</div></div>
        <div><div style="font-size:12px; color:#6b7280;">Budget</div><div style="font-weight:600;">{{ financials.budget.toLocaleString() }}</div></div>
        <div><div style="font-size:12px; color:#6b7280;">Actual</div><div style="font-weight:600;">{{ financials.actual.toLocaleString() }} ({{ financials.budget_util }}%)</div></div>
      </div>
```

- [ ] **Step 3: Build**

Run: `cd frontend && yarn build` → clean.

- [ ] **Step 4: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add frontend/src/views/ProjectDashboard.vue
git commit -m "feat: SO vs Budget vs Actual card on project dashboard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 95% budget guard on new time entries

**Files:**
- Modify: `next_pms/next_pms/doctype/pms_time_log/pms_time_log.py`
- Test: `next_pms/next_pms/doctype/pms_time_log/test_pms_time_log.py`

- [ ] **Step 1: Write the failing test**

In `test_pms_time_log.py` add (create a project at 96% utilisation + a task, assert insert throws; at 94% assert allowed). Concrete:
```python
import frappe
from frappe.tests.utils import FrappeTestCase


class TestBudgetGuard(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _project_at(self, util):
        proj = frappe.get_doc({
            "doctype": "PMS Project", "project_name": f"ZZ Guard {util}",
            "status": "Active", "total_budget": 1000,
            "sales_order": frappe.db.get_value("Sales Order", {}, "name"),
        })
        proj.insert(ignore_permissions=True)
        # force utilisation directly (bypass recompute)
        frappe.db.set_value("PMS Project", proj.name, "budget_utilization", util)
        task = frappe.get_doc({
            "doctype": "PMS Task", "task_title": "ZZ Guard Task",
            "project": proj.name, "status": "Open",
        })
        task.insert(ignore_permissions=True)
        return task.name

    def test_blocks_new_log_at_96(self):
        task = self._project_at(96)
        log = frappe.get_doc({"doctype": "PMS Time Log", "task": task,
                              "user": "Administrator", "is_running": 1})
        with self.assertRaises(frappe.ValidationError):
            log.insert(ignore_permissions=True)

    def test_allows_new_log_at_94(self):
        task = self._project_at(94)
        log = frappe.get_doc({"doctype": "PMS Time Log", "task": task,
                              "user": "Administrator", "is_running": 1})
        log.insert(ignore_permissions=True)  # must not throw
        self.assertTrue(log.name)
```
(If `Sales Order` has no record in the test DB, the project insert will fail the SO requirement; in that case create a minimal submitted Sales Order in `setUp`, or `frappe.db.set_value` the project's sales_order after a bypassed insert. Use whichever keeps the test focused on the guard — document the choice.)

- [ ] **Step 2: Run, expect FAIL**

Run: `bench --site mysite.local run-tests --module next_pms.next_pms.doctype.pms_time_log.test_pms_time_log`
Expected: `test_blocks_new_log_at_96` FAILS (no guard yet — insert succeeds).

- [ ] **Step 3: Add the guard**

In `pms_time_log.py`, add `from frappe import _` and `from frappe.utils import flt` to imports, and add the method + hook it into `validate` is wrong (validate runs on update too) — use `before_insert`:
```python
    def before_insert(self):
        self.validate_budget_available()

    def validate_budget_available(self):
        # Block NEW time entries (timer start or manual) when project budget is exhausted.
        # Updating/stopping an existing log is not an insert → not blocked.
        if not self.task:
            return
        project = frappe.db.get_value("PMS Task", self.task, "project")
        if not project:
            return
        util = flt(frappe.db.get_value("PMS Project", project, "budget_utilization"))
        if util >= 95:
            frappe.throw(
                _("Project budget at {0}% (>= 95%). New time entries are blocked until the budget is increased. Use 'Request budget increase'.").format(round(util)),
                title=_("Budget Exhausted"),
            )
```

- [ ] **Step 4: Run, expect PASS**

Run: `bench --site mysite.local run-tests --module next_pms.next_pms.doctype.pms_time_log.test_pms_time_log`
Expected: PASS (both new tests + any existing).

- [ ] **Step 5: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/next_pms/doctype/pms_time_log/pms_time_log.py next_pms/next_pms/doctype/pms_time_log/test_pms_time_log.py
git commit -m "feat: block new time entries at >=95% project budget

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: request_budget_increase endpoint + timer-store wiring

**Files:**
- Modify: `next_pms/api/budget.py` (new endpoint)
- Modify: `frontend/src/store/timer.js` (catch Budget-Exhausted)
- Test: `next_pms/api/test_budget_request.py` (new)

- [ ] **Step 1: Write the failing test**

Create `next_pms/api/test_budget_request.py`:
```python
# apps/next_pms/next_pms/api/test_budget_request.py
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

from next_pms.api import budget


class TestBudgetRequest(FrappeTestCase):
    def test_request_emails_sayanth(self):
        proj = frappe.db.get_value("PMS Project", {}, "name")
        if not proj:
            self.skipTest("no project")
        with patch("frappe.sendmail") as m:
            res = budget.request_budget_increase(proj)
        self.assertTrue(res.get("success"))
        self.assertIn("sayanth@enfono.in", m.call_args.kwargs.get("recipients", []))
```

- [ ] **Step 2: Run, expect FAIL**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_budget_request`
Expected: FAIL — `module 'next_pms.api.budget' has no attribute 'request_budget_increase'`.

- [ ] **Step 3: Implement the endpoint**

In `next_pms/api/budget.py` (add `from frappe import _` and `from frappe.utils import flt` if missing):
```python
@frappe.whitelist()
def request_budget_increase(project):
    """Email a budget-increase request to the approver (sayanth@enfono.in)."""
    APPROVER = "sayanth@enfono.in"
    p = frappe.db.get_value(
        "PMS Project", project,
        ["project_name", "total_budget", "calculated_cost", "budget_utilization"],
        as_dict=True,
    )
    if not p:
        frappe.throw(_("Project not found"))
    requester = frappe.session.user
    requester_name = frappe.db.get_value("User", requester, "full_name") or requester
    msg = f"""
    <h3>Budget Increase Request</h3>
    <p><b>{requester_name}</b> ({requester}) requests a budget increase.</p>
    <table style="border-collapse:collapse;">
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Project</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{p.project_name}</td></tr>
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Current Budget</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{flt(p.total_budget):,.2f}</td></tr>
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Actual Cost</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{flt(p.calculated_cost):,.2f}</td></tr>
      <tr><td style="padding:6px 12px; border:1px solid #e5e7eb;">Utilisation</td><td style="padding:6px 12px; border:1px solid #e5e7eb;">{flt(p.budget_utilization):.0f}%</td></tr>
    </table>
    <p>Raise the Total Budget on the project to unblock time logging.</p>
    """
    frappe.sendmail(recipients=[APPROVER], subject=_("Budget increase request: {0}").format(p.project_name),
                    message=msg, now=True)
    return {"success": True, "message": _("Request sent to {0}").format(APPROVER)}
```

- [ ] **Step 4: Run, expect PASS**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_budget_request`
Expected: PASS.

- [ ] **Step 5: Frontend — offer request on Budget-Exhausted**

In `frontend/src/store/timer.js`, in the `start_timer` call's catch/error path (~line 129), detect the budget error and offer the request. Concrete: wrap the existing call so that when the error message contains "Budget" / "budget", prompt:
```javascript
      // inside the catch for start_timer failure, after capturing `err`
      const emsg = (err && (err.message || err._server_messages || String(err))) || ''
      if (/budget/i.test(emsg)) {
        // surface a request action; project resolved from the task's project
        if (confirm('Project budget exhausted (>=95%). Send a budget-increase request to sayanth@enfono.in?')) {
          try {
            const projName = await call('frappe.client.get_value', {
              doctype: 'PMS Task', filters: { name: taskId }, fieldname: 'project',
            })
            const project = projName?.message?.project || projName?.project
            if (project) await call('next_pms.api.budget.request_budget_increase', { project })
            alert('Budget increase request sent to sayanth@enfono.in')
          } catch (e) { console.error('request failed', e) }
        }
      }
```
(Adapt variable names to the store's actual `start_timer` action — `taskId` is whatever the action received. Keep the existing error rethrow/handling intact; just add this branch.)

- [ ] **Step 6: Build**

Run: `cd frontend && yarn build` → clean.

- [ ] **Step 7: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/api/budget.py next_pms/api/test_budget_request.py frontend/src/store/timer.js
git commit -m "feat: request_budget_increase endpoint + timer-store budget-exhausted prompt

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Rebuild frontend bundle + docs

**Files:**
- Modify: `next_pms/public/frontend/*` (built), `CLAUDE.md`, `skills/session-logs/2026-05-31-features.md`

- [ ] **Step 1: Final frontend build**

Run: `cd frontend && yarn build`
Expected: clean build producing updated `next_pms/public/frontend/` assets.

- [ ] **Step 2: Update CLAUDE.md**

Add a May-2026 Confirmed-Features entry: SO mandatory on new projects + SO/Budget/Actual comparison (reports + dashboard); 95% budget guard blocking new time entries with email approval to sayanth@enfono.in; working-hours/weekly-recipient now editable in the Team→AI Settings tab.

- [ ] **Step 3: Commit (built assets + docs)**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/public/frontend CLAUDE.md skills/session-logs/2026-05-31-features.md
git commit -m "build+docs: SO/budget-guard/hours-UI bundle + memory

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Deployment (after local verification — office, manual, window-gated)

Per CLAUDE.md deploy block (server EFTSP-009, site `enfono-office-new`, via control→Tailscale `100.104.220.9`):
1. `git pull` (clean stale dist first: `git clean -fd next_pms/public/frontend/` as root + `chown -R v15:v15`).
2. `bench --site enfono-office-new migrate` (syncs `sales_order` field).
3. `bench build --app next_pms`.
4. root `supervisorctl restart frappe-bench-web: frappe-bench-workers:`.
5. Verify `office.enfonoerp.com/api/method/ping`=200; set working hours in AI Settings tab; confirm SO required on new project; confirm timer block at ≥95%.

---

## Self-Review

**Spec coverage:**
- A hours-in-UI → Tasks 1 (API) + 2 (UI). ✓
- B SO mandatory → Task 3; create flow → Task 4; comparison helper + reports → Task 5; dashboard → Task 6. ✓
- C 95% guard → Task 7; approval email + frontend → Task 8. ✓
- Build + docs → Task 9. ✓

**Type/name consistency:** `get_project_financials`/`_financials_dict` keys (`so_value`, `budget`, `actual`, `budget_util`, `so_util`) consistent across Tasks 5/6. `working_hours_per_day`/`weekly_summary_recipient` consistent Tasks 1/2. `request_budget_increase(project)` consistent Tasks 8 frontend+backend. `validate_sales_order`/`sales_order` consistent Task 3/4. ✓

**Placeholders:** code shown for every step. Two frontend steps (Task 6 dashboard load hook, Task 8 timer store var names) say "adapt to the existing lifecycle/var" — unavoidable since they depend on the file's structure; the implementer reads the file first. Acceptable (not a logic placeholder).

**Risk note:** Tasks 7 & 8 tests need a `Sales Order` record to exist (because PMS Project now requires one). Implementer must create a minimal submitted Sales Order in test setUp or bypass via `frappe.db.set_value` — documented in those tasks.
