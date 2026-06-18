<template>
  <div class="dr">
    <!-- Header band -->
    <div class="dr-head">
      <div class="dr-head-l">
        <h2 class="dr-title">Daily Report</h2>
        <p class="dr-sub" v-if="data && !loading">
          {{ prettyDate(data.report_date) }}
          <span v-if="skippedReason" class="dr-chip warn">{{ skippedReason }}</span>
        </p>
        <p class="dr-sub" v-else>AI productivity summary</p>
      </div>
      <div class="dr-controls">
        <input type="date" v-model="selectedDate" :max="maxDate" class="dr-date" />
        <button class="dr-regen" :disabled="loading" @click="regenerate" title="Re-run AI analysis for this date">
          <span v-if="loading" class="dr-spin"></span>
          {{ loading ? 'Generating…' : 'Regenerate' }}
        </button>
      </div>
    </div>

    <div v-if="errorMsg" class="dr-error">{{ errorMsg }} <button class="dr-link" @click="load(true)">Retry</button></div>

    <div v-if="loading" class="dr-loading">
      <span class="dr-spin big"></span>
      <p>Generating AI analysis…</p>
      <span class="dr-loading-hint">crunching time logs, attendance and tasks — about 15 seconds</span>
    </div>

    <template v-else-if="data">
      <!-- KPI strip -->
      <div class="dr-kpis">
        <div class="dr-kpi"><span class="v">{{ num(overall.total_time_logged) }}<small>h</small></span><span class="l">Hours Logged</span></div>
        <div class="dr-kpi"><span class="v">{{ num(overall.active_users) }}</span><span class="l">Active Users</span></div>
        <div class="dr-kpi"><span class="v">{{ num(overall.tasks_completed_today) }}</span><span class="l">Tasks Done</span></div>
        <div class="dr-kpi"><span class="v">{{ num(overall.active_projects) }}</span><span class="l">Active Projects</span></div>
        <div class="dr-kpi"><span class="v">{{ num(overall.total_tasks_modified) }}</span><span class="l">Tasks Touched</span></div>
      </div>

      <!-- Executive summary lead -->
      <section v-if="data.ai && data.ai.executive_summary" class="dr-lead">
        <span class="dr-lead-label">Executive Summary</span>
        <p>{{ data.ai.executive_summary }}</p>
      </section>
      <div v-else-if="data.ai_error" class="dr-chip warn block">AI analysis unavailable ({{ data.ai_error }}). Metrics shown below.</div>

      <!-- People -->
      <section class="dr-card" v-if="data.user_metrics && data.user_metrics.length" style="--i:0">
        <h3 class="dr-h3">People <span class="dr-count">{{ data.user_metrics.length }}</span></h3>
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
                <td class="dr-name">{{ m.full_name }}</td>
                <td><span class="dr-badge" :class="ratingClass(m.full_name)">{{ ratingFor(m.full_name) }}</span></td>
                <td class="r">{{ num(m.hours_logged_today) }}</td>
                <td class="r dr-muted">{{ num(m.target_hours) }}</td>
                <td class="r"><span class="dr-util" :class="utilClass(m.utilization_pct)">{{ m.utilization_pct ?? '—' }}</span></td>
                <td class="r">{{ m.tasks_completed }}</td>
                <td class="r">{{ m.efficiency_pct ?? '—' }}</td>
                <td class="r">{{ num(m.login_hours) }}<span v-if="m.missed_checkout" class="dr-warn-ico" title="missed checkout"> ⚠</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="dr-assess-wrap" v-if="assessments.length">
          <div v-for="a in assessments" :key="a.name" class="dr-assess">
            <span class="dr-badge" :class="ratingClassRaw(a.rating)">{{ a.rating }}</span>
            <span><strong>{{ a.name }}</strong> — {{ a.summary }}</span>
          </div>
        </div>
      </section>

      <!-- Two-column insight grid -->
      <div class="dr-grid">
        <section class="dr-card" v-if="aiList('bottlenecks').length" style="--i:1">
          <h3 class="dr-h3">Bottlenecks</h3>
          <div v-for="(b, i) in aiList('bottlenecks')" :key="i" class="dr-line">
            <span class="dr-badge" :class="'sev-' + (b.severity || '').toLowerCase()">{{ b.severity }}</span>
            <span>{{ b.issue }}</span>
          </div>
        </section>

        <section class="dr-card" v-if="aiList('process_insights').length" style="--i:2">
          <h3 class="dr-h3">Process Insights</h3>
          <ul class="dr-list"><li v-for="(t, i) in aiList('process_insights')" :key="i">{{ t }}</li></ul>
        </section>

        <section class="dr-card" v-if="aiList('time_analysis').length" style="--i:3">
          <h3 class="dr-h3">Time Analysis</h3>
          <ul class="dr-list"><li v-for="(t, i) in aiList('time_analysis')" :key="i">{{ t }}</li></ul>
        </section>

        <section class="dr-card dr-recos" v-if="recommendations.length" style="--i:4">
          <h3 class="dr-h3">Recommendations</h3>
          <ol class="dr-reco-list">
            <li v-for="(rec, i) in recommendations" :key="i"><span class="dr-pri">{{ rec.priority || i + 1 }}</span>{{ rec.action }}</li>
          </ol>
        </section>
      </div>

      <!-- Projects -->
      <section class="dr-card" v-if="data.project_summary && data.project_summary.length" style="--i:5">
        <h3 class="dr-h3">Projects <span class="dr-count">{{ data.project_summary.length }}</span></h3>
        <div class="dr-table-wrap">
          <table class="dr-table">
            <thead>
              <tr><th>Project</th><th class="r">Hours</th><th class="r">Done</th><th class="r">Open</th><th class="r">Budget %</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in sortedProjects" :key="p.project">
                <td class="dr-name">{{ p.project }}</td>
                <td class="r">{{ num(p.hours_today) }}</td>
                <td class="r">{{ p.tasks_done_today }}</td>
                <td class="r dr-muted">{{ p.open_tasks }}</td>
                <td class="r"><span v-if="p.budget_pct != null" class="dr-util" :class="utilClass(p.budget_pct)">{{ p.budget_pct }}</span><span v-else class="dr-muted">—</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
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
function prettyDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short', year: 'numeric' })
}
function num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const maxDate = yesterdayISO()
const selectedDate = ref(yesterdayISO())
const data = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const cacheByDate = {}

