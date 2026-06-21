# Daily Report tab — design spec

**Date:** 2026-06-18
**Author:** Sayanth + Claude
**App:** next_pms (Frappe v15 app, Vue 3 + Vite SPA frontend)
**Status:** Approved for planning

## Goal

Add the daily AI productivity report (currently **email-only**, sent by the `0 3 * * *` scheduler job `next_pms.api.ai_report.generate_daily_report`) as a **viewable tab in the Reports section** of the PMS SPA, so leadership can open and browse it on demand instead of only receiving the morning email.

## Decisions (locked)

| Decision | Choice |
|---|---|
| Content source | **Live-generate on view** — no storage DocType; build + LLM on request |
| Rendering | **Native Vue layout** — cards/tables themed to the SPA (not the email HTML) |
| Visibility | **Managers / Finance** — gated by `can_view_finance` (same as Finance tab) |
| Date access | **Date picker with history** — default yesterday, browse any past day |

## Non-goals (YAGNI)

- No persistence of generated reports (explicitly declined — live-generate each view).
- No new DocType.
- No change to the email job's schedule, recipients, or behaviour.
- No per-person email split / subscriptions (out of scope).

## Architecture

### Backend — `next_pms/api/ai_report.py`

**1. Refactor: extract a shared build helper.**
Today `generate_daily_report` inlines: gather builders → `full_data` → `_call_llm` → `_parse_ai_response` → send email. Extract the build half into:

```python
def _build_report(report_date, settings, detail_level=None):
    """Gather metrics + run the LLM for report_date. No email, no perms.
    Returns (full_data, ai_parsed, ai_raw, ai_error, user_metrics,
             process_mining, time_patterns, project_summary)."""
```

`generate_daily_report` (email path) and the new view endpoint both call `_build_report`, so the two paths can never drift. The LLM call keeps the existing Claude→DeepSeek fallback. Inside the helper, wrap `_call_llm`/`_parse_ai_response` in try/except → on failure set `ai_parsed=None`, `ai_error=str(e)`; metrics still returned.

**2. New whitelisted endpoint.**

```python
@frappe.whitelist()
def get_daily_report_data(report_date=None):
    _require_finance_viewer()                 # server-side gate, see below
    report_date = getdate(report_date) if report_date else add_days(today(), -1)
    # guard: no future dates
    if getdate(report_date) >= getdate(today()):
        frappe.throw(_("Report date must be in the past."))
    skipped = _should_skip_report_for(report_date)   # Sunday / holiday reason or None
    settings = _get_ai_settings()
    ... = _build_report(str(report_date), settings)
    return {
        "report_date": str(report_date),
        "skipped_reason": skipped,            # str|None — UI shows a notice, still renders metrics
        "overall": full_data.get("overall", {}),
        "ai": ai_parsed,                      # structured dict or None
        "ai_raw": ai_raw,
        "ai_error": ai_error,                 # str|None
        "user_metrics": user_metrics,
        "process_mining": process_mining,
        "time_patterns": time_patterns,
        "project_summary": project_summary,
    }
```

- **Read-only:** never calls `_send_report_email`; ignores `daily_report_enabled` (that flag governs the email job only).
- **Skip handling differs from email:** the email job *aborts* on Sunday/holiday; the view still returns the data with a `skipped_reason` notice (a manager may want to inspect a Sunday). Refactor `_should_skip_report` → `_should_skip_report_for(report_date)` taking an explicit date; existing caller passes yesterday.
- **Permission gate** `_require_finance_viewer()`: reuse the **same source** that computes `can_view_finance` for the SPA (so tab visibility == endpoint access). If `can_view_finance` is role-derived, mirror `_require_billing_manager`'s pattern (`{System Manager, Administrator, PMS Manager}`); confirm the exact source in `settings.py` during implementation and use it verbatim. Throw `PermissionError` via `frappe.throw(..., frappe.PermissionError)` if denied.

### AI structured shape (already produced by `_build_analysis_prompt`)

