<template>
  <div class="project-list">
    <div class="page-header">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-subtitle">Manage and track all your projects</p>
      </div>
      <button v-if="settingsStore.canCreateProject" class="btn btn-primary" @click="createNewProject">
        <span class="btn-icon">+</span>
        New Project
      </button>
    </div>

    <!-- Toolbar: Search + Filter + View Toggle -->
    <div v-if="!projectStore.loading && projectStore.projects.length" class="toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search projects..."
            class="search-input"
          />
        </div>
        <select v-model="statusFilter" class="filter-select">
          <option value="all">All Projects</option>
          <option value="active">Active</option>
          <option value="planning">Planning</option>
          <option value="on-hold">On Hold</option>
          <option value="completed">Completed</option>
        </select>
        <button
          :class="['filter-btn', { active: favoriteFilter }]"
          @click="favoriteFilter = !favoriteFilter"
          title="Show favorites only"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" :fill="favoriteFilter ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          Favorites
        </button>
      </div>
      <div class="toolbar-right">
        <span class="project-count">{{ filteredProjects.length }} projects</span>
        <div class="view-toggle">
          <button :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'" title="Grid view">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
            </svg>
          </button>
          <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'" title="List view">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="projectStore.loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading projects...</p>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-else-if="!projectStore.projects.length"
      icon="folder"
      title="No Projects Yet"
      description="Create your first project to start tracking tasks, budgets, and timelines."
      actionText="Create Project"
      @action="createNewProject"
    />

    <!-- No results -->
    <div v-else-if="!filteredProjects.length" class="empty-filter">
      <p>No projects match your search or filter.</p>
      <button class="btn-clear-filter" @click="searchQuery = ''; statusFilter = 'all'">Clear filters</button>
    </div>

    <!-- Grid View -->
    <div v-else-if="viewMode === 'grid'" class="project-grid">
      <div
        v-for="project in filteredProjects"
        :key="project.name"
        class="project-card"
        :style="{ borderLeftColor: statusBorderColor(project.status) }"
        @click="openProject(project.name)"
      >
        <div class="card-header">
          <div class="card-header-left">
            <button
              class="star-btn"
              :class="{ active: isFavorite(project.name) }"
              @click="toggleFavorite($event, project.name)"
              :title="isFavorite(project.name) ? 'Remove from favorites' : 'Add to favorites'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" :fill="isFavorite(project.name) ? '#f59e0b' : 'none'" stroke="#f59e0b" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            </button>
            <h3 class="project-name">{{ project.project_name }}</h3>
          </div>
          <span class="status-badge" :class="statusClass(project.status)">
            {{ project.status }}
          </span>
        </div>

        <p v-if="project.client" class="project-client">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          {{ project.client }}
        </p>

        <div v-if="project.start_date || (settingsStore.canViewFinance && project.total_budget)" class="card-details">
          <span v-if="project.start_date" class="detail-item">
            &#128197; {{ formatDate(project.start_date) }}
          </span>
          <span v-if="settingsStore.canViewFinance && project.total_budget" class="detail-item">
            &#128176; {{ formatCurrency(project.total_budget) }}
          </span>
        </div>

        <div class="progress-section">
          <div class="progress-info">
            <span class="task-count">
              {{ project.done_tasks || 0 }} / {{ project.total_tasks || 0 }} tasks
            </span>
            <span class="progress-pct">{{ progressPercent(project) }}%</span>
          </div>
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: progressPercent(project) + '%' }"
            ></div>
          </div>
        </div>

        <div class="card-footer">
          <div class="task-summary">
            <span class="summary-dot dot-success"></span>
            {{ project.done_tasks || 0 }} done
            <span class="summary-dot dot-warning"></span>
            {{ (project.total_tasks || 0) - (project.done_tasks || 0) }} left
          </div>
          <div v-if="settingsStore.canViewFinance && project.total_budget" class="budget-chip">
            {{ formatBudgetUtil(project) }}% budget
          </div>
        </div>
      </div>
    </div>

    <!-- List View -->
    <div v-else-if="viewMode === 'list'" class="project-table-wrap">
      <table class="project-table">
        <thead>
          <tr>
            <th>Project</th>
            <th>Status</th>
            <th>Client</th>
            <th>Progress</th>
            <th>Tasks</th>
            <th v-if="settingsStore.canViewFinance">Budget</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="project in filteredProjects"
            :key="project.name"
            class="project-row"
            @click="openProject(project.name)"
          >
            <td>
              <div class="table-project-name">
                <span class="table-color-dot" :style="{ background: statusBorderColor(project.status) }"></span>
                <div>
                  <span class="table-name">{{ project.project_name }}</span>
                  <span v-if="project.start_date" class="table-date">Started {{ formatDate(project.start_date) }}</span>
                </div>
              </div>
            </td>
            <td>
              <span class="status-badge" :class="statusClass(project.status)">{{ project.status }}</span>
            </td>
            <td class="table-client">{{ project.client || '—' }}</td>
            <td>
              <div class="table-progress">
                <div class="progress-bar-mini">
                  <div class="progress-fill-mini" :style="{ width: progressPercent(project) + '%' }"></div>
                </div>
                <span class="table-pct">{{ progressPercent(project) }}%</span>
              </div>
            </td>
            <td class="table-tasks">
              {{ project.done_tasks || 0 }}/{{ project.total_tasks || 0 }}
            </td>
            <td v-if="settingsStore.canViewFinance" class="table-budget">
              {{ project.total_budget ? formatCurrency(project.total_budget) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Project Modal -->
    <CreateProjectModal
      :show="showCreateProject"
      @close="showCreateProject = false"
      @created="onProjectCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '@/utils/frappe'
import { useProjectStore } from '@/store/projects'
import { useSettingsStore } from '@/store/settings'
import EmptyState from '@/components/EmptyState.vue'
import CreateProjectModal from '@/components/CreateProjectModal.vue'

const router = useRouter()
const projectStore = useProjectStore()
const settingsStore = useSettingsStore()
const showCreateProject = ref(false)
const searchQuery = ref('')
const statusFilter = ref('all')
const viewMode = ref('grid')
const favoriteProjects = ref([])
const favoriteFilter = ref(false)

onMounted(() => {
  projectStore.fetchProjects()
  loadFavorites()
})

async function loadFavorites() {
  try {
    const result = await call('next_pms.api.crud.get_favorite_projects')
    favoriteProjects.value = result || []
  } catch (e) {
    console.error('Failed to load favorites:', e)
  }
}

async function toggleFavorite(e, projectName) {
  e.stopPropagation()
  try {
    const result = await call('next_pms.api.crud.toggle_favorite_project', {
      project: projectName,
    })
    if (result.is_favorite) {
      favoriteProjects.value.push(projectName)
    } else {
      favoriteProjects.value = favoriteProjects.value.filter(p => p !== projectName)
    }
  } catch (err) {
    console.error('Failed to toggle favorite:', err)
  }
}

function isFavorite(projectName) {
  return favoriteProjects.value.includes(projectName)
}

const filteredProjects = computed(() => {
  let projects = projectStore.projects || []

  // Favorites filter
  if (favoriteFilter.value) {
    projects = projects.filter(p => favoriteProjects.value.includes(p.name))
  }

  // Search filter
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    projects = projects.filter(p =>
      (p.project_name || '').toLowerCase().includes(q) ||
      (p.client || '').toLowerCase().includes(q)
    )
  }

  // Status filter
  if (statusFilter.value !== 'all') {
    const filterMap = {
      'active': ['Active', 'In Progress'],
      'planning': ['Planning', 'Planned', 'Open'],
      'on-hold': ['On Hold'],
      'completed': ['Completed'],
    }
    const allowed = filterMap[statusFilter.value] || []
    projects = projects.filter(p => allowed.includes(p.status))
  }

  return projects
})

function openProject(name) {
  router.push(`/project/${name}`)
}

function createNewProject() {
  showCreateProject.value = true
}

function onProjectCreated(result) {
  showCreateProject.value = false
  projectStore.fetchProjects()
  if (result && result.name) {
    router.push(`/project/${result.name}`)
  }
}

function progressPercent(project) {
  if (!project.total_tasks) return 0
  return Math.round(((project.done_tasks || 0) / project.total_tasks) * 100)
}

function formatBudgetUtil(project) {
  if (project.budget_utilization) return Math.round(project.budget_utilization)
  if (!project.total_budget) return 0
  const used = project.calculated_cost || project.used_budget || project.total_cost || 0
  return Math.round((used / project.total_budget) * 100)
}

function formatCurrency(value) {
  return settingsStore.formatCurrency(value)
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function statusClass(status) {
  const map = {
    'Open': 'badge-primary',
    'Planning': 'badge-primary',
    'Active': 'badge-success',
    'In Progress': 'badge-success',
    'On Hold': 'badge-warning',
    'Completed': 'badge-done',
    'Cancelled': 'badge-danger',
  }
  return map[status] || 'badge-default'
}

function statusBorderColor(status) {
  const map = {
    'Active': '#10b981', 'In Progress': '#10b981',
    'Planning': '#3b82f6', 'Planned': '#3b82f6', 'Open': '#3b82f6',
    'Completed': '#059669',
    'On Hold': '#F59E0B',
    'Cancelled': '#EF4444',
  }
  return map[status] || '#9ca3af'
}
</script>

<style scoped>
.project-list {
  padding: 16px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

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
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
}

/* Toolbar */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.search-box {
  position: relative;
  max-width: 280px;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 34px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  transition: border-color 0.15s;
  outline: none;
}

.search-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}

.search-input::placeholder {
  color: var(--text-tertiary);
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  cursor: pointer;
  outline: none;
}

.filter-select:focus {
  border-color: var(--color-primary);
}

.project-count {
  font-size: 13px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.view-toggle {
  display: flex;
  gap: 0;
  background: var(--bg-surface-hover);
  border-radius: 8px;
  padding: 3px;
}

.view-toggle button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.view-toggle button.active {
  background: var(--bg-surface);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
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
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* Empty filter */
.empty-filter {
  text-align: center;
  padding: 60px 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.btn-clear-filter {
  margin-top: 12px;
  padding: 8px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.btn-clear-filter:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
}

/* Grid View */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.project-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-left: 4px solid var(--text-tertiary);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px var(--shadow-sm);
}

.project-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}

.project-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
  margin-right: 12px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.badge-primary { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.badge-success { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.badge-warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.badge-danger { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
.badge-done { background: rgba(16, 185, 129, 0.15); color: #059669; }
.badge-default { background: var(--bg-surface-hover); color: var(--text-secondary); }

.project-client {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 10px 0;
}

.project-client svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.card-details {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.detail-item {
  font-size: 12px;
  color: var(--text-tertiary);
}

.progress-section {
  margin-bottom: 14px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.task-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.progress-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-success);
}

.progress-bar {
  height: 5px;
  background: var(--border-default);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.task-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.summary-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot-success { background: var(--color-success); }
.dot-warning { background: var(--color-warning); }

.budget-chip {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

/* List/Table View */
.project-table-wrap {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px var(--shadow-sm);
}

.project-table {
  width: 100%;
  border-collapse: collapse;
}

.project-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-surface-active);
  border-bottom: 1px solid var(--border-default);
}

.project-table td {
  padding: 14px 16px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
}

.project-row {
  cursor: pointer;
  transition: background 0.1s;
}

.project-row:hover {
  background: var(--bg-surface-active);
}

.project-row:last-child td {
  border-bottom: none;
}

.table-project-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.table-name {
  display: block;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.table-date {
  display: block;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.table-client {
  color: var(--text-secondary);
}

.table-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 120px;
}

.progress-bar-mini {
  flex: 1;
  height: 5px;
  background: var(--border-default);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill-mini {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
}

.table-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-success);
  white-space: nowrap;
}

.table-tasks {
  font-weight: 500;
  color: var(--text-secondary);
}

.table-budget {
  font-weight: 600;
  color: var(--text-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .project-list { padding: 12px 0; }
  .page-header {
    flex-wrap: wrap;
    gap: 12px;
  }
  .page-header .btn {
    width: 100%;
    justify-content: center;
  }
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-left { flex-direction: column; }
  .search-box { max-width: 100%; }
  .toolbar-right { justify-content: space-between; }
  .project-grid { grid-template-columns: 1fr; }
}

.star-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  opacity: 0.4;
  transition: opacity 0.15s;
}
.star-btn:hover,
.star-btn.active {
  opacity: 1;
}
.card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.card-header-left .project-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 6px;
  background: white;
  font-size: 13px;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover {
  border-color: var(--primary, #3b82f6);
  color: var(--primary, #3b82f6);
}
.filter-btn.active {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #b45309;
}
</style>
