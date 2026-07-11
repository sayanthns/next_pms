# Next PMS — Developer Documentation

Technical reference for developers working on `next_pms`. For end-user docs see the hosted guide at `/pms-guide` (source: [`next_pms/www/pms-guide.html`](../next_pms/www/pms-guide.html)).

---

## Architecture

```
next_pms/                       Frappe app (Python, v15)
├── next_pms/
│   ├── api/                    Whitelisted HTTP endpoints (SPA backend)
│   ├── next_pms/doctype/       DocTypes + controllers
│   ├── www/                    Public web pages (user-guide, pms-portal)
│   ├── public/frontend/        BUILT Vue SPA (committed — see Deploy)
│   ├── tasks.py                Scheduler jobs (emails, reminders, alerts)
│   └── hooks.py                Scheduler events, fixtures, assets
├── frontend/                   Vue 3 + Vite + Pinia SPA source
│   └── src/{views,components,store,utils}
├── android-capacitor/          Capacitor Android wrapper
└── docs/                       This documentation
```

- **SPA** served at `/next-pms` from `next_pms/public/frontend` (vite build output).
- **Client portal** at `/pms-portal?token=…` — server-rendered, token-auth, no login.
- **Desk** is secondary; primary UX is the SPA.

## DocTypes

| DocType | Purpose | Notes |
|---|---|---|
| PMS Project | Project + budget + team + portal settings | `budget_utilization` auto-computed; 80% alert |
| PMS Project Member | Child: member + hourly rate | Rate feeds task cost |
| PMS Sprint | Sprint with date range | Planning → Active → Completed |
| PMS Task | Task | `estimated_hours` PM-set; `actual_hours` timer-derived; statuses Backlog/To Do/In Progress/In Review/Done |
| PMS Time Log | Timer entry | **The only "actual hours" source** in the entire app |
| PMS Checkin | Attendance | Informational; never a work-hours baseline |
| PMS Comment | Task comments | ⚠️ fields are `comment` and `user` — NOT `content`/`author` |
| PMS Meeting | Calendar meetings | Attendees child table; MoM mandatory |
| Weekly Plan (+ children) | Weekly allocations matrix | `published=1` plans feed Plan Adherence |
| PMS AI Settings | Single: report/email config | `working_hours_per_day`, recipients, toggles |
| PMS Client Portal Access | Portal tokens | |

## API layer (`next_pms/api/`)

All SPA calls go through whitelisted methods here. Key modules:

| Module | Responsibility |
|---|---|
| `_hours.py` | **Single source of truth** for target/utilization math (see Metrics Engine) |
| `productivity.py` | Employee Productivity tab (`get_employee_productivity`) |
| `performance.py` | Composite Performance Score (`get_performance_score`, management-only) |
| `crud.py` | Task report, task/project CRUD |
| `weekly_plan.py` | Weekly Plan matrix builder |
| `calendar.py` | Meetings |
| `ai_report.py` | Daily AI report generation |
| `permissions.py` | `is_admin_user()`, `is_manager_user()`, `get_user_projects()` |
| `portal.py` | Client portal (token auth) |
| `timer.py`, `checkin.py`, `notifications.py`, `settings.py`, `users.py` | Self-explanatory |

### Hard rules (production incidents happened — respect these)

1. **PMS Comment fields are `comment` and `user`** — not `content`/`author`.
2. **All portal `frappe.get_all()` need `ignore_permissions=True`** — PMS Customer users lack doctype read perms.
3. **Never `frappe.get_doc()` in portal APIs** — use `frappe.db.get_value()` / `frappe.get_all(..., ignore_permissions=True)`.
4. Whitelisted methods that expose cross-user data must gate on `is_admin_user() or is_manager_user()` and `frappe.throw` otherwise.
5. Coerce inputs with `cint`/`flt`/`cstr`/`getdate` from `frappe.utils`, never bare `int()`/`float()`.
6. No f-string SQL, ever. `frappe.qb` or parameterised `frappe.db.sql`.

## Metrics engine

### `_hours.py` — the shared basis

Every report derives "how many hours should this person have worked" from here so numbers stay consistent:

```
target_hours = effective_working_days × working_hours_per_day (default 8)

effective_working_days = all days in range
                       − Sundays
                       − holidays (employee's Holiday List, weekly_off=0)
                       − full-day approved leave (docstatus != 2!)
                       − 0.5 × half-day approved leave
```

- `PMS Time Log.duration_hours` is the only "actual hours" source. Check-in/out is informational.
- Frappe quirk handled here: cancelled Leave Applications keep `status='Approved'` with `docstatus=2` — must exclude docstatus 2 explicitly.

### The two headline metrics — do not conflate

| | Utilization | Efficiency |
|---|---|---|
| Formula | logged ÷ target × 100 | estimated ÷ actual × 100 |
| Question | enough hours vs the bar? | estimates accurate? (>100% = faster) |

Windows also differ by surface: **weekly email = fixed Mon–Fri week** (Saturday cron, Saturday excluded from target); **Task Report periods = rolling N days ending today**. Same engine, different slice — both metrics are now labelled with their formula wherever shown.

### Performance Score (`performance.py`)

Management-only composite, 8 dimensions, weights fixed in `WEIGHTS` (sum 100):