```
executive_summary : str
user_assessments  : [{ name, rating: Good|Average|Needs Attention|Critical, summary }]
process_insights  : [str]
time_analysis     : [str]
bottlenecks       : [{ severity: High|Medium|Low, issue }]
recommendations   : [{ priority: int, action }]
```

### Frontend — new `frontend/src/components/DailyReportTab.vue`

- **Date picker:** default = yesterday; `max` = yesterday; allows past dates.
- **Fetch:** on date change call `get_daily_report_data(report_date)` via the app's frappe `call()` util. Show a loading state (~15s): "Generating AI analysis…".
- **In-session cache:** keep a `{ [date]: payload }` map in component state. Re-selecting a cached date renders instantly (past-day data is immutable). A **Regenerate** button bypasses the cache and re-calls (re-pays the LLM) for the current date.
- **Sections (native):**
  1. Header: date picker + Regenerate.
  2. Executive summary card (`ai.executive_summary`); if `ai_error`, show an "AI analysis unavailable" notice instead and continue to metrics.
  3. Overall stats row (`overall`).
  4. Per-user: assessment cards (rating badge colour-coded) joined with the `user_metrics` table (logged / target / utilization / done / efficiency / login-hrs, mirroring the email).
  5. Bottlenecks (severity badges).
  6. Process insights (list) + `process_mining` summary.
  7. Time analysis (list) + `time_patterns` summary.
  8. Recommendations (priority-ordered list).
  9. Project summary table (`project_summary`).
- **States:** loading · normal · `skipped_reason` notice (Sunday/holiday, still shows metrics) · `ai_error` (metrics only) · empty (no activity that day).

### `frontend/src/views/ReportsView.vue`

- Add tab button after Finance: `v-if="settingsStore.canViewFinance"`, `reportTab === 'daily'`, label "Daily Report".
- Render `<DailyReportTab v-if="!embedded && reportTab === 'daily'" />`.
- Import `DailyReportTab` alongside the existing `ClientReportsTab` / `ProjectFinanceTab` imports.

## Error handling

- Non-finance user calling the endpoint → `frappe.PermissionError` (frontend never shows the tab, but the API is defended independently).
- Future/invalid date → `frappe.throw` validation message.
- LLM both providers fail → `ai=None, ai_error` set; tab renders all metric tables + an "AI unavailable" banner (never a blank screen).
- Network/500 in the tab → inline error with a Retry button.

## Testing

Backend (`test_ai_report.py`, `FrappeTestCase`, run on local `mysite.local`):
- `get_daily_report_data` returns the documented keys for a date with data.
- Non-finance session → `PermissionError`.
- Future date → throws.
- Sunday date → `skipped_reason` set **and** metric keys still present.
- Monkeypatch `_call_llm` to raise → `ai is None`, `ai_error` set, metrics present.
- `_build_report` parity: email path and view path call the same helper (assert helper returns the tuple the email renderer expects).

Frontend: manual verification in the preview/build — tab appears only when `canViewFinance`, date change triggers fetch, cache + Regenerate behave, skip/error states render.

## Deploy

- Python change → **no migrate** (no schema). Frontend → `cd frontend && yarn build`.
- Deploy to **both** PMS sites' bench (office + enfono-office-new on EFTSP-009 `/home/v15`), per the next_pms runbook: `git reset --hard origin/main` (chown v15 first if root-owned build assets block it) → `cd apps/next_pms/frontend && yarn build` (frontend build — NOT `bench build`) → restart web **and** workers as root (`supervisorctl restart frappe-bench-web: frappe-bench-workers:`).
- Verify both sites ping 200 and the tab loads for a finance user.

## Cost note

Each non-cached view = one LLM call (DeepSeek, since Anthropic is out of credits). In-session cache + explicit Regenerate keep repeats minimal. If cost becomes a concern later, revisit the "store on send" option (a `PMS Daily Report` DocType) — deliberately deferred now.
