<template>
  <div class="project-gantt">
    <div class="gantt-header">
      <div v-if="!embedded">
        <h1 class="page-title">Gantt Chart</h1>
        <p class="page-subtitle">{{ id }}</p>
      </div>
      <div class="view-toggle">
        <button
          v-for="mode in viewModes"
          :key="mode"
          class="toggle-btn"
          :class="{ active: currentViewMode === mode }"
          @click="setViewMode(mode)"
        >
          {{ mode }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading Gantt data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p class="error-text">{{ error }}</p>
      <button class="btn btn-primary" @click="loadGanttData">Retry</button>
    </div>

    <!-- Gantt Chart Container -->
    <div v-else-if="ganttAvailable && ganttTasks.length" class="gantt-wrapper">
      <div ref="ganttContainer" class="gantt-chart-container"></div>
    </div>

    <!-- Table Fallback -->
    <div v-else-if="ganttTasks.length" class="table-fallback">
      <table class="gantt-table">
        <thead>
          <tr>
            <th>Task</th>
            <th>Start</th>
            <th>End</th>
            <th>Status</th>
            <th>Progress</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="task in ganttTasks"
            :key="task.id"
            class="table-row clickable"
            @click="openTask(task.id)"
          >
            <td class="task-name-cell">{{ task.name }}</td>
            <td>{{ formatDate(task.start) }}</td>
            <td>{{ formatDate(task.end) }}</td>
            <td>
              <span class="status-badge" :class="statusClass(task.status)">
                {{ task.status }}
              </span>
            </td>
            <td>
              <div class="table-progress">
                <div class="progress-bar-mini">
                  <div
                    class="progress-fill-mini"
                    :style="{ width: task.progress + '%' }"
                  ></div>
                </div>
                <span class="progress-text">{{ task.progress }}%</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- No Data -->
    <div v-else class="empty-container">
      <p class="empty-text">No tasks with dates found for this project.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '@/utils/frappe'
import Gantt from 'frappe-gantt'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
  embedded: { type: Boolean, default: false },
})

const router = useRouter()

const ganttTasks = ref([])
const loading = ref(false)
const error = ref(null)
const ganttAvailable = ref(!!Gantt)
const currentViewMode = ref('Week')
const ganttContainer = ref(null)

const viewModes = ['Day', 'Week', 'Month']

let GanttClass = Gantt
let ganttInstance = null

onMounted(async () => {
  await loadGanttData()
})

watch(currentViewMode, () => {
  if (ganttInstance) {
    ganttInstance.change_view_mode(currentViewMode.value)
  }
})

async function loadGanttData() {
  loading.value = true
  error.value = null
  try {
    const result = await call('next_pms.api.gantt.get_gantt_data', {
      project: props.id,
    })
    ganttTasks.value = (result || []).map((t) => ({
      id: t.id || t.name,
      name: t.name || t.task_title || t.title,
      start: t.start || t.start_date,
      end: t.end || t.end_date,
      progress: t.progress || 0,
      status: t.status || 'Open',
      dependencies: t.dependencies || '',
    }))

  } catch (e) {
    console.error('Failed to load Gantt data:', e)
    error.value = 'Failed to load Gantt data. Please try again.'
  } finally {
    loading.value = false
  }

  // Render after loading is false so the container is in the DOM
  if (ganttAvailable.value && ganttTasks.value.length) {
    await nextTick()
    renderGanttChart()
  }
}

function renderGanttChart() {
  if (!GanttClass || !ganttContainer.value || !ganttTasks.value.length) return

  // Clear previous instance
  ganttContainer.value.innerHTML = ''

  const tasks = ganttTasks.value.map((t) => ({
    id: t.id,
    name: t.name,
    start: t.start,
    end: t.end,
    progress: t.progress,
    dependencies: t.dependencies,
  }))

  try {
    ganttInstance = new GanttClass(ganttContainer.value, tasks, {
      view_mode: currentViewMode.value,
      date_format: 'YYYY-MM-DD',
      on_click: (task) => {
        openTask(task.id)
      },
      on_date_change: async (task, start, end) => {
        try {
          await call('next_pms.api.gantt.update_task_dates', {
            task: task.id,
            start_date: formatDateISO(start),
            end_date: formatDateISO(end),
          })
        } catch (e) {
          console.error('Failed to update task dates:', e)
        }
      },
      on_progress_change: (task, progress) => {
        // Optional: handle progress change
      },
      custom_popup_html: (task) => {
        return `
          <div class="gantt-popup">
            <h4>${task.name}</h4>
            <p>${formatDate(task._start)} - ${formatDate(task._end)}</p>
            <p>Progress: ${task.progress}%</p>
          </div>
        `
      },
    })
  } catch (e) {
    console.error('Failed to create Gantt chart:', e)
    // Fall back to table view
    ganttAvailable.value = false
  }
}

function setViewMode(mode) {
  currentViewMode.value = mode
}

function openTask(name) {
  router.push(`/task/${name}`)
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatDateISO(date) {
  if (!date) return ''
  const d = new Date(date)
  return d.toISOString().split('T')[0]
}

function statusClass(status) {
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
</script>

<style scoped>
.project-gantt {
  padding: 16px 0;
}

.gantt-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
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

.view-toggle {
  display: flex;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 3px;
}

.toggle-btn {
  padding: 6px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn.active {
  background: #fff;
  color: #6366f1;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.toggle-btn:hover:not(.active) {
  color: #374151;
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
  border: 3px solid #e5e7eb;
  border-top-color: #6366f1;
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
  background: #6366f1;
  color: #fff;
}

.btn-primary:hover {
  background: #4f46e5;
}

.gantt-wrapper {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: auto;
}

.gantt-chart-container {
  min-height: 400px;
}

/* Table Fallback */
.table-fallback {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.gantt-table {
  width: 100%;
  border-collapse: collapse;
}

.gantt-table thead {
  background: #f9fafb;
}

.gantt-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #e5e7eb;
}

.gantt-table td {
  padding: 12px 16px;
  font-size: 14px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
}

.table-row.clickable {
  cursor: pointer;
  transition: background 0.15s ease;
}

.table-row.clickable:hover {
  background: #f9fafb;
}

.task-name-cell {
  font-weight: 500;
  color: #1a1a2e;
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

.badge-primary {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
}

.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.badge-info {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.badge-danger {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.badge-default {
  background: #f3f4f6;
  color: #6b7280;
}

.table-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar-mini {
  flex: 1;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
  min-width: 60px;
}

.progress-fill-mini {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 12px;
  font-weight: 600;
  color: #10b981;
  min-width: 32px;
}

.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.empty-text {
  color: #9ca3af;
  font-size: 14px;
}
</style>
