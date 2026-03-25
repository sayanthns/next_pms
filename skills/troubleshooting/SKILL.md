# Next PMS — Known Issues & Fixes

## Quick Reference: "If you see X, check Y"

| Symptom | Check This |
|---------|-----------|
| Portal drawer shows "Loading..." forever | API uses `frappe.get_doc()` or missing `ignore_permissions=True` |
| `Unknown column 'content'` error | You used `content` instead of `comment` on PMS Comment |
| `Unknown column 'author'` error | You used `author` instead of `user` on PMS Comment |
| Portal shows empty data / "No tasks found" | Missing `ignore_permissions=True` on `frappe.get_all()` |
| Grant Access shows "No portal-enabled projects" | `client_portal_enabled` not set. Fix: auto-enable in `invite_client()` |
| `Client portal is not enabled for project` on insert | Must enable `client_portal_enabled` BEFORE creating `PMS Client Portal Access` record |
| Customer sees admin dashboard instead of portal | `settingsStore.isCustomer` not detected. Check `isCustomer` flag in settings.js |
| Frontend shows old UI after deploy | Browser cache. Hard refresh: Cmd+Shift+R |
| API returns 403 on dev server (port 8081) | Dev server can't forward auth cookies. Test at `localhost:8000` instead |
| `bench migrate` affects wrong site | Forgot `bench use office`. Always run it first |
| Python changes not taking effect after deploy | Forgot `supervisorctl restart all`. Workers cache modules |
| Support tickets showing in Tasks tab | Portal API not filtering `task_type != "Support Ticket"` |
| `Method Not Allowed` error | Function missing `@frappe.whitelist()` decorator |
| Token login fails | Token may have been regenerated. Check DB for current token |

---

## Bug Pattern 1: PMS Comment Field Names

### Symptom
`pymysql.err.OperationalError: (1054, "Unknown column 'content' in 'SELECT'")`

### Root Cause
PMS Comment doctype uses non-standard field names:
- Content field: `comment` (NOT `content`)
- Author field: `user` (NOT `author`)

### Why It Keeps Happening
Every developer (including AI agents) assumes comments have `content` and `author` fields. The PMS Comment doctype deviates from this convention.

### Fix
```python
# WRONG
frappe.get_all("PMS Comment", fields=["content", "author", "creation"])

# CORRECT
frappe.get_all("PMS Comment", fields=["comment", "user", "task", "mentions", "creation"])
```

### Prevention
Always check the doctype JSON or run `DESCRIBE \`tabPMS Comment\`` before writing queries.

---

## Bug Pattern 2: Portal Permission Errors

### Symptom
Portal pages show "Loading..." or empty data. Console shows 403 or PermissionError.

### Root Cause
PMS Customer users lack doctype-level read permissions on PMS Task, PMS Sprint, etc. Frappe's default `get_all()` and `get_doc()` enforce these permissions.

### Diagnosis
1. Check browser console for the failing API call
2. Look at the Python function — does it use `frappe.get_doc()` or `frappe.get_all()` without `ignore_permissions`?
3. Test the API as the customer user (not Administrator)

### Fix
```python
# WRONG — will fail for PMS Customer
t = frappe.get_doc("PMS Task", task_name)

# CORRECT — bypass doctype permissions, verify access manually
_verify_portal_access(user, project)  # ALWAYS call this first
task_data = frappe.db.get_value("PMS Task", task_name,
    ["name", "task_title", "status", "priority"], as_dict=True)
```

For list queries:
```python
# WRONG
tasks = frappe.get_all("PMS Task", filters={"project": project}, fields=[...])

# CORRECT
tasks = frappe.get_all("PMS Task", filters={"project": project}, fields=[...], ignore_permissions=True)
```

### Prevention
Every new portal API MUST:
1. Call `_verify_portal_access(user, project)` first
2. Use `ignore_permissions=True` on ALL `frappe.get_all()` calls
3. Use `frappe.db.get_value()` instead of `frappe.get_doc()`

---

## Bug Pattern 3: Portal Access Auto-Enable Race Condition

### Symptom
`frappe.exceptions.ValidationError: Client portal is not enabled for project PROJ-XXXX`

