<template>
  <div class="project-backlog">
    <div class="backlog-header">
      <div v-if="!embedded">
        <h1 class="page-title">Sprint Backlog</h1>
        <p class="page-subtitle">{{ id }}</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" @click="showCreateSprint = true">
          + New Sprint
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading backlog...</p>
    </div>

    <div v-else class="backlog-content">
      <!-- Sprint Sections -->
      <div
        v-for="sprint in sprintSections"
        :key="sprint.name"
        class="sprint-section"
        @dragover.prevent="onDragOver($event, sprint.name)"
        @dragleave="onDragLeave($event, sprint.name)"
        @drop="onDrop($event, sprint.name)"
        :class="{ 'drop-highlight': dragOverSprint === sprint.name }"
      >
        <div class="sprint-header">
          <div class="sprint-info">
            <h3 class="sprint-name">{{ sprint.sprint_name || sprint.name }}</h3>
            <span
              class="status-badge"
              :class="sprintStatusClass(sprint.status)"
            >
              {{ sprint.status || 'Active' }}
            </span>
            <span
              v-if="sprint.approval_status && sprint.approval_status !== 'Pending'"
              class="approval-badge"
              :class="approvalStatusClass(sprint.approval_status)"
            >
              <svg v-if="sprint.approval_status === 'Approved'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              <svg v-else-if="sprint.approval_status === 'Ready for Review'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <svg v-else-if="sprint.approval_status === 'Changes Requested'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              {{ sprint.approval_status }}
            </span>
            <span v-if="sprint.start_date || sprint.end_date" class="sprint-dates">
              {{ formatDate(sprint.start_date) }} - {{ formatDate(sprint.end_date) }}
            </span>
          </div>
          <div class="sprint-header-actions">
            <span class="sprint-task-count">
              {{ getSprintTasks(sprint.name).length }} tasks
            </span>
            <button
              v-if="canManage && (!sprint.approval_status || sprint.approval_status === 'Pending' || sprint.approval_status === 'Changes Requested')"
              class="approval-action-btn btn-mark-review"
              @click.stop="markReadyForReview(sprint)"
              :disabled="approvalActioning === sprint.name"
              title="Mark sprint as ready for client review"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              {{ approvalActioning === sprint.name ? '...' : 'Send for Review' }}
            </button>
            <button
              v-if="canManage && sprint.approval_status === 'Ready for Review'"
              class="approval-action-btn btn-reset-approval"
              @click.stop="resetApproval(sprint)"
              :disabled="approvalActioning === sprint.name"
              title="Reset approval status to Pending"
            >
              Reset
            </button>
            <button v-if="canCreateTask" class="add-task-btn" @click="openCreateTask(sprint.name)" title="Add task to sprint">+ Task</button>
          </div>
        </div>

        <!-- Sprint Progress -->
        <div v-if="sprint.name !== '__backlog__'" class="sprint-progress">
          <div class="progress-info">
            <span class="progress-label">
              {{ sprintDoneCount(sprint.name) }} / {{ getSprintTasks(sprint.name).length }} completed
            </span>
            <span class="progress-pct">{{ sprintProgressPct(sprint.name) }}%</span>
          </div>
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: sprintProgressPct(sprint.name) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Task List -->
        <div class="task-list">
          <div
            v-for="task in getSprintTasks(sprint.name)"
            :key="task.name"
            class="task-row"
            draggable="true"
            @dragstart="onDragStart($event, task)"
          >
            <div class="task-left">
              <span
                class="priority-dot"
                :class="priorityClass(task.priority)"
                :title="task.priority"
              ></span>
              <router-link
                :to="`/task/${task.name}`"
                class="task-title-link"
                @click.stop
              >
                {{ task.task_title }}
              </router-link>
            </div>
            <div class="task-right">
              <span
                class="status-badge status-badge-sm"
                :class="taskStatusClass(task.status)"
              >
                {{ task.status }}
              </span>
              <span v-if="task.assigned_to" class="assignee" :title="task.assigned_to">
                {{ getInitials(task.assigned_to) }}
              </span>
              <span v-if="task.estimated_hours" class="est-hours" title="Estimated hours">
                {{ task.estimated_hours }}h
              </span>
            </div>
          </div>

          <div
            v-if="!getSprintTasks(sprint.name).length"
            class="no-tasks"
          >
            Drag tasks here to assign them to this sprint
          </div>
        </div>
      </div>

      <!-- Backlog Section -->
      <div
        class="sprint-section backlog-section"
        @dragover.prevent="onDragOver($event, '__backlog__')"
        @dragleave="onDragLeave($event, '__backlog__')"
        @drop="onDrop($event, '__backlog__')"
        :class="{ 'drop-highlight': dragOverSprint === '__backlog__' }"
      >
        <div class="sprint-header">
          <div class="sprint-info">
            <h3 class="sprint-name">Backlog</h3>
            <span class="status-badge badge-default">Unassigned</span>
          </div>
          <div class="sprint-header-actions">
            <span class="sprint-task-count">
              {{ backlogTasks.length }} tasks
            </span>
            <button v-if="canCreateTask" class="add-task-btn" @click="openCreateTask('')" title="Add task to backlog">+ Task</button>
          </div>
        </div>

        <div class="task-list">
          <div
            v-for="task in backlogTasks"
            :key="task.name"
            class="task-row"
            draggable="true"
            @dragstart="onDragStart($event, task)"
          >
            <div class="task-left">
              <span
                class="priority-dot"
                :class="priorityClass(task.priority)"
                :title="task.priority"
              ></span>
              <router-link
                :to="`/task/${task.name}`"
                class="task-title-link"
                @click.stop
              >
                {{ task.task_title }}
              </router-link>
            </div>
            <div class="task-right">
              <span
                class="status-badge status-badge-sm"
                :class="taskStatusClass(task.status)"
              >
                {{ task.status }}
              </span>
              <span v-if="task.assigned_to" class="assignee" :title="task.assigned_to">
                {{ getInitials(task.assigned_to) }}
              </span>
              <span v-if="task.estimated_hours" class="est-hours" title="Estimated hours">
                {{ task.estimated_hours }}h
              </span>
            </div>
          </div>

          <div v-if="!backlogTasks.length" class="no-tasks">
            No unassigned tasks
          </div>
        </div>
      </div>
    </div>

    <!-- Create Sprint Modal -->
    <CreateSprintModal
      :show="showCreateSprint"
      :projectId="id"
      @close="showCreateSprint = false"
      @created="onSprintCreated"
    />

    <!-- Create Task Modal -->
    <CreateTaskModal
      :show="showCreateTask"
      :projectId="id"
      :sprints="sprints"
      :defaultSprint="createTaskSprint"
      @close="showCreateTask = false"
      @created="onTaskCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/store/tasks'
