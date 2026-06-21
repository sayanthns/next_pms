# Daily Report Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the daily AI productivity report (today email-only) as a live, native, finance-gated, date-browsable tab in the PMS Reports section.

**Architecture:** Refactor `ai_report.py` to share a build helper between the email job and a new read-only whitelisted endpoint `get_daily_report_data`. A new `DailyReportTab.vue` (mirroring `ProjectFinanceTab.vue`) calls it on date-select, caches per-date in-session, and renders the structured AI output + metric tables natively. Tab gated by `canViewFinance`; endpoint gated server-side by the same roles.

**Tech Stack:** Frappe v15 (Python), Vue 3 + Vite SPA, `@/utils/frappe` `call()`, Pinia `settingsStore`.

Spec: `docs/superpowers/specs/2026-06-18-daily-report-tab-design.md`

---

## File Structure

- `next_pms/api/ai_report.py` — modify: refactor skip-check + extract `_build_report`; add `_require_finance_viewer` + `get_daily_report_data`.
- `next_pms/api/test_ai_report.py` — create: backend tests (`FrappeTestCase`).
- `frontend/src/components/DailyReportTab.vue` — create: the tab UI.
- `frontend/src/views/ReportsView.vue` — modify: tab button + import + render.

Backend tests run on local dev site `mysite.local` as Administrator:
`bench --site mysite.local run-tests --module next_pms.api.test_ai_report`

---

## Task 1: Refactor skip-check to take an explicit date

**Files:**
- Modify: `next_pms/api/ai_report.py` (replace `_should_skip_report`, lines ~75-103)
- Test: `next_pms/api/test_ai_report.py`

- [ ] **Step 1: Write the failing test**

Create `next_pms/api/test_ai_report.py`:

```python
# next_pms/api/test_ai_report.py
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from next_pms.api import ai_report as R


class TestDailyReportSkip(FrappeTestCase):
    def test_sunday_returns_reason(self):
        # 2026-06-14 is a Sunday
        reason = R._should_skip_report_for("2026-06-14")
        self.assertTrue(reason)
        self.assertIn("Sunday", reason)

    def test_weekday_returns_none(self):
        # 2026-06-16 is a Tuesday; assumes no Holiday row for that date in dev DB
        self.assertIsNone(R._should_skip_report_for("2026-06-16"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_ai_report`
Expected: FAIL — `AttributeError: module 'next_pms.api.ai_report' has no attribute '_should_skip_report_for'`

- [ ] **Step 3: Implement the refactor**

In `next_pms/api/ai_report.py`, replace the whole `_should_skip_report` function (currently ~lines 75-103) with:

```python
def _should_skip_report_for(report_date):
    """Return a skip reason (str) if report_date is a Sunday or a holiday, else None."""
    dt = getdate(report_date)
    if dt.weekday() == 6:  # Sunday
        return f"{report_date} was Sunday (weekly off)."
    try:
        if frappe.db.exists("Holiday", {"holiday_date": str(report_date)}):
            return f"{report_date} is a holiday."
    except Exception:
        pass
    return None


def _should_skip_report():
    """Email-path skip check for yesterday (back-compat wrapper)."""
    return _should_skip_report_for(add_days(today(), -1))
```

