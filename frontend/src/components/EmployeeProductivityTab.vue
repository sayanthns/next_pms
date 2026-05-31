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

    <div v-if="loading" class="prod-loading">
      <div class="spinner"></div>
      <span>Loading productivity data...</span>
    </div>
    <div v-else-if="!selectedUser" class="prod-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
      <p>Select an employee to view productivity report</p>
    </div>

    <template v-else-if="data">
      <!-- Employee Header (no colored score) -->
      <div class="emp-header">
        <div class="emp-avatar">{{ initials(data.user_full_name) }}</div>
        <div class="emp-info">
          <div class="emp-name">{{ data.user_full_name }}</div>
          <div class="emp-period">{{ formatDate(data.from_date) }} – {{ formatDate(data.to_date) }}</div>
        </div>
        <div class="emp-meta-pills">
          <span class="meta-pill">{{ data.checked_in_days_count }}/{{ data.working_days_count }} days</span>
          <span class="meta-pill">{{ data.attendance_pct }}% attendance</span>
          <span class="meta-pill" v-if="data.overall_completion_pct !== null">{{ data.overall_completion_pct }}% tasks done</span>
          <span class="meta-pill" :class="effPillClass(data.overall_efficiency_pct)" v-if="data.overall_efficiency_pct !== null">{{ data.overall_efficiency_pct }}% efficiency</span>
        </div>
      </div>

      <!-- Stat Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-icon">📅</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.checked_in_days_count }}/{{ data.working_days_count }}</span>
            <span class="stat-lbl">Days Checked In</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">🏢</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.total_office_hours }}h</span>
            <span class="stat-lbl">Office Hours (avg {{ data.avg_hours_per_day }}h/day)</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">⏱</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.total_logged_hours }}h</span>
            <span class="stat-lbl">Task Hours Logged</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">✅</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.done_count }}/{{ data.total_tasks }}</span>
            <span class="stat-lbl">Tasks Completed ({{ data.overall_completion_pct }}%)</span>
          </div>
        </div>
        <div class="stat-card" :class="{ warn: data.overdue_count > 0 }">
          <span class="stat-icon">⚠️</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.overdue_count }}</span>
            <span class="stat-lbl">Overdue Tasks</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">🎯</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.on_time_pct != null ? data.on_time_pct + '%' : 'N/A' }}</span>
            <span class="stat-lbl">On-Time Completion</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">📊</span>
          <div class="stat-body">
            <span class="stat-val" :class="effValClass(data.overall_efficiency_pct)">
              {{ data.overall_efficiency_pct != null ? data.overall_efficiency_pct + '%' : 'N/A' }}
            </span>
            <span class="stat-lbl">Efficiency (Est÷Act×100)</span>
          </div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">📋</span>
          <div class="stat-body">
            <span class="stat-val">{{ data.total_estimated_hours }}h / {{ data.total_actual_hours }}h</span>
            <span class="stat-lbl">Estimated / Actual Hours</span>
          </div>
        </div>
      </div>

      <div class="two-col">
        <!-- Projects Worked On -->
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
                  <th class="num">Completion</th>
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
                    <span :class="compClass(proj.completion_pct)">{{ proj.completion_pct }}%</span>
                  </td>
                  <td class="num">
                    <span v-if="proj.efficiency_pct != null" :class="effClass(proj.efficiency_pct)">{{ proj.efficiency_pct }}%</span>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
                <!-- Overall row -->
                <tr class="overall-row">
                  <td class="proj-name"><strong>Overall</strong></td>
                  <td class="num"><strong>{{ data.total_tasks }}</strong></td>
                  <td class="num done-num"><strong>{{ data.done_count }}</strong></td>
                  <td class="num wip-num"><strong>{{ data.in_progress_count }}</strong></td>
                  <td class="num" :class="{ 'overdue-num': data.overdue_count > 0 }"><strong>{{ data.overdue_count }}</strong></td>
                  <td class="num"><strong>{{ data.total_estimated_hours }}</strong></td>
                  <td class="num"><strong>{{ data.total_actual_hours }}</strong></td>
                  <td class="num">
                    <strong :class="compClass(data.overall_completion_pct)">{{ data.overall_completion_pct }}%</strong>
                  </td>
                  <td class="num">
                    <strong v-if="data.overall_efficiency_pct != null" :class="effClass(data.overall_efficiency_pct)">{{ data.overall_efficiency_pct }}%</strong>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="eff-note">Efficiency = Estimated ÷ Actual × 100. &gt;100% = faster than estimated.</div>
          </div>
        </div>

        <!-- Attendance Breakdown (no highlight) -->
        <div class="section-card">
          <div class="section-title">Attendance Breakdown</div>

          <div v-if="data.leaves.length" class="attend-section">
            <div class="attend-section-label">🏖 Approved Leaves ({{ data.leave_days_count }} day(s))</div>
            <div v-for="l in data.leaves" :key="l.from_date + l.leave_type" class="attend-row leave-row">
              <span class="ar-type">{{ l.leave_type }}</span>
              <span class="ar-dates">{{ formatDate(l.from_date) }}<template v-if="l.from_date !== l.to_date"> – {{ formatDate(l.to_date) }}</template></span>
              <span class="ar-days">{{ l.days }}d</span>
            </div>
          </div>

          <div v-if="data.holidays.length" class="attend-section">
            <div class="attend-section-label">🎉 Public Holidays ({{ data.holiday_days_count }} day(s))</div>
            <div v-for="h in data.holidays" :key="h.date" class="attend-row holiday-row">
              <span class="ar-type">{{ h.description || 'Holiday' }}</span>
              <span class="ar-dates">{{ formatDate(h.date) }}</span>
              <span class="day-weekday">{{ weekday(h.date) }}</span>
            </div>
          </div>

          <div class="attend-section">
            <div class="attend-section-label">
              ⚠ Missing Check-ins
              <span class="missing-count" :class="{ red: data.missing_days.length > 3 }">
                {{ data.missing_days.length }} day(s)
              </span>
            </div>
            <div v-if="!data.missing_days.length" class="section-empty success">✅ No missing check-ins.</div>
            <div v-else class="missing-days-list">
              <div v-for="d in data.missing_days" :key="d" class="missing-day">
                <span class="day-dot"></span>
                <span class="day-date">{{ formatDate(d) }}</span>
                <span class="day-weekday">{{ weekday(d) }}</span>
              </div>
            </div>
          </div>
          <div class="missing-note">Sundays, public holidays, and approved leaves excluded.</div>
        </div>
      </div>

      <!-- Day-wise Hours Summary -->
      <div class="section-card" v-if="data.day_summary.length">
        <div class="section-title">
          Day-wise Hours Summary
          <span v-if="data.timer_missing_days.length" class="timer-missing-badge">
            ⏱ {{ data.timer_missing_days.length }} day(s) with no task timer
          </span>
        </div>
        <div class="day-table-wrap">
          <table class="mini-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Day</th>
                <th class="num">Target</th>
                <th class="num">Task Hours Logged</th>
                <th class="num">Gap</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="d in data.day_summary"
                :key="d.date"
                :class="{ 'row-timer-missing': d.timer_missing }"
              >
                <td class="day-cell">{{ formatDate(d.date) }}</td>
                <td class="day-cell text-muted">{{ weekday(d.date) }}</td>
                <td class="num">{{ d.target_hours }}h</td>
                <td class="num">{{ d.logged_hours }}h</td>
                <td class="num" :class="gapClass(d.target_hours, d.logged_hours)">
                  {{ gapHours(d.target_hours, d.logged_hours) }}
                </td>
                <td>
                  <span v-if="d.status === 'off'" class="status-no-timer">Off day</span>
                  <span v-else-if="d.status === 'good'" class="status-good">Good</span>
                  <span v-else-if="d.status === 'partial'" class="status-partial">Partial</span>
                  <span v-else class="status-no-timer">No timer</span>
                </td>
              </tr>
            </tbody>
          </table>
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
import { ref, onMounted } from 'vue'
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
  if (pct == null) return 'text-muted'
  if (pct >= 90) return 'eff-good'
  if (pct >= 70) return 'eff-mid'
  return 'eff-low'
}

