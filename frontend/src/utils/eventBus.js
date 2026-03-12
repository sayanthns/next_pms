/**
 * Simple event bus for cross-component communication.
 * Used to trigger data refreshes after mutations (create task, change status, etc.)
 */
const listeners = {}

export const eventBus = {
  on(event, callback) {
    if (!listeners[event]) listeners[event] = []
    listeners[event].push(callback)
  },

  off(event, callback) {
    if (!listeners[event]) return
    listeners[event] = listeners[event].filter(cb => cb !== callback)
  },

  emit(event, data) {
    if (!listeners[event]) return
    listeners[event].forEach(cb => cb(data))
  },
}

// Event names
export const EVENTS = {
  TASK_CREATED: 'task:created',
  TASK_UPDATED: 'task:updated',
  TASK_STATUS_CHANGED: 'task:status_changed',
  TASK_DELETED: 'task:deleted',
  PROJECT_UPDATED: 'project:updated',
  TIMER_STOPPED: 'timer:stopped',
  CHECKIN_CHANGED: 'checkin:changed',
}
