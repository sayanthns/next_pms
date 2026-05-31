<template>
  <div class="project-dashboard">
    <div v-if="!embedded" class="page-header">
      <div>
        <h1 class="page-title">Project Dashboard</h1>
        <p class="page-subtitle">{{ dashboard?.project_name || id }}</p>
      </div>
      <div class="header-actions">
        <span class="status-chip" :class="'chip-' + statusKey(dashboard?.status)">{{ dashboard?.status }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading project dashboard...</p>
    </div>

    <template v-else-if="dashboard">
      <!-- KPI Cards -->
      <div v-if="!embedded" class="kpi-cards">
        <div class="kpi-card">
          <span class="kpi-label">Total Tasks</span>
          <span class="kpi-value">{{ dashboard.total_tasks }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Completed</span>
          <span class="kpi-value kpi-green">{{ dashboard.task_counts['Done'] || 0 }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">In Progress</span>
          <span class="kpi-value kpi-orange">{{ dashboard.task_counts['In Progress'] || 0 }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Est. Hours</span>
          <span class="kpi-value">{{ dashboard.total_estimated_hours }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Actual Hours</span>
          <span class="kpi-value">{{ Math.round(dashboard.total_actual_hours * 10) / 10 }}</span>
        </div>
        <div v-if="settingsStore.canViewFinance" class="kpi-card">
          <span class="kpi-label">Budget Used</span>
          <span class="kpi-value" :class="{ 'kpi-red': dashboard.budget_utilization > 90 }">
            {{ Math.round(dashboard.budget_utilization) }}%
          </span>
        </div>
      </div>

      <!-- Progress Bar -->
      <div v-if="!embedded" class="progress-section">
        <div class="progress-header">
          <span class="progress-label">Overall Progress</span>
          <span class="progress-pct">{{ overallProgress }}%</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: overallProgress + '%' }"></div>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- Task Status Breakdown -->
        <div class="dash-card">
          <h3 class="dash-card-title">Task Status</h3>
          <div class="status-breakdown">
            <div v-for="(count, status) in dashboard.task_counts" :key="status" class="status-row">
              <span class="status-dot" :style="{ background: statusColor(status) }"></span>
              <span class="status-name">{{ status }}</span>
              <span class="status-count">{{ count }}</span>
              <div class="status-bar-mini">
                <div
                  class="status-bar-mini-fill"
                  :style="{ width: statusPct(count) + '%', background: statusColor(status) }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Budget Overview -->
        <div v-if="settingsStore.canViewFinance" class="dash-card">
          <h3 class="dash-card-title">Budget Overview</h3>
          <div class="budget-overview">
            <div class="budget-row">
              <span class="budget-label">Total Budget</span>
              <span class="budget-value">{{ formatCurrency(dashboard.total_budget) }}</span>
            </div>
            <div class="budget-row">
              <span class="budget-label">Spent</span>
              <span class="budget-value">{{ formatCurrency(dashboard.calculated_cost) }}</span>
            </div>
            <div class="budget-row">
              <span class="budget-label">Remaining</span>
              <span class="budget-value" :class="{ 'budget-negative': dashboard.budget_remaining < 0 }">
                {{ formatCurrency(dashboard.budget_remaining) }}
              </span>
            </div>
            <div class="budget-bar-wrap">
              <div class="budget-bar">
                <div
                  class="budget-bar-fill"
                  :style="{ width: Math.min(dashboard.budget_utilization, 100) + '%' }"
                  :class="{ 'over-budget': dashboard.budget_utilization > 100 }"
                ></div>
              </div>
            </div>
          </div>
          <div v-if="financials" class="financials-card" style="display:flex; gap:24px; padding:16px; border:1px solid #e5e7eb; border-radius:8px; margin:16px 0;">
            <div><div style="font-size:12px; color:#6b7280;">Sales Order</div><div style="font-weight:600;">{{ Number(financials.so_value).toLocaleString() }}</div></div>
            <div><div style="font-size:12px; color:#6b7280;">Budget</div><div style="font-weight:600;">{{ Number(financials.budget).toLocaleString() }}</div></div>
            <div><div style="font-size:12px; color:#6b7280;">Actual</div><div style="font-weight:600;">{{ Number(financials.actual).toLocaleString() }} ({{ financials.budget_util }}%)</div></div>
          </div>
        </div>

        <!-- Sprints -->
        <div class="dash-card">
          <h3 class="dash-card-title">Sprints</h3>
          <div v-if="dashboard.sprints.length" class="sprint-list">
            <div v-for="s in dashboard.sprints" :key="s.name" class="sprint-row">
              <div class="sprint-info">
                <span class="sprint-name">{{ s.sprint_name }}</span>
                <span class="sprint-status" :class="'chip-' + statusKey(s.status)">{{ s.status }}</span>
              </div>
              <div class="sprint-progress-row">
                <div class="sprint-bar">
                  <div class="sprint-bar-fill" :style="{ width: s.progress + '%' }"></div>
                </div>
                <span class="sprint-pct">{{ s.done_tasks }}/{{ s.total_tasks }}</span>
              </div>
            </div>
          </div>
          <p v-else class="no-data-text">No sprints yet</p>
        </div>

        <!-- Team -->
        <div class="dash-card">
          <h3 class="dash-card-title">Team</h3>
          <div v-if="dashboard.team_members.length" class="team-list">
            <div v-for="m in dashboard.team_members" :key="m.user" class="team-row">
              <span class="team-avatar">{{ getInitials(m.user) }}</span>
              <div class="team-info">
                <span class="team-name">{{ m.user }}</span>
                <span class="team-role">{{ m.role || 'Member' }}</span>
              </div>
              <span class="team-hours">{{ m.total_hours }}h</span>
            </div>
          </div>
          <p v-else class="no-data-text">No team members</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'

const settingsStore = useSettingsStore()

const props = defineProps({
  id: { type: String, required: true },
  embedded: { type: Boolean, default: false },
})

const loading = ref(true)
const dashboard = ref(null)
const financials = ref(null)

async function loadFinancials(projectName) {
  if (!projectName) return
  try {
    const r = await call('next_pms.api.project_report.get_project_financials', { project: projectName })
    financials.value = r?.message || r
  } catch (e) { console.error('financials load failed', e) }
}

onMounted(async () => {
  loading.value = true
  try {
    dashboard.value = await call('next_pms.api.dashboard.get_project_dashboard', {
      project: props.id,
    })
    loadFinancials(props.id)
  } catch (e) {
    console.error('Failed to load project dashboard:', e)
  } finally {
    loading.value = false
  }
})

const overallProgress = computed(() => {
  if (!dashboard.value || !dashboard.value.total_tasks) return 0
  return Math.round(((dashboard.value.task_counts['Done'] || 0) / dashboard.value.total_tasks) * 100)
})

function statusPct(count) {
  if (!dashboard.value || !dashboard.value.total_tasks) return 0
  return Math.round((count / dashboard.value.total_tasks) * 100)
}

function statusColor(status) {
  const map = { Backlog: '#9ca3af', 'To Do': '#3b82f6', 'In Progress': '#F59E0B', 'In Review': '#8b5cf6', Done: '#10b981' }
  return map[status] || '#9ca3af'
}

function statusKey(status) {
  return (status || '').toLowerCase().replace(/\s+/g, '-')
}

function formatCurrency(value) {
  return settingsStore.formatCurrency(value)
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}
</script>

<style scoped>
.project-dashboard {
  padding: 16px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-secondary); margin: 2px 0 0 0; }

.loading-container { display: flex; flex-direction: column; align-items: center; padding: 80px 0; }
.spinner { width: 40px; height: 40px; border: 3px solid var(--border-default); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { margin-top: 16px; color: var(--text-secondary); font-size: 14px; }

/* KPI Cards */
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
}

.kpi-label { display: block; font-size: 10px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.kpi-value { display: block; font-size: 22px; font-weight: 700; color: var(--text-primary); }
.kpi-green { color: var(--color-success); }
.kpi-orange { color: var(--color-warning); }
.kpi-red { color: var(--color-danger); }

/* Progress */
.progress-section { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; }
.progress-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.progress-label { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.progress-pct { font-size: 14px; font-weight: 700; color: var(--color-success); }
.progress-bar { height: 8px; background: var(--border-default); border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #10b981, #34d399); border-radius: 4px; transition: width 0.4s ease; }

/* Dashboard Grid */
.dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.dash-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px; }
.dash-card-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 12px 0; }

/* Status breakdown */
.status-breakdown { display: flex; flex-direction: column; gap: 10px; }
.status-row { display: flex; align-items: center; gap: 10px; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.status-name { font-size: 13px; color: var(--text-primary); width: 80px; }
.status-count { font-size: 13px; font-weight: 600; color: var(--text-primary); width: 30px; text-align: right; }
.status-bar-mini { flex: 1; height: 6px; background: var(--border-light); border-radius: 3px; overflow: hidden; }
.status-bar-mini-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }

/* Budget */
.budget-overview { display: flex; flex-direction: column; gap: 12px; }
.budget-row { display: flex; justify-content: space-between; }
.budget-label { font-size: 13px; color: var(--text-secondary); }
.budget-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.budget-negative { color: var(--color-danger); }
.budget-bar-wrap { margin-top: 4px; }
.budget-bar { height: 8px; background: var(--border-default); border-radius: 4px; overflow: hidden; }
.budget-bar-fill { height: 100%; background: var(--color-success); border-radius: 4px; transition: width 0.4s; }
.budget-bar-fill.over-budget { background: var(--color-danger); }

/* Sprints */
.sprint-list { display: flex; flex-direction: column; gap: 12px; }
.sprint-row { padding: 10px; background: var(--bg-surface-active); border-radius: 8px; }
.sprint-info { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.sprint-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.sprint-status { display: inline-flex; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600; }
.sprint-progress-row { display: flex; align-items: center; gap: 10px; }
.sprint-bar { flex: 1; height: 4px; background: var(--border-default); border-radius: 2px; overflow: hidden; }
.sprint-bar-fill { height: 100%; background: var(--color-success); border-radius: 2px; }
.sprint-pct { font-size: 11px; color: var(--text-secondary); white-space: nowrap; }

/* Team */
.team-list { display: flex; flex-direction: column; gap: 8px; }
.team-row { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; transition: background 0.1s; }
.team-row:hover { background: var(--bg-surface-active); }
.team-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--color-primary); color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.team-info { flex: 1; }
.team-name { display: block; font-size: 13px; font-weight: 500; color: var(--text-primary); }
.team-role { display: block; font-size: 11px; color: var(--text-tertiary); }
.team-hours { font-size: 13px; font-weight: 600; color: var(--text-primary); }

.no-data-text { text-align: center; color: var(--text-tertiary); font-size: 13px; padding: 20px 0; margin: 0; }

/* Status chips */
.chip-planning { background: var(--color-primary-bg); color: var(--color-primary); }
.chip-active { background: var(--color-success-bg); color: var(--color-success); }
.chip-on-hold { background: var(--color-warning-bg); color: var(--color-warning); }
.chip-completed { background: rgba(5, 150, 105, 0.1); color: var(--color-success-hover); }
.chip-planned { background: var(--color-primary-bg); color: var(--color-primary); }
.status-chip { display: inline-flex; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }

@media (max-width: 768px) {
  .kpi-cards { grid-template-columns: repeat(2, 1fr); }
  .dashboard-grid { grid-template-columns: 1fr; }
}
</style>
