import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { call } from '@/utils/frappe'

// Notification sound — short pleasant tone (base64 encoded tiny mp3 is too large, use Web Audio API)
function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    // Pleasant two-tone chime
    oscillator.frequency.setValueAtTime(587.33, ctx.currentTime) // D5
    oscillator.frequency.setValueAtTime(783.99, ctx.currentTime + 0.15) // G5
    oscillator.type = 'sine'

    gainNode.gain.setValueAtTime(0.3, ctx.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4)

    oscillator.start(ctx.currentTime)
    oscillator.stop(ctx.currentTime + 0.4)
  } catch (e) {
    // Audio not available, silently skip
  }
}

function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

function showBrowserNotification(title, body, url) {
  if ('Notification' in window && Notification.permission === 'granted') {
    const notification = new Notification(title, {
      body,
      icon: '/assets/next_pms/frontend/assets/logo.svg',
      tag: 'pms-notification',
      requireInteraction: false,
    })
    notification.onclick = () => {
      window.focus()
      if (url) window.location.hash = url
      notification.close()
    }
    // Auto close after 5 seconds
    setTimeout(() => notification.close(), 5000)
  }
}

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref([])
  const loading = ref(false)
  const previousCount = ref(0)

  const unreadCount = computed(() => notifications.value.length)

  async function fetchNotifications() {
    loading.value = true
    try {
      const data = await call('next_pms.api.notifications.get_notifications')
      const newNotifications = data || []

      // Check if there are new notifications since last fetch
      if (newNotifications.length > previousCount.value && previousCount.value > 0) {
        // New notification arrived
        const latest = newNotifications[0]
        playNotificationSound()
        showBrowserNotification(
          'Next PMS',
          latest.subject || 'You have a new notification',
          latest.document_name ? `#/task/${latest.document_name}` : null
        )
      }

      previousCount.value = newNotifications.length
      notifications.value = newNotifications
    } catch (error) {
      console.error('Failed to fetch notifications:', error)
      notifications.value = []
    } finally {
      loading.value = false
    }
  }

  async function markRead(notificationName) {
    try {
      await call('next_pms.api.notifications.mark_notification_read', { notification: notificationName })
      notifications.value = notifications.value.filter(n => n.name !== notificationName)
      previousCount.value = notifications.value.length
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }

  async function markAllRead() {
    try {
      await call('next_pms.api.notifications.mark_all_read')
      notifications.value = []
      previousCount.value = 0
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  }

  // Auto-refresh every 30 seconds
  let refreshInterval = null
  function startAutoRefresh() {
    requestNotificationPermission()
    fetchNotifications()
    refreshInterval = setInterval(fetchNotifications, 30000)

    // Listen for Frappe realtime push notifications
    if (window.frappe && window.frappe.realtime) {
      window.frappe.realtime.on('pms_notification', (data) => {
        playNotificationSound()
        showBrowserNotification(
          data.type === 'task_status_changed'
            ? `Task ${data.new_status}: ${data.task_title}`
            : 'Next PMS',
          data.changed_by
            ? `${data.changed_by} changed status to ${data.new_status}`
            : 'You have a new notification',
          data.task ? `#/task/${data.task}` : null
        )
        // Refresh notification list
        fetchNotifications()
      })
    }
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
    if (window.frappe && window.frappe.realtime) {
      window.frappe.realtime.off('pms_notification')
    }
  }

  return {
    notifications,
    loading,
    unreadCount,
    fetchNotifications,
    markRead,
    markAllRead,
    startAutoRefresh,
    stopAutoRefresh,
  }
})