const overall = computed(() => (data.value && data.value.overall) || {})
const skippedReason = computed(() => data.value && data.value.skipped_reason)
const recommendations = computed(() => {
  const a = data.value && data.value.ai
  return (a && Array.isArray(a.recommendations)) ? [...a.recommendations].sort((x, y) => (x.priority || 0) - (y.priority || 0)) : []
})
const assessments = computed(() => {
  const a = data.value && data.value.ai
  return (a && Array.isArray(a.user_assessments)) ? a.user_assessments : []
})
const sortedProjects = computed(() => {
  const rows = (data.value && data.value.project_summary) || []
  // most active first: hours desc, then done desc, then open desc
  return [...rows].sort((a, b) =>
    (b.hours_today || 0) - (a.hours_today || 0) ||
    (b.tasks_done_today || 0) - (a.tasks_done_today || 0) ||
    (b.open_tasks || 0) - (a.open_tasks || 0))
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
function ratingClassRaw(rating) { return 'rt-' + String(rating || '').toLowerCase().replace(/\s+/g, '-') }
function utilClass(pct) {
  const n = Number(pct)
  if (!Number.isFinite(n)) return ''
  if (n >= 90) return 'u-good'
  if (n >= 60) return 'u-mid'
  return 'u-low'
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
.dr { padding: 4px 0 32px; }

/* Header */
.dr-head { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid var(--border-color, #eaecf0); }
.dr-title { font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.01em; }
.dr-sub { margin: 4px 0 0; font-size: 13px; color: #667085; display: flex; align-items: center; gap: 8px; }
.dr-controls { display: flex; gap: 8px; align-items: center; }
.dr-date { padding: 7px 11px; border: 1px solid var(--border-color, #d0d5dd); border-radius: 8px; font-size: 13px; background: #fff; color: inherit; }
.dr-regen { display: inline-flex; align-items: center; gap: 7px; padding: 7px 14px; border: 1px solid var(--border-color, #d0d5dd); border-radius: 8px; background: #fff; cursor: pointer; font-size: 13px; font-weight: 500; transition: background .15s, border-color .15s; }
.dr-regen:hover:not(:disabled) { background: #f5f7fa; border-color: #b9c0cc; }
.dr-regen:disabled { opacity: .6; cursor: default; }

/* KPI strip */
.dr-kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 18px; }
.dr-kpi { background: #fff; border: 1px solid var(--border-color, #eaecf0); border-radius: 12px; padding: 16px 14px; position: relative; overflow: hidden; }
.dr-kpi::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: linear-gradient(180deg, #3b82f6, #6366f1); }
.dr-kpi .v { display: block; font-size: 26px; font-weight: 700; letter-spacing: -0.02em; line-height: 1; }
.dr-kpi .v small { font-size: 14px; font-weight: 600; color: #98a2b3; margin-left: 2px; }
.dr-kpi .l { display: block; font-size: 11.5px; color: #667085; margin-top: 7px; text-transform: uppercase; letter-spacing: .04em; }

/* Executive summary lead */
.dr-lead { background: linear-gradient(135deg, #f8fafc, #eef2ff); border: 1px solid #e0e7ff; border-radius: 12px; padding: 18px 20px; margin-bottom: 18px; }
.dr-lead-label { display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: #6366f1; margin-bottom: 6px; }
.dr-lead p { margin: 0; font-size: 15px; line-height: 1.6; color: #1d2939; }

/* Cards */
.dr-card { background: #fff; border: 1px solid var(--border-color, #eaecf0); border-radius: 12px; padding: 18px; margin-bottom: 16px; animation: drIn .4s ease both; animation-delay: calc(var(--i, 0) * 60ms); }
.dr-h3 { margin: 0 0 12px; font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; color: #1d2939; }
.dr-count { font-size: 11px; font-weight: 600; color: #667085; background: #f2f4f7; border-radius: 20px; padding: 1px 8px; }

/* Two-column grid for the four insight cards */
.dr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.dr-grid .dr-card { margin-bottom: 0; }
.dr-recos { grid-column: 1 / -1; }

/* Tables */
.dr-table-wrap { overflow-x: auto; }
.dr-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dr-table th { text-align: left; font-weight: 600; color: #667085; font-size: 11.5px; text-transform: uppercase; letter-spacing: .03em; padding: 6px 10px; border-bottom: 1px solid #eaecf0; }
.dr-table td { padding: 9px 10px; border-bottom: 1px solid #f2f4f7; }
.dr-table tbody tr:last-child td { border-bottom: none; }
.dr-table tbody tr:hover { background: #fafbfc; }
.dr-table th.r, .dr-table td.r { text-align: right; }
.dr-name { font-weight: 600; color: #1d2939; }
.dr-muted { color: #98a2b3; }

/* Lists */
.dr-list { margin: 0; padding-left: 18px; }
.dr-list li { padding: 3px 0; line-height: 1.5; font-size: 13.5px; }
.dr-line { display: flex; gap: 10px; align-items: baseline; padding: 7px 0; border-bottom: 1px solid #f7f8fa; font-size: 13.5px; line-height: 1.5; }
.dr-line:last-child { border-bottom: none; }

/* Recommendations */
.dr-reco-list { list-style: none; margin: 0; padding: 0; counter-reset: r; }
.dr-reco-list li { display: flex; gap: 12px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid #f7f8fa; font-size: 14px; line-height: 1.5; }
.dr-reco-list li:last-child { border-bottom: none; }
.dr-pri { flex: none; width: 22px; height: 22px; border-radius: 50%; background: #eef2ff; color: #4f46e5; font-size: 12px; font-weight: 700; display: grid; place-items: center; }

/* Assessments */
.dr-assess-wrap { margin-top: 14px; padding-top: 12px; border-top: 1px dashed #eaecf0; display: flex; flex-direction: column; gap: 9px; }
.dr-assess { display: flex; gap: 9px; align-items: baseline; font-size: 13px; line-height: 1.5; color: #475467; }

/* Badges */
.dr-badge { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.rt-good { background: #e6f4ea; color: #1a7f37; }
.rt-average { background: #eef2f6; color: #475467; }
.rt-needs-attention { background: #fff7e6; color: #b54708; }
.rt-critical { background: #fee4e2; color: #b42318; }
.sev-high { background: #fee4e2; color: #b42318; }
.sev-medium { background: #fff7e6; color: #b54708; }
.sev-low { background: #eef2f6; color: #475467; }

/* Utilization pill */
.dr-util { font-weight: 600; }
.u-good { color: #1a7f37; }
.u-mid { color: #b54708; }
.u-low { color: #b42318; }
.dr-warn-ico { color: #b54708; }

/* Chips / states */
.dr-chip { font-size: 11.5px; font-weight: 600; padding: 2px 9px; border-radius: 20px; }
.dr-chip.warn { background: #fff7e6; color: #b54708; }
.dr-chip.block { display: block; margin-bottom: 16px; padding: 10px 14px; border: 1px solid #ffe1b3; }
.dr-error { background: #fee4e2; border: 1px solid #fda29b; padding: 10px 14px; border-radius: 10px; margin-bottom: 16px; color: #912018; }
.dr-link { background: none; border: none; color: #b42318; font-weight: 600; cursor: pointer; text-decoration: underline; }

/* Loading */
.dr-loading { text-align: center; padding: 56px 0; color: #667085; }
.dr-loading p { margin: 14px 0 4px; font-size: 14px; font-weight: 500; color: #344054; }
.dr-loading-hint { font-size: 12.5px; color: #98a2b3; }
.dr-spin { width: 14px; height: 14px; border: 2px solid #d0d5dd; border-top-color: #4f46e5; border-radius: 50%; display: inline-block; animation: drSpin .7s linear infinite; }
.dr-spin.big { width: 30px; height: 30px; border-width: 3px; }

@keyframes drSpin { to { transform: rotate(360deg); } }
@keyframes drIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .dr-card { animation: none; } .dr-spin { animation-duration: 1.2s; } }

/* Responsive */
@media (max-width: 900px) {
  .dr-kpis { grid-template-columns: repeat(2, 1fr); }
  .dr-grid { grid-template-columns: 1fr; }
}
</style>
