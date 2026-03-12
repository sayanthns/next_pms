<template>
  <div class="reports-view">
    <div v-if="!embedded" class="page-header">
      <div>
        <h1 class="page-title">Reports</h1>
        <p class="page-subtitle">Project analytics and insights</p>
      </div>
    </div>

    <!-- Project Selector (shown if no projectId prop and not embedded) -->
    <div v-if="!selectedProject && !embedded" class="project-selector-bar">
      <div class="selector-row">
        <label class="selector-label">Project</label>
        <select
          v-if="projectOptions.length"
          v-model="pickedProject"
          class="selector-dropdown"
          @change="selectProject"
        >
          <option value="" disabled>Select a project to view reports...</option>
          <option
            v-for="p in projectOptions"
            :key="p.name"
            :value="p.name"
          >
            {{ p.project_name || p.name }}
          </option>
        </select>
        <div v-else-if="projectsLoading" class="selector-loading-inline">
          <div class="spinner-sm"></div>
          <span>Loading projects...</span>
        </div>
        <p v-else class="no-projects-inline">No projects found.</p>
      </div>
      <!-- Placeholder content when no project selected -->
      <div class="reports-placeholder">
        <div class="placeholder-grid">
          <div class="placeholder-card" v-for="i in 4" :key="i">
            <div class="placeholder-icon"></div>
            <div class="placeholder-lines">
              <div class="placeholder-line short"></div>
              <div class="placeholder-line long"></div>
            </div>
          </div>
        </div>
        <div class="placeholder-sections">
          <div class="placeholder-section" v-for="i in 3" :key="i">
            <div class="placeholder-line short"></div>
            <div class="placeholder-bar-group">
              <div class="placeholder-bar" v-for="j in 5" :key="j" :style="{ width: (90 - j * 12) + '%' }"></div>
            </div>
          </div>
        </div>
        <div class="placeholder-overlay">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          <p>Select a project above to view analytics</p>
        </div>
      </div>
    </div>

    <!-- Dashboard Content -->
    <template v-else>
      <!-- Project switcher bar (only when standalone, not embedded) -->
      <div v-if="!embedded" class="project-switcher-bar">
        <select v-model="switchProject" class="switcher-dropdown" @change="onSwitchProject">
          <option v-for="p in projectOptions" :key="p.name" :value="p.name">{{ p.project_name || p.name }}</option>
        </select>
      </div>
      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
        <p class="loading-text">Loading dashboard...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-container">
        <p class="error-text">{{ error }}</p>
        <button class="btn btn-primary" @click="loadDashboard">Retry</button>
      </div>

      <!-- Dashboard -->
      <div v-else-if="dashboard" class="dashboard-content">
        <!-- Summary Cards -->
        <div class="summary-grid">
          <div class="summary-card">
            <div class="summary-icon icon-tasks">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
              </svg>
            </div>
            <div class="summary-data">
              <span class="summary-value">{{ dashboard.total_tasks || 0 }}</span>
              <span class="summary-label">Total Tasks</span>
            </div>
          </div>

          <div class="summary-card">
            <div class="summary-icon icon-hours">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="summary-data">
              <span class="summary-value">{{ formatHours(dashboard.total_hours || dashboard.total_actual_hours) }}</span>
              <span class="summary-label">Total Hours</span>
            </div>
          </div>

          <div class="summary-card">
            <div class="summary-icon icon-cost">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="1" x2="12" y2="23"/>
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              </svg>
            </div>
            <div class="summary-data">
              <span class="summary-value">{{ formatCurrency(dashboard.total_cost) }}</span>
              <span class="summary-label">Total Cost</span>
            </div>
          </div>

          <div class="summary-card">
            <div class="summary-icon icon-budget">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div class="summary-data">
              <span class="summary-value">{{ budgetUtilization }}%</span>
              <span class="summary-label">Budget Utilization</span>
            </div>
          </div>
        </div>

        <!-- Budget Widget -->
        <div class="section-card" v-if="dashboard.total_budget">
          <h3 class="section-title">Budget Overview</h3>
          <BudgetWidget
            :totalBudget="dashboard.total_budget || 0"
            :usedBudget="dashboard.used_budget || dashboard.calculated_cost || dashboard.total_cost || 0"
            :utilization="budgetUtilization"
          />
        </div>

        <!-- Task Status Breakdown -->
        <div class="section-card">
          <h3 class="section-title">Task Status Breakdown</h3>
          <div v-if="statusBreakdown.length" class="breakdown-table-wrap">
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th class="text-right">Count</th>
                  <th class="text-right">Percentage</th>
                  <th>Distribution</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in statusBreakdown" :key="row.status">
                  <td>
                    <div class="status-cell">
                      <span class="status-dot" :style="{ background: row.color }"></span>
                      {{ row.status }}
                    </div>
                  </td>
                  <td class="text-right">{{ row.count }}</td>
                  <td class="text-right">{{ row.percentage }}%</td>
                  <td>
                    <div class="bar-cell">
                      <div
                        class="bar-fill"
                        :style="{ width: row.percentage + '%', background: row.color }"
                      ></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="no-data-text">No task data available.</p>
        </div>

        <!-- Team Cost Breakdown -->
        <div class="section-card" v-if="teamCostBreakdown.length">
          <h3 class="section-title">Team Cost Breakdown</h3>
          <div class="breakdown-table-wrap">
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Role</th>
                  <th class="text-right">Rate</th>
                  <th class="text-right">Hours</th>
                  <th class="text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="member in teamCostBreakdown" :key="member.member">
                  <td>
                    <div class="member-cell">
                      <span class="mini-avatar" :style="{ background: getAvatarColor(member.member) }">
                        {{ getInitials(member.member) }}
                      </span>
                      {{ member.member }}
                    </div>
                  </td>
                  <td>{{ member.role || '-' }}</td>
                  <td class="text-right">{{ formatCurrency(member.rate) }}</td>
                  <td class="text-right">{{ formatHours(member.hours) }}</td>
                  <td class="text-right font-semibold">{{ formatCurrency(member.cost) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Hours Overview -->
        <div class="section-card">
          <h3 class="section-title">Hours Overview</h3>
          <div class="hours-grid">
            <div class="hours-item">
              <span class="hours-label">Estimated</span>
              <span class="hours-val">{{ formatHours(dashboard.total_estimated_hours) }}h</span>
            </div>
            <div class="hours-item">
              <span class="hours-label">Actual</span>
              <span class="hours-val">{{ formatHours(dashboard.total_actual_hours || dashboard.total_hours) }}h</span>
            </div>
            <div class="hours-item">
              <span class="hours-label">Variance</span>
              <span class="hours-val" :class="hoursVarianceClass">{{ hoursVariance }}</span>
            </div>
            <div class="hours-item">
              <span class="hours-label">Completion Rate</span>
              <span class="hours-val">{{ completionRate }}%</span>
            </div>
          </div>
          <div class="hours-bar-section">
            <div class="hours-bar-label">
              <span>Estimated</span>
              <span>{{ formatHours(dashboard.total_estimated_hours) }}h</span>
            </div>
            <div class="hours-bar"><div class="hours-bar-fill est-bar" style="width: 100%"></div></div>
            <div class="hours-bar-label">
              <span>Actual</span>
              <span>{{ formatHours(dashboard.total_actual_hours || dashboard.total_hours) }}h</span>
            </div>
            <div class="hours-bar"><div class="hours-bar-fill actual-bar" :style="{ width: actualHoursBarWidth + '%' }"></div></div>
          </div>
        </div>

        <!-- Priority Distribution -->
        <div class="section-card" v-if="statusBreakdown.length">
          <h3 class="section-title">Task Distribution Summary</h3>
          <div class="dist-stats">
            <div class="dist-stat">
              <span class="dist-stat-val">{{ dashboard.total_tasks || 0 }}</span>
              <span class="dist-stat-label">Total Tasks</span>
            </div>
            <div class="dist-stat">
              <span class="dist-stat-val text-success">{{ (dashboard.task_counts || {}).Done || 0 }}</span>
              <span class="dist-stat-label">Completed</span>
            </div>
            <div class="dist-stat">
              <span class="dist-stat-val text-warning">{{ ((dashboard.task_counts || {})['In Progress'] || 0) + ((dashboard.task_counts || {})['In Review'] || 0) }}</span>
              <span class="dist-stat-label">In Progress</span>
            </div>
            <div class="dist-stat">
              <span class="dist-stat-val text-muted">{{ ((dashboard.task_counts || {}).Backlog || 0) + ((dashboard.task_counts || {})['To Do'] || 0) }}</span>
              <span class="dist-stat-label">Pending</span>
            </div>
          </div>
        </div>

        <!-- Sprint Progress -->
        <div class="section-card" v-if="sprintProgress.length">
          <h3 class="section-title">Sprint Progress</h3>
          <div class="sprint-list">
            <div
              v-for="sprint in sprintProgress"
              :key="sprint.name"
              class="sprint-progress-item"
            >
              <div class="sprint-progress-header">
                <div class="sprint-name-row">
                  <span class="sprint-name">{{ sprint.sprint_name || sprint.name }}</span>
                  <span
                    class="status-badge"
                    :class="sprintStatusClass(sprint.status)"
                  >
                    {{ sprint.status }}
                  </span>
                </div>
                <span class="sprint-pct">{{ sprint.progress }}%</span>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: sprint.progress + '%' }"
                ></div>
              </div>
              <div class="sprint-meta">
                <span>{{ sprint.completed }} / {{ sprint.total }} tasks completed</span>
                <span v-if="sprint.start_date">
                  {{ formatDate(sprint.start_date) }} - {{ formatDate(sprint.end_date) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/store/projects'
import { useSettingsStore } from '@/store/settings'
import { getList } from '@/utils/frappe'
import BudgetWidget from '@/components/BudgetWidget.vue'

const props = defineProps({
  projectId: {
    type: String,
    default: '',
  },
  embedded: { type: Boolean, default: false },
})

const router = useRouter()
const projectStore = useProjectStore()
const settingsStore = useSettingsStore()

const projectOptions = ref([])
const projectsLoading = ref(false)
const pickedProject = ref('')
const selectedProject = ref(props.projectId || '')
const switchProject = ref(props.projectId || '')
const dashboard = ref(null)
const loading = ref(false)
const error = ref(null)

const statusColorMap = {
  'Backlog': '#9ca3af',
  'To Do': '#3b82f6',
  'In Progress': '#F59E0B',
  'In Review': '#8b5cf6',
  'Done': '#10b981',
  'Cancelled': '#EF4444',
}

onMounted(async () => {
  // Always load project options for switcher
  loadProjectOptions()
  if (props.projectId) {
    selectedProject.value = props.projectId
    switchProject.value = props.projectId
    await loadDashboard()
  }
})

watch(() => props.projectId, async (newVal) => {
  if (newVal) {
    selectedProject.value = newVal
    await loadDashboard()
  }
})

async function loadProjectOptions() {
  projectsLoading.value = true
  try {
    projectOptions.value = await getList('PMS Project', {
      fields: ['name', 'project_name', 'status'],
      filters: {},
      orderBy: 'modified desc',
      limit: 0,
    })
    // Auto-select first project if none selected
    if (!selectedProject.value && !props.projectId && projectOptions.value.length) {
      const first = projectOptions.value[0]
      pickedProject.value = first.name
      selectedProject.value = first.name
      switchProject.value = first.name
      loadDashboard()
    }
  } catch (e) {
    console.error('Failed to fetch projects:', e)
    projectOptions.value = []
  } finally {
    projectsLoading.value = false
  }
}

function selectProject() {
  if (!pickedProject.value) return
  selectedProject.value = pickedProject.value
  switchProject.value = pickedProject.value
  loadDashboard()
}

function onSwitchProject() {
  if (!switchProject.value) return
  selectedProject.value = switchProject.value
  loadDashboard()
}

async function loadDashboard() {
  loading.value = true
  error.value = null
  try {
    dashboard.value = await projectStore.fetchDashboard(selectedProject.value)
    if (!dashboard.value) {
      error.value = 'No dashboard data returned.'
    }
  } catch (e) {
    console.error('Failed to load dashboard:', e)
    error.value = 'Failed to load dashboard data. Please try again.'
  } finally {
    loading.value = false
  }
}

const budgetUtilization = computed(() => {
  if (!dashboard.value) return 0
  if (dashboard.value.budget_utilization !== undefined) {
    return Math.round(dashboard.value.budget_utilization)
  }
  const budget = dashboard.value.total_budget
  const used = dashboard.value.used_budget || dashboard.value.total_cost || 0
  if (!budget) return 0
  return Math.round((used / budget) * 100)
})

const statusBreakdown = computed(() => {
  if (!dashboard.value) return []
  // API returns task_counts; fallback to status_breakdown
  const breakdown = dashboard.value.task_counts || dashboard.value.status_breakdown
  if (!breakdown) return []
  const total = dashboard.value.total_tasks || Object.values(breakdown).reduce((s, v) => s + v, 0)
  if (!total) return []
  return Object.entries(breakdown).map(([status, count]) => ({
    status,
    count,
    percentage: Math.round((count / total) * 100),
    color: statusColorMap[status] || '#9ca3af',
  }))
})

const teamCostBreakdown = computed(() => {
  if (!dashboard.value) return []
  // API returns team_members; fallback to team_cost_breakdown
  const members = dashboard.value.team_members || dashboard.value.team_cost_breakdown
  if (!members) return []
  return members.map((m) => ({
    member: m.user || m.member,
    role: m.role || '-',
    rate: m.hourly_rate || m.rate || 0,
    hours: m.total_hours || m.hours || 0,
    cost: m.total_cost || m.cost || 0,
  }))
})

const sprintProgress = computed(() => {
  if (!dashboard.value) return []
  // API returns sprints; fallback to sprint_progress
  const sprints = dashboard.value.sprints || dashboard.value.sprint_progress
  if (!sprints) return []
  return sprints.map((s) => ({
    ...s,
    completed: s.done_tasks ?? s.completed ?? 0,
    total: s.total_tasks ?? s.total ?? 0,
    progress: (s.total_tasks || s.total)
      ? Math.round(((s.done_tasks ?? s.completed ?? 0) / (s.total_tasks ?? s.total)) * 100)
      : 0,
  }))
})

const hoursVariance = computed(() => {
  if (!dashboard.value) return '0h'
  const est = dashboard.value.total_estimated_hours || 0
  const act = dashboard.value.total_actual_hours || dashboard.value.total_hours || 0
  const diff = act - est
  const sign = diff > 0 ? '+' : ''
  return `${sign}${diff.toFixed(1)}h`
})

const hoursVarianceClass = computed(() => {
  if (!dashboard.value) return ''
  const est = dashboard.value.total_estimated_hours || 0
  const act = dashboard.value.total_actual_hours || dashboard.value.total_hours || 0
  return act > est ? 'text-danger' : 'text-success'
})

const actualHoursBarWidth = computed(() => {
  if (!dashboard.value) return 0
  const est = dashboard.value.total_estimated_hours || 1
  const act = dashboard.value.total_actual_hours || dashboard.value.total_hours || 0
  return Math.min(100, Math.round((act / est) * 100))
})

const completionRate = computed(() => {
  if (!dashboard.value || !dashboard.value.total_tasks) return 0
  const done = (dashboard.value.task_counts || {}).Done || 0
  return Math.round((done / dashboard.value.total_tasks) * 100)
})

function formatHours(val) {
  if (!val && val !== 0) return '-'
  return Number(val).toFixed(1)
}

function formatCurrency(value) {
  return settingsStore.formatCurrency(value)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getInitials(email) {
  if (!email) return '?'
  const name = email.split('@')[0]
  const parts = name.split(/[._-]/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function getAvatarColor(email) {
  const colors = [
    '#2563EB', '#14b8a6', '#F59E0B', '#EF4444',
    '#3b82f6', '#8b5cf6', '#ec4899', '#10b981',
  ]
  let hash = 0
  for (let i = 0; i < (email || '').length; i++) {
    hash = email.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function sprintStatusClass(status) {
  const map = {
    'Planning': 'badge-default',
    'Active': 'badge-success',
    'In Progress': 'badge-success',
    'Completed': 'badge-primary',
    'Closed': 'badge-default',
  }
  return map[status] || 'badge-default'
}
</script>

<style scoped>
.reports-view {
  padding: 16px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 4px 0 0 0;
}

/* Project Selector - Full width bar */
.project-selector-bar {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
}

.selector-label {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  white-space: nowrap;
}

.selector-dropdown {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  color: #374151;
  background: #f9fafb;
  outline: none;
  cursor: pointer;
}

.selector-dropdown:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.selector-loading-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.no-projects-inline {
  color: #9ca3af;
  font-size: 14px;
  margin: 0;
}

/* Placeholder when no project selected */
.reports-placeholder {
  position: relative;
  opacity: 0.4;
}

.placeholder-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.placeholder-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.placeholder-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #f3f4f6;
  flex-shrink: 0;
}

.placeholder-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.placeholder-line {
  height: 10px;
  background: #f3f4f6;
  border-radius: 4px;
}

.placeholder-line.short { width: 50%; }
.placeholder-line.long { width: 80%; }

.placeholder-sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.placeholder-section {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
}

.placeholder-bar-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.placeholder-bar {
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
}

.placeholder-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(248, 249, 250, 0.6);
  border-radius: 12px;
}

.placeholder-overlay p {
  font-size: 15px;
  color: #6b7280;
  font-weight: 500;
  margin: 0;
}

/* Project Switcher Bar (when project already selected) */
.project-switcher-bar {
  margin-bottom: 16px;
}

.switcher-dropdown {
  padding: 8px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  color: #374151;
  background: #fff;
  outline: none;
  cursor: pointer;
  min-width: 260px;
}

.switcher-dropdown:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-primary {
  background: #2563EB;
  color: #fff;
}

.btn-primary:hover {
  background: #1D4ED8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #2563EB;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-sm {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top-color: #2563EB;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: #6b7280;
  font-size: 14px;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
}

.error-text {
  color: #EF4444;
  font-size: 14px;
  margin-bottom: 16px;
}

/* Dashboard Content */
.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Summary Grid */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.summary-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.summary-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-tasks {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.icon-hours {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.icon-cost {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.icon-budget {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.summary-data {
  display: flex;
  flex-direction: column;
}

.summary-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.summary-label {
  font-size: 13px;
  color: #6b7280;
  margin-top: 2px;
}

/* Section Card */
.section-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px 0;
}

/* Tables */
.breakdown-table-wrap {
  overflow-x: auto;
}

.breakdown-table {
  width: 100%;
  border-collapse: collapse;
}

.breakdown-table thead {
  background: #f9fafb;
}

.breakdown-table th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #e5e7eb;
}

.breakdown-table td {
  padding: 12px 14px;
  font-size: 14px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
}

.text-right {
  text-align: right;
}

.font-semibold {
  font-weight: 600;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bar-cell {
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
  min-width: 80px;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.member-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.no-data-text {
  color: #9ca3af;
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
  margin: 0;
}

/* Sprint Progress */
.sprint-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sprint-progress-item {
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.sprint-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sprint-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sprint-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}

.sprint-pct {
  font-size: 14px;
  font-weight: 700;
  color: #10b981;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 4px;
  transition: width 0.4s ease;
}

.sprint-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #9ca3af;
}

/* Badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-primary {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.badge-danger {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.badge-default {
  background: #f3f4f6;
  color: #6b7280;
}

/* Hours Overview */
.hours-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.hours-item {
  background: #f9fafb;
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}

.hours-label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.hours-val {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}

.hours-bar-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hours-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
}

.hours-bar {
  height: 10px;
  background: #f3f4f6;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 8px;
}

.hours-bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.4s ease;
}

.est-bar { background: #2563EB; }
.actual-bar { background: #10b981; }

/* Distribution Stats */
.dist-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.dist-stat {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.dist-stat-val {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.dist-stat-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.text-success { color: #10b981; }
.text-warning { color: #F59E0B; }
.text-danger { color: #EF4444; }
.text-muted { color: #6b7280; }

@media (max-width: 768px) {
  .hours-grid, .dist-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