import { useSettingsStore } from '@/store/settings'
import { getList, setValue, call } from '@/utils/frappe'
import CreateSprintModal from '@/components/CreateSprintModal.vue'
import CreateTaskModal from '@/components/CreateTaskModal.vue'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
  embedded: { type: Boolean, default: false },
})

const taskStore = useTaskStore()
const settingsStore = useSettingsStore()
const canCreateTask = computed(() => settingsStore.featurePermissions.create_task !== false)
const canManage = computed(() => settingsStore.isAdmin || settingsStore.isManager)
const approvalActioning = ref('')

const sprints = ref([])
const loading = ref(false)
const dragOverSprint = ref(null)
const showCreateSprint = ref(false)
const showCreateTask = ref(false)
const createTaskSprint = ref('')

function openCreateTask(sprintName) {
  createTaskSprint.value = sprintName
  showCreateTask.value = true
}

async function onSprintCreated() {
  showCreateSprint.value = false
  await loadSprints()
}

async function onTaskCreated() {
  showCreateTask.value = false
  await taskStore.fetchTasks(props.id)
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      loadSprints(),
      taskStore.fetchTasks(props.id),
    ])
  } finally {
    loading.value = false
  }
})

async function loadSprints() {
  try {
    sprints.value = await getList('PMS Sprint', {
      fields: ['name', 'sprint_name', 'status', 'start_date', 'end_date', 'project', 'approval_status'],
      filters: { project: props.id },
      orderBy: 'start_date asc',
      limit: 0,
    })
  } catch (e) {
    console.error('Failed to fetch sprints:', e)
    sprints.value = []
  }
}

const sprintSections = computed(() => {
  return sprints.value
})

const backlogTasks = computed(() => {
  return taskStore.tasks.filter((t) => !t.sprint)
})

function getSprintTasks(sprintName) {
  if (sprintName === '__backlog__') return backlogTasks.value
  return taskStore.tasks.filter((t) => t.sprint === sprintName)
}

function sprintDoneCount(sprintName) {
  return getSprintTasks(sprintName).filter((t) => t.status === 'Done').length
}

function sprintProgressPct(sprintName) {
  const tasks = getSprintTasks(sprintName)
  if (!tasks.length) return 0
  return Math.round((sprintDoneCount(sprintName) / tasks.length) * 100)
}

// Drag and Drop
function onDragStart(event, task) {
  event.dataTransfer.setData('text/plain', task.name)
  event.dataTransfer.effectAllowed = 'move'
}

function onDragOver(event, sprintName) {
  event.dataTransfer.dropEffect = 'move'
  dragOverSprint.value = sprintName
}

function onDragLeave(event, sprintName) {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX
  const y = event.clientY
  if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
    dragOverSprint.value = null
  }
}

