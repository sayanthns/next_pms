<template>
  <div class="prod-tab">
    <!-- Controls -->
    <div class="prod-controls">
      <div class="control-group">
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
            :class="{ active: period === p.value }"
            @click="period = p.value; load()"
          >{{ p.label }}</button>
        </div>
      </div>
    </div>

    <!-- Loading / Empty -->
    <div v-if="loading" class="prod-loading">
      <div class="spinner"></div>
      <span>Loading productivity data...</span>
    </div>
    <div v-else-if="!selectedUser" class="prod-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
      <p>Select an employee to view productivity report</p>
    </div>

    <template v-else-if="data">
      <!-- Employee Header -->
      <div class="emp-header">
        <div class="emp-avatar">{{ initials(data.user_full_name) }}</div>
        <div class="emp-info">
          <div class="emp-name">{{ data.user_full_name }}</div>
          <div class="emp-period">{{ formatDate(data.from_date) }} – {{ formatDate(data.to_date) }}</div>
        </div>
        <div class="emp-score" :class="scoreClass">
          <span class="score-num">{{ data.attendance_pct }}%</span>
          <span class="score-label">Attendance</span>
        </div>
      </div>

      <!-- Stat Cards Row -->
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-icon attend">📅</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.checked_in_days_count }}/{{ data.working_days_count }}</span>
            <span class="stat-lbl">Days Checked In</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon hours">⏱</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.total_hours_logged }}h</span>
            <span class="stat-lbl">Hours Logged (avg {{ data.avg_hours_per_day }}h/day)</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon tasks">✅</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.done_count }}/{{ data.total_tasks }}</span>
            <span class="stat-lbl">Tasks Completed</span>
          </div>
        </div>
        <div class="stat-card" :class="{ warn: data.overdue_count > 0 }">
          <span class="stat-icon overdue">⚠️</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.overdue_count }}</span>
            <span class="stat-lbl">Overdue Tasks</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon ontime">🎯</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.on_time_pct != null ? data.on_time_pct + '%' : 'N/A' }}</span>
            <span class="stat-lbl">On-Time Completion</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon est">📊</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.total_estimated_hours }}h / {{ data.total_actual_hours }}h</span>
            <span class="stat-lbl">Estimated / Actual Hours</span>
          </div>
        </div>
      </div>

      <div class="two-col">
        <!-- Projects Breakdown -->
        <div class="section-card">
          <div class="section-title">Projects Worked On ({{ data.projects.length }})</div>
          <div v-if="!data.projects.length" class="section-empty">No projects found.</div>
          <div v-else class="proj-table-wrap">
            <table class="mini-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th class="num">Total</th>
                  <th class="num">Done</th>
                  <th class="num">WIP</th>
                  <th class="num">Overdue</th>
                  <th class="num">Est.h</th>
                  <th class="num">Act.h</th>
                  <th class="num">Efficiency</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="proj in data.projects" :key="proj.project">
                  <td class="proj-name">{{ proj.project_name }}</td>
                  <td class="num">{{ proj.total }}</td>
                  <td class="num done-num">{{ proj.done }}</td>
                  <td class="num wip-num">{{ proj.in_progress }}</td>
                  <td class="num" :class="{ 'overdue-num': proj.overdue > 0 }">{{ proj.overdue }}</td>
                  <td class="num">{{ proj.estimated_hours }}</td>
                  <td class="num">{{ proj.actual_hours }}</td>
                  <td class="num">
                    <span v-if="proj.efficiency_pct != null" :class="effClass(proj.efficiency_pct)">
                      {{ proj.efficiency_pct }}%
                    </span>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Missing Check-in Days -->
        <div class="section-card">
          <div class="section-title">
            Check-in Missing Days
            <span class="missing-count" :class="{ red: data.missing_days.length > 3 }">
              {{ data.missing_days.length }} day(s)
            </span>
          </div>
          <div v-if="!data.missing_days.length" class="section-empty success">
            ✅ No missing check-ins in this period.
          </div>
          <div v-else class="missing-days-list">
            <div
              v-for="d in data.missing_days"
              :key="d"
              class="missing-day"
            >
              <span class="day-dot"></span>
              <span class="day-date">{{ formatDate(d) }}</span>
              <span class="day-weekday">{{ weekday(d) }}</span>
            </div>
          </div>
          <div v-if="data.missing_days.length" class="missing-note">
            Sundays excluded (treated as holidays).
          </div>
        </div>
      </div>

      <!-- Recommendations -->
      <div class="reco-card" v-if="data.recommendations.length">
        <div class="reco-title">💡 Recommendations</div>
        <ul class="reco-list">
          <li v-for="(r, i) in data.recommendations" :key="i" class="reco-item">{{ r }}</li>
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
const loading = ref(false)

const periods = [
  { label: '5d', value: 5 },
  { label: '10d', value: 10 },
  { label: '30d', value: 30 },
  { label: '45d', value: 45 },
  { label: '60d', value: 60 },
  { label: '90d', value: 90 },
  { label: 'All', value: 0 },
]

onMounted(async () => {
  try {
    users.value = await call('next_pms.api.productivity.get_productivity_users')
    // Auto-select if only one user
    if (users.value.length === 1) {
      selectedUser.value = users.value[0].name
      await load()
    }
  } catch (e) {
    console.error('Failed to load users:', e)
  }
})

