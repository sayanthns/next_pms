<template>
  <div class="task-report-view">
    <div class="page-header">
      <h1 class="page-title">Task Report</h1>
      <p class="page-subtitle">Comprehensive task overview with filters</p>
    </div>

    <!-- Filters -->
    <div class="filters-card">
      <div class="filters-grid">
        <div class="filter-group filter-search">
          <label class="filter-label">Search Task</label>
          <input v-model="filters.search" type="text" class="filter-input" placeholder="Search by task name..." @input="onSearchInput" />
        </div>
        <div class="filter-group">
          <label class="filter-label">Project</label>
          <select v-model="filters.project" class="filter-select" @change="fetchReport">
            <option value="">All Projects</option>
            <option v-for="p in projectOptions" :key="p.name" :value="p.name">{{ p.project_name }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">User</label>
          <select v-model="filters.user" class="filter-select" @change="fetchReport">
            <option value="">All Users</option>
            <option v-for="u in userOptions" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">Status</label>
          <select v-model="filters.status" class="filter-select" @change="fetchReport">
            <option value="">All Statuses</option>
            <option value="Backlog">Backlog</option>
            <option value="To Do">To Do</option>
            <option value="In Progress">In Progress</option>
            <option value="In Review">In Review</option>
            <option value="Done">Done</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">Priority</label>
          <select v-model="filters.priority" class="filter-select" @change="fetchReport">
            <option value="">All Priorities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">Task Type</label>
          <select v-model="filters.task_type" class="filter-select" @change="fetchReport">
            <option value="">All Types</option>
            <option value="Feature">Feature</option>
            <option value="Bug">Bug</option>
            <option value="Improvement">Improvement</option>
            <option value="Research">Research</option>
            <option value="Documentation">Documentation</option>
            <option value="Meeting">Meeting</option>
            <option value="Bench Task">Bench Task</option>
            <option value="R&D Task">R&amp;D Task</option>
            <option value="Support">Support</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">From Date</label>
          <input v-model="filters.from_date" type="date" class="filter-input" @change="fetchReport" />
        </div>
        <div class="filter-group">
          <label class="filter-label">To Date</label>
          <input v-model="filters.to_date" type="date" class="filter-input" @change="fetchReport" />
        </div>
        <div class="filter-group filter-actions">
          <button class="btn btn-outline btn-sm" @click="clearFilters">Clear Filters</button>
        </div>
      </div>
    </div>

    <!-- Summary Cards -->
    <div v-if="summary" class="summary-row">
      <div class="summary-card">
        <span class="summary-label">Total Tasks</span>
        <span class="summary-value">{{ summary.total_tasks }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Estimated Hours</span>
        <span class="summary-value">{{ summary.total_estimated_hours }}h</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Actual Hours</span>
        <span class="summary-value">{{ summary.total_actual_hours }}h</span>
      </div>
      <div class="summary-card" v-if="settingsStore.canViewFinance">
        <span class="summary-label">Total Cost</span>
        <span class="summary-value">{{ formatCurrency(summary.total_cost) }}</span>
      </div>
    </div>

    <!-- Status Breakdown -->
    <div v-if="summary && summary.status_breakdown" class="status-breakdown-row">
      <div v-for="(count, status) in summary.status_breakdown" :key="status" class="status-chip" :class="statusChipClass(status)">
        {{ status }}: {{ count }}
      </div>
    </div>

    <!-- Task Table -->
    <div class="report-card">
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
        <p class="loading-text">Loading report...</p>
      </div>
      <div v-else-if="error" class="empty-state">
        <p class="empty-text" style="color:#dc2626">{{ error }}</p>
        <button class="btn btn-outline btn-sm" @click="fetchReport" style="margin-top:8px">Retry</button>
      </div>
      <div v-else-if="!tasks.length" class="empty-state">
        <p class="empty-text">No tasks found matching the filters.</p>
      </div>
      <div v-else class="table-wrap">
        <table class="report-table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Project</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Type</th>
              <th>Assignees</th>
              <th>Due Date</th>
              <th>Est. Hours</th>
              <th>Actual Hours</th>
              <th v-if="settingsStore.canViewFinance">Cost</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.name">
              <td>
                <router-link :to="`/task/${task.name}`" class="task-link">{{ task.task_title }}</router-link>
              </td>
              <td>
                <router-link v-if="task.project" :to="`/project/${task.project}`" class="project-link">{{ task.project_name }}</router-link>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <span class="status-badge" :class="statusBadgeClass(task.status)">{{ task.status }}</span>
              </td>
              <td>
                <span class="priority-badge" :class="priorityClass(task.priority)">{{ task.priority }}</span>
              </td>
              <td>
                <span v-if="task.task_type" class="type-badge">{{ task.task_type }}</span>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="assignee-cell">{{ task.assignee_names || '-' }}</td>
              <td class="text-nowrap">{{ formatDate(task.due_date) || '-' }}</td>
              <td class="text-right">{{ task.estimated_hours || '-' }}</td>
              <td class="text-right">{{ task.actual_hours || '-' }}</td>
              <td v-if="settingsStore.canViewFinance" class="text-right">{{ task.calculated_cost ? formatCurrency(task.calculated_cost) : '-' }}</td>
              <td class="text-nowrap">{{ formatDate(task.creation) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { call, getList } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'

const settingsStore = useSettingsStore()

const loading = ref(true)
const tasks = ref([])
const summary = ref(null)
const error = ref(null)
const projectOptions = ref([])
const userOptions = ref([])

// Default dates to today
const today = new Date().toISOString().slice(0, 10)

const filters = reactive({
  search: '',
  project: '',
  user: '',
  status: '',
  priority: '',
  task_type: '',
  from_date: today,
  to_date: today,
})

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchReport(), 400)
}

onMounted(async () => {
  // Load filter options and report in parallel
  Promise.all([loadFilterOptions(), fetchReport()])
})

async function loadFilterOptions() {
  try {
    const [projects, users] = await Promise.all([
      getList('PMS Project', { fields: ['name', 'project_name'], orderBy: 'project_name asc', limit: 0 }),
      call('next_pms.api.crud.get_all_users'),
    ])
    projectOptions.value = projects
    userOptions.value = users
  } catch (e) {
    console.error('Failed to load filter options:', e)
  }
}

async function fetchReport() {
  loading.value = true
  error.value = null
  try {
    const activeFilters = {}
    Object.entries(filters).forEach(([k, v]) => { if (v) activeFilters[k] = v })

    const data = await call('next_pms.api.crud.get_task_report', {
      filters: JSON.stringify(activeFilters),
    })
    tasks.value = data.tasks || []
    summary.value = data.summary || null
  } catch (err) {
    console.error('Failed to fetch task report:', err)
    error.value = err.message || 'Failed to load report'
    tasks.value = []
    summary.value = null
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  filters.search = ''
  filters.project = ''
  filters.user = ''
  filters.status = ''
  filters.priority = ''
  filters.task_type = ''
  filters.from_date = today
  filters.to_date = today
  fetchReport()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatCurrency(val) {
  if (!val) return '₹0'
  return '₹' + Number(val).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function statusBadgeClass(status) {
  const map = {
    'Backlog': 'badge-backlog', 'To Do': 'badge-todo', 'In Progress': 'badge-progress',
    'In Review': 'badge-review', 'Done': 'badge-done', 'Cancelled': 'badge-cancelled',
  }
  return map[status] || ''
}

function statusChipClass(status) {
  const map = {
    'Backlog': 'chip-backlog', 'To Do': 'chip-todo', 'In Progress': 'chip-progress',
    'In Review': 'chip-review', 'Done': 'chip-done', 'Cancelled': 'chip-cancelled',
  }
  return map[status] || ''
}

function priorityClass(priority) {
  const map = { 'Critical': 'priority-critical', 'High': 'priority-high', 'Medium': 'priority-medium', 'Low': 'priority-low' }
  return map[priority] || ''
}
</script>

<style scoped>
.task-report-view { padding: 16px 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 12px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-subtitle { font-size: 14px; color: var(--text-secondary); margin-top: 4px; }

/* Filters */
.filters-card { background: var(--bg-surface); border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 1px 3px var(--shadow-sm); }
.filters-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; align-items: end; }
.filter-label { display: block; font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; }
.filter-select, .filter-input {
  width: 100%; padding: 7px 10px; border: 1px solid var(--border-default); border-radius: 6px;
  font-size: 13px; color: var(--text-primary); background: var(--bg-surface);
}
.filter-select:focus, .filter-input:focus { outline: none; border-color: var(--color-primary); box-shadow: 0 0 0 2px var(--color-primary-bg); }
.filter-search { grid-column: span 2; }
.filter-actions { display: flex; align-items: flex-end; }

/* Summary */
.summary-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 16px; }
.summary-card { background: var(--bg-surface); border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px var(--shadow-sm); }
.summary-label { display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; }
.summary-value { font-size: 24px; font-weight: 700; color: var(--text-primary); margin-top: 4px; display: block; }

/* Status Breakdown Row */
.status-breakdown-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.status-chip { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.chip-backlog { background: #f1f5f9; color: #64748b; }
.chip-todo { background: #dbeafe; color: #2563eb; }
.chip-progress { background: #fef3c7; color: #d97706; }
.chip-review { background: #ede9fe; color: #7c3aed; }
.chip-done { background: #dcfce7; color: #16a34a; }
.chip-cancelled { background: #fef2f2; color: #dc2626; }

/* Table */
.report-card { background: var(--bg-surface); border-radius: 10px; box-shadow: 0 1px 3px var(--shadow-sm); overflow: hidden; }
.table-wrap { overflow-x: auto; }
.report-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.report-table th { padding: 10px 12px; text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid var(--border-default); white-space: nowrap; }
.report-table td { padding: 10px 12px; border-bottom: 1px solid var(--border-light); color: var(--text-primary); vertical-align: middle; }
.report-table tr:hover { background: var(--bg-surface-hover); }

.task-link { color: var(--color-primary); text-decoration: none; font-weight: 500; }
.task-link:hover { text-decoration: underline; }
.project-link { color: var(--text-secondary); text-decoration: none; font-size: 12px; }
.project-link:hover { color: var(--color-primary); }
.text-muted { color: var(--text-tertiary); }
.text-nowrap { white-space: nowrap; }
.text-right { text-align: right; }
.assignee-cell { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }

/* Badges */
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.badge-backlog { background: #f1f5f9; color: #64748b; }
.badge-todo { background: #dbeafe; color: #2563eb; }
.badge-progress { background: #fef3c7; color: #d97706; }
.badge-review { background: #ede9fe; color: #7c3aed; }
.badge-done { background: #dcfce7; color: #16a34a; }
.badge-cancelled { background: #fef2f2; color: #dc2626; }

.priority-badge { font-size: 11px; font-weight: 600; }
.priority-critical { color: #dc2626; }
.priority-high { color: #ea580c; }
.priority-medium { color: #d97706; }
.priority-low { color: #64748b; }

.type-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: var(--color-primary-bg); color: var(--color-primary); }

.loading-container { padding: 60px 0; text-align: center; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--border-default); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.6s linear infinite; margin: 0 auto 12px; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { color: var(--text-tertiary); font-size: 14px; }
.empty-state { padding: 60px 0; text-align: center; }
.empty-text { color: var(--text-tertiary); font-size: 14px; }

.btn { padding: 7px 14px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; }
.btn-outline { background: transparent; border: 1px solid var(--border-default); color: var(--text-secondary); }
.btn-outline:hover { background: var(--bg-surface-active); border-color: var(--border-default); }
.btn-sm { padding: 5px 10px; font-size: 12px; }

@media (max-width: 768px) {
  .filters-grid { grid-template-columns: 1fr 1fr; }
  .summary-row { grid-template-columns: 1fr 1fr; }
}
</style>