| Dimension | Weight | Formula (each scored 0–100) |
|---|---|---|
| delivery | 25 | Σ est. hours of completed tasks ÷ target, cap 100 |
| timeliness | 15 | on-time ÷ due-dated completions |
| utilization | 15 | logged ÷ target, cap 100 |
| plan_adherence | 15 | hours on published-Weekly-Plan projects ÷ planned, cap 100 |
| efficiency | 10 | est ÷ actual, capped `EFFICIENCY_CAP=120`, normalised /120 |
| quality | 10 | 1 − reopened ÷ completed (reopen = Version history shows status Done→other) |
| consistency | 5 | days with ≥50% daily target logged ÷ working days |
| attendance | 5 | checked-in ÷ working days |

- Composite = Σ(weight × score) ÷ Σ included weights. **Dimensions with no data are excluded and weights renormalised** — missing data never scores zero.
- "Completed in window" proxy = `status='Done' AND modified BETWEEN window` (PMS Task has no completion_date — roadmap item).
- Bands: A ≥ 85, B ≥ 70, C ≥ 50, else D.
- Methodology is user-documented inside the Performance tab (`PerformanceTab.vue`) — **keep code, tab docs and this file in sync when changing formulas.**

## Scheduler jobs (`tasks.py` + `hooks.py`)

| Job | Cron | What |
|---|---|---|
| `send_weekly_summary` | Sat 07:00 | Per-member email + management team table (Utilization + Efficiency) |
| `generate_daily_report` (`ai_report.py`) | daily 03:00 | AI daily report to management |
| `send_checkin_reminders` | per config | Missing check-in/out nudges |
| Budget alerts | on update | ≥80% budget utilisation |

⚠️ After deploying scheduler-code changes, **restart workers** — stale workers silently run old code (2026-06-18 incident: 4-day silent outage).

## Frontend (Vue 3 + Vite + Pinia)

- Views in `frontend/src/views`, shared components in `frontend/src/components`.
- API calls: `import { call } from '@/utils/frappe'` → `call('next_pms.api.module.method', {args})`.
- Role gates: `useSettingsStore()` → `isAdmin`, `isManager`, `canViewFinance`. Gate **both** the UI (`v-if`) and the backend (throw) — UI hiding alone is not security.
- Dev: `npx vite --port 8081` (proxies `/api` to `localhost:8000`). Local site: `mysite.local` — `bench serve` serves `sites/currentsite.txt`; if the SPA says "App next_pms is not installed", you're on the wrong current site (`bench use mysite.local`).

## Build & Deploy

**Built SPA assets are committed to the repo** (`next_pms/public/frontend`). Production deploy is therefore pull-only:

```bash
# 1. Local: build + commit
cd frontend && yarn build          # outputs to next_pms/public/frontend
git add -A && git commit && git push

# 2. Server (as bench user)
cd frappe-bench/apps/next_pms && git pull origin main

# 3. Restart (root — `bench restart` fails as bench user on office)
supervisorctl restart all

# 4. Only if a www/ page changed:
bench --site <site> clear-website-cache

# 5. Only if DocType JSON / fixtures / hooks cron changed:
bench --site <site> migrate       # ⚠️ see migrate warning below
```

- **`yarn build` in `frontend/` ≠ `bench build`.** The former builds the SPA; the latter bundles Frappe assets. SPA changes need the former.
- ⚠️ **Migrate on office is currently booby-trapped** by an HRMS web-form duplicate. For new doctypes prefer targeted `frappe.reload_doc(module, "doctype", "name")` over full migrate; always take a DB backup first.
- Multiple sites exist on production benches — **verify the site** before any `bench --site` command.

## Testing

```bash
bench --site mysite.local run-tests --app next_pms          # all
bench --site mysite.local run-tests --module next_pms.api.test_hours
```

Tests live beside the modules (`api/test_*.py`) and in doctype folders (`test_<doctype>.py`), inheriting `FrappeTestCase`. Anything touching money, hours math, or permissions needs a test.

## Roadmap

| Status | Item | Notes |
|---|---|---|
| **Next** | **Monthly Performance Score snapshots** | New submittable doctype `PMS Performance Score` (employee, month, per-dimension scores, composite, band). Monthly cron computes + submits → frozen, tamper-evident appraisal record that doesn't drift as live data changes; enables trend graphs without recompute. Needs: doctype + cron hook + migrate strategy (reload_doc), fixture export. |
| **Next** | **PM override ±10 with mandatory comment** | Stored adjustment on the monthly snapshot (adjustment, reason, adjusted_by, timestamp). Metrics inform, humans decide — with an audit trail. Blocked on the snapshot doctype above. |
| Planned | `completion_date` on PMS Task | Replace the "Done + modified-in-window" proxy in performance/email metrics. |
| Planned | PMS Performance Settings (Single) | Management-tunable `WEIGHTS`/caps; replaces hardcoded dict in `performance.py`. |
| Planned | Android APK release | Capacitor build in `android-capacitor/`. |

## Related docs

- [`README.md`](../README.md) — features, install, access points
- [`PERMISSIONS.md`](../PERMISSIONS.md) — role system deep-dive
- `/pms-guide` (hosted) — end-user documentation
- `CLAUDE.md` — AI-agent project memory (safety rules, session logs)
