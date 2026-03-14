<template>
  <div class="my-tasks-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">My Tasks</h1>
        <p class="page-subtitle">Tasks assigned to you across all projects</p>
      </div>
      <div class="view-controls">
        <div class="view-toggle">
          <button :class="{ active: viewMode === 'board' }" @click="viewMode = 'board'">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            Board
          </button>
          <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            List
          </button>
        </div>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar">
      <div class="search-box">
        <svg class="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input v-model="searchQuery" type="text" placeholder="Search tasks..." class="search-input" />
      </div>
      <select v-model="filterProject" class="filter-select">
        <option value="">All Projects</option>
        <option v-for="p in projectList" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filterStatus" class="filter-select">
        <option value="">All Statuses</option>
        <option value="Backlog">Backlog</option>
        <option value="To Do">To Do</option>
        <option value="In Progress">In Progress</option>
        <option value="In Review">In Review</option>
        <option value="Done">Done</option>
      </select>
      <span v-if="filteredTasks.length !== myTasks.length" class="filter-count">
        {{ filteredTasks.length }} of {{ myTasks.length }}
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading tasks...</p>
    </div>

    <!-- Board View -->
    <div v-else-if="viewMode === 'board'" class="kanban-container">
      <div
        v-for="col in columns"
        :key="col.status"
        class="kanban-column"
        :class="{ 'drop-highlight': dragOverColumn === col.status }"
        @dragover.prevent="onDragOver($event, col.status)"
        @dragleave="onDragLeave($event, col.status)"
        @drop="onDrop($event, col.status)"
      >
        <div class="column-header">
          <span class="column-dot" :style="{ background: col.color }"></span>
          <span class="column-title">{{ col.label }}</span>
          <span class="column-count">{{ tasksByStatus(col.status).length }}</span>
        </div>
        <div class="column-body">
          <KanbanCard
            v-for="task in tasksByStatus(col.status)"
            :key="task.name"
            :task="task"
            :showProjectTag="true"
            @click="router.push(`/task/${task.name}`)"
          />
          <div v-if="!tasksByStatus(col.status).length" class="column-empty">
            No tasks
          </div>
        </div>
      </div>
    </div>

    <!-- List View -->
    <div v-else-if="viewMode === 'list'" class="task-table-wrap">
      <table class="task-table">
        <thead>
          <tr>
            <th>Priority</th>
            <th>Task</th>
            <th>Project</th>
            <th>Status</th>
            <th>Due Date</th>
            <th>Hours</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in filteredTasks" :key="task.name" @click="$router.push(`/task/${task.name}`)" class="task-row">
            <td>
              <span class="priority-dot" :style="{ background: priorityColor(task.priority) }"></span>
              {{ task.priority }}
            </td>
            <td>
              <span class="task-id">{{ task.name }}</span>
              <span class="task-name">{{ task.task_title }}</span>
            </td>
            <td>{{ task.project }}</td>
            <td><span class="status-chip" :class="'chip-' + (task.status || '').toLowerCase().replace(/\s+/g, '-')">{{ task.status }}</span></td>
            <td>{{ task.due_date ? formatDate(task.due_date) : '—' }}</td>
            <td>{{ task.estimated_hours ? task.estimated_hours + 'h' : '—' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filteredTasks.length" class="empty-state">
        <p>{{ myTasks.length ? 'No tasks match your filters.' : 'No tasks assigned to you.' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { call, getList, setValue } from '@/utils/frappe'
import { useAutoRefresh } from '@/utils/realtime'
import KanbanCard from '@/components/KanbanCard.vue'

const router = useRouter()

const viewMode = ref('board')
const loading = ref(true)
const myTasks = ref([])
const searchQuery = ref('')
const filterProject = ref('')
const filterStatus = ref('')
const dragOverColumn = ref(null)

const columns = [
  { status: 'To Do', label: 'To Do', color: '#3b82f6' },
  { status: 'In Progress', label: 'In Progress', color: '#F59E0B' },
  { status: 'In Review', label: 'In Review', color: '#8b5cf6' },
  { status: 'Done', label: 'Done', color: '#10b981' },
]

const projectList = computed(() => {
  const projects = new Set()
  myTasks.value.forEach(t => { if (t.project) projects.add(t.project) })
  return Array.from(projects).sort()
})

const filteredTasks = computed(() => {
  let tasks = myTasks.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    tasks = tasks.filter(t =>
      (t.task_title || '').toLowerCase().includes(q) ||
      (t.name || '').toLowerCase().includes(q) ||
      (t.project || '').toLowerCase().includes(q)
    )
  }
  if (filterProject.value) {
    tasks = tasks.filter(t => t.project === filterProject.value)
  }
  if (filterStatus.value) {
    tasks = tasks.filter(t => t.status === filterStatus.value)
  }
  return tasks
})

function tasksByStatus(status) {
  return filteredTasks.value.filter(t => t.status === status)
}

function priorityColor(p) {
  const map = { Critical: '#EF4444', High: '#F59E0B', Medium: '#FBBF24', Low: '#9ca3af' }
  return map[p] || '#9ca3af'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function onDragOver(event, status) {
  event.dataTransfer.dropEffect = 'move'
  dragOverColumn.value = status
}

function onDragLeave(event, status) {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX
  const y = event.clientY
  if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
    dragOverColumn.value = null
  }
}

async function onDrop(event, newStatus) {
  dragOverColumn.value = null
  try {
    const data = JSON.parse(event.dataTransfer.getData('application/json'))
    if (!data?.taskName) return
    const task = myTasks.value.find(t => t.name === data.taskName)
    if (task && task.status !== newStatus) {
      task.status = newStatus
      await setValue('PMS Task', data.taskName, 'status', newStatus)
    }
  } catch (e) {
    console.error('Drop failed:', e)
  }
}

async function loadMyTasks() {
  loading.value = true
  try {
    myTasks.value = await call('next_pms.api.crud.get_my_tasks', { limit: 200 })
  } catch (e) {
    console.error('Failed to load tasks:', e)
  } finally {
    loading.value = false
  }
}

// Real-time: auto-refresh when tasks are updated by anyone
useAutoRefresh(() => loadMyTasks())

onMounted(() => loadMyTasks())
</script>

<style scoped>
.my-tasks-view {
  padding: 16px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #6b7280; margin: 2px 0 0 0; }

/* View Toggle */
.view-toggle {
  display: flex;
  gap: 0;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 3px;
}

.view-toggle button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.view-toggle button.active {
  background: #ffffff;
  color: #1a1a2e;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* Filters Bar */
.filters-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0 10px;
  flex: 1;
  min-width: 180px;
  max-width: 300px;
}

.search-icon {
  color: #9ca3af;
  flex-shrink: 0;
}

.search-input {
  border: none;
  outline: none;
  font-size: 13px;
  padding: 8px 0;
  width: 100%;
  background: transparent;
  color: #374151;
}

.search-input::placeholder { color: #9ca3af; }

.filter-select {
  padding: 7px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: #fff;
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: #2563EB;
}

.filter-count {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

/* Loading */
.loading-container { display: flex; flex-direction: column; align-items: center; padding: 80px 0; }
.spinner { width: 40px; height: 40px; border: 3px solid #e5e7eb; border-top-color: #2563EB; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { margin-top: 16px; color: #6b7280; font-size: 14px; }

/* Kanban */
.kanban-container {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.kanban-column {
  flex: 1;
  min-width: 0;
  background: #f8f9fa;
  border-radius: 10px;
  padding: 0;
}

.column-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
}

.column-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  white-space: nowrap;
}

.column-count {
  background: #e5e7eb;
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 8px;
}

.column-body {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: calc(100vh - 280px);
  overflow-y: auto;
}

.kanban-column.drop-highlight {
  background: #eef2ff;
  border: 2px dashed #2563EB;
  border-radius: 10px;
}

.column-empty {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 30px 0;
}

/* List View */
.task-table-wrap {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
}

.task-table th {
  text-align: left;
  padding: 10px 14px;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #f8f9fa;
  border-bottom: 1px solid #e5e7eb;
}

.task-table td {
  padding: 10px 14px;
  font-size: 13px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
}

.task-row {
  cursor: pointer;
  transition: background 0.1s;
}

.task-row:hover {
  background: #f8f9fa;
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.task-id {
  display: block;
  font-size: 10px;
  color: #9ca3af;
  font-family: monospace;
}

.task-name {
  display: block;
  font-weight: 500;
  color: #1a1a2e;
}

.status-chip {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.chip-backlog { background: #f3f4f6; color: #6b7280; }
.chip-to-do { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.chip-in-progress { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.chip-in-review { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
.chip-done { background: rgba(16, 185, 129, 0.1); color: #10b981; }

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: #9ca3af;
  font-size: 14px;
}

@media (max-width: 768px) {
  .my-tasks-view { padding: 12px 0; }
  .page-header { flex-direction: column; gap: 12px; }
  .filters-bar { flex-direction: column; align-items: stretch; }
  .search-box { max-width: 100%; }
  .kanban-container { flex-direction: column; }
  .kanban-column { min-width: 100%; }
}
</style>
