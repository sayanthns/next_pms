<template>
  <div class="gantt-wrapper">
    <div class="gantt-controls">
      <div class="gantt-view-modes">
        <button
          v-for="mode in viewModes"
          :key="mode"
          :class="['view-mode-btn', { active: currentMode === mode }]"
          @click="changeViewMode(mode)"
        >
          {{ mode }}
        </button>
      </div>
      <div class="gantt-color-by">
        <label>Color by:</label>
        <select v-model="colorBy" @change="refreshChart">
          <option value="priority">Priority</option>
          <option value="status">Status</option>
          <option value="assignee">Assignee</option>
        </select>
      </div>
    </div>
    <div ref="ganttContainer" class="gantt-container"></div>
    <div v-if="!tasks || !tasks.length" class="gantt-empty">
      <p>No tasks with dates to display.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

const props = defineProps({
  tasks: {
    type: Array,
    default: () => [],
  },
  onDateChange: {
    type: Function,
    default: null,
  },
  onTaskClick: {
    type: Function,
    default: null,
  },
})

const viewModes = ['Day', 'Week', 'Month']
const currentMode = ref('Week')
const colorBy = ref('priority')
const ganttContainer = ref(null)

let GanttClass = null
let ganttInstance = null

// Color maps
const priorityColors = {
  Critical: '#EF4444',
  Urgent: '#dc2626',
  High: '#F97316',
  Medium: '#F59E0B',
  Normal: '#3b82f6',
  Low: '#94A3B8',
}

const statusColors = {
  Backlog: '#9CA3AF',
  'To Do': '#3B82F6',
  'In Progress': '#F59E0B',
  'In Review': '#8B5CF6',
  Done: '#10b981',
  Cancelled: '#EF4444',
}

const assigneePalette = [
  '#6366F1', '#3B82F6', '#8B5CF6', '#EC4899', '#14B8A6',
  '#F97316', '#10B981', '#EF4444', '#06B6D4', '#84CC16',
  '#E11D48', '#0EA5E9', '#D946EF', '#F59E0B', '#0D9488',
]

const assigneeColorMap = {}

function getAssigneeColor(assignee) {
  if (!assignee) return '#94A3B8'
  if (!assigneeColorMap[assignee]) {
    const idx = Object.keys(assigneeColorMap).length % assigneePalette.length
    assigneeColorMap[assignee] = assigneePalette[idx]
  }
  return assigneeColorMap[assignee]
}

function getTaskColor(task) {
  if (colorBy.value === 'priority') {
    return priorityColors[task.priority] || priorityColors.Low
  }
  if (colorBy.value === 'status') {
    return statusColors[task.status] || statusColors.Backlog
  }
  if (colorBy.value === 'assignee') {
    return getAssigneeColor(task.assigned_to)
  }
  return '#2563EB'
}

