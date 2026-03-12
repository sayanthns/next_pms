<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Home</h1>
        <p class="page-subtitle">Welcome back! Here's your project overview</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading dashboard...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p class="error-message">{{ error }}</p>
      <button @click="loadDashboard" class="retry-button">Retry</button>
    </div>

    <template v-else>
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="summary-card-top">
            <div class="summary-icon summary-icon-projects">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="summary-info">
              <span class="summary-label">Total Projects</span>
              <span class="summary-value">{{ stats.totalProjects }}</span>
            </div>
          </div>
          <div class="summary-trend trend-up">
            <span>&#8599; +2 this week</span>
          </div>
        </div>

        <div class="summary-card">
          <div class="summary-card-top">
            <div class="summary-icon summary-icon-active">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="summary-info">
              <span class="summary-label">Active Projects</span>
              <span class="summary-value">{{ stats.activeProjects }}</span>
            </div>
          </div>
          <div class="summary-trend trend-neutral">
            <span>In progress</span>
          </div>
        </div>

        <div class="summary-card">
          <div class="summary-card-top">
            <div class="summary-icon summary-icon-tasks">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 11 12 14 22 4"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
              </svg>
            </div>
            <div class="summary-info">
              <span class="summary-label">Total Tasks</span>
              <span class="summary-value">{{ stats.totalTasks }}</span>
            </div>
          </div>
          <div class="summary-trend trend-neutral">
            <span>All tasks</span>
          </div>
        </div>

        <div class="summary-card">
          <div class="summary-card-top">
            <div class="summary-icon summary-icon-done">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <div class="summary-info">
              <span class="summary-label">Completed Tasks</span>
              <span class="summary-value">{{ stats.doneTasks }}</span>
            </div>
          </div>
          <div class="summary-trend trend-up">
            <span>&#8599; +5 today</span>
          </div>
        </div>
      </div>

      <!-- Project Overview Section -->
      <div class="dash-section">
        <div class="dash-section-header">
          <h2 class="dash-section-title">Project Overview</h2>
          <div class="section-actions">
            <select v-model="projectFilter" class="filter-dropdown">
              <option value="all">All Projects</option>
              <option value="active">Active</option>
              <option value="planning">Planning</option>
              <option value="completed">Completed</option>
              <option value="on-hold">On Hold</option>
            </select>
            <router-link to="/projects" class="dash-section-link">View All &rarr;</router-link>
          </div>
        </div>
        <div class="project-overview-grid">
          <div
            v-for="p in filteredProjects"
            :key="p.name"
            class="project-overview-card"
            :style="{ borderLeftColor: statusBorderColor(p.status) }"
            @click="$router.push(`/project/${p.name}`)"
          >
            <div class="project-card-header">
              <span class="project-card-name">{{ p.project_name }}</span>
              <span
                class="project-status-badge"
                :style="{
                  backgroundColor: statusBorderColor(p.status) + '18',
                  color: statusBorderColor(p.status)
                }"
              >
                {{ p.status }}
              </span>
            </div>
            <div class="project-card-client" v-if="p.client">
              {{ p.client }}
            </div>
            <div class="project-card-deadline" v-if="p.expected_end_date">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
              <span>{{ formatDate(p.expected_end_date) }}</span>
            </div>
            <div class="project-card-progress">
              <div class="progress-bar-container">
                <div
                  class="progress-bar-fill"
                  :style="{ width: progressPct(p) + '%', backgroundColor: statusBorderColor(p.status) }"
                ></div>
              </div>
              <span class="progress-label">{{ progressPct(p) }}%</span>
            </div>
            <div class="project-card-footer">
              <div class="team-avatar-stack">
                <div
                  v-for="(member, idx) in (p.team_members || []).slice(0, 3)"
                  :key="idx"
                  class="team-avatar"
                  :style="{ zIndex: 3 - idx }"
                  :title="member"
                >
                  {{ getInitials(member) }}
                </div>
                <div
                  v-if="(p.team_members || []).length > 3"
                  class="team-avatar team-avatar-more"
                  :style="{ zIndex: 0 }"
                >
                  +{{ (p.team_members || []).length - 3 }}
                </div>
              </div>
              <div class="project-task-count">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 11 12 14 22 4"/>
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                </svg>
                <span>{{ p.done_tasks || 0 }}/{{ p.total_tasks || 0 }} tasks</span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="filteredProjects.length === 0" class="dash-empty">
          No projects found matching the selected filter.
        </div>
      </div>

      <!-- My Tasks Section -->
      <div class="dash-section">
        <div class="dash-section-header">
          <h2 class="dash-section-title">My Tasks</h2>
          <div class="section-actions">
            <span class="dash-section-count">{{ myTasks.length }}</span>
            <router-link to="/my-tasks" class="dash-section-link">View All &rarr;</router-link>
          </div>
        </div>
        <div v-if="myTasks.length" class="my-tasks-list">
          <router-link
            v-for="t in myTasks"
            :key="t.name"
            :to="`/task/${t.name}`"
            class="my-task-row"
          >
            <span class="task-status-indicator" :style="{ backgroundColor: getTaskStatusColor(t.status) }"></span>
            <div class="my-task-info">
              <span class="my-task-title">{{ t.task_title }}</span>
              <span class="my-task-project">
                {{ t.project || 'No Project' }}
                <span v-if="t.due_date" class="task-due"> &middot; Due {{ formatDate(t.due_date) }}</span>
              </span>
            </div>
            <span class="task-priority" :class="'priority-' + (t.priority || 'medium').toLowerCase()">
              {{ t.priority || 'Medium' }}
            </span>
          </router-link>
        </div>
        <div v-else class="dash-empty">No tasks assigned to you.</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { call, getList } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'
