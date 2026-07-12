<template>
  <div class="perf-tab">
    <!-- Controls -->
    <div class="perf-controls">
      <div class="control-group">
        <label class="ctrl-label">View</label>
        <div class="period-btns">
          <button class="period-btn" :class="{ active: view === 'individual' }" @click="view = 'individual'; reload()">Individual</button>
          <button class="period-btn" :class="{ active: view === 'leaderboard' }" @click="view = 'leaderboard'; reload()">🏆 Leaderboard</button>
        </div>
      </div>
      <div class="control-group" v-if="view === 'individual'">
        <label class="ctrl-label">Employee</label>
        <select v-model="selectedUser" class="ctrl-select" @change="load">
          <option value="">Select employee...</option>
          <option v-for="u in users" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
        </select>
      </div>
      <div class="control-group">
        <label class="ctrl-label">Period</label>
        <div class="period-btns">
          <button
            v-for="p in periods"
            :key="p.value"
            class="period-btn"
            :class="{ active: !customRange && period === p.value }"
            @click="clearRange(); period = p.value; reload()"
          >{{ p.label }}</button>
        </div>
      </div>
      <div class="control-group">
        <label class="ctrl-label">Custom Range</label>
        <div class="range-inputs">
          <input type="date" v-model="fromDate" class="ctrl-date" @change="onRangeChange" />
          <span class="range-sep">→</span>
          <input type="date" v-model="toDate" class="ctrl-date" @change="onRangeChange" />
          <button v-if="customRange" class="range-clear" title="Clear custom range" @click="clearRange(); reload()">✕</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="perf-loading">
      <div class="spinner"></div>
      <span>{{ view === 'leaderboard' ? 'Scoring the whole team...' : 'Computing performance score...' }}</span>
    </div>

    <!-- ══════════════ Leaderboard view ══════════════ -->
    <template v-else-if="view === 'leaderboard' && board">
      <div class="dim-card">
        <h3 class="dim-title">Team Leaderboard — {{ board.from_date }} → {{ board.to_date }}</h3>
        <div v-if="topPerformer" class="award-banner">
          🏆 <strong>Top performer: {{ topPerformer.full_name }}</strong> — {{ topPerformer.composite_score.toFixed(1) }} (Band {{ topPerformer.band }})
        </div>
        <table class="dim-table board-table">
          <thead>
            <tr>
              <th>Rank</th><th>Member</th><th>Score</th><th></th><th>Band</th>
              <th>Hours (logged vs target)</th><th>Tasks Done</th><th>Weakest Dimension</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in board.rows" :key="r.user" :class="{ 'row-top': r.rank === 1, 'row-unranked': !r.rank }"
                class="board-row" @click="openMember(r)">
              <td class="rank-cell">{{ medal(r.rank) }}{{ r.rank ? '#' + r.rank : '—' }}</td>
              <td class="dim-name">{{ r.full_name }}</td>
              <td class="dim-score">{{ r.rank ? r.composite_score.toFixed(1) : 'no data' }}</td>
              <td class="dim-bar-cell">
                <div class="dim-bar-track">
                  <div class="dim-bar-fill" :style="{ width: (r.composite_score || 0) + '%', background: barColor(r.composite_score) }"></div>
                </div>
              </td>
              <td><span v-if="r.rank" class="band-chip" :style="{ color: barColor(r.composite_score) }">{{ r.band }}</span><span v-else>—</span></td>
              <td>{{ r.total_logged_hours.toFixed(1) }}h logged · {{ r.target_hours.toFixed(1) }}h target</td>
              <td>{{ r.completed_count }}</td>
              <td class="dim-raw">{{ weakest(r) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="board-note">Ranked by composite score; members with no scorable data appear unranked. Click a row for the full breakdown. Logged hours can exceed target (overtime / weekend work) — Utilization still caps at 100%. On the 1st of each month every member is emailed their own score &amp; rank; management receives this leaderboard.</p>
      </div>
    </template>

    <div v-else-if="view === 'individual' && !selectedUser" class="perf-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M12 20V10M18 20V4M6 20v-4"/></svg>
      <p>Select an employee to view their performance score</p>
    </div>

    <template v-else-if="view === 'individual' && data">
      <!-- Score hero -->
      <div class="score-hero">
        <div class="score-ring" :class="'band-' + data.band.toLowerCase()">
          <span class="score-num">{{ data.composite_score }}</span>
          <span class="score-band">Band {{ data.band }}</span>
        </div>
        <div class="score-meta">
          <div class="score-name">{{ data.user_full_name }}</div>
          <div class="score-period">{{ data.from_date }} → {{ data.to_date }}</div>
          <div class="score-pills">
            <span class="pill">{{ data.working_days_count }} working days</span>
            <span class="pill">{{ data.total_logged_hours }}h logged / {{ data.target_hours }}h target</span>
            <span class="pill">{{ data.completed_count }} tasks completed</span>
            <span class="pill" v-if="data.included_weight < 100">scored on {{ data.included_weight }}/100 weight (missing data renormalised)</span>
          </div>
        </div>
      </div>

      <!-- Dimension breakdown -->
      <div class="dim-card">
        <h3 class="dim-title">Dimension Breakdown</h3>
        <p class="dim-note">
          <strong>Basis</strong> shows the exact inputs behind each score.
          <strong>Delivery</strong> = value of completed work (sum of done-task estimates) ÷ your hours target — <em>not</em> estimate-vs-actual.
          <strong>Efficiency</strong> = estimate ÷ actual hours logged. Different questions, so their numbers won't match.
        </p>
        <table class="dim-table">
          <thead>
            <tr>
              <th>Dimension</th><th>Weight</th><th>Score</th><th></th><th>Contribution</th><th>Basis</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in data.dimensions" :key="d.key" :class="{ excluded: !d.included }">
              <td class="dim-name">{{ labels[d.key] }}</td>
              <td>{{ d.weight }}%</td>
              <td class="dim-score">{{ d.included ? d.score : '—' }}</td>
              <td class="dim-bar-cell">
                <div class="dim-bar-track">
                  <div class="dim-bar-fill" :style="{ width: (d.score || 0) + '%', background: barColor(d.score) }"></div>
                </div>
              </td>
              <td>{{ d.included ? '+' + d.weighted : '—' }}</td>
              <td class="dim-raw">{{ d.raw }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ══════════════ Score History (frozen monthly snapshots) ══════════════ -->
      <div class="dim-card">
        <h3 class="dim-title">Score History</h3>
        <div v-if="!history.length" class="hist-empty">No frozen snapshots yet — created on the 1st of each month.</div>
        <table v-else class="dim-table">
          <thead>
            <tr>
              <th>Month</th><th>Final Score</th><th></th><th>Band</th><th>Rank</th><th>Adjustment</th><th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="h in history" :key="h.name">
              <tr>
                <td class="dim-name">{{ h.month_label || h.month_key }}</td>
                <td class="dim-score">{{ fmt1(h.final_score) }}</td>
                <td class="dim-bar-cell">
                  <div class="dim-bar-track">
                    <div class="dim-bar-fill" :style="{ width: (h.final_score || 0) + '%', background: barColor(h.final_score) }"></div>
                  </div>
                </td>
                <td><span class="band-chip" :style="{ color: barColor(h.final_score) }">{{ h.final_band }}</span></td>
                <td>#{{ h.rank }} of {{ h.total_ranked }}</td>
                <td>
                  <span v-if="Number(h.adjustment)" class="adj-badge" :title="adjTitle(h)">adj {{ Number(h.adjustment) > 0 ? '+' : '' }}{{ fmt1(h.adjustment) }}</span>
                  <span v-else>—</span>
                </td>
                <td><button class="adjust-btn" @click="toggleAdjust(h)">Adjust</button></td>
              </tr>
              <tr v-if="adjusting === h.name">
                <td colspan="7">
                  <div class="adjust-editor">
                    <label class="ctrl-label">Adjustment</label>
                    <input type="number" v-model.number="adjValue" min="-10" max="10" step="0.5" class="adj-input" />
                    <label class="ctrl-label">Reason</label>
                    <input type="text" v-model="adjReason" class="adj-reason" placeholder="Required for non-zero adjustment" />
                    <button class="period-btn active" :disabled="adjSaving" @click="saveAdjust(h)">Save</button>
                    <button class="period-btn" @click="adjusting = null">Cancel</button>
                    <span v-if="adjError" class="adj-error">{{ adjError }}</span>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <p class="board-note">Frozen on the 1st of each month before the performance emails go out; the adjustment (±10, reasoned) is the only change allowed afterwards and is fully audited.</p>
      </div>

      <!-- ══════════════ Methodology documentation ══════════════ -->
      <div class="doc-card">
        <h3 class="doc-title">📖 Methodology — how this score is calculated</h3>

        <p class="doc-p">
          The Performance Score is a weighted composite of 8 independent dimensions, each scored 0–100.
          <strong>Composite = Σ (weight × dimension score) ÷ Σ included weights.</strong>
          A dimension with no underlying data in the period (e.g. no completed tasks → no Timeliness data)
          is <em>excluded</em> and the remaining weights are renormalised — nobody scores zero for missing data.
          Bands: <strong>A ≥ 85 · B ≥ 70 · C ≥ 50 · D &lt; 50</strong>.
        </p>

        <table class="doc-table">
          <thead><tr><th>Dimension</th><th>Weight</th><th>Formula</th><th>What it measures</th></tr></thead>
          <tbody>
            <tr><td>Delivery</td><td>25%</td><td>Σ estimated hours of tasks completed ÷ target hours (cap 100%)</td><td>Real output volume. Uses PM-approved estimates, not raw task count — 28 tiny tasks ≠ 3 large ones.</td></tr>
            <tr><td>Timeliness</td><td>15%</td><td>on-time completions ÷ completions with a due date</td><td>Deadline reliability.</td></tr>
            <tr><td>Utilization</td><td>15%</td><td>logged timer hours ÷ target hours (cap 100%)</td><td>Timer discipline / engagement vs the leave-adjusted bar.</td></tr>
            <tr><td>Plan Adherence</td><td>15%</td><td>hours logged on Weekly-Plan projects ÷ planned hours (cap 100%)</td><td>Did the week's committed plan actually get worked?</td></tr>
            <tr><td>Efficiency</td><td>10%</td><td>estimated ÷ actual hours, capped at 120%</td><td>Estimate accuracy. Cap stops rewarding inflated estimates.</td></tr>
            <tr><td>Quality</td><td>10%</td><td>1 − (reopened tasks ÷ completed tasks)</td><td>Rework rate, via task status history (Done → reopened).</td></tr>
            <tr><td>Consistency</td><td>5%</td><td>days with ≥ 50% of daily target logged ÷ working days</td><td>Steady daily work vs end-of-week binge logging.</td></tr>
            <tr><td>Attendance</td><td>5%</td><td>checked-in days ÷ effective working days</td><td>Presence, on days that count.</td></tr>
          </tbody>
        </table>

        <h4 class="doc-h4">Fairness rules</h4>
        <ul class="doc-ul">
          <li><strong>Leave &amp; holiday adjusted everywhere.</strong> Target hours = 8h × effective working days. Sundays, public holidays (per the employee's holiday list) and approved leave are removed <em>before</em> any percentage is computed. Half-day leave deducts 0.5 day. An employee on approved leave is never penalised for it.</li>
          <li><strong>Estimates are PM-controlled</strong> (~90% set by project managers), so the Delivery and Efficiency dimensions can't be gamed by self-inflating estimates.</li>
          <li><strong>Caps prevent gaming.</strong> Efficiency capped at 120%; Delivery and Utilization at 100%. Anomalies like "100% utilization with 0 tasks done" surface as a high Utilization but zero Delivery — the composite exposes it.</li>
          <li><strong>Evaluate trends, not snapshots.</strong> Use 30/60/90-day periods for appraisal decisions; a single week is noise (one sick day on a 5-day week moves every % by 20 points).</li>
          <li><strong>Management-only.</strong> This tab and its API are restricted to System Manager / PMS Manager roles.</li>
          <li><strong>Metrics inform, humans decide.</strong> The score is an input to promotion/increment discussions, not a verdict.</li>
        </ul>

        <h4 class="doc-h4">⚠️ Utilization vs Efficiency — two different questions</h4>
        <p class="doc-p">These two percentages appear across NextPMS reports and are <strong>not comparable to each other</strong>:</p>
        <table class="doc-table">
          <thead><tr><th></th><th>Utilization</th><th>Efficiency</th></tr></thead>
          <tbody>
            <tr><td><strong>Formula</strong></td><td>logged hours ÷ target hours × 100</td><td>estimated hours ÷ actual hours × 100</td></tr>
            <tr><td><strong>Question answered</strong></td><td>"Did they log enough hours against the 8h/day bar?"</td><td>"Were the task time-estimates accurate?" (&gt;100% = finished faster than estimated)</td></tr>
            <tr><td><strong>High value means</strong></td><td>Fully engaged / good timer discipline</td><td>Fast against estimates (or estimates were generous)</td></tr>
            <tr><td><strong>Low value means</strong></td><td>Under-logged: either low activity or timers not run</td><td>Slower than estimated (or estimates were tight)</td></tr>
          </tbody>
        </table>
        <p class="doc-p">
          <strong>Why the weekly email and this report can show different numbers for the same person:</strong>
        </p>
        <ul class="doc-ul">
          <li><strong>Different date windows.</strong> The weekly email always covers the fixed calendar week <em>Monday–Friday</em>. The Task Report periods (5d/10d/30d…) are <em>rolling windows ending today</em> — a "5d" view opened on Saturday covers Tue–Sat, dropping Monday's hours and adding a Saturday with zero hours. Same person, different days summed.</li>
          <li><strong>Different metrics.</strong> The email headline is <em>Utilization</em>; the Task Report headline is <em>Efficiency</em>. Example: 49% utilization (15.7h logged of a 32h leave-adjusted target) and 79% efficiency (9.5h estimated ÷ 12.03h actual) can both be true simultaneously — one measures volume, the other estimate accuracy.</li>
          <li><strong>Same engine underneath.</strong> Both reports use identical leave/holiday/target logic (<code>next_pms.api._hours</code>); only the window and the question differ. Both figures are now labelled with their formula wherever they appear.</li>
        </ul>

        <h4 class="doc-h4">Data sources</h4>
        <ul class="doc-ul">
          <li><strong>Hours:</strong> PMS Time Log (timer) — the only "actual hours" source. Check-in/out is informational and only feeds Attendance.</li>
          <li><strong>Tasks:</strong> PMS Task (status, estimates, due dates). "Completed in period" = status Done with last modification inside the window.</li>
          <li><strong>Plan:</strong> published Weekly Plan allocations (planned hours per project per member).</li>
          <li><strong>Absence:</strong> approved Leave Applications + the employee's Holiday List.</li>
          <li><strong>Rework:</strong> Frappe Version history of task status changes.</li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const users = ref([])
const selectedUser = ref('')
const period = ref(30)
const data = ref(null)
const board = ref(null)
const loading = ref(false)
const view = ref('individual')
const fromDate = ref('')
const toDate = ref('')
const history = ref([])
const adjusting = ref(null)
const adjValue = ref(0)
const adjReason = ref('')
const adjError = ref('')
const adjSaving = ref(false)

const customRange = computed(() => !!(fromDate.value && toDate.value))
const topPerformer = computed(() => {
  const top = board.value?.rows?.find(r => r.rank === 1)
  return top && top.composite_score > 0 ? top : null
})

const periods = [
  { label: '5d', value: 5 },
  { label: '10d', value: 10 },
  { label: '30d', value: 30 },
  { label: '45d', value: 45 },
  { label: '60d', value: 60 },
  { label: '90d', value: 90 },
  { label: 'All', value: 0 },
]

const labels = {
  delivery: 'Delivery',
  timeliness: 'Timeliness',
  utilization: 'Utilization',
  plan_adherence: 'Plan Adherence',
  efficiency: 'Efficiency',
  quality: 'Quality',
  consistency: 'Consistency',
  attendance: 'Attendance',
}

onMounted(async () => {
  try {
    users.value = await call('next_pms.api.productivity.get_productivity_users')
  } catch (e) {
    console.error('Failed to load users:', e)
  }
})

function windowArgs() {
  const args = { period_days: period.value }
  if (customRange.value) {
    args.from_date = fromDate.value
    args.to_date = toDate.value
  }
  return args
}

function reload() {
  if (view.value === 'leaderboard') loadBoard()
  else load()
}

function onRangeChange() {
  if (customRange.value) reload()
}

function clearRange() {
  fromDate.value = ''
  toDate.value = ''
}

async function load() {
  if (!selectedUser.value) return
  loading.value = true
  adjusting.value = null
  loadHistory()
  try {
    data.value = await call('next_pms.api.performance.get_performance_score', {
      user: selectedUser.value,
      ...windowArgs(),
    })
  } catch (e) {
    console.error('Failed to load performance score:', e)
    data.value = null
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  if (!selectedUser.value) {
    history.value = []
    return
  }
  try {
    history.value = await call('next_pms.api.performance.get_score_history', {
      user: selectedUser.value,
    })
  } catch (e) {
    console.error('Failed to load score history:', e)
    history.value = []
  }
}

function fmt1(v) {
  return v == null ? '—' : Number(v).toFixed(1)
}

function adjTitle(h) {
  const parts = []
  if (h.adjustment_reason) parts.push(h.adjustment_reason)
  if (h.adjusted_by) parts.push('by ' + h.adjusted_by)
  return parts.join(' — ')
}

function toggleAdjust(h) {
  if (adjusting.value === h.name) {
    adjusting.value = null
    return
  }
  adjusting.value = h.name
  adjValue.value = Number(h.adjustment) || 0
  adjReason.value = h.adjustment_reason || ''
  adjError.value = ''
}

async function saveAdjust(h) {
  const adj = Number(adjValue.value) || 0
  // client-side mirror of the server rules for fast feedback — the
  // server (controller) stays authoritative
  if (adj < -10 || adj > 10) {
    adjError.value = 'Adjustment must be between −10 and +10.'
    return
  }
  if (adj !== 0 && !adjReason.value.trim()) {
    adjError.value = 'A reason is required for a non-zero adjustment.'
    return
  }
  adjSaving.value = true
  adjError.value = ''
  try {
    const row = await call('next_pms.api.performance.apply_adjustment', {
      name: h.name,
      adjustment: adj,
      reason: adjReason.value,
    })
    const i = history.value.findIndex(r => r.name === h.name)
    if (i !== -1) history.value[i] = row
    adjusting.value = null
  } catch (e) {
    console.error('Failed to apply adjustment:', e)
    adjError.value = 'Could not save adjustment — check the value and reason.'
  } finally {
    adjSaving.value = false
  }
}

async function loadBoard() {
  loading.value = true
  try {
    board.value = await call('next_pms.api.performance.get_team_performance', windowArgs())
  } catch (e) {
    console.error('Failed to load leaderboard:', e)
    board.value = null
  } finally {
    loading.value = false
  }
}

function medal(rank) {
  return { 1: '🏆 ', 2: '🥈 ', 3: '🥉 ' }[rank] || ''
}

function weakest(r) {
  const entries = Object.entries(r.dimensions || {})
  if (!entries.length) return '—'
  const [key, score] = entries.reduce((min, e) => (e[1] < min[1] ? e : min))
  return `${labels[key]} (${score.toFixed(0)})`
}

function openMember(r) {
  if (!r.rank && r.included_weight === 0) return
  selectedUser.value = r.user
  view.value = 'individual'
  load()
}

function barColor(score) {
  if (score == null) return 'var(--border-default)'
  if (score >= 85) return '#10B981'
  if (score >= 70) return '#2563eb'
  if (score >= 50) return '#F59E0B'
  return '#EF4444'
}
</script>

<style scoped>
.perf-tab { display: flex; flex-direction: column; gap: 20px; }
.perf-controls { display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-end; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 16px 20px; }
.control-group { display: flex; flex-direction: column; gap: 6px; }
.ctrl-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); }
.ctrl-select { padding: 8px 12px; border: 1px solid var(--border-default); border-radius: 8px; background: var(--bg-body); color: var(--text-primary); font-size: 13px; min-width: 220px; }
.period-btns { display: flex; gap: 4px; }
.period-btn { padding: 7px 14px; border: 1px solid var(--border-default); background: var(--bg-body); color: var(--text-secondary); font-size: 12px; font-weight: 500; cursor: pointer; border-radius: 8px; transition: all 0.15s; }
.period-btn.active { background: var(--color-primary, #2563eb); color: #fff; border-color: var(--color-primary, #2563eb); }

.range-inputs { display: flex; align-items: center; gap: 6px; }
.ctrl-date { padding: 7px 10px; border: 1px solid var(--border-default); border-radius: 8px; background: var(--bg-body); color: var(--text-primary); font-size: 12.5px; }
.range-sep { color: var(--text-secondary); font-size: 12px; }
.range-clear { border: 1px solid var(--border-default); background: var(--bg-body); color: var(--text-secondary); border-radius: 8px; padding: 6px 9px; cursor: pointer; font-size: 11px; }
.range-clear:hover { color: #ef4444; border-color: #ef4444; }

.award-banner { background: #fefce8; border: 1px solid #fde68a; color: #92400e; border-radius: 8px; padding: 10px 14px; font-size: 13.5px; margin-bottom: 14px; }
.board-row { cursor: pointer; }
.board-row:hover td { background: var(--bg-surface-hover); }
.board-row.row-top td { background: #fefce8; }
.board-row.row-unranked td { opacity: 0.5; }
.rank-cell { font-weight: 700; white-space: nowrap; }
.band-chip { font-weight: 800; font-size: 13px; }
.board-note { font-size: 12px; color: var(--text-secondary); margin-top: 12px; line-height: 1.6; }
.dim-note { font-size: 12px; color: var(--text-secondary); margin: -4px 0 14px; line-height: 1.6; background: var(--bg-surface-hover); border-left: 3px solid var(--color-primary, #2563eb); border-radius: 6px; padding: 8px 12px; }

.perf-loading, .perf-empty { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 20px; color: var(--text-secondary); font-size: 13px; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--border-default); border-top-color: var(--color-primary, #2563eb); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.score-hero { display: flex; align-items: center; gap: 28px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 24px 28px; }
.score-ring { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 120px; height: 120px; border-radius: 50%; border: 6px solid; flex-shrink: 0; }
.score-ring.band-a { border-color: #10B981; }
.score-ring.band-b { border-color: #2563eb; }
.score-ring.band-c { border-color: #F59E0B; }
.score-ring.band-d { border-color: #EF4444; }
.score-num { font-size: 32px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.score-band { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-top: 4px; }
.score-name { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.score-period { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.score-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.pill { font-size: 11px; padding: 4px 10px; border-radius: 999px; background: var(--bg-surface-hover); border: 1px solid var(--border-default); color: var(--text-secondary); }

.dim-card, .doc-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px 24px; }
.dim-title, .doc-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0 0 14px; }
.dim-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dim-table th { text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); border-bottom: 2px solid var(--border-default); }
.dim-table td { padding: 10px; border-bottom: 1px solid var(--border-light); color: var(--text-primary); vertical-align: middle; }
.dim-table tr.excluded td { opacity: 0.45; }
.dim-name { font-weight: 600; }
.dim-score { font-weight: 700; }
.dim-bar-cell { width: 180px; }
.dim-bar-track { height: 8px; background: var(--bg-surface-hover); border-radius: 4px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.dim-raw { font-size: 12px; color: var(--text-secondary); }

.hist-empty { font-size: 13px; color: var(--text-secondary); padding: 8px 2px; }
.adj-badge { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; background: #fef3c7; border: 1px solid #fde68a; color: #92400e; cursor: help; }
.adjust-btn { border: 1px solid var(--border-default); background: var(--bg-body); color: var(--text-secondary); border-radius: 8px; padding: 5px 10px; font-size: 11.5px; cursor: pointer; }
.adjust-btn:hover { color: var(--color-primary, #2563eb); border-color: var(--color-primary, #2563eb); }
.adjust-editor { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 8px 2px; }
.adj-input { width: 80px; padding: 7px 10px; border: 1px solid var(--border-default); border-radius: 8px; background: var(--bg-body); color: var(--text-primary); font-size: 12.5px; }
.adj-reason { flex: 1; min-width: 220px; padding: 7px 10px; border: 1px solid var(--border-default); border-radius: 8px; background: var(--bg-body); color: var(--text-primary); font-size: 12.5px; }
.adj-error { font-size: 12px; color: #ef4444; }

.doc-p { font-size: 13px; line-height: 1.65; color: var(--text-primary); margin: 8px 0; }
.doc-h4 { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 18px 0 6px; }
.doc-ul { margin: 6px 0 6px 18px; padding: 0; }
.doc-ul li { font-size: 13px; line-height: 1.65; color: var(--text-primary); margin-bottom: 6px; }
.doc-table { width: 100%; border-collapse: collapse; font-size: 12.5px; margin: 10px 0; }
.doc-table th { text-align: left; padding: 8px 10px; background: var(--bg-surface-hover); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; border: 1px solid var(--border-default); }
.doc-table td { padding: 8px 10px; border: 1px solid var(--border-light); color: var(--text-primary); line-height: 1.5; vertical-align: top; }
.doc-card code { background: var(--bg-surface-hover); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
</style>