function getInitials(email) {
  if (!email) return ''
  const name = email.split('@')[0]
  const parts = name.split(/[._-]/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function buildGanttTasks() {
  return (props.tasks || [])
    .filter((t) => t.start_date && t.end_date)
    .map((t) => ({
      id: t.name || t.id,
      name: t.task_title || t.title || t.name,
      start: t.start_date || t.start,
      end: t.end_date || t.end,
      progress: t.progress || 0,
      dependencies: t.dependencies || '',
      custom_class: `bar-color-${colorBy.value}`,
      _original: t,
    }))
}

async function initGantt() {
  try {
    const module = await import('frappe-gantt')
    GanttClass = module.default || module
  } catch {
    GanttClass = null
  }
}

function renderChart() {
  if (!GanttClass || !ganttContainer.value) return

  const ganttTasks = buildGanttTasks()
  if (!ganttTasks.length) return

  // Clear previous instance
  ganttContainer.value.innerHTML = ''

  ganttInstance = new GanttClass(ganttContainer.value, ganttTasks, {
    view_mode: currentMode.value,
    date_format: 'YYYY-MM-DD',
    on_click: (task) => {
      if (props.onTaskClick) {
        props.onTaskClick(task)
      }
    },
    on_date_change: (task, start, end) => {
      if (props.onDateChange) {
        const startISO = formatDateISO(start)
        const endISO = formatDateISO(end)
        props.onDateChange(task, startISO, endISO)
      }
    },
    on_progress_change: () => {
      // Optional progress change handler
    },
    custom_popup_html: (task) => {
      const original = task._original || {}
      const assignee = original.assigned_to ? getInitials(original.assigned_to) : ''
      const priority = original.priority || ''
      const status = original.status || ''
      return `
        <div class="gantt-popup-custom">
          <div class="gantt-popup-title">${task.name}</div>
          <div class="gantt-popup-meta">
            <span>${formatDateDisplay(task._start)} - ${formatDateDisplay(task._end)}</span>
          </div>
          <div class="gantt-popup-details">
            ${priority ? `<span class="gantt-popup-priority">${priority}</span>` : ''}
            ${status ? `<span class="gantt-popup-status">${status}</span>` : ''}
            ${assignee ? `<span class="gantt-popup-assignee">${assignee}</span>` : ''}
          </div>
          <div class="gantt-popup-progress">Progress: ${task.progress}%</div>
        </div>
      `
    },
  })

  // Apply custom colors to bars after render
  applyBarColors(ganttTasks)
}

function applyBarColors(ganttTasks) {
  nextTick(() => {
    if (!ganttContainer.value) return
    const bars = ganttContainer.value.querySelectorAll('.bar-wrapper')
    bars.forEach((bar, index) => {
      if (index < ganttTasks.length) {
        const task = ganttTasks[index]
        const color = getTaskColor(task._original || {})
        const barEl = bar.querySelector('.bar')
        const progressEl = bar.querySelector('.bar-progress')
        const labelEl = bar.querySelector('.bar-label')

        if (barEl) {
          barEl.style.fill = color
          barEl.style.opacity = '0.35'
          barEl.style.rx = '4'
          barEl.style.ry = '4'
        }
        if (progressEl) {
          progressEl.style.fill = color
          progressEl.style.opacity = '1'
          progressEl.style.rx = '4'
          progressEl.style.ry = '4'
        }
        if (labelEl) {
          labelEl.style.fill = '#374151'
          labelEl.style.fontWeight = '500'
          labelEl.style.fontSize = '12px'
        }
      }
    })
  })
}

function changeViewMode(mode) {
  currentMode.value = mode
  if (ganttInstance) {
    ganttInstance.change_view_mode(mode)
  }
}

function refreshChart() {
  renderChart()
}

function formatDateISO(date) {
  if (!date) return ''
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDateDisplay(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return String(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

onMounted(async () => {
  await initGantt()
  if (props.tasks && props.tasks.length) {
    renderChart()
  }
})

onBeforeUnmount(() => {
  ganttInstance = null
})

watch(
  () => props.tasks,
  () => {
    renderChart()
  },
  { deep: true }
)

watch(colorBy, () => {
  renderChart()
})
</script>

<style scoped>
.gantt-wrapper {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
}

.gantt-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-surface-active);
  border-bottom: 1px solid var(--border-default);
}

.gantt-view-modes {
  display: flex;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 2px;
}

.view-mode-btn {
  padding: 6px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.view-mode-btn.active {
  background: #2563EB;
  color: #fff;
  font-weight: 600;
}

.view-mode-btn:hover:not(.active) {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.gantt-color-by {
  display: flex;
  align-items: center;
  gap: 8px;
}

.gantt-color-by label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.gantt-color-by select {
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s ease;
}

.gantt-color-by select:focus {
  border-color: var(--color-primary);
}

.gantt-container {
  min-height: 300px;
  overflow-x: auto;
  padding: 10px 0;
}

.gantt-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--text-tertiary);
  font-size: 14px;
}
</style>

<style>
/* Global styles for frappe-gantt overrides */
.gantt-wrapper .gantt .grid-header {
  fill: #f9fafb;
}

.gantt-wrapper .gantt .grid-row {
  fill: #fff;
}

.gantt-wrapper .gantt .grid-row:nth-child(even) {
  fill: #fafafa;
}

.gantt-wrapper .gantt .row-line {
  stroke: #f3f4f6;
}

.gantt-wrapper .gantt .tick {
  stroke: #f0f0f0;
  stroke-dasharray: none;
}

.gantt-wrapper .gantt .today-highlight {
  fill: rgba(37, 99, 235, 0.06);
}

.gantt-wrapper .gantt .bar {
  rx: 4;
  ry: 4;
}

.gantt-wrapper .gantt .bar-progress {
  rx: 4;
  ry: 4;
}

.gantt-wrapper .gantt .bar-label {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 12px;
  font-weight: 500;
  fill: #374151;
}

.gantt-wrapper .gantt .bar-label.big {
  font-size: 12px;
  fill: #fff;
}

.gantt-wrapper .gantt .handle {
  fill: rgba(37, 99, 235, 0.6);
}

.gantt-wrapper .gantt .upper-text,
.gantt-wrapper .gantt .lower-text {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 12px;
  fill: #6b7280;
  font-weight: 500;
}

.gantt-wrapper .gantt .upper-text {
  font-weight: 600;
  fill: #374151;
}

.gantt-wrapper .gantt .arrow {
  stroke: #d1d5db;
  stroke-width: 1.5;
}

/* Custom popup */
.gantt-popup-custom {
  padding: 12px 16px;
  min-width: 180px;
}

.gantt-popup-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
  line-height: 1.3;
}

.gantt-popup-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.gantt-popup-details {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.gantt-popup-priority,
.gantt-popup-status {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
}

.gantt-popup-assignee {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 9px;
  font-weight: 600;
}

.gantt-popup-progress {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 500;
}

/* Popup container override */
.gantt-wrapper .popup-wrapper {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.gantt-wrapper .popup-wrapper .pointer {
  display: none;
}

.gantt-wrapper .popup-wrapper .title {
  display: none;
}
</style>
