<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-mini': isDesktopCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <img v-show="isDesktopCollapsed" class="logo-icon" src="@/assets/logo-icon.svg" alt="Next PMS" />
          <img v-show="!isDesktopCollapsed" class="logo-icon" src="@/assets/logo.svg" alt="Next PMS" />
          <span v-show="!isDesktopCollapsed" class="logo-text"><span class="logo-next">Next</span><span class="logo-pms">PMS</span></span>
        </div>
        <div class="sidebar-header-actions">
          <button class="sidebar-toggle-desktop" @click="toggleSidebar" title="Toggle sidebar">
            <span v-if="isDesktopCollapsed">&#9776;</span>
            <span v-else>&laquo;</span>
          </button>
          <button class="sidebar-toggle-mobile" @click="sidebarCollapsed = !sidebarCollapsed">
            <span v-if="sidebarCollapsed">&#9776;</span>
            <span v-else>&times;</span>
          </button>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <span v-show="!isDesktopCollapsed" class="nav-section-label">Menu</span>
          <router-link to="/dashboard" class="nav-link" :class="{ active: isActive('/dashboard') }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">Home</span>
          </router-link>
          <router-link v-if="settingsStore.sidebarPermissions.projects !== false" to="/projects" class="nav-link" :class="{ active: route.path === '/projects' }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">Projects</span>
          </router-link>
          <router-link v-if="settingsStore.sidebarPermissions.my_tasks !== false" to="/my-tasks" class="nav-link" :class="{ active: isActive('/my-tasks') }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">My Tasks</span>
          </router-link>
          <router-link v-if="settingsStore.sidebarPermissions.timelogs !== false" to="/timelogs" class="nav-link" :class="{ active: isActive('/timelogs') }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">Time Logs</span>
          </router-link>
          <router-link v-if="settingsStore.canViewAnalytics && settingsStore.sidebarPermissions.reports !== false" to="/reports" class="nav-link" :class="{ active: isActive('/reports') }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">Reports</span>
          </router-link>
          <router-link v-if="settingsStore.sidebarPermissions.settings !== false" to="/team" class="nav-link" :class="{ active: isActive('/team') }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">Settings</span>
          </router-link>
        </div>

      </nav>

      <div class="sidebar-footer">
        <!-- Check-in Status -->
        <div v-show="!isDesktopCollapsed" class="sidebar-checkin">
          <div class="checkin-status" @click="handleCheckinToggle">
            <span class="checkin-dot" :class="{ 'checked-in': checkinStore.isCheckedIn }"></span>
            <span class="checkin-label">{{ checkinStore.isCheckedIn ? 'Checked In' : 'Check In' }}</span>
            <span v-if="checkinStore.loading" class="checkin-spinner"></span>
          </div>
          <div v-if="checkinStore.isCheckedIn && checkinStore.checkinData?.checkin_time" class="checkin-time">
            Since {{ formatCheckinTime(checkinStore.checkinData.checkin_time) }}
          </div>
        </div>

        <!-- Notification Bell in sidebar -->
        <div v-show="!isDesktopCollapsed" class="sidebar-notification" @click.stop="showNotifications = !showNotifications">
          <span class="sidebar-notif-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          </span>
          <span class="sidebar-notif-label">Notifications</span>
          <span v-if="notificationStore.unreadCount > 0" class="sidebar-notif-badge">
            {{ notificationStore.unreadCount > 9 ? '9+' : notificationStore.unreadCount }}
          </span>
          <!-- Notification Dropdown -->
          <div v-if="showNotifications" class="notification-dropdown sidebar-dropdown" @click.stop>
            <div class="notification-dropdown-header">
              <span class="notification-dropdown-title">Notifications</span>
              <button
                v-if="notificationStore.unreadCount > 0"
                class="notification-mark-all"
                @click.stop="notificationStore.markAllRead()"
              >
                Mark all read
              </button>
            </div>
            <div v-if="notificationStore.loading" class="notification-loading">Loading...</div>
            <div v-else-if="notificationStore.notifications.length === 0" class="notification-empty">
              No new notifications
            </div>
            <div v-else class="notification-list">
              <div
                v-for="n in notificationStore.notifications"
                :key="n.name"
                class="notification-item"
                @click.stop="handleNotificationClick(n)"
              >
                <div class="notification-item-message">{{ n.subject }}</div>
                <div class="notification-item-meta">
                  <span class="notification-item-doctype">{{ n.document_type }}</span>
                  <span class="notification-item-time">{{ timeAgo(n.creation) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- User Profile -->
        <div v-show="!isDesktopCollapsed" class="sidebar-user" @click.stop="showUserMenu = !showUserMenu">
          <span class="sidebar-user-avatar">{{ userInitials }}</span>
          <div class="sidebar-user-info">
            <span class="sidebar-user-name">{{ userFullName }}</span>
            <span class="sidebar-user-email">{{ currentUser }}</span>
          </div>
          <svg class="sidebar-user-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>

          <!-- User Menu Dropdown -->
          <div v-if="showUserMenu" class="user-menu-dropdown" @click.stop>
            <a href="/app" class="user-menu-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              <span>Switch to Desk</span>
            </a>
            <a href="/app/user-settings" class="user-menu-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              <span>Settings</span>
            </a>
            <div class="user-menu-divider"></div>
            <a href="/api/method/logout" class="user-menu-item user-menu-logout">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              <span>Log Out</span>
            </a>
          </div>
        </div>

      </div>
    </aside>

    <!-- Overlay for mobile sidebar -->
    <div
      v-if="!sidebarCollapsed"
      class="sidebar-overlay"
      @click="sidebarCollapsed = true"
    ></div>

    <!-- Main content -->
    <main class="main-content">
      <!-- Global timer bar -->
      <div v-if="timerStore.isRunning" class="global-timer-bar">
        <div class="timer-bar-info">
          <span class="timer-bar-indicator"></span>
          <span class="timer-bar-task">{{ timerStore.currentTaskTitle || timerStore.currentTask }}</span>
          <span class="timer-bar-elapsed">{{ timerStore.elapsedFormatted }}</span>
        </div>
        <button class="timer-bar-stop" @click="timerStore.stopTimer()">Stop</button>
      </div>

      <div class="content-area">
        <router-view />
      </div>
    </main>

    <!-- Mobile sidebar toggle (floating) -->
    <button
      v-if="sidebarCollapsed"
      class="mobile-menu-btn"
      @click="sidebarCollapsed = false"
    >
      &#9776;
    </button>

    <!-- Create Project Modal is in ProjectList.vue -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTimerStore } from '@/store/timer'
import { useNotificationStore } from '@/store/notifications'
import { useSettingsStore } from '@/store/settings'
import { useCheckinStore } from '@/store/checkin'
// CreateProjectModal is used only in ProjectList.vue

const route = useRoute()
const router = useRouter()
const timerStore = useTimerStore()
const notificationStore = useNotificationStore()
const settingsStore = useSettingsStore()
const checkinStore = useCheckinStore()
const sidebarCollapsed = ref(true)
const showNotifications = ref(false)
const showUserMenu = ref(false)
// showCreateProject moved to ProjectList.vue
const isDesktopCollapsed = ref(localStorage.getItem('pms-sidebar-collapsed') === 'true')

const currentUser = computed(() => {
  return window.frappe?.boot?.user?.name || window.pms_boot?.user || window.frappe?.session?.user || 'User'
})

const userFullName = computed(() => {
  return window.frappe?.boot?.user?.full_name || window.pms_boot?.user_fullname || currentUser.value || 'User'
})

const userInitials = computed(() => {
  const name = userFullName.value || ''
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
})

function toggleSidebar() {
  isDesktopCollapsed.value = !isDesktopCollapsed.value
  localStorage.setItem('pms-sidebar-collapsed', isDesktopCollapsed.value)
}

function timeAgo(dateString) {
  if (!dateString) return ''
  const now = new Date()
  const date = new Date(dateString)
  const seconds = Math.floor((now - date) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString()
}

async function handleNotificationClick(n) {
  await notificationStore.markRead(n.name)
  showNotifications.value = false
  if (n.document_type === 'PMS Task' && n.document_name) {
    router.push(`/task/${n.document_name}`)
  } else if (n.document_type === 'PMS Project' && n.document_name) {
    router.push(`/project/${n.document_name}`)
  }
}

// onProjectCreated moved to ProjectList.vue

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

async function handleCheckinToggle() {
  if (checkinStore.loading) return
  try {
    if (checkinStore.isCheckedIn) {
      await checkinStore.doCheckout()
    } else {
      await checkinStore.doCheckin()
    }
  } catch (e) {
    console.error('Check-in toggle failed:', e)
  }
}

function formatCheckinTime(dt) {
  if (!dt) return ''
  const date = new Date(dt)
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function handleKeydown(e) {
  const tag = e.target.tagName.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return

  if (e.key === 't' || e.key === 'T') {
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('pms:toggle-timer'))
  }
  if (e.key === 'd' || e.key === 'D') {
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('pms:mark-done'))
  }
}

function handleClickOutside(e) {
  if (showNotifications.value && !e.target.closest('.sidebar-notification')) {
    showNotifications.value = false
  }
  if (showUserMenu.value && !e.target.closest('.sidebar-user')) {
    showUserMenu.value = false
  }
}

// Auto-refresh on visibility change (tab focus)
function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    checkinStore.fetchTodayCheckin()
    timerStore.fetchRunningTimer()
    settingsStore.fetchSettings()
  }
}