function effValClass(pct) {
  if (pct == null) return ''
  if (pct >= 90) return 'val-good'
  if (pct >= 70) return 'val-mid'
  return 'val-low'
}

function effPillClass(pct) {
  if (pct == null) return ''
  if (pct >= 90) return 'pill-good'
  if (pct >= 70) return 'pill-mid'
  return 'pill-low'
}

function compClass(pct) {
  if (pct >= 70) return 'eff-good'
  if (pct >= 40) return 'eff-mid'
  return 'eff-low'
}

function gapHours(office, logged) {
  const g = office - logged
  if (g <= 0) return '0h'
  return '-' + g.toFixed(1) + 'h'
}

function gapClass(office, logged) {
  const g = office - logged
  if (g <= 0) return 'gap-ok'
  if (g <= 2) return 'gap-mid'
  return 'gap-high'
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
.prod-empty svg { margin: 0 auto 12px; display: block; }
.prod-empty p { font-size: 14px; }

/* Employee Header — plain, no color score */
.emp-header {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 18px 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px var(--shadow-sm);
}
.emp-avatar {
  width: 48px; height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.emp-info { flex: 1; }
.emp-name { font-size: 17px; font-weight: 700; color: var(--text-primary); }
.emp-period { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }
.emp-meta-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.meta-pill {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--bg-surface-hover, #f3f4f6);
  color: var(--text-secondary);
  border: 1px solid var(--border-light, #e5e7eb);
}
.pill-good { background: #dcfce7; color: #15803d; border-color: #bbf7d0; }
.pill-mid { background: #fef9c3; color: #854d0e; border-color: #fde68a; }
.pill-low { background: #fee2e2; color: #b91c1c; border-color: #fecaca; }

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
.stat-card.warn { border-left: 3px solid #f59e0b; }
.stat-icon { font-size: 22px; flex-shrink: 0; }
.stat-body { display: flex; flex-direction: column; gap: 2px; }
.stat-val { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.stat-lbl { font-size: 11px; color: var(--text-tertiary); font-weight: 500; }
.val-good { color: #16a34a; }
.val-mid { color: #d97706; }
.val-low { color: #dc2626; }

/* Two-column */
.two-col { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 16px; }
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

.section-card {
  background: var(--bg-surface);
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px var(--shadow-sm);
  margin-bottom: 16px;
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.section-empty { font-size: 13px; color: var(--text-tertiary); padding: 8px 0; }
.section-empty.success { color: #16a34a; }

/* Projects table */
.proj-table-wrap, .day-table-wrap { overflow-x: auto; }
.eff-note { font-size: 11px; color: var(--text-tertiary); margin-top: 8px; }
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
.mini-table tr:hover td { background: var(--bg-surface-hover); }
.mini-table .num { text-align: right; }
.proj-name { font-weight: 500; max-width: 160px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.overall-row td { background: var(--bg-surface-hover, #f9fafb); border-top: 2px solid var(--border-default); }
.done-num { color: #16a34a; font-weight: 600; }
.wip-num { color: #d97706; }
.overdue-num { color: #dc2626; font-weight: 700; }
.text-muted { color: var(--text-tertiary); }
.eff-good { color: #16a34a; font-weight: 700; }
.eff-mid { color: #d97706; font-weight: 600; }
.eff-low { color: #dc2626; font-weight: 600; }

/* Day-wise table */
.day-cell { white-space: nowrap; }
.row-timer-missing td { background: #fff7ed !important; }
.gap-ok { color: #16a34a; }
.gap-mid { color: #d97706; }
.gap-high { color: #dc2626; font-weight: 600; }
.timer-missing-badge {
  font-size: 11px;
  font-weight: 600;
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
  padding: 2px 8px;
  border-radius: 8px;
}
.status-good { font-size: 11px; font-weight: 600; color: #16a34a; }
.status-partial { font-size: 11px; font-weight: 600; color: #d97706; }
.status-no-timer { font-size: 11px; font-weight: 600; color: #dc2626; }

/* Attendance breakdown */
.attend-section { margin-bottom: 12px; }
.attend-section-label {
  font-size: 11px; font-weight: 700; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.3px;
  margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
}
.missing-count { font-size: 11px; font-weight: 600; background: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 10px; }
.missing-count.red { background: #fef2f2; color: #dc2626; }
.attend-row {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; border-radius: 6px; margin-bottom: 3px; font-size: 12px;
}
.leave-row { background: #f0fdf4; }
.holiday-row { background: #fefce8; }
.ar-type { font-weight: 600; color: var(--text-primary); flex: 1; }
.ar-dates { color: var(--text-secondary); }
.ar-days { font-size: 11px; font-weight: 700; color: #059669; background: #d1fae5; padding: 1px 6px; border-radius: 8px; }
.missing-days-list { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; }
.missing-day { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 6px; background: var(--bg-surface-hover); }
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
