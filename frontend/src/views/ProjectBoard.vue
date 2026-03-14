<template>
  <div class="project-board">
    <div v-if="!embedded" class="board-header">
      <div>
        <h1 class="page-title">Kanban Board</h1>
        <p class="page-subtitle">{{ id }}</p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="taskStore.loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading tasks...</p>
    </div>

    <!-- Board -->
    <div v-else class="kanban-container">
      <div
        v-for="column in columns"
        :key="column.status"
        class="kanban-column"
        @dragover.prevent="onDragOver($event, column.status)"
        @dragleave="onDragLeave($event, column.status)"
        @drop="onDrop($event, column.status)"
        :class="{ 'drop-highlight': dragOverColumn === column.status }"
      >
        <div class="column-header" :style="{ borderTopColor: column.color }">
          <div class="column-title-row">
            <span class="column-dot" :style="{ background: column.color }"></span>
            <h3 class="column-title">{{ column.label }}</h3>
          </div>
          <div class="column-header-actions">
            <span class="column-count">{{ getColumnTasks(column.status).length }}</span>
            <button v-if="canCreateTask" class="column-add-btn" @click="openCreateTask(column.status)" title="Add task">+</button>
          </div>
        </div>

        <div class="column-body">
          <div
            v-for="task in getColumnTasks(column.status)"
            :key="task.name"
            class="card-wrapper"
            draggable="true"
            @dragstart="onDragStart($event, task)"
            :class="{ 'flash-done': flashTask === task.name }"
          >
            <KanbanCard
              :task="task"
              @click="openTask(task.name)"
              @start-timer="onStartTimer(task)"
            />
            <button
              v-if="task.status !== 'Done'"
              class="quick-done-btn"
              title="Mark as Done"
              @click.stop="markDone(task)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </button>
          </div>

          <div v-if="!getColumnTasks(column.status).length" class="column-empty">
            <p>No tasks</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Task Modal -->
    <CreateTaskModal
      :show="showCreateTask"
      :projectId="id"
      :defaultStatus="createTaskStatus"
      @close="showCreateTask = false"
      @created="onTaskCreated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/store/tasks'
import { useTimerStore } from '@/store/timer'
import { useSettingsStore } from '@/store/settings'
import { useRealtime } from '@/utils/realtime'
import KanbanCard from '@/components/KanbanCard.vue'
import CreateTaskModal from '@/components/CreateTaskModal.vue'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
  embedded: { type: Boolean, default: false },
})

const router = useRouter()
const taskStore = useTaskStore()
const timerStore = useTimerStore()
const settingsStore = useSettingsStore()
const canCreateTask = computed(() => settingsStore.featurePermissions.create_task !== false)

const dragOverColumn = ref(null)
const flashTask = ref(null)
const showCreateTask = ref(false)
const createTaskStatus = ref('Backlog')

function openCreateTask(status) {
  createTaskStatus.value = status
  showCreateTask.value = true
}

function onTaskCreated() {
  showCreateTask.value = false
  taskStore.fetchTasks(props.id)
}

const columns = [
  { status: 'Backlog', label: 'Backlog', color: '#9ca3af' },
  { status: 'To Do', label: 'To Do', color: '#3b82f6' },
  { status: 'In Progress', label: 'In Progress', color: '#F59E0B' },
  { status: 'In Review', label: 'In Review', color: '#3b82f6' },
  { status: 'Done', label: 'Done', color: '#10b981' },
]

// Real-time: refresh board when tasks change via Socket.IO
useRealtime('task_updated', (data) => {
  if (data?.project === props.id) taskStore.fetchTasks(props.id)
})
useRealtime('task_assigned', (data) => {
  if (data?.project === props.id) taskStore.fetchTasks(props.id)
})

onMounted(() => {
  taskStore.fetchTasks(props.id)
})

function getColumnTasks(status) {
  return taskStore.tasks.filter((t) => t.status === status)
}

function openTask(name) {
  router.push(`/task/${name}`)
}

// Drag and Drop
function onDragStart(event, task) {
  event.dataTransfer.setData('text/plain', task.name)
  event.dataTransfer.effectAllowed = 'move'
}

function onDragOver(event, status) {
  event.dataTransfer.dropEffect = 'move'
  dragOverColumn.value = status
}

function onDragLeave(event, status) {
  // Only clear if leaving the column entirely
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX
  const y = event.clientY
  if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
    dragOverColumn.value = null
  }
}

async function onDrop(event, newStatus) {
  dragOverColumn.value = null
  const taskName = event.dataTransfer.getData('text/plain')
  if (!taskName) return

  const task = taskStore.tasks.find((t) => t.name === taskName)
  if (task && task.status !== newStatus) {
    await taskStore.updateTaskStatus(taskName, newStatus)
  }
}

async function markDone(task) {
  flashTask.value = task.name
  await taskStore.updateTaskStatus(task.name, 'Done')
  setTimeout(() => {
    flashTask.value = null
  }, 600)
}

function onStartTimer(task) {
  if (timerStore.isRunning) {
    timerStore.stopTimer().then(() => {
      timerStore.startTimer(task.name)
    })
  } else {
    timerStore.startTimer(task.name)
  }
}
</script>

<style scoped>
.project-board {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.board-header {
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

.kanban-container {
  display: flex;
  gap: 16px;
  flex: 1;
  overflow-x: auto;
  padding-bottom: 16px;
}

.kanban-column {
  flex: 0 0 280px;
  background: var(--bg-surface-active);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 180px);
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.kanban-column.drop-highlight {
  background: var(--color-primary-bg);
  box-shadow: inset 0 0 0 2px rgba(37, 99, 235, 0.3);
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-top: 3px solid transparent;
  border-radius: 12px 12px 0 0;
}

.column-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.column-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.column-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.column-count {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 6px;
  background: var(--border-default);
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.column-add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1;
}

.column-add-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.column-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-wrapper {
  position: relative;
  cursor: grab;
  transition: transform 0.15s ease;
}

.card-wrapper:active {
  cursor: grabbing;
  transform: rotate(2deg);
  opacity: 0.85;
}

.card-wrapper.flash-done {
  animation: flashGreen 0.6s ease;
}

@keyframes flashGreen {
  0% { background: transparent; }
  30% { background: rgba(16, 185, 129, 0.2); border-radius: 10px; }
  100% { background: transparent; }
}

.quick-done-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1.5px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
  z-index: 2;
}

.card-wrapper:hover .quick-done-btn {
  opacity: 1;
}

.quick-done-btn:hover {
  border-color: var(--color-success);
  color: var(--color-success);
  background: var(--color-success-bg);
}

.column-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.column-empty p {
  margin: 0;
}
</style>