async function load() {
  if (!selectedUser.value) return
  loading.value = true
  try {
    data.value = await call('next_pms.api.productivity.get_employee_productivity', {
      user: selectedUser.value,
      period_days: period.value,
    })
  } catch (e) {
    console.error('Failed to load productivity:', e)
    data.value = null
  } finally {
    loading.value = false
  }
}

const scoreClass = computed(() => {
  if (!data.value) return ''
  const pct = data.value.attendance_pct
  if (pct >= 80) return 'score-good'
  if (pct >= 60) return 'score-mid'
  return 'score-low'
})

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function weekday(dateStr) {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  return days[new Date(dateStr + 'T00:00:00').getDay()]
}

function effClass(pct) {
  if (pct >= 90) return 'eff-good'
  if (pct >= 70) return 'eff-mid'
  return 'eff-low'
}
</script>

<style scoped>
.prod-tab { padding-top: 4px; }

/* Controls */
.prod-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
  background: var(--bg-surface);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px var(--shadow-sm);
}
.control-group { display: flex; flex-direction: column; gap: 6px; }
.ctrl-label { font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }
.ctrl-select {
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  min-width: 220px;
}
.ctrl-select:focus { outline: none; border-color: var(--color-primary, #2563eb); }
.period-btns { display: flex; gap: 4px; flex-wrap: wrap; }
.period-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.period-btn:hover { border-color: var(--color-primary, #2563eb); color: var(--color-primary, #2563eb); }
.period-btn.active { background: var(--color-primary, #2563eb); color: #fff; border-color: var(--color-primary, #2563eb); font-weight: 600; }

/* Loading / Empty */
.prod-loading { display: flex; align-items: center; gap: 12px; padding: 60px 0; justify-content: center; color: var(--text-tertiary); }
.spinner { width: 22px; height: 22px; border: 3px solid var(--border-default); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.6s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
.prod-empty { text-align: center; padding: 60px 0; color: var(--text-tertiary); }
.prod-empty svg { margin-bottom: 12px; display: block; margin-left: auto; margin-right: auto; }
.prod-empty p { font-size: 14px; }

/* Employee Header */
.emp-header {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px var(--shadow-sm);
}
.emp-avatar {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.emp-info { flex: 1; }
.emp-name { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.emp-period { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }
.emp-score { text-align: center; }
.score-num { display: block; font-size: 28px; font-weight: 800; }
.score-label { font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; }
.score-good .score-num { color: #16a34a; }
.score-mid .score-num { color: #d97706; }
.score-low .score-num { color: #dc2626; }

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card {
  background: var(--bg-surface);
  border-radius: 10px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 3px var(--shadow-sm);
}
.stat-card.warn { border-left: 3px solid #dc2626; }
.stat-icon { font-size: 22px; flex-shrink: 0; }
.stat-body { display: flex; flex-direction: column; gap: 2px; }
.stat-val { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.stat-lbl { font-size: 11px; color: var(--text-tertiary); font-weight: 500; }

/* Two-column layout */
.two-col {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

.section-card {
  background: var(--bg-surface);
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px var(--shadow-sm);
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.missing-count { font-size: 11px; font-weight: 600; background: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 10px; }
.missing-count.red { background: #fef2f2; color: #dc2626; }
.section-empty { font-size: 13px; color: var(--text-tertiary); padding: 12px 0; }
.section-empty.success { color: #16a34a; }

/* Mini table */
.proj-table-wrap { overflow-x: auto; }
.mini-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.mini-table th {
  padding: 7px 10px;
  text-align: left;
  font-weight: 600;
  color: var(--text-tertiary);
  font-size: 10px;
  text-transform: uppercase;
  border-bottom: 2px solid var(--border-default);
  white-space: nowrap;
}
.mini-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-light); color: var(--text-primary); }
.mini-table tr:hover { background: var(--bg-surface-hover); }
.mini-table .num { text-align: right; }
.proj-name { font-weight: 500; max-width: 160px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.done-num { color: #16a34a; font-weight: 600; }
.wip-num { color: #d97706; }
.overdue-num { color: #dc2626; font-weight: 700; }
.text-muted { color: var(--text-tertiary); }
.eff-good { color: #16a34a; font-weight: 700; }
.eff-mid { color: #d97706; font-weight: 600; }
.eff-low { color: #dc2626; font-weight: 600; }

/* Missing Days */
.missing-days-list { display: flex; flex-direction: column; gap: 4px; max-height: 260px; overflow-y: auto; }
.missing-day { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; background: var(--bg-surface-hover); }
.day-dot { width: 7px; height: 7px; background: #f59e0b; border-radius: 50%; flex-shrink: 0; }
.day-date { font-size: 12px; font-weight: 500; color: var(--text-primary); flex: 1; }
.day-weekday { font-size: 11px; color: var(--text-tertiary); font-weight: 600; }
.missing-note { margin-top: 8px; font-size: 11px; color: var(--text-tertiary); }

/* Recommendations */
.reco-card {
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border: 1px solid #bae6fd;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
}
.reco-title { font-size: 13px; font-weight: 700; color: #0369a1; margin-bottom: 10px; }
.reco-list { margin: 0; padding-left: 18px; }
.reco-item { font-size: 13px; color: #0c4a6e; margin-bottom: 4px; line-height: 1.5; }
</style>
