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