import { eventBus, EVENTS } from '@/utils/eventBus'

const settingsStore = useSettingsStore()
const loading = ref(true)
const error = ref(null)
const projects = ref([])
const myTasks = ref([])
const allTaskCounts = ref({})
const projectFilter = ref('all')

function onDataChanged() {
  loadDashboard()
}

onMounted(async () => {
  await loadDashboard()
  eventBus.on(EVENTS.TASK_CREATED, onDataChanged)
  eventBus.on(EVENTS.TASK_STATUS_CHANGED, onDataChanged)
  eventBus.on(EVENTS.TASK_DELETED, onDataChanged)
  eventBus.on(EVENTS.TIMER_STOPPED, onDataChanged)
})

onUnmounted(() => {
  eventBus.off(EVENTS.TASK_CREATED, onDataChanged)
  eventBus.off(EVENTS.TASK_STATUS_CHANGED, onDataChanged)
  eventBus.off(EVENTS.TASK_DELETED, onDataChanged)
  eventBus.off(EVENTS.TIMER_STOPPED, onDataChanged)
})

async function loadDashboard() {
  loading.value = true
  error.value = null
  try {
    // Build task filters — developer only sees their assigned tasks
    const taskFilters = { status: ['not in', ['Done', 'Cancelled']] }
    const currentUser = window.frappe?.boot?.user?.name || window.pms_boot?.user || ''
    if (settingsStore.isDeveloper && !settingsStore.isManager && !settingsStore.isAdmin) {
      taskFilters.assigned_to = currentUser
    }

    const [projectsData, myTasksData] = await Promise.all([
      call('next_pms.api.dashboard.get_all_projects_summary'),
      getList('PMS Task', {
        fields: ['name', 'task_title', 'status', 'priority', 'project', 'due_date', 'assigned_to'],
        filters: taskFilters,
        orderBy: 'priority desc, due_date asc',
        limit: 20,
      }),
    ])
    projects.value = projectsData || []
    myTasks.value = myTasksData || []

    // Fetch team members for each project
    const projectsWithDetails = await Promise.all(
      (projectsData || []).map(async (project) => {
        let teamMembers = []
        try {
          const members = await getList('PMS Project Team', {
            filters: { parent: project.name },
            fields: ['employee_name'],
            limit: 0,
          })
          teamMembers = members.map((m) => m.employee_name)
        } catch {
          // team members not available
        }
        return {
          ...project,
          team_members: teamMembers,
        }
      })
    )
    projects.value = projectsWithDetails

    // Fetch actual task counts by status
    const counts = { 'Backlog': 0, 'To Do': 0, 'In Progress': 0, 'In Review': 0, 'Done': 0 }
    const statuses = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Done']
    for (const status of statuses) {
      try {
        const list = await getList('PMS Task', {
          fields: ['count(name) as cnt'],
          filters: { status },
          limit: 1,
        })
        counts[status] = list[0]?.cnt || 0
      } catch {
        counts[status] = 0
      }
    }
    allTaskCounts.value = counts
  } catch (e) {
    console.error('Failed to load dashboard:', e)
    error.value = 'Failed to load dashboard data. Please try again.'
  } finally {
    loading.value = false
  }
}

const stats = computed(() => {
  const totalProjects = projects.value.length
  const activeProjects = projects.value.filter(p => p.status === 'Active' || p.status === 'In Progress').length
  const totalTasks = Object.values(allTaskCounts.value).reduce((a, b) => a + b, 0)
  const doneTasks = allTaskCounts.value['Done'] || 0
  return { totalProjects, activeProjects, totalTasks, doneTasks }
})

const filteredProjects = computed(() => {
  if (projectFilter.value === 'all') return projects.value
  const filterMap = {
    active: ['Active', 'In Progress'],
    planning: ['Planning', 'Planned'],
    completed: ['Completed'],
    'on-hold': ['On Hold'],
  }
  const allowed = filterMap[projectFilter.value] || []
  return projects.value.filter((p) => allowed.includes(p.status))
})

