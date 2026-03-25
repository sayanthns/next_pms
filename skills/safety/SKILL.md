# Safety Rules & Precautions for Next PMS

> Read this FIRST before making ANY changes. Violations can break production for multiple client sites.

## Hard Rules (NEVER do these)

### 1. NEVER commit without explicit user confirmation
- **Why:** The user has standing instructions that NO git commits happen without their approval.
- **What happens if you violate:** Loss of trust, unwanted changes pushed to production.

### 2. NEVER run `bench build` for frontend deployment
- **Why:** The frontend is a standalone Vue 3 SPA. The correct command is `cd apps/next_pms/frontend && yarn build`.
- **What happens if you violate:** `bench build` builds Frappe bundles, NOT the Vue SPA. The site will serve stale frontend code while appearing to have "deployed successfully."

### 3. NEVER run `bench migrate` without `bench use <site>` first
- **Why:** The production server has 4 sites: `office`, `katcherp`, `enfono-office-new`, `spice`. Running migrate without specifying the site may migrate the wrong database.
- **What happens if you violate:** Schema changes applied to wrong client database. Data corruption risk.
- **Correct sequence:** `bench use office && bench migrate`

### 4. NEVER expose cost/finance data in portal APIs
- **Why:** Portal APIs are accessed by external customers. Fields like `hourly_rate`, `calculated_cost`, `total_budget`, `spent` must NEVER be included in portal API responses.
- **What happens if you violate:** Customers see internal billing rates and project costs. Business-critical data leak.
- **Files to check:** `next_pms/api/portal.py` — every function that returns task/project data.

### 5. NEVER use `frappe.get_doc()` in portal customer-facing APIs
- **Why:** `frappe.get_doc()` checks Frappe permissions. PMS Customer users typically lack read access to PMS Task, PMS Sprint, etc. It will throw `PermissionError`.
- **What happens if you violate:** Task/ticket detail drawers show "Loading..." forever.
- **Use instead:** `frappe.db.get_value()` for single values, `frappe.get_all(..., ignore_permissions=True)` for lists. Always verify access via `_verify_portal_access()` FIRST.

### 6. NEVER add `frappe.get_all()` without `ignore_permissions=True` in portal APIs
- **Why:** PMS Customer users don't have doctype-level read permissions. Default `frappe.get_all()` will return empty results or throw errors.
- **What happens if you violate:** Portal pages show empty data. Customers see "No tasks found" when tasks exist.

### 7. NEVER use `content` or `author` fields on PMS Comment
- **Why:** The actual field names are `comment` and `user`. This is a known gotcha that has caused production bugs multiple times.
- **What happens if you violate:** `pymysql.err.OperationalError: Unknown column 'content' in 'SELECT'`
- **Correct fields:** `comment` (longtext), `user` (Link to User), `task` (Link to PMS Task), `mentions` (Small Text)

### 8. NEVER push to main without testing on feature branch first
- **Why:** Main is auto-deployed to production. Untested code breaks the live site.
- **Correct flow:** Push to `feature/customer-portal` → test → merge to `main` → deploy.

### 9. NEVER skip `supervisorctl restart all` after deploying Python changes
- **Why:** Frappe's gunicorn workers cache Python modules. Without restart, old code runs even after git pull.
- **What happens if you violate:** API changes appear to not work. Confusing debugging sessions.

### 10. NEVER delete portal access records — revoke them instead
- **Why:** `PMS Client Portal Access` records track access history. Use `is_active = 0` to revoke.
- **What happens if you violate:** Audit trail lost. No way to know who had access to what.

---

## ALWAYS do these before certain operations

### Before ANY portal API change:
1. Check if the API is `allow_guest=True` or requires session auth
2. Verify `_verify_portal_access()` is called BEFORE any data fetch
3. Ensure ALL `frappe.get_all()` calls have `ignore_permissions=True`
4. Confirm NO cost/finance fields are returned
5. Test with a PMS Customer user session, not Administrator

### Before ANY frontend deploy:
1. Run `yarn build` in `frontend/` directory
2. Check build output for errors
3. Hard refresh browser (Cmd+Shift+R) after deploy — browser caches aggressively

### Before ANY database migration:
1. `bench use office` (production server)
2. Check which doctypes will be modified
3. Migration may fail on unrelated apps (HRMS, frappe_appointment) — next_pms doctypes usually sync before the error. This is OK.

### Before granting portal access:
1. The `PMS Client Portal Access` doctype validates `client_portal_enabled` on the project during `validate()`.
2. You MUST enable `client_portal_enabled` on the project BEFORE creating the access record.
3. The `invite_client()` API auto-enables it, but if creating records manually, set it first.

---

## Decision Matrix

| Situation | Do This | Don't Do This |
|-----------|---------|---------------|
| Need to fetch task data in portal API | `frappe.get_all("PMS Task", ..., ignore_permissions=True)` | `frappe.get_doc("PMS Task", name)` |
| Need to return comments | Use fields `comment`, `user`, `task` | Use fields `content`, `author` |
| Deploying frontend changes | `cd frontend && yarn build` | `bench build --app next_pms` |
| Deploying Python API changes | `git pull && supervisorctl restart all` | `git pull` alone |
| Adding new portal endpoint | Add `@frappe.whitelist()`, call `_verify_portal_access()` | Skip access verification |
| Customer can't see data | Add `ignore_permissions=True` to query | Remove permission checks entirely |
| Need to test portal | Use incognito + token URL | Test as Administrator (hides permission bugs) |
| Modifying PMS Comment | Check `comment` and `user` field names | Assume `content` and `author` |
| Multiple sites on server | `bench use office` first | Run `bench migrate` directly |

---

## Pre-Deployment Checklist

- [ ] All `frappe.get_all()` in portal APIs have `ignore_permissions=True`
- [ ] No cost/finance fields exposed in portal responses
- [ ] PMS Comment queries use `comment` and `user` (not `content`/`author`)
- [ ] `yarn build` completed without errors
- [ ] Tested with PMS Customer user (not just Administrator)
- [ ] `bench use office` run before migrate on server
- [ ] `supervisorctl restart all` run after Python changes
- [ ] Browser hard-refreshed after frontend deploy
- [ ] No `frappe.get_doc()` used in customer-facing portal APIs