let refreshInterval = null

onMounted(() => {
  settingsStore.fetchSettings()
  checkinStore.fetchTodayCheckin()
  timerStore.fetchRunningTimer()
  notificationStore.startAutoRefresh()
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('visibilitychange', onVisibilityChange)

  // Periodic refresh every 60s for checkin and timer
  refreshInterval = setInterval(() => {
    checkinStore.fetchTodayCheckin()
    timerStore.fetchRunningTimer()
  }, 60000)

  if (window.innerWidth < 768) {
    sidebarCollapsed.value = true
  } else {
    sidebarCollapsed.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  notificationStore.stopAutoRefresh()
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<style>
/* CSS Reset & Global Styles */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f0f2f5;
  color: #1e1e2e;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

#app {
  min-height: 100vh;
}
</style>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

/* ---- Sidebar (White Theme) ---- */
.sidebar {
  width: 240px;
  min-width: 240px;
  background: #ffffff;
  color: #64748b;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
  border-right: 1px solid #e5e7eb;
  transition: transform 0.25s ease;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 18px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.sidebar-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: contain;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.logo-next {
  color: #29D5F5;
}

.logo-pms {
  color: #2563EB;
}

.sidebar-toggle-mobile {
  display: none;
  background: none;
  border: none;
  color: #64748b;
  font-size: 22px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}

.sidebar-toggle-mobile:hover {
  background: #f3f4f6;
}

/* ---- Navigation ---- */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 14px 10px;
}

.nav-section {
  margin-bottom: 24px;
}

.nav-section-label {
  display: block;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #9ca3af;
  padding: 0 10px 10px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #64748b;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.nav-link:hover {
  background: #f3f4f6;
  color: #1e1e2e;
}

.nav-link.active {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
  font-weight: 600;
}

.nav-link .nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-link .nav-icon svg {
  display: block;
}

/* ---- Check-in Status ---- */
.sidebar-checkin {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8f9fa;
}

.checkin-status {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 0;
  transition: opacity 0.15s;
}

.checkin-status:hover {
  opacity: 0.85;
}

.checkin-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  flex-shrink: 0;
  transition: background 0.2s;
}

.checkin-dot.checked-in {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
  animation: pulse-checkin 2s infinite;
}

@keyframes pulse-checkin {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  70% { box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.checkin-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  flex: 1;
}

.checkin-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(100, 116, 139, 0.3);
  border-top-color: #64748b;
  border-radius: 50%;
  animation: spin-checkin 0.6s linear infinite;
}

@keyframes spin-checkin {
  to { transform: rotate(360deg); }
}

.checkin-time {
  font-size: 10px;
  color: #64748b;
  padding-left: 16px;
  margin-top: 2px;
}

/* ---- Sidebar Footer ---- */
.sidebar-footer {
  padding: 14px 18px;
  border-top: 1px solid #e5e7eb;
}


/* ---- Sidebar Notification ---- */
.sidebar-notification {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #64748b;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  position: relative;
  margin-bottom: 10px;
}

.sidebar-notification:hover {
  background: #f3f4f6;
  color: #1e1e2e;
}

.sidebar-notif-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sidebar-notif-label {
  flex: 1;
}

.sidebar-notif-badge {
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  line-height: 1;
}

.sidebar-dropdown {
  left: calc(100% + 8px);
  bottom: 0;
  top: auto;
  right: auto;
}

.notification-dropdown {
  position: absolute;
  width: 360px;
  max-height: 400px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  overflow: hidden;
}

.notification-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
}

