<template>
  <div class="task-list-view">
    <div v-if="!embedded" class="list-header-title">
      <h1 class="page-title">Tasks</h1>
      <p class="page-subtitle">{{ id }}</p>
    </div>
    <div class="list-header">
      <div class="list-actions">
        <div class="search-box">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input v-model="searchQuery" type="text" placeholder="Search tasks..." class="search-input" />
        </div>
        <select v-model="filterStatus" class="filter-select">
          <option value="">All Status</option>
          <option value="Backlog">Backlog</option>
          <option value="To Do">To Do</option>
          <option value="In Progress">In Progress</option>
          <option value="In Review">In Review</option>
          <option value="Done">Done</option>
        </select>
        <select v-model="filterPriority" class="filter-select">
          <option value="">All Priority</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <button v-if="canCreateTask" class="btn btn-primary" @click="showCreateTask = true">
          <span class="btn-icon">+</span> New Task
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="taskStore.loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading tasks...</p>
    </div>

    <!-- Task Table -->
    <div v-else-if="filteredTasks.length" class="task-table-wrap">
      <table class="task-table">
        <thead>
          <tr>
            <th class="th-sortable" @click="toggleSort('priority')">
              Priority
              <span v-if="sortField === 'priority'" class="sort-icon">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="th-sortable" @click="toggleSort('task_title')">
              Task
              <span v-if="sortField === 'task_title'" class="sort-icon">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th>Status</th>
            <th>Assignees</th>
            <th class="th-sortable" @click="toggleSort('due_date')">
              Due Date
              <span v-if="sortField === 'due_date'" class="sort-icon">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th>Type</th>
            <th>Est. Hours</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="task in filteredTasks"
            :key="task.name"
            class="task-row"
            @click="openTask(task.name)"
          >
            <td>
              <span class="priority-dot" :class="'dot-' + (task.priority || 'medium').toLowerCase()"></span>
              <span class="priority-text">{{ task.priority }}</span>
            </td>
            <td>
              <div class="task-cell">
                <span class="task-id-text">{{ task.name }}</span>
                <span class="task-title-text">{{ task.task_title }}</span>
              </div>
            </td>
            <td>
              <span class="status-chip" :class="'chip-' + statusKey(task.status)">{{ task.status }}</span>
            </td>
            <td>
              <div class="assignee-cell">
                <template v-if="task.assignees && task.assignees.length">
                  <span
                    v-for="(a, idx) in task.assignees.slice(0, 2)"
                    :key="a.user"
                    class="mini-avatar"
                    :class="'avatar-color-' + (idx % 5)"
                    :title="a.full_name || a.user"
                  >
                    {{ getInitials(a.full_name || a.user) }}
                  </span>
                  <span v-if="task.assignees.length > 2" class="mini-avatar avatar-more">
                    +{{ task.assignees.length - 2 }}
                  </span>
                </template>
                <template v-else-if="task.assigned_to">
                  <span class="mini-avatar avatar-color-0" :title="task.assigned_to">
                    {{ getInitials(task.assigned_to) }}
                  </span>
                </template>
                <span v-else class="no-assignee">—</span>
              </div>
            </td>
            <td>
              <span v-if="task.due_date" class="due-text" :class="dueDateClass(task)">
                {{ formatDate(task.due_date) }}
              </span>
              <span v-else class="no-data">—</span>
            </td>
            <td>
              <span v-if="task.task_type" class="type-chip">{{ task.task_type }}</span>
              <span v-else class="no-data">—</span>
            </td>
            <td>
              <span v-if="task.estimated_hours" class="hours-text">{{ task.estimated_hours }}h</span>
              <span v-else class="no-data">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty -->
    <div v-else class="empty-state">
      <p class="empty-text">No tasks found</p>
      <button v-if="canCreateTask" class="btn btn-primary" @click="showCreateTask = true">Create First Task</button>
    </div>

    <!-- Create Task Modal -->
    <CreateTaskModal
      :show="showCreateTask"
      :projectId="id"
      @close="showCreateTask = false"
      @created="onTaskCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/store/tasks'
import { useSettingsStore } from '@/store/settings'
import CreateTaskModal from '@/components/CreateTaskModal.vue'

const props = defineProps({
  id: { type: String, required: true },
  embedded: { type: Boolean, default: false },
})

const router = useRouter()
const taskStore = useTaskStore()
const settingsStore = useSettingsStore()
const canCreateTask = computed(() => settingsStore.featurePermissions.create_task !== false)

const showCreateTask = ref(false)
const searchQuery = ref('')
const filterStatus = ref('')
const filterPriority = ref('')
const sortField = ref('priority')
const sortDir = ref('desc')

onMounted(() => {
  taskStore.fetchTasks(props.id)
})

