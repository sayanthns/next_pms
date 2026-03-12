<template>
  <div
    class="kanban-card"
    draggable="true"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
    @click="$emit('click', task)"
  >
    <!-- Row 1: Project tag (optional) + Priority badge -->
    <div class="card-header-row">
      <span
        v-if="showProjectTag && task.project"
        class="project-tag"
        :title="task.project"
      >
        {{ task.project }}
      </span>
      <span class="header-spacer"></span>
      <span class="priority-badge" :class="priorityClass">
        {{ priorityLabel }}
      </span>
    </div>

    <!-- Row 2: Task title (2 line clamp) -->
    <div class="card-title">{{ task.task_title }}</div>

    <!-- Row 3: Task ID + Task Type chip -->
    <div class="card-meta-row">
      <span class="task-id">{{ task.name }}</span>
      <span v-if="task.task_type" class="meta-separator">|</span>
      <span v-if="task.task_type" class="task-type-chip">{{ task.task_type }}</span>
    </div>

    <!-- Row 4: Due date, Avatar stack, Timer button -->
    <div class="card-bottom">
      <div class="card-bottom-left">
        <span
          v-if="task.due_date"
          class="due-date-chip"
          :class="dueDateClass"
        >
          {{ formatDueDate(task.due_date) }}
        </span>

        <!-- Multiple assignee avatars (stacked) -->
        <div v-if="assigneeList.length" class="avatar-stack">
          <span
            v-for="(user, idx) in assigneeList.slice(0, 3)"
            :key="user.user || user"
            class="avatar-initials"
            :class="'avatar-color-' + (idx % 5)"
            :title="user.full_name || user.user || user"
            :style="{ zIndex: 3 - idx }"
          >
            {{ getInitials(user.full_name || user.user || user) }}
          </span>
          <span
            v-if="assigneeList.length > 3"
            class="avatar-initials avatar-more"
            :title="assigneeList.length - 3 + ' more'"
          >
            +{{ assigneeList.length - 3 }}
          </span>
        </div>
      </div>

      <button
        class="mini-timer-btn"
        title="Start timer"
        @click.stop="$emit('start-timer', task)"
      >
        &#9654;
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    required: true,
  },
  showProjectTag: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['click', 'start-timer'])

// Compute assignees list from either child table or legacy field
const assigneeList = computed(() => {
  if (props.task.assignees && props.task.assignees.length) {
    return props.task.assignees
  }
  // Fallback to legacy assigned_to
  if (props.task.assigned_to) {
    return [{ user: props.task.assigned_to, full_name: props.task.assigned_to }]
  }
  return []
})

const priorityClass = computed(() => {
  const p = (props.task.priority || '').toLowerCase()
  if (p === 'critical' || p === 'urgent') return 'priority-critical'
  if (p === 'high') return 'priority-high'
  if (p === 'medium') return 'priority-medium'
  return 'priority-low'
})

const priorityLabel = computed(() => {
  const p = (props.task.priority || '').toLowerCase()
  if (p === 'critical') return 'Critical'
  if (p === 'urgent') return 'Urgent'
  if (p === 'high') return 'High'
  if (p === 'medium') return 'Medium'
  if (p === 'low') return 'Low'
  // Capitalize first letter for any other value
  if (props.task.priority) {
    return props.task.priority.charAt(0).toUpperCase() + props.task.priority.slice(1).toLowerCase()
  }
  return 'Low'
})

const dueDateClass = computed(() => {
  if (!props.task.due_date) return ''
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(props.task.due_date)
  due.setHours(0, 0, 0, 0)
  const diffDays = Math.floor((due - today) / (1000 * 60 * 60 * 24))

  if (diffDays < 0) return 'due-overdue'
  if (diffDays === 0) return 'due-today'
  if (diffDays <= 3) return 'due-upcoming'
  return 'due-normal'
})

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function formatDueDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(dateStr)
  due.setHours(0, 0, 0, 0)
  const diffDays = Math.floor((due - today) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays === -1) return 'Yesterday'
  if (diffDays < -1) return `${Math.abs(diffDays)}d overdue`
  if (diffDays <= 7) return `${diffDays}d left`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function onDragStart(event) {
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('application/json', JSON.stringify({
    taskName: props.task.name,
    taskTitle: props.task.task_title,
    currentStatus: props.task.status,
  }))
  event.target.classList.add('dragging')
}

function onDragEnd(event) {
  event.target.classList.remove('dragging')
}
</script>

<style scoped>
.kanban-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-left: 3px solid transparent;
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: box-shadow 0.18s ease, border-color 0.18s ease, border-left-color 0.18s ease, transform 0.1s ease;
  user-select: none;
}

.kanban-card:hover {
  border-color: #d1d5db;
  border-left-color: #6366f1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
}

.kanban-card.dragging {
  opacity: 0.5;
  transform: rotate(2deg);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* Row 1: Header — project tag + priority badge */
.card-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.header-spacer {
  flex: 1;
}

/* Project tag */
.project-tag {
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 6px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 1;
}

/* Priority badge pill */
.priority-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.priority-critical {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.priority-high {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.priority-medium {
  background: rgba(251, 191, 36, 0.1);
  color: #D97706;
}

.priority-low {
  background: rgba(156, 163, 175, 0.1);
  color: #9ca3af;
}

/* Row 2: Title */
.card-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #1e1e2e;
  line-height: 1.45;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Row 3: Task ID + Task Type meta row */
.card-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.task-id {
  font-size: 11px;
  font-weight: 500;
  color: #9ca3af;
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
}

.meta-separator {
  font-size: 10px;
  color: #d1d5db;
  user-select: none;
}

.task-type-chip {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #6b7280;
}

/* Row 4: Bottom row */
.card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-bottom-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

/* Stacked avatars */
.avatar-stack {
  display: flex;
  align-items: center;
}

.avatar-stack .avatar-initials {
  margin-left: -6px;
  border: 2px solid #fff;
}

.avatar-stack .avatar-initials:first-child {
  margin-left: 0;
}

.avatar-initials {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: white;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

.avatar-color-0 { background: #6366f1; }
.avatar-color-1 { background: #7C3AED; }
.avatar-color-2 { background: #059669; }
.avatar-color-3 { background: #D97706; }
.avatar-color-4 { background: #DC2626; }

.avatar-more {
  background: #9ca3af !important;
  font-size: 9px;
  font-weight: 700;
}

/* Due date chip */
.due-date-chip {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.due-overdue {
  background: #fef2f2;
  color: #EF4444;
  border: 1px solid #fecaca;
}

.due-today {
  background: #fff7ed;
  color: #F59E0B;
  border: 1px solid #fed7aa;
}

.due-upcoming {
  background: #fffbeb;
  color: #d97706;
  border: 1px solid #fde68a;
}

.due-normal {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

/* Mini timer button */
.mini-timer-btn {
  width: 26px;
  height: 26px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  color: #6366f1;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s;
  flex-shrink: 0;
}

.mini-timer-btn:hover {
  background: rgba(99, 102, 241, 0.05);
  border-color: #6366f1;
}
</style>