.notification-dropdown-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e1e2e;
}

.notification-mark-all {
  background: none;
  border: none;
  color: #2563EB;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.notification-mark-all:hover {
  background: rgba(37, 99, 235, 0.08);
}

.notification-loading,
.notification-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.notification-list {
  max-height: 340px;
  overflow-y: auto;
}

.notification-item {
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background 0.15s;
}

.notification-item:hover {
  background: #f8f9fa;
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item-message {
  font-size: 13px;
  color: #1e1e2e;
  line-height: 1.4;
  margin-bottom: 4px;
}

.notification-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #9ca3af;
}

.notification-item-doctype {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
  color: #6b7280;
}

.notification-item-time {
  white-space: nowrap;
}

/* ---- User Profile in Sidebar ---- */
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
  margin-bottom: 10px;
}

.sidebar-user:hover {
  background: #f3f4f6;
}

.sidebar-user-avatar {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: 50%;
  background: #2563EB;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.sidebar-user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-user-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e1e2e;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-user-email {
  font-size: 11px;
  color: #64748b;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-user-chevron {
  color: #64748b;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.sidebar-user:hover .sidebar-user-chevron {
  color: #374151;
}

/* User Menu Dropdown */
.user-menu-dropdown {
  position: absolute;
  left: calc(100% + 8px);
  bottom: 0;
  width: 200px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  overflow: hidden;
  padding: 6px;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 6px;
  color: #374151;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  cursor: pointer;
}

