import { onMounted, onUnmounted } from 'vue'
import { eventBus, EVENTS } from './eventBus'

function rt() {
  return window.frappe?.realtime || null
}

/**
 * Vue composable: subscribe to a single Frappe realtime event
 * for the lifetime of the component.
 */
export function useRealtime(event, callback) {
  onMounted(() => {
    if (rt()) rt().on(event, callback)
  })
  onUnmounted(() => {
    if (rt()) rt().off(event, callback)
  })
}

/**
 * Vue composable: subscribe to all PMS-related realtime events
 * and call refreshFn when any fire. Also listens to local eventBus
 * for changes made by the current user.
 *
 * @param {Function} refreshFn  - called with optional event data
 * @param {Object}   options    - { project: 'PROJ-XXX' } to filter
 */
export function useAutoRefresh(refreshFn, options = {}) {
  let unsubs = []

  function handleRealtimeEvent(data) {
    // If project filter is set, only refresh for matching project
    if (options.project && data?.project && data.project !== options.project) return
    refreshFn(data)
  }

  onMounted(() => {
    // Frappe Socket.IO events (from other users)
    const events = ['task_updated', 'task_assigned', 'pms_notification']
    events.forEach(evt => {
      if (rt()) {
        rt().on(evt, handleRealtimeEvent)
        unsubs.push(() => rt()?.off(evt, handleRealtimeEvent))
      }
    })

    // Local event bus (from current user's actions)
    const localHandler = () => refreshFn()
    const busEvents = [
      EVENTS.TASK_CREATED,
      EVENTS.TASK_STATUS_CHANGED,
      EVENTS.TASK_UPDATED,
      EVENTS.TIMER_STOPPED,
    ]
    busEvents.forEach(evt => {
      eventBus.on(evt, localHandler)
      unsubs.push(() => eventBus.off(evt, localHandler))
    })
  })

  onUnmounted(() => {
    unsubs.forEach(fn => fn())
    unsubs = []
  })
}

export function publishRealtime(event, data) {
  if (rt()) rt().emit(event, data)
}

export function joinRoom(room) {
  if (rt()) rt().emit('join_room', room)
}

export function leaveRoom(room) {
  if (rt()) rt().emit('leave_room', room)
}
