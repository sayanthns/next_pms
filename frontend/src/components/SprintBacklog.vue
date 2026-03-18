<template>
  <div class="sprint-backlog">
    <!-- Sprint Header -->
    <div class="sprint-header" @click="toggleCollapse">
      <div class="sprint-header-left">
        <button class="collapse-btn" :class="{ collapsed: isCollapsed }">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2L8 6L4 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <h3 class="sprint-name">{{ sprintData.sprint_name || sprintName }}</h3>
        <span class="status-badge" :class="sprintStatusClass">
          {{ sprintData.status || 'Planning' }}
        </span>
        <span
          v-if="sprintData.approval_status && sprintData.approval_status !== 'Pending'"
          class="approval-badge"
          :class="approvalBadgeClass"
        >
          <svg v-if="sprintData.approval_status === 'Approved'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <svg v-else-if="sprintData.approval_status === 'Ready for Review'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <svg v-else-if="sprintData.approval_status === 'Changes Requested'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          {{ sprintData.approval_status }}
        </span>
        <span v-if="sprintData.start_date || sprintData.end_date" class="sprint-dates">
          {{ formatDate(sprintData.start_date) }} - {{ formatDate(sprintData.end_date) }}
        </span>
      </div>
      <div class="sprint-header-right">
        <span class="task-count">{{ tasks.length }} tasks</span>
      </div>
    </div>

    <!-- Progress Bar -->
    <div v-if="!isCollapsed && tasks.length" class="sprint-progress-section">
      <div class="progress-info">
        <span class="progress-label">
          {{ doneCount }} / {{ tasks.length }} completed
        </span>
        <span class="progress-pct">{{ progressPercent }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>

    <!-- Task Table -->
    <div v-if="!isCollapsed" class="task-table-wrapper">
      <table class="task-table" v-if="tasks.length">
        <thead>
          <tr>
            <th class="col-drag"></th>
            <th class="col-priority">Priority</th>
            <th class="col-title">Title</th>
            <th class="col-status">Status</th>
            <th class="col-assignee">Assignee</th>
            <th class="col-est-hours">Est. Hours</th>
            <th class="col-actual-hours">Actual Hours</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(task, index) in tasks"
            :key="task.name"
            class="task-row"
            draggable="true"
            @dragstart="onDragStart($event, task, index)"
            @dragover.prevent="onDragOver($event, index)"
            @dragleave="onDragLeave"
            @drop="onDrop($event, index)"
            :class="{ 'drag-over': dragOverIndex === index }"
          >
            <td class="col-drag">
              <span class="drag-handle" title="Drag to reorder">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="5" cy="3" r="1" fill="#9CA3AF"/>
                  <circle cx="9" cy="3" r="1" fill="#9CA3AF"/>
                  <circle cx="5" cy="7" r="1" fill="#9CA3AF"/>
                  <circle cx="9" cy="7" r="1" fill="#9CA3AF"/>
                  <circle cx="5" cy="11" r="1" fill="#9CA3AF"/>
                  <circle cx="9" cy="11" r="1" fill="#9CA3AF"/>
                </svg>
              </span>
            </td>
            <td class="col-priority">
              <span
                class="priority-dot"
                :class="priorityClass(task.priority)"
                :title="task.priority || 'Low'"
              ></span>
            </td>
            <td class="col-title">
              <router-link
                :to="`/task/${task.name}`"
                class="task-title-link"
                @click.stop
              >
                {{ task.task_title || task.title || task.name }}
              </router-link>
            </td>
            <td class="col-status">
              <span
                class="status-badge status-badge-sm"
                :class="taskStatusClass(task.status)"
              >
                {{ task.status || 'Backlog' }}
              </span>
            </td>
            <td class="col-assignee">
              <span v-if="task.assigned_to" class="assignee-avatar" :title="task.assigned_to">
                {{ getInitials(task.assigned_to) }}
              </span>
              <span v-else class="unassigned">--</span>
            </td>
            <td class="col-est-hours">
              <span v-if="task.estimated_hours" class="hours-value">
                {{ task.estimated_hours }}h
              </span>
              <span v-else class="hours-empty">--</span>
            </td>
            <td class="col-actual-hours">
              <span v-if="task.actual_hours" class="hours-value">
                {{ task.actual_hours }}h
              </span>
              <span v-else class="hours-empty">--</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!tasks.length" class="empty-tasks">
        No tasks in this sprint. Drag tasks here or add a new task.
      </div>

      <!-- Inline Add Task -->
      <div class="add-task-section">
        <div v-if="showAddForm" class="inline-add-form">
          <input
            ref="newTaskInput"
            v-model="newTaskTitle"
            type="text"
            class="add-task-input"
            placeholder="Task title..."
            @keyup.enter="submitNewTask"
            @keyup.escape="cancelAddTask"
          />
          <select v-model="newTaskPriority" class="add-task-select">
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
          <input
            v-model="newTaskEstHours"
            type="number"
            class="add-task-hours"
            placeholder="Est. hours"
            min="0"
            step="0.5"
          />
          <button class="btn-add-confirm" @click="submitNewTask">Add</button>
          <button class="btn-add-cancel" @click="cancelAddTask">Cancel</button>
        </div>
        <button v-else class="btn-add-task" @click="showAddTaskForm">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2V12M2 7H12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          Add Task
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  sprintName: {
    type: String,
    required: true,
  },
  sprintData: {
    type: Object,
    default: () => ({
      name: '',
      sprint_name: '',
      status: 'Planning',
      start_date: '',
      end_date: '',
    }),
  },
  tasks: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits([
  'add-task',
  'reorder-tasks',
  'move-task',
  'task-drag-start',
])

const isCollapsed = ref(false)
const showAddForm = ref(false)
const newTaskTitle = ref('')
const newTaskPriority = ref('Medium')
const newTaskEstHours = ref('')
const newTaskInput = ref(null)
const dragOverIndex = ref(null)
let draggedTaskIndex = null

// Computed
const doneCount = computed(() => {
  return props.tasks.filter((t) => t.status === 'Done').length
})

const progressPercent = computed(() => {
  if (!props.tasks.length) return 0
  return Math.round((doneCount.value / props.tasks.length) * 100)
})

const sprintStatusClass = computed(() => {
  const map = {
    Planning: 'badge-default',
    Active: 'badge-success',
    'In Progress': 'badge-success',
    Completed: 'badge-primary',
    Closed: 'badge-muted',
  }
  return map[props.sprintData.status] || 'badge-default'
})

const approvalBadgeClass = computed(() => {
  const map = {
    'Ready for Review': 'approval-review',
    'Approved': 'approval-approved',
    'Changes Requested': 'approval-changes',
  }
  return map[props.sprintData.approval_status] || ''
})

// Methods
function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function showAddTaskForm() {
  showAddForm.value = true
  nextTick(() => {
    if (newTaskInput.value) {
      newTaskInput.value.focus()
    }
  })
}

function cancelAddTask() {
  showAddForm.value = false
  newTaskTitle.value = ''
  newTaskPriority.value = 'Medium'
  newTaskEstHours.value = ''
}

function submitNewTask() {
  if (!newTaskTitle.value.trim()) return

  emit('add-task', {
    task_title: newTaskTitle.value.trim(),
    priority: newTaskPriority.value,
    estimated_hours: newTaskEstHours.value ? parseFloat(newTaskEstHours.value) : 0,
    sprint: props.sprintName,
  })

  cancelAddTask()
}

// Drag and drop for reordering
function onDragStart(event, task, index) {
  draggedTaskIndex = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('application/json', JSON.stringify({
    taskName: task.name,
    taskTitle: task.task_title || task.title,
    fromSprint: props.sprintName,
    fromIndex: index,
  }))
  emit('task-drag-start', task)
}

function onDragOver(event, index) {
  event.dataTransfer.dropEffect = 'move'
  dragOverIndex.value = index
}

function onDragLeave() {
  dragOverIndex.value = null
}

function onDrop(event, toIndex) {
  dragOverIndex.value = null

  try {
    const data = JSON.parse(event.dataTransfer.getData('application/json'))
    if (data.fromSprint === props.sprintName && draggedTaskIndex !== null) {
      // Reordering within same sprint
      emit('reorder-tasks', {
        sprint: props.sprintName,
        fromIndex: draggedTaskIndex,
        toIndex,
      })
    } else if (data.fromSprint !== props.sprintName) {
      // Moving from another sprint
      emit('move-task', {
        taskName: data.taskName,
        fromSprint: data.fromSprint,
        toSprint: props.sprintName,
        toIndex,
      })
    }
  } catch {
    // Fallback: use plain text data
    const taskName = event.dataTransfer.getData('text/plain')
    if (taskName) {
      emit('move-task', {
        taskName,
        fromSprint: '',
        toSprint: props.sprintName,
        toIndex,
      })
    }
  }
  draggedTaskIndex = null
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

function priorityClass(priority) {
  const map = {
    Critical: 'priority-critical',
    Urgent: 'priority-critical',
    High: 'priority-high',
    Medium: 'priority-medium',
    Low: 'priority-low',
  }
  return map[priority] || 'priority-low'
}

function taskStatusClass(status) {
  const map = {
    Backlog: 'badge-default',
    'To Do': 'badge-primary',
    'In Progress': 'badge-warning',
    'In Review': 'badge-info',
    Done: 'badge-success',
    Cancelled: 'badge-danger',
  }
  return map[status] || 'badge-default'
}
</script>

<style scoped>
.sprint-backlog {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.sprint-backlog:hover {
  box-shadow: 0 1px 4px var(--shadow-sm);
}

/* Sprint Header */
.sprint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: var(--bg-surface-active);
  border-bottom: 1px solid var(--border-default);
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}

.sprint-header:hover {
  background: var(--bg-surface-hover);
}

.sprint-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sprint-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: transform 0.2s ease;
  transform: rotate(90deg);
  padding: 0;
}

.collapse-btn.collapsed {
  transform: rotate(0deg);
}

.sprint-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.sprint-dates {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* Approval Status Badge */
.approval-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.approval-review { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.approval-approved { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.approval-changes { background: rgba(245, 158, 11, 0.1); color: #d97706; }

.task-count {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Progress Section */
.sprint-progress-section {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-light);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.progress-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.progress-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-success);
}

.progress-bar {
  height: 6px;
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

/* Task Table */
.task-table-wrapper {
  padding: 0;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
}

.task-table thead {
  background: #fafafa;
}

.task-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-light);
}

.task-table td {
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--bg-surface-active);
  vertical-align: middle;
}

.task-row {
  transition: background 0.12s ease;
  cursor: grab;
}

.task-row:hover {
  background: #fafafa;
}

.task-row:active {
  cursor: grabbing;
}

.task-row.drag-over {
  border-top: 2px solid var(--color-primary);
}

/* Column widths */
.col-drag { width: 36px; text-align: center; }
.col-priority { width: 50px; text-align: center; }
.col-title { min-width: 200px; }
.col-status { width: 120px; }
.col-assignee { width: 80px; text-align: center; }
.col-est-hours { width: 90px; text-align: right; }
.col-actual-hours { width: 100px; text-align: right; }

/* Drag handle */
.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  color: var(--text-placeholder);
  transition: color 0.15s ease;
}

.drag-handle:hover {
  color: var(--text-tertiary);
}

/* Priority dot */
.priority-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.priority-critical { background: #EF4444; }
.priority-high { background: #F97316; }
.priority-medium { background: #F59E0B; }
.priority-low { background: #94A3B8; }

/* Task title link */
.task-title-link {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
  transition: color 0.15s ease;
}

.task-title-link:hover {
  color: var(--color-primary);
}

/* Status badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.status-badge-sm {
  padding: 2px 8px;
  font-size: 10px;
}

.badge-primary { background: var(--color-primary-bg); color: var(--color-primary); }
.badge-success { background: var(--color-success-bg); color: var(--color-success); }
.badge-warning { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-info { background: rgba(139, 92, 246, 0.1); color: #8B5CF6; }
.badge-danger { background: var(--color-danger-bg); color: var(--color-danger); }
.badge-default { background: var(--bg-surface-hover); color: var(--text-secondary); }
.badge-muted { background: var(--bg-surface-hover); color: var(--text-tertiary); }

/* Assignee avatar */
.assignee-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
}

.unassigned {
  color: var(--text-placeholder);
  font-size: 12px;
}

/* Hours */
.hours-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.hours-empty {
  color: var(--text-placeholder);
  font-size: 12px;
}

/* Empty state */
.empty-tasks {
  padding: 32px 20px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
}

/* Add task section */
.add-task-section {
  padding: 10px 20px 14px;
}

.btn-add-task {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px dashed var(--border-default);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-add-task:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

/* Inline add form */
.inline-add-form {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.add-task-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s ease;
}

.add-task-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.add-task-select {
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  cursor: pointer;
}

.add-task-select:focus {
  border-color: var(--color-primary);
}

.add-task-hours {
  width: 90px;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.add-task-hours:focus {
  border-color: var(--color-primary);
}

.btn-add-confirm {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #2563EB;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-add-confirm:hover {
  background: #1D4ED8;
}

.btn-add-cancel {
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-add-cancel:hover {
  background: var(--bg-surface-active);
  color: var(--text-primary);
}
</style>