async function onDrop(event, targetSprint) {
  dragOverSprint.value = null
  const taskName = event.dataTransfer.getData('text/plain')
  if (!taskName) return

  const newSprint = targetSprint === '__backlog__' ? '' : targetSprint

  try {
    await setValue('PMS Task', taskName, 'sprint', newSprint)
    // Update local state
    const task = taskStore.tasks.find((t) => t.name === taskName)
    if (task) {
      task.sprint = newSprint
    }
  } catch (e) {
    console.error('Failed to reassign sprint:', e)
  }
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
    'Critical': 'priority-critical',
    'Urgent': 'priority-urgent',
    'High': 'priority-high',
    'Medium': 'priority-medium',
    'Normal': 'priority-normal',
    'Low': 'priority-low',
  }
  return map[priority] || 'priority-low'
}

function taskStatusClass(status) {
  const map = {
    'Backlog': 'badge-default',
    'To Do': 'badge-primary',
    'In Progress': 'badge-warning',
    'In Review': 'badge-info',
    'Done': 'badge-success',
    'Cancelled': 'badge-danger',
  }
  return map[status] || 'badge-default'
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

function approvalStatusClass(status) {
  const map = {
    'Pending': 'approval-pending',
    'Ready for Review': 'approval-review',
    'Approved': 'approval-approved',
    'Changes Requested': 'approval-changes',
  }
  return map[status] || 'approval-pending'
}

async function markReadyForReview(sprint) {
  approvalActioning.value = sprint.name
  try {
    await call('next_pms.api.portal.mark_sprint_ready_for_review', { sprint: sprint.name })
    sprint.approval_status = 'Ready for Review'
  } catch (e) {
    console.error('Failed to mark sprint for review:', e)
    alert(e?.message || 'Failed to update sprint')
  } finally {
    approvalActioning.value = ''
  }
}

async function resetApproval(sprint) {
  if (!confirm('Reset approval status to Pending?')) return
  approvalActioning.value = sprint.name
  try {
    await call('next_pms.api.portal.reset_sprint_approval', { sprint: sprint.name })
    sprint.approval_status = 'Pending'
  } catch (e) {
    console.error('Failed to reset approval:', e)
    alert(e?.message || 'Failed to reset approval')
  } finally {
    approvalActioning.value = ''
  }
}
</script>

<style scoped>
.project-backlog {
  padding: 16px 0;
}

.backlog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
}

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

.backlog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sprint-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.sprint-section.drop-highlight {
  box-shadow: inset 0 0 0 2px rgba(37, 99, 235, 0.3);
  background: rgba(37, 99, 235, 0.02);
}

.backlog-section {
  border-style: dashed;
}

.sprint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-surface-active);
  border-bottom: 1px solid var(--border-default);
}

.sprint-info {
  display: flex;
  align-items: center;
  gap: 12px;
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

.sprint-task-count {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.sprint-progress {
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

.task-list {
  padding: 8px 12px;
}

.task-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 8px;
  border-radius: 8px;
  cursor: grab;
  transition: background 0.15s ease;
}

.task-row:hover {
  background: var(--bg-surface-active);
}

.task-row:active {
  cursor: grabbing;
}

.task-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.priority-critical {
  background: #EF4444;
}

.priority-urgent {
  background: #dc2626;
}

.priority-high {
  background: var(--color-warning);
}

.priority-medium {
  background: #FBBF24;
}

.priority-normal {
  background: #3b82f6;
}

.priority-low {
  background: var(--text-tertiary);
}

.task-title-link {
  font-size: 14px;
  color: var(--text-primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-title-link:hover {
  color: var(--color-primary);
}

.task-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

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

.status-badge-sm {
  padding: 2px 8px;
  font-size: 10px;
}

.badge-primary {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.badge-success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.badge-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.badge-info {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.badge-danger {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.badge-default {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
}

.assignee {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
}

.est-hours {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.no-tasks {
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 8px;
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
  transition: all 0.15s ease;
}

.btn-outline {
  background: var(--bg-surface);
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.btn-outline:hover {
  background: var(--color-primary-bg);
}

.sprint-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.add-task-btn {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.add-task-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

/* ── Sprint Approval Status ────────────────────────── */
.approval-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.approval-pending {
  background: var(--bg-surface-hover);
  color: var(--text-tertiary);
}

.approval-review {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.approval-approved {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.approval-changes {
  background: rgba(245, 158, 11, 0.1);
  color: #d97706;
}

.approval-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid;
  white-space: nowrap;
}

.approval-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-mark-review {
  background: rgba(59, 130, 246, 0.05);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
}

.btn-mark-review:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
}

.btn-reset-approval {
  background: var(--bg-surface);
  color: var(--text-secondary);
  border-color: var(--border-default);
}

.btn-reset-approval:hover:not(:disabled) {
  background: var(--bg-surface-hover);
  border-color: var(--text-tertiary);
}
</style>