### Root Cause
The `PMS Client Portal Access` doctype has a `validate()` hook that checks `client_portal_enabled` on the project. If you try to create an access record on a project where portal isn't enabled, it throws.

### Diagnosis
Check `invite_client()` in `portal.py` — the auto-enable must happen BEFORE `doc.insert()`.

### Fix
```python
# Auto-enable BEFORE creating access record
if not frappe.db.get_value("PMS Project", project, "client_portal_enabled"):
    frappe.db.set_value("PMS Project", project, "client_portal_enabled", 1)

# THEN create the record
doc = frappe.get_doc({...})
doc.insert(ignore_permissions=True)
```

### Prevention
Never create `PMS Client Portal Access` records manually without enabling portal on the project first.

---

## Bug Pattern 4: Frontend Cache After Deploy

### Symptom
Users see old UI even after deploying new code. Features appear missing.

### Root Cause
Browsers aggressively cache JavaScript bundles. Vite generates hashed filenames, but the browser may cache the `index.html` that points to old bundle names.

### Fix
Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

### Prevention
After deploying frontend changes, always instruct users to hard refresh. Consider adding cache-busting headers to nginx config.

---

## Bug Pattern 5: bench migrate on Wrong Site

### Symptom
Schema changes applied to wrong database. Wrong site gets new doctype fields. Or migration fails because the wrong site doesn't have next_pms installed.

### Root Cause
Production server has 4 sites. `bench migrate` uses `currentsite.txt`. If it's set to `katcherp` instead of `office`, migration runs on the wrong DB.

### Fix
```bash
bench use office  # ALWAYS run this first
bench migrate
```

### Prevention
Every deploy script must include `bench use office` before any bench command.

---

## Bug Pattern 6: Support Tickets Mixed with Regular Tasks

### Symptom
Support tickets appear in the Tasks tab of portal project view, mixed with regular development tasks.

### Root Cause
The `get_portal_project_detail()` API fetches ALL tasks for the project without filtering out support tickets.

### Fix
```python
# Filter out support tickets from tasks tab
tasks = frappe.get_all("PMS Task",
    filters={"project": project, "task_type": ["!=", "Support Ticket"]},
    ...
)
```

### Prevention
Any API that returns task lists should consider whether support tickets should be included or excluded.

---

## Bug Pattern 7: Customer Accessing Admin Dashboard

### Symptom
User with `PMS Customer` role sees the full admin PMS dashboard (Home, Projects, My Tasks, etc.) instead of being redirected to the portal.

### Root Cause
The route guard in `router/index.js` checks `settingsStore.isCustomer` but the settings may not be loaded yet, or the `isCustomer` flag isn't properly set.

### Diagnosis
1. Check if the user has `PMS Customer` role in Frappe
2. Check `get_pms_settings()` API response — does it return the customer role?
3. Check `settingsStore.isCustomer` in browser console

### Fix
The route guard in `router/index.js` (`router.beforeEach`) must:
1. Load settings if not loaded
2. Check `settingsStore.isCustomer`
3. Redirect to `/portal` for all non-portal routes

---

## Bug Pattern 8: Token Changed After Regenerate

### Symptom
Portal token URL stops working. Error: "Invalid or expired access token"

### Root Cause
Someone clicked "Regenerate Token" in the Client Portal management tab. The old token is invalidated.

### Diagnosis
```sql
SELECT access_token FROM `tabPMS Client Portal Access` WHERE client_email='...' AND project='...';
```

### Fix
Use the new token from the database. Or generate a new one from the management UI.

---

## Bug Pattern 9: Email Notifications Not Sending

### Symptom
Portal clients don't receive email when their ticket gets a response.

### Root Cause
The `notify_portal_client()` method in `pms_comment.py` uses `frappe.enqueue()` which requires the worker to be running. If the short worker is down, emails queue but never send.

### Diagnosis
```bash
# Check worker status
sudo supervisorctl status | grep worker

# Check email queue
bench --site office console
>>> frappe.get_all("Email Queue", filters={"status": "Not Sent"}, fields=["name", "recipients", "creation"])
```

### Fix
```bash
sudo supervisorctl restart frappe-bench-workers:frappe-bench-frappe-short-worker-0
```
