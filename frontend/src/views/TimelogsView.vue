<template>
  <div class="timelogs-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Time Logs</h1>
        <p class="page-subtitle">Track and manage time entries across projects</p>
      </div>
    </div>

    <!-- Active Timers Section (Admin/PM only, and view_all_timelogs enabled) -->
    <div v-if="filterOptions.is_admin && canViewAllTimelogs && activeTimers.length" class="active-timers-section">
      <h3 class="section-label">
        <span class="live-dot"></span>
        Active Timers ({{ activeTimers.length }})
      </h3>
      <div class="active-timers-grid">
        <div v-for="timer in activeTimers" :key="timer.name" class="active-timer-card">
          <div class="timer-card-top">
            <span class="timer-user-avatar">{{ getInitials(timer.user_full_name) }}</span>
            <div class="timer-user-info">
              <span class="timer-user-name">{{ timer.user_full_name }}</span>
              <span class="timer-user-email">{{ timer.user }}</span>
            </div>
          </div>
          <div class="timer-card-task">
            <router-link :to="`/task/${timer.task}`" class="timer-task-link">{{ timer.task_title }}</router-link>
            <router-link v-if="timer.project" :to="`/project/${timer.project}`" class="timer-project-tag">{{ timer.project }}</router-link>
          </div>
          <div class="timer-card-elapsed">
            <span class="live-dot"></span>
            {{ formatElapsed(timer.elapsed_seconds) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filters-left">
        <select v-if="filterOptions.is_admin && canViewAllTimelogs" v-model="filters.user" class="filter-select" @change="fetchLogs">
          <option value="">All Users</option>
          <option v-for="u in filterOptions.users" :key="u.user" :value="u.user">{{ u.full_name || u.user }}</option>
        </select>
        <select v-model="filters.project" class="filter-select" @change="onProjectChange">
          <option value="">All Projects</option>
          <option v-for="p in filterOptions.projects" :key="p.project" :value="p.project">{{ p.project_name }}</option>
        </select>
        <select v-model="filters.task" class="filter-select" @change="fetchLogs">
          <option value="">All Tasks</option>
          <option v-for="t in projectTasks" :key="t.name" :value="t.name">{{ t.task_title }}</option>
        </select>
        <input v-model="filters.from_date" type="date" class="filter-input" @change="fetchLogs" placeholder="From" />
        <input v-model="filters.to_date" type="date" class="filter-input" @change="fetchLogs" placeholder="To" />
      </div>
      <div class="filters-right">
        <button class="btn-filter-clear" @click="clearFilters">Clear</button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="summary-row" v-if="logs.length">
      <div class="summary-card">
        <span class="summary-label">Total Entries</span>
        <span class="summary-value">{{ totalCount }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Total Hours</span>
        <span class="summary-value">{{ totalHours.toFixed(1) }}h</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Running</span>
        <span class="summary-value">{{ runningCount }}</span>
      </div>
    </div>

    <!-- Time Logs Table -->
    <div class="logs-card">
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
        <p class="loading-text">Loading time logs...</p>
      </div>
      <div v-else-if="!logs.length" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <p class="empty-text">No time logs found</p>
        <p class="empty-subtext">Start a timer on any task to begin tracking time</p>
      </div>
      <div v-else class="table-wrap">
        <table class="logs-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Task</th>
              <th>Project</th>
              <th>Start</th>
              <th>End</th>
              <th>Duration</th>
              <th>Notes</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.name" :class="{ 'row-running': log.is_running }">
              <td>
                <div class="user-cell">
                  <span class="user-avatar-sm">{{ getInitials(log.user_full_name) }}</span>
                  <span class="user-name-text">{{ log.user_full_name }}</span>
                </div>
              </td>
              <td>
                <router-link :to="`/task/${log.task}`" class="task-link">{{ log.task_title }}</router-link>
              </td>
              <td>
                <router-link v-if="log.project" :to="`/project/${log.project}`" class="project-link">{{ log.project }}</router-link>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="text-nowrap">{{ formatDateTime(log.start_time) }}</td>
              <td class="text-nowrap">
                <span v-if="log.is_running" class="running-badge">
                  <span class="live-dot"></span> Running
                </span>
                <span v-else>{{ log.end_time ? formatDateTime(log.end_time) : '-' }}</span>
              </td>
              <td class="text-nowrap">
                <span v-if="log.duration_hours || log.duration_minutes">
                  {{ log.duration_hours || 0 }}h {{ log.duration_minutes ? (log.duration_minutes % 60) : 0 }}m
                </span>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <span class="notes-text">{{ log.notes || '-' }}</span>
              </td>
              <td>
                <span v-if="log.is_running" class="status-tag tag-running">Running</span>
                <span v-else class="status-tag tag-completed">Completed</span>
              </td>
              <td>
                <button
                  v-if="canDeleteTimelog(log)"
                  class="tl-delete-btn"
                  @click="handleDeleteTimelog(log)"
                  title="Delete time log"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalCount > pageSize" class="pagination">
        <button class="btn-page" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">&laquo; Prev</button>
        <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
        <button class="btn-page" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">Next &raquo;</button>
      </div>
    </div>
    <!-- Delete Confirmation -->
    <ConfirmDialog
      :show="showDeleteTimelogConfirm"
      title="Delete Time Log"
      message="Are you sure you want to delete this time log? This action cannot be undone."
      confirmLabel="Delete"
      :confirmDanger="true"
      :loading="deletingTimelog"
      @confirm="confirmDeleteTimelog"
      @cancel="showDeleteTimelogConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { call, getList } from '@/utils/frappe'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useSettingsStore } from '@/store/settings'

const settingsStore = useSettingsStore()

const loading = ref(false)
const logs = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = 30
const activeTimers = ref([])
const projectTasks = ref([])

// Delete timelog state
const showDeleteTimelogConfirm = ref(false)
const deletingTimelog = ref(false)
const timelogToDelete = ref(null)

const filterOptions = reactive({
  users: [],
  projects: [],
  is_admin: false,
})

const filters = reactive({
  user: '',
  project: '',
  task: '',
  from_date: '',
  to_date: '',
})

const canViewAllTimelogs = computed(() => settingsStore.featurePermissions.view_all_timelogs !== false)

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize))

const totalHours = computed(() => {
  return logs.value.reduce((sum, log) => sum + (log.duration_hours || 0), 0)
})

const runningCount = computed(() => {
  return logs.value.filter(l => l.is_running).length
})

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatElapsed(seconds) {
  if (!seconds) return '00:00:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

async function fetchFilterOptions() {
  try {
    const data = await call('next_pms.api.timer.get_timelog_filters')
    filterOptions.users = data.users || []
    filterOptions.projects = data.projects || []
    filterOptions.is_admin = data.is_admin || false
  } catch (err) {
    console.error('Failed to fetch filter options:', err)
  }
}

async function fetchLogs() {
  loading.value = true
  try {
    const activeFilters = {}
    if (filters.user) activeFilters.user = filters.user
    if (filters.project) activeFilters.project = filters.project
    if (filters.task) activeFilters.task = filters.task
    if (filters.from_date) activeFilters.from_date = filters.from_date
    if (filters.to_date) activeFilters.to_date = filters.to_date

    const data = await call('next_pms.api.timer.get_all_timelogs', {
      filters: JSON.stringify(activeFilters),
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
    })
    logs.value = data.logs || []
    totalCount.value = data.total || 0
  } catch (err) {
    console.error('Failed to fetch time logs:', err)
    logs.value = []
  } finally {
    loading.value = false
  }
}

async function fetchActiveTimers() {
  if (!filterOptions.is_admin) return
  try {
    activeTimers.value = await call('next_pms.api.timer.get_active_timers')
  } catch {
    activeTimers.value = []
  }
}

async function onProjectChange() {
  filters.task = ''
  projectTasks.value = []
  if (filters.project) {
    try {
      projectTasks.value = await getList('PMS Task', {
        fields: ['name', 'task_title'],
        filters: { project: filters.project },
        orderBy: 'task_title asc',
        limit: 0,
      })
    } catch {
      projectTasks.value = []
    }
  }
  fetchLogs()
}

function clearFilters() {
  filters.user = ''
  filters.project = ''
  filters.task = ''
  filters.from_date = ''
  filters.to_date = ''
  projectTasks.value = []
  currentPage.value = 1
  fetchLogs()
}

function goToPage(page) {
  currentPage.value = page
  fetchLogs()
}

function canDeleteTimelog(log) {
  if (filterOptions.is_admin) return true
  const currentUser = window.frappe?.session?.user || window.pms_boot?.user || ''
  return log.user === currentUser
}

function handleDeleteTimelog(log) {
  timelogToDelete.value = log
  showDeleteTimelogConfirm.value = true
}

async function confirmDeleteTimelog() {
  if (!timelogToDelete.value) return
  deletingTimelog.value = true
  try {
    await call('next_pms.api.crud.delete_timelog', { timelog: timelogToDelete.value.name })
    showDeleteTimelogConfirm.value = false
    timelogToDelete.value = null
    fetchLogs()
  } catch (e) {
    console.error('Failed to delete timelog:', e)
    alert('Failed to delete time log. Please try again.')
  } finally {
    deletingTimelog.value = false
  }
}

onMounted(async () => {
  await fetchFilterOptions()
  fetchLogs()
  fetchActiveTimers()
})
</script>

<style scoped>
.timelogs-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 4px 0 0;
}

/* Active Timers */
.active-timers-section {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 20px;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  display: inline-block;
  animation: pulse-green 2s infinite;
  flex-shrink: 0;
}

@keyframes pulse-green {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.active-timers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.active-timer-card {
  border: 1px solid #d1fae5;
  background: #ecfdf5;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timer-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.timer-user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.timer-user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.timer-user-name {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timer-user-email {
  font-size: 11px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timer-card-task {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.timer-task-link {
  font-size: 13px;
  color: #2563EB;
  text-decoration: none;
  font-weight: 500;
}

.timer-task-link:hover {
  text-decoration: underline;
}

.timer-project-tag {
  font-size: 10px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
  padding: 2px 6px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: 500;
}

.timer-card-elapsed {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  font-size: 16px;
  font-weight: 700;
  color: #059669;
}

/* Filters */
.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 16px;
}

.filters-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-select,
.filter-input {
  padding: 7px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: #fff;
  outline: none;
  transition: border-color 0.2s;
  min-width: 140px;
}

.filter-select:focus,
.filter-input:focus {
  border-color: #2563EB;
}

.filter-input {
  min-width: 130px;
}

.btn-filter-clear {
  padding: 7px 16px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-filter-clear:hover {
  background: #e5e7eb;
  color: #374151;
}

/* Summary */
.summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.summary-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

/* Table */
.logs-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.table-wrap {
  overflow-x: auto;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
}

.logs-table thead {
  background: #f9fafb;
}

.logs-table th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
}

.logs-table td {
  padding: 10px 14px;
  font-size: 13px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.logs-table tr:last-child td {
  border-bottom: none;
}

.logs-table tr:hover {
  background: #f9fafb;
}

.row-running {
  background: #ecfdf5 !important;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar-sm {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-name-text {
  font-weight: 500;
  white-space: nowrap;
}

.task-link {
  color: #2563EB;
  text-decoration: none;
  font-weight: 500;
}

.task-link:hover {
  text-decoration: underline;
}

.project-link {
  color: #6b7280;
  text-decoration: none;
  font-size: 12px;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
}

.project-link:hover {
  color: #2563EB;
  background: rgba(37, 99, 235, 0.08);
}

.text-muted {
  color: #9ca3af;
}

.text-nowrap {
  white-space: nowrap;
}

.notes-text {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

.running-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #059669;
  font-weight: 500;
  font-size: 12px;
}

.status-tag {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.tag-running {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.tag-completed {
  background: #f3f4f6;
  color: #6b7280;
}

.tl-delete-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
}

.tl-delete-btn:hover {
  background: #fef2f2;
  color: #EF4444;
  border-color: #fecaca;
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 14px;
  border-top: 1px solid #e5e7eb;
}

.btn-page {
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-page:hover:not(:disabled) {
  background: #f3f4f6;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 12px;
  color: #6b7280;
}

/* Loading / Empty */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e5e7eb;
  border-top-color: #2563EB;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 12px;
  color: #6b7280;
  font-size: 13px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
  gap: 8px;
}

.empty-text {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  margin: 8px 0 0;
}

.empty-subtext {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

@media (max-width: 768px) {
  .filters-left {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }

  .filter-select,
  .filter-input {
    width: 100%;
    min-width: auto;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }

  .active-timers-grid {
    grid-template-columns: 1fr;
  }
}
</style>