function progressPct(project) {
  if (!project.total_tasks) return 0
  return Math.round(((project.done_tasks || 0) / project.total_tasks) * 100)
}

function statusKey(status) {
  return (status || '').toLowerCase().replace(/\s+/g, '-')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const options = { month: 'short', day: 'numeric', year: 'numeric' }
  return date.toLocaleDateString('en-US', options)
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return parts[0][0].toUpperCase()
}

function statusBorderColor(status) {
  const colorMap = {
    'Active': '#10b981',
    'In Progress': '#10b981',
    'Planning': '#2563EB',
    'Planned': '#2563EB',
    'Completed': '#059669',
    'On Hold': '#F59E0B',
    'Cancelled': '#EF4444',
  }
  return colorMap[status] || '#9ca3af'
}

function getTaskStatusColor(status) {
  const colorMap = {
    'Backlog': '#9ca3af',
    'To Do': '#3b82f6',
    'In Progress': '#10b981',
    'In Review': '#8b5cf6',
    'Done': '#16a34a',
    'Cancelled': '#9ca3af',
  }
  return colorMap[status] || '#9ca3af'
}
</script>

<style scoped>
.dashboard {
  padding: 16px 0;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

/* Loading & Error */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
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
  margin-top: 16px;
  color: #6b7280;
  font-size: 14px;
}

.error-container {
  text-align: center;
  padding: 60px 0;
}

.error-message {
  color: #EF4444;
  margin-bottom: 16px;
  font-size: 15px;
}

.retry-button {
  padding: 8px 20px;
  background-color: #2563EB;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s;
}

.retry-button:hover {
  background-color: #1D4ED8;
}

/* Summary Cards */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.summary-card {
  background: #fff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s;
}

.summary-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.summary-card-top {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
}

.summary-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.summary-icon-projects { background: rgba(37, 99, 235, 0.1); }
.summary-icon-active { background: rgba(245, 158, 11, 0.1); }
.summary-icon-tasks { background: rgba(59, 130, 246, 0.1); }
.summary-icon-done { background: rgba(16, 185, 129, 0.1); }

.summary-info {
  display: flex;
  flex-direction: column;
}

.summary-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  margin-bottom: 2px;
}

.summary-value {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.summary-trend {
  font-size: 12px;
  font-weight: 500;
  padding-top: 2px;
}

.trend-up {
  color: #10b981;
}

.trend-down {
  color: #EF4444;
}

.trend-neutral {
  color: #9ca3af;
}

/* Sections */
.dash-section {
  background: #fff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.dash-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 12px;
}

.dash-section-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-dropdown {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: #fff;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.filter-dropdown:focus {
  border-color: #2563EB;
}

.dash-section-count {
  background: #e5e7eb;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.dash-section-link {
  font-size: 13px;
  font-weight: 500;
  color: #2563EB;
  text-decoration: none;
  transition: color 0.2s;
}

.dash-section-link:hover {
  color: #1D4ED8;
}

.dash-empty {
  text-align: center;
  padding: 32px 20px;
  color: #9ca3af;
  font-size: 13px;
}

/* Project Overview Grid */
.project-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.project-overview-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #f3f4f6;
  border-left: 4px solid #9ca3af;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}

.project-overview-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.project-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 12px;
}

.project-card-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  line-height: 1.4;
}

.project-status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}

.project-card-client {
  font-size: 13px;
  color: #9ca3af;
  margin-bottom: 10px;
}

.project-card-deadline {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 14px;
}

.project-card-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.progress-bar-container {
  flex: 1;
  height: 6px;
  background-color: #f3f4f6;
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.progress-label {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  min-width: 36px;
  text-align: right;
}

.project-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.team-avatar-stack {
  display: flex;
  align-items: center;
}

.team-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: #2563EB;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  position: relative;
}

.team-avatar + .team-avatar {
  margin-left: -8px;
}

.team-avatar-more {
  background-color: #e5e7eb;
  color: #6b7280;
  font-size: 9px;
}

.project-task-count {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #6b7280;
}

/* My Tasks */
.my-tasks-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.my-task-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
  text-decoration: none;
  transition: box-shadow 0.2s, transform 0.15s;
}

.my-task-row:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.task-status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.my-task-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.my-task-title {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-task-project {
  display: block;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.task-due {
  color: #6b7280;
}

.task-priority {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}

.priority-critical,
.priority-urgent {
  background-color: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.priority-high {
  background-color: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.priority-medium {
  background-color: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.priority-low {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

/* Responsive */
@media (max-width: 860px) {
  .project-overview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .dashboard {
    padding: 12px 0;
  }

  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .summary-value {
    font-size: 22px;
  }

  .dash-section-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