const filteredTasks = computed(() => {
  let result = [...taskStore.tasks]

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      (t.task_title || '').toLowerCase().includes(q) ||
      (t.name || '').toLowerCase().includes(q)
    )
  }
  if (filterStatus.value) {
    result = result.filter(t => t.status === filterStatus.value)
  }
  if (filterPriority.value) {
    result = result.filter(t => t.priority === filterPriority.value)
  }

  // Sort
  const priorityOrder = { Critical: 4, High: 3, Medium: 2, Low: 1 }
  result.sort((a, b) => {
    let valA, valB
    if (sortField.value === 'priority') {
      valA = priorityOrder[a.priority] || 0
      valB = priorityOrder[b.priority] || 0
    } else if (sortField.value === 'due_date') {
      valA = a.due_date || '9999-12-31'
      valB = b.due_date || '9999-12-31'
    } else {
      valA = (a[sortField.value] || '').toLowerCase()
      valB = (b[sortField.value] || '').toLowerCase()
    }
    if (valA < valB) return sortDir.value === 'asc' ? -1 : 1
    if (valA > valB) return sortDir.value === 'asc' ? 1 : -1
    return 0
  })

  return result
})

function toggleSort(field) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'desc'
  }
}

function openTask(name) {
  router.push(`/task/${name}`)
}

function onTaskCreated() {
  showCreateTask.value = false
  taskStore.fetchTasks(props.id)
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function dueDateClass(task) {
  if (!task.due_date || task.status === 'Done') return ''
  const today = new Date(); today.setHours(0,0,0,0)
  const due = new Date(task.due_date); due.setHours(0,0,0,0)
  const diff = Math.floor((due - today) / 86400000)
  if (diff < 0) return 'due-overdue'
  if (diff === 0) return 'due-today'
  if (diff <= 3) return 'due-upcoming'
  return ''
}

function statusKey(status) {
  return (status || '').toLowerCase().replace(/\s+/g, '-')
}
</script>

<style scoped>
.task-list-view {
  padding: 16px 0;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.list-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-tertiary);
}

.search-input {
  border: none;
  outline: none;
  font-size: 13px;
  color: var(--text-primary);
  width: 160px;
  background: transparent;
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

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-icon {
  font-size: 16px;
  line-height: 1;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-text {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* Table */
.task-table-wrap {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
}

.task-table thead {
  background: var(--bg-surface-active);
}

.task-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
}

.th-sortable {
  cursor: pointer;
  user-select: none;
}

.th-sortable:hover {
  color: var(--color-primary);
}

.sort-icon {
  margin-left: 4px;
  color: var(--color-primary);
}

.task-table td {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.task-row {
  cursor: pointer;
  transition: background 0.1s;
}

.task-row:hover {
  background: var(--bg-surface-active);
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  vertical-align: middle;
  margin-right: 6px;
}

.dot-critical, .dot-urgent { background: var(--color-danger); }
.dot-high { background: var(--color-warning); }
.dot-medium { background: #FBBF24; }
.dot-low { background: var(--text-tertiary); }

.priority-text {
  font-size: 13px;
  font-weight: 500;
  vertical-align: middle;
}

.task-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-id-text {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
}

.task-title-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

/* Status Chip */
.status-chip {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.chip-backlog { background: var(--bg-surface-hover); color: var(--text-secondary); }
.chip-to-do { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.chip-in-progress { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.chip-in-review { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.chip-done { background: rgba(16, 185, 129, 0.1); color: #10b981; }

/* Assignee Cell */
.assignee-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mini-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: white;
  font-size: 10px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-color-0 { background: var(--color-primary); }
.avatar-color-1 { background: #7C3AED; }
.avatar-color-2 { background: var(--color-success-hover); }
.avatar-color-3 { background: var(--color-warning-hover); }
.avatar-color-4 { background: var(--color-danger-hover); }
.avatar-more { background: var(--text-tertiary); font-size: 9px; }

.no-assignee, .no-data {
  color: var(--text-placeholder);
  font-size: 13px;
}

.due-text {
  font-size: 13px;
}

.due-overdue { color: var(--color-danger); font-weight: 600; }
.due-today { color: var(--color-warning); font-weight: 600; }
.due-upcoming { color: var(--color-warning-hover); }

.type-chip {
  display: inline-flex;
  padding: 2px 8px;
  background: var(--bg-surface-hover);
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
}

.hours-text {
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  font-size: 13px;
  color: var(--text-primary);
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px;
  gap: 16px;
}

.empty-text {
  color: var(--text-tertiary);
  font-size: 14px;
}

@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
  }
  .list-actions {
    width: 100%;
  }
  .task-table-wrap {
    overflow-x: auto;
  }
}
</style>
