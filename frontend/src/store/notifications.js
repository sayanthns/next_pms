import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { call } from '@/utils/frappe'

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref([])
  const loading = ref(false)

  const unreadCount = computed(() => notifications.value.length)

  async function fetchNotifications() {
    loading.value = true
    try {
      notifications.value = await call('next_pms.api.notifications.get_notifications')
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
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }

  async function markAllRead() {
    try {
      await call('next_pms.api.notifications.mark_all_read')
      notifications.value = []
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  }

  // Auto-refresh every 30 seconds
  let refreshInterval = null
  function startAutoRefresh() {
    fetchNotifications()
    refreshInterval = setInterval(fetchNotifications, 30000)
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
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
