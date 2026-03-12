import { onMounted, onUnmounted } from 'vue'

export function useRealtime(event, callback) {
  onMounted(() => {
    if (window.frappe && window.frappe.realtime) {
      window.frappe.realtime.on(event, callback)
    }
  })
  onUnmounted(() => {
    if (window.frappe && window.frappe.realtime) {
      window.frappe.realtime.off(event, callback)
    }
  })
}

export function publishRealtime(event, data) {
  if (window.frappe && window.frappe.realtime) {
    window.frappe.realtime.emit(event, data)
  }
}

export function joinRoom(room) {
  if (window.frappe && window.frappe.realtime) {
    window.frappe.realtime.emit('join_room', room)
  }
}

export function leaveRoom(room) {
  if (window.frappe && window.frappe.realtime) {
    window.frappe.realtime.emit('leave_room', room)
  }
}