.user-menu-item:hover {
  background: #f3f4f6;
  color: #1e1e2e;
}

.user-menu-item svg {
  flex-shrink: 0;
  color: #6b7280;
}

.user-menu-item:hover svg {
  color: #374151;
}

.user-menu-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 0;
}

.user-menu-logout {
  color: #ef4444;
}

.user-menu-logout:hover {
  background: #fef2f2;
  color: #dc2626;
}

.user-menu-logout svg {
  color: #ef4444;
}

.user-menu-logout:hover svg {
  color: #dc2626;
}

/* ---- Main Content ---- */
.main-content {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f0f2f5;
}

.content-area {
  flex: 1;
  padding: 24px 28px;
}

/* ---- Global Timer Bar ---- */
.global-timer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 28px;
  background: #1a1d2e;
  color: #ffffff;
  border-bottom: 2px solid #ef4444;
  flex-shrink: 0;
}

.timer-bar-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.timer-bar-indicator {
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
  70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.timer-bar-task {
  font-size: 13px;
  font-weight: 500;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timer-bar-elapsed {
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  font-size: 14px;
  font-weight: 600;
  color: #ef4444;
}

.timer-bar-stop {
  padding: 5px 14px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.timer-bar-stop:hover {
  background: #dc2626;
}

/* ---- Sidebar Overlay (mobile) ---- */
.sidebar-overlay {
  display: none;
}

/* ---- Mobile Menu Button ---- */
.mobile-menu-btn {
  display: none;
  position: fixed;
  bottom: 20px;
  left: 20px;
  z-index: 90;
  width: 44px;
  height: 44px;
  background: #2563EB;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 20px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
  align-items: center;
  justify-content: center;
}

/* ---- Desktop Sidebar Toggle Button ---- */
.sidebar-toggle-desktop {
  display: none;
  background: none;
  border: none;
  color: #64748b;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
  line-height: 1;
}

.sidebar-toggle-desktop:hover {
  background: #f3f4f6;
}

@media (min-width: 769px) {
  .sidebar-toggle-desktop {
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

/* ---- Collapsed Sidebar (Desktop Mini Mode) ---- */
.sidebar-mini .sidebar {
  width: 64px;
  min-width: 64px;
}

.sidebar-mini .sidebar-header {
  padding: 20px 12px 16px;
  justify-content: center;
}

.sidebar-mini .sidebar-header-actions {
  gap: 4px;
}

.sidebar-mini .sidebar-nav {
  padding: 12px 8px;
}

.sidebar-mini .nav-section {
  margin-bottom: 12px;
}

.sidebar-mini .nav-link {
  justify-content: center;
  padding: 10px;
  gap: 0;
}

.sidebar-mini .nav-link .nav-icon {
  margin: 0;
}

.sidebar-mini .main-content {
  margin-left: 64px;
}

/* Smooth transitions */
.sidebar,
.main-content {
  transition: width 0.25s ease, min-width 0.25s ease, margin-left 0.25s ease, transform 0.25s ease;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .sidebar-toggle-mobile {
    display: block;
  }

  .sidebar-toggle-desktop {
    display: none !important;
  }

  .sidebar-mini .sidebar {
    width: 240px;
    min-width: 240px;
  }

  .sidebar-mini .main-content {
    margin-left: 0;
  }

  .sidebar {
    transform: translateX(0);
  }

  .sidebar-collapsed .sidebar {
    transform: translateX(-240px);
  }

  .main-content {
    margin-left: 0;
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
  }

  .sidebar-collapsed .sidebar-overlay {
    display: none;
  }

  .mobile-menu-btn {
    display: flex;
  }

  .sidebar-collapsed .mobile-menu-btn {
    display: flex;
  }

  .content-area {
    padding: 16px 16px;
  }

  .global-timer-bar {
    padding: 8px 16px;
  }

  .timer-bar-task {
    max-width: 160px;
  }
}
</style>