(`getdate`, `today`, `add_days` are already imported at the top of the file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_ai_report`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add next_pms/api/ai_report.py next_pms/api/test_ai_report.py
git commit -m "refactor(ai-report): _should_skip_report_for(date) + back-compat wrapper"
```

---

## Task 2: Extract `_build_report` shared helper

**Files:**
- Modify: `next_pms/api/ai_report.py` (`generate_daily_report` body, lines ~37-72; add `_build_report`)
- Test: `next_pms/api/test_ai_report.py`

- [ ] **Step 1: Write the failing test**

Append to `next_pms/api/test_ai_report.py`:

```python
class TestBuildReport(FrappeTestCase):
    def _settings(self):
        return {"ai_provider": "Claude", "ai_api_key": "x",
                "ai_model": "m", "report_detail_level": "Detailed",
                "fallback_provider": "", "fallback_api_key": None, "fallback_model": "deepseek-chat"}

    def test_ai_failure_returns_metrics_and_error(self):
        with patch.object(R, "_call_llm", side_effect=Exception("boom")):
            out = R._build_report("2026-06-16", self._settings())
        self.assertIsNone(out["ai_parsed"])
        self.assertEqual(out["ai_error"], "boom")
        # metric keys always present even when AI fails
        for k in ("full_data", "user_metrics", "process_mining", "time_patterns", "project_summary"):
            self.assertIn(k, out)

    def test_ai_success_parses(self):
        fake = '{"executive_summary":"ok","recommendations":[]}'
        with patch.object(R, "_call_llm", return_value=fake):
            out = R._build_report("2026-06-16", self._settings())
        self.assertIsNone(out["ai_error"])
        self.assertEqual(out["ai_parsed"]["executive_summary"], "ok")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_ai_report`
Expected: FAIL — `AttributeError: ... has no attribute '_build_report'`

- [ ] **Step 3: Implement `_build_report` and refactor `generate_daily_report`**

In `next_pms/api/ai_report.py`, add after `_get_recipients` (before `get_daily_work_summary`):

```python
def _build_report(report_date, settings, detail_level=None):
    """Gather all metrics for report_date and run the LLM analysis.
    No email, no permission check. Reused by the email job and the view endpoint.
    On LLM failure: ai_parsed=None, ai_error set, metrics still returned."""
    report_date = str(report_date)
    detail_level = detail_level or settings.get("report_detail_level", "Detailed")

    work_data = get_daily_work_summary(report_date)
    user_metrics = _build_user_metrics(report_date)
    process_mining = _get_process_mining_data(report_date)
    time_patterns = _get_time_patterns(report_date)
    project_summary = _get_project_summary(report_date)

    full_data = {
        "date": report_date,
        "overall": work_data.get("overall", {}),
        "user_metrics": user_metrics,
        "process_mining": process_mining,
        "time_patterns": time_patterns,
        "project_summary": project_summary,
    }

    ai_parsed = None
    ai_raw = ""
    ai_error = None
    try:
        ai_raw = _call_llm(settings, full_data, detail_level)
        ai_parsed = _parse_ai_response(ai_raw)
    except Exception as e:
        frappe.log_error(f"PMS AI Report: LLM call failed - {str(e)}")
        ai_error = str(e)
        ai_raw = f"AI analysis unavailable: {str(e)}"

    return {
        "full_data": full_data,
        "ai_parsed": ai_parsed,
        "ai_raw": ai_raw,
        "ai_error": ai_error,
        "user_metrics": user_metrics,
        "process_mining": process_mining,
        "time_patterns": time_patterns,
        "project_summary": project_summary,
    }
```

Then in `generate_daily_report`, replace the block from `report_date = str(add_days(today(), -1))` through the `_send_report_email(...)` call (lines ~39-70) with:

```python
    report_date = str(add_days(today(), -1))
    detail_level = settings.get("report_detail_level", "Detailed")
    r = _build_report(report_date, settings, detail_level)

    _send_report_email(
        recipients, r["full_data"], r["ai_parsed"], r["ai_raw"],
        r["user_metrics"], r["process_mining"], r["time_patterns"], r["project_summary"],
    )
```

(The `return {"success": True, ...}` line below stays unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_ai_report`
Expected: PASS (4 tests total)

- [ ] **Step 5: Commit**

```bash
git add next_pms/api/ai_report.py next_pms/api/test_ai_report.py
git commit -m "refactor(ai-report): extract _build_report shared by email + view paths"
```

---

## Task 3: Add `get_daily_report_data` endpoint + permission gate

**Files:**
- Modify: `next_pms/api/ai_report.py` (add `_require_finance_viewer`, `get_daily_report_data`)
- Test: `next_pms/api/test_ai_report.py`

- [ ] **Step 1: Write the failing test**

Append to `next_pms/api/test_ai_report.py`:

```python
class TestGetDailyReportData(FrappeTestCase):
    def test_denies_non_finance(self):
        with patch.object(frappe, "get_roles", return_value=["PMS Developer"]):
            with self.assertRaises(frappe.PermissionError):
                R.get_daily_report_data("2026-06-16")

    def test_future_date_throws(self):
        # run-tests session is Administrator -> permission passes
        from frappe.utils import add_days, today
        future = add_days(today(), 1)
        with self.assertRaises(frappe.exceptions.ValidationError):
            R.get_daily_report_data(future)

    def test_returns_shape(self):
        fake = '{"executive_summary":"ok","recommendations":[]}'
        with patch.object(R, "_call_llm", return_value=fake):
            out = R.get_daily_report_data("2026-06-16")
        for k in ("report_date", "skipped_reason", "overall", "ai", "ai_raw",
                  "ai_error", "user_metrics", "process_mining", "time_patterns", "project_summary"):
            self.assertIn(k, out)
        self.assertEqual(out["report_date"], "2026-06-16")

    def test_sunday_still_returns_data_with_notice(self):
        fake = '{"executive_summary":"ok","recommendations":[]}'
        with patch.object(R, "_call_llm", return_value=fake):
            out = R.get_daily_report_data("2026-06-14")  # Sunday
        self.assertTrue(out["skipped_reason"])
        self.assertIn("user_metrics", out)  # data present despite skip notice
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_ai_report`
Expected: FAIL — `AttributeError: ... has no attribute 'get_daily_report_data'`

- [ ] **Step 3: Implement the gate + endpoint**

In `next_pms/api/ai_report.py`, add (place near the top after imports, and the endpoint after `generate_daily_report`). Ensure `from frappe import _` style is available — the file uses `frappe.throw`; import the translator: at top add `from frappe import _` if not present.

```python
def _require_finance_viewer():
    """Mirror settings.can_view_finance (is_admin or is_manager). API defends itself
    independently of the frontend tab gating."""
    roles = set(frappe.get_roles(frappe.session.user))
    if not ({"System Manager", "Administrator", "PMS Manager"} & roles):
        frappe.throw(_("You are not permitted to view the daily report."), frappe.PermissionError)


@frappe.whitelist()
def get_daily_report_data(report_date=None):
    """Read-only, on-demand daily report for the Reports tab. Never emails; ignores
    daily_report_enabled. Returns metrics + structured AI analysis for report_date."""
    _require_finance_viewer()

    rd = getdate(report_date) if report_date else add_days(getdate(today()), -1)
    if rd >= getdate(today()):
        frappe.throw(_("Report date must be in the past."))

    settings = _get_ai_settings()
    if not settings:
        frappe.throw(_("AI settings are not configured."))

    skipped = _should_skip_report_for(rd)
    r = _build_report(str(rd), settings)

    return {
        "report_date": str(rd),
        "skipped_reason": skipped,
        "overall": r["full_data"].get("overall", {}),
        "ai": r["ai_parsed"],
        "ai_raw": r["ai_raw"],
        "ai_error": r["ai_error"],
        "user_metrics": r["user_metrics"],
        "process_mining": r["process_mining"],
        "time_patterns": r["time_patterns"],
        "project_summary": r["project_summary"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site mysite.local run-tests --module next_pms.api.test_ai_report`
Expected: PASS (8 tests total)

- [ ] **Step 5: Run semgrep + commit**

```bash
bash ~/.claude/skills/frappe-erpnext-expert/scripts/semgrep_check.sh next_pms || true
git add next_pms/api/ai_report.py next_pms/api/test_ai_report.py
git commit -m "feat(ai-report): get_daily_report_data read-only endpoint (finance-gated)"
```

---

## Task 4: Create `DailyReportTab.vue`

**Files:**
- Create: `frontend/src/components/DailyReportTab.vue`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/DailyReportTab.vue` with the full content:

```vue
<template>
  <div class="dr">
    <div class="dr-head">
      <h2 class="dr-title">Daily Report</h2>
      <div class="dr-controls">
        <input type="date" v-model="selectedDate" :max="maxDate" class="dr-date" />
        <button class="dr-regen" :disabled="loading" @click="regenerate">Regenerate</button>
      </div>
    </div>

    <div v-if="skippedReason" class="dr-notice">{{ skippedReason }} — showing data anyway.</div>
    <div v-if="errorMsg" class="dr-error">{{ errorMsg }} <button class="dr-retry" @click="load(true)">Retry</button></div>
    <div v-if="loading" class="dr-loading">Generating AI analysis… (~15s)</div>

    <template v-else-if="data">
      <!-- Executive summary -->
      <div v-if="data.ai && data.ai.executive_summary" class="dr-card dr-exec">
        <h3>Executive Summary</h3>
        <p>{{ data.ai.executive_summary }}</p>
      </div>
      <div v-else-if="data.ai_error" class="dr-notice">AI analysis unavailable ({{ data.ai_error }}). Metrics shown below.</div>

      <!-- Overall stats -->
      <div class="dr-cards" v-if="overall">
        <div class="dr-stat"><span class="v">{{ overall.total_hours ?? '—' }}</span><span class="l">Hours Logged</span></div>
        <div class="dr-stat"><span class="v">{{ overall.active_users ?? '—' }}</span><span class="l">Active Users</span></div>
        <div class="dr-stat"><span class="v">{{ overall.tasks_completed ?? '—' }}</span><span class="l">Tasks Done</span></div>
      </div>

      <!-- Per-user assessments + metrics -->
      <div class="dr-card" v-if="data.user_metrics && data.user_metrics.length">
        <h3>People</h3>
        <div class="dr-table-wrap">
          <table class="dr-table">
            <thead>
              <tr>
                <th>Name</th><th>Rating</th><th class="r">Logged</th><th class="r">Target</th>
                <th class="r">Util %</th><th class="r">Done</th><th class="r">Eff %</th><th class="r">Login Hrs</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in data.user_metrics" :key="m.user">
                <td>{{ m.full_name }}</td>
                <td><span class="dr-badge" :class="ratingClass(m.full_name)">{{ ratingFor(m.full_name) }}</span></td>
                <td class="r">{{ m.hours_logged_today }}</td>
                <td class="r">{{ m.target_hours }}</td>
                <td class="r">{{ m.utilization_pct ?? '—' }}</td>
                <td class="r">{{ m.tasks_completed }}</td>
                <td class="r">{{ m.efficiency_pct ?? '—' }}</td>
                <td class="r">{{ m.login_hours }}<span v-if="m.missed_checkout" title="missed checkout"> ⚠</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-for="a in assessments" :key="a.name" class="dr-assess">
          <span class="dr-badge" :class="ratingClassRaw(a.rating)">{{ a.rating }}</span>
          <strong>{{ a.name }}</strong> — {{ a.summary }}
        </div>
      </div>

      <!-- Bottlenecks -->
      <div class="dr-card" v-if="aiList('bottlenecks').length">
        <h3>Bottlenecks</h3>
        <div v-for="(b, i) in aiList('bottlenecks')" :key="i" class="dr-line">
          <span class="dr-badge" :class="'sev-' + (b.severity || '').toLowerCase()">{{ b.severity }}</span> {{ b.issue }}
        </div>
      </div>

      <!-- Process insights -->
      <div class="dr-card" v-if="aiList('process_insights').length">
        <h3>Process Insights</h3>
        <ul><li v-for="(t, i) in aiList('process_insights')" :key="i">{{ t }}</li></ul>
      </div>

      <!-- Time analysis -->
      <div class="dr-card" v-if="aiList('time_analysis').length">
        <h3>Time Analysis</h3>
        <ul><li v-for="(t, i) in aiList('time_analysis')" :key="i">{{ t }}</li></ul>
      </div>

      <!-- Recommendations -->
      <div class="dr-card" v-if="recommendations.length">
        <h3>Recommendations</h3>
        <ol><li v-for="(rec, i) in recommendations" :key="i">{{ rec.action }}</li></ol>
      </div>

      <!-- Project summary -->
      <div class="dr-card" v-if="data.project_summary && data.project_summary.length">
        <h3>Projects</h3>
        <div class="dr-table-wrap">
          <table class="dr-table">
            <thead><tr><th>Project</th><th class="r">Hours</th><th class="r">Tasks</th></tr></thead>
            <tbody>
              <tr v-for="p in data.project_summary" :key="p.project || p.name">
                <td>{{ p.project_name || p.project || p.name }}</td>
                <td class="r">{{ p.hours ?? p.total_hours ?? '—' }}</td>
                <td class="r">{{ p.tasks ?? p.task_count ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { call } from '@/utils/frappe'

function yesterdayISO() {
  const d = new Date(); d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

const maxDate = yesterdayISO()
const selectedDate = ref(yesterdayISO())
const data = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const cacheByDate = {}   // in-session cache: { 'YYYY-MM-DD': payload }

const overall = computed(() => data.value && data.value.overall)
const skippedReason = computed(() => data.value && data.value.skipped_reason)
const recommendations = computed(() => {
  const a = data.value && data.value.ai
  return (a && Array.isArray(a.recommendations)) ? [...a.recommendations].sort((x, y) => (x.priority || 0) - (y.priority || 0)) : []
})
const assessments = computed(() => {
  const a = data.value && data.value.ai
  return (a && Array.isArray(a.user_assessments)) ? a.user_assessments : []
})
function aiList(key) {
  const a = data.value && data.value.ai
  return (a && Array.isArray(a[key])) ? a[key] : []
}
function ratingFor(name) {
  const hit = assessments.value.find(x => x.name === name)
  return hit ? hit.rating : '—'
}
function ratingClass(name) { return ratingClassRaw(ratingFor(name)) }
function ratingClassRaw(rating) {
  return 'rt-' + String(rating || '').toLowerCase().replace(/\s+/g, '-')
}

async function load(force = false) {
  const date = selectedDate.value
  if (!date) return
  if (!force && cacheByDate[date]) { data.value = cacheByDate[date]; errorMsg.value = ''; return }
  loading.value = true; errorMsg.value = ''
  try {
    const res = await call('next_pms.api.ai_report.get_daily_report_data', { report_date: date })
    cacheByDate[date] = res
    data.value = res
  } catch (e) {
    data.value = null
    errorMsg.value = (e && e.message) || 'Failed to load the daily report.'
  } finally {
    loading.value = false
  }
}
function regenerate() { load(true) }

watch(selectedDate, () => load(false))
onMounted(() => load(false))
</script>

<style scoped>
.dr { padding: 4px 0; }
.dr-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.dr-title { font-size: 18px; font-weight: 600; margin: 0; }
.dr-controls { display: flex; gap: 8px; align-items: center; }
.dr-date { padding: 6px 10px; border: 1px solid var(--border-color, #d0d5dd); border-radius: 6px; }
.dr-regen, .dr-retry { padding: 6px 12px; border: 1px solid var(--border-color, #d0d5dd); border-radius: 6px; background: #fff; cursor: pointer; }
.dr-regen:disabled { opacity: .5; cursor: default; }
.dr-notice { background: #fff7e6; border: 1px solid #ffd591; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }
.dr-error { background: #fff1f0; border: 1px solid #ffa39e; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }
.dr-loading { padding: 40px 0; text-align: center; color: #667085; }
.dr-card { background: #fff; border: 1px solid var(--border-color, #eaecf0); border-radius: 8px; padding: 16px; margin-bottom: 14px; }
.dr-card h3 { margin: 0 0 10px; font-size: 15px; font-weight: 600; }
.dr-exec p { margin: 0; line-height: 1.55; }
.dr-cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.dr-stat { flex: 1; min-width: 120px; background: #fff; border: 1px solid #eaecf0; border-radius: 8px; padding: 14px; text-align: center; }
.dr-stat .v { display: block; font-size: 22px; font-weight: 700; }
.dr-stat .l { display: block; font-size: 12px; color: #667085; margin-top: 4px; }
.dr-table-wrap { overflow-x: auto; }
.dr-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dr-table th, .dr-table td { padding: 8px 10px; border-bottom: 1px solid #f0f1f3; text-align: left; }
.dr-table th.r, .dr-table td.r { text-align: right; }
.dr-line { padding: 6px 0; }
.dr-assess { padding: 6px 0; border-top: 1px solid #f5f5f5; }
.dr-badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-right: 6px; }
.rt-good { background: #e6f4ea; color: #1a7f37; }
.rt-average { background: #eef2f6; color: #475467; }
.rt-needs-attention { background: #fff7e6; color: #b54708; }
.rt-critical { background: #fff1f0; color: #b42318; }
.sev-high { background: #fff1f0; color: #b42318; }
.sev-medium { background: #fff7e6; color: #b54708; }
.sev-low { background: #eef2f6; color: #475467; }
</style>
```

- [ ] **Step 2: Build to verify it compiles**

Run: `cd frontend && yarn build`
Expected: build succeeds, no Vue/Rollup errors referencing `DailyReportTab.vue`. (Component isn't wired yet — Task 5 wires it. This step only checks it parses.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DailyReportTab.vue
git commit -m "feat(reports): DailyReportTab.vue — native daily report view"
```

---

## Task 5: Wire the tab into `ReportsView.vue`

**Files:**
- Modify: `frontend/src/views/ReportsView.vue` (tab bar ~lines 28-44; imports ~line 465)

- [ ] **Step 1: Add the import**

In the `<script setup>` block, next to the existing component imports (after `import ProjectFinanceTab from '@/components/ProjectFinanceTab.vue'`, ~line 465), add:

```js
import DailyReportTab from '@/components/DailyReportTab.vue'
```

- [ ] **Step 2: Add the tab button**

In the tab bar, immediately after the Finance tab button block (the `<button ... reportTab === 'finance' ...>Finance</button>`, ~lines 29-37), add:

```html
      <button
        v-if="settingsStore.canViewFinance"
        class="reports-tab-btn"
        :class="{ active: reportTab === 'daily' }"
        @click="reportTab = 'daily'"
      >
        Daily Report
      </button>
```

- [ ] **Step 3: Add the tab render**

Immediately after the Finance render line (`<ProjectFinanceTab v-if="!embedded && reportTab === 'finance'" />`, ~line 43), add:

```html
    <!-- Daily Report Tab -->
    <DailyReportTab v-if="!embedded && reportTab === 'daily'" />
```

- [ ] **Step 4: Build to verify**

Run: `cd frontend && yarn build`
Expected: build succeeds, no errors.

- [ ] **Step 5: Manual verification (local dev)**

Run `bench --site mysite.local serve` (or the project's dev command) and confirm, as an admin/manager user:
- "Daily Report" tab appears in Reports (and is absent for a PMS Developer/Customer user).
- Selecting a date triggers a load; a weekday shows summary + tables; a Sunday shows the notice + data.
- Regenerate re-calls; switching back to a visited date is instant (cache).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/ReportsView.vue
git commit -m "feat(reports): wire Daily Report tab (finance-gated) into ReportsView"
```

---

## Task 6: Deploy to office (after user go-ahead)

**Files:** none (deploy only). Production op — confirm with the user before running; prefer the maintenance window or an authorized out-of-window override.

- [ ] **Step 1: Push**

```bash
git push origin main
```

- [ ] **Step 2: Deploy on EFTSP-009 (office bench, both PMS sites share it)**

Via control → Tailscale (per the next_pms runbook). On the bench as needed:

```bash
# as v15: pull
cd /home/v15/frappe-bench/apps/next_pms && git fetch && git reset --hard origin/main
# build frontend (NOT bench build)
cd /home/v15/frappe-bench/apps/next_pms/frontend && yarn build
# Python-only backend change -> NO migrate needed
# restart web AND workers (rule #6) as root:
supervisorctl restart frappe-bench-web: frappe-bench-workers:
```

(If `git reset` fails on root-owned build assets: `chown -R v15:v15 apps/next_pms` first.)

- [ ] **Step 3: Verify**

- `curl -s https://office.enfono.com/api/method/ping` → 200 and `https://office.enfonoerp.com/...` → 200.
- Log in as a finance/manager user on each site → Reports → Daily Report → pick yesterday → report renders.
- Update `~/.claude/skills/enfono-servers/LIVE_STATE.md` RECENT INCIDENTS with the deploy.

---

## Self-Review

**Spec coverage:**
- Live-generate on view → Task 3 endpoint calls `_build_report` each request (no storage). ✓
- Native Vue layout → Task 4 renders structured sections, no email HTML. ✓
- Finance-gated (frontend + backend) → Task 3 `_require_finance_viewer`; Task 5 `v-if="canViewFinance"`. ✓
- Date picker / history → Task 4 date input (default + max yesterday), per-date load. ✓
- Read-only, ignores `daily_report_enabled`, Sunday shows data + notice → Task 3 endpoint + `_should_skip_report_for`. ✓
- AI-failure shows metrics → Task 2 `_build_report` try/except; Task 4 `ai_error` branch. ✓
- In-session cache + Regenerate → Task 4 `cacheByDate` + `regenerate()`. ✓
- Tests (shape, perm, future, Sunday, AI-failure) → Tasks 1-3. ✓
- Deploy both sites, no migrate, frontend yarn build → Task 6. ✓

**Placeholder scan:** none — all steps carry full code/commands.

**Type consistency:** `_build_report` returns dict with `full_data/ai_parsed/ai_raw/ai_error/user_metrics/process_mining/time_patterns/project_summary`; `get_daily_report_data` reads exactly those keys and renames `ai_parsed`→`ai`, `full_data.overall`→`overall`. `DailyReportTab` reads endpoint keys `report_date/skipped_reason/overall/ai/ai_raw/ai_error/user_metrics/project_summary` and AI sub-keys `executive_summary/user_assessments/process_insights/time_analysis/bottlenecks/recommendations` (match `_build_analysis_prompt`). `user_metrics` row keys match `_build_user_metrics` (`full_name/hours_logged_today/target_hours/utilization_pct/tasks_completed/efficiency_pct/login_hours/missed_checkout`). Consistent.

**Note / verify during implementation:** `overall` keys (`total_hours/active_users/tasks_completed`) and `project_summary` row keys (`project_name/hours/tasks`) are rendered defensively with `??` fallbacks — confirm against `get_daily_work_summary` / `_get_project_summary` return shapes when implementing Task 4 and adjust labels if the real keys differ.
