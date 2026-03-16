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
      if (url) {
        // Use proper navigation for HTML5 history mode router
        const fullPath = url.startsWith('/next-pms') ? url : '/next-pms' + url
        window.location.href = fullPath
      }
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
        const notifUrl = latest.document_name
          ? (latest.document_type === 'PMS Project'
            ? `/project/${latest.document_name}`
            : `/task/${latest.document_name}`)
          : null
        showBrowserNotification(
          'Next PMS',
          latest.subject || 'You have a new notification',
          notifUrl
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

  // Auto-refresh every 30 seconds, pauses when tab is hidden
  let refreshInterval = null
  let _visibilityHandler = null

  async function subscribeToPush() {
    try {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) return

      // Get VAPID public key from server
      const vapidKey = await call('next_pms.api.push.get_vapid_public_key')
      if (!vapidKey) return

      // Wait for service worker to be ready
      const registration = await navigator.serviceWorker.ready

      // Check if already subscribed
      let subscription = await registration.pushManager.getSubscription()
      if (!subscription) {
        // Convert VAPID key from base64url to Uint8Array
        const padding = '='.repeat((4 - vapidKey.length % 4) % 4)
        const base64 = (vapidKey + padding).replace(/-/g, '+').replace(/_/g, '/')
        const rawData = atob(base64)
        const applicationServerKey = new Uint8Array(rawData.length)
        for (let i = 0; i < rawData.length; i++) {
          applicationServerKey[i] = rawData.charCodeAt(i)
        }

        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey,
        })
      }

      // Send subscription to server
      await call('next_pms.api.push.save_push_subscription', {
        subscription: JSON.stringify(subscription.toJSON()),
      })
    } catch (e) {
      console.warn('Push subscription failed:', e)
    }
  }

  function startAutoRefresh() {
    requestNotificationPermission()
    fetchNotifications()
    _startPolling()

    // Subscribe to push notifications (non-blocking)
    subscribeToPush()

    // Pause polling when tab is hidden, resume when visible
    _visibilityHandler = () => {
      if (document.visibilityState === 'visible') {
        fetchNotifications() // immediate fetch on tab focus
        _startPolling()
      } else {
        _stopPolling()
      }
    }
    document.addEventListener('visibilitychange', _visibilityHandler)

    // Listen for Frappe realtime push notifications
    if (window.frappe && window.frappe.realtime) {
      window.frappe.realtime.on('pms_notification', (data) => {
        playNotificationSound()

        // Build notification title and body based on type
        let title = 'Next PMS'
        let body = 'You have a new notification'
        if (data.type === 'task_status_changed') {
          title = `Task ${data.new_status}: ${data.task_title}`
          body = `${data.changed_by || 'Someone'} changed status to ${data.new_status}`
        } else if (data.type === 'task_assigned') {
          title = `Task Assigned: ${data.task_title}`
          body = `${data.changed_by || 'Someone'} assigned you a task`
        }

        showBrowserNotification(
          title,
          body,
          data.task ? `/task/${data.task}` : null
        )
        // Refresh notification list immediately
        fetchNotifications()
      })
    }
  }

  function _startPolling() {
    if (refreshInterval) return // already running
    refreshInterval = setInterval(fetchNotifications, 30000)
  }

  function _stopPolling() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  function stopAutoRefresh() {
    _stopPolling()
    if (_visibilityHandler) {
      document.removeEventListener('visibilitychange', _visibilityHandler)
      _visibilityHandler = null
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
