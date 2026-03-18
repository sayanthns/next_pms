<template>
  <div class="portal-layout">
    <!-- Left Sidebar -->
    <aside class="portal-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-top">
        <div class="sidebar-logo">
          <img src="@/assets/logo-icon.svg" alt="Logo" class="sidebar-logo-icon" />
          <span v-show="!sidebarCollapsed" class="sidebar-logo-text">Client Portal</span>
        </div>
        <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed" title="Toggle sidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <polyline v-if="sidebarCollapsed" points="9 18 15 12 9 6"/>
            <polyline v-else points="15 18 9 12 15 6"/>
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <span v-show="!sidebarCollapsed" class="nav-section-label">MENU</span>
        <router-link to="/portal" class="sidebar-nav-link" :class="{ active: isExactActive('/portal') }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </span>
          <span v-show="!sidebarCollapsed" class="nav-label">Dashboard</span>
          <span v-if="notifications.pending_approvals && !sidebarCollapsed" class="nav-badge nav-badge-amber">{{ notifications.pending_approvals }}</span>
        </router-link>

        <router-link to="/portal/tickets" class="sidebar-nav-link" :class="{ active: isActive('/portal/tickets') }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          </span>
          <span v-show="!sidebarCollapsed" class="nav-label">Support Tickets</span>
          <span v-if="notifications.unread_responses && !sidebarCollapsed" class="nav-badge">{{ notifications.unread_responses }}</span>
        </router-link>

        <router-link to="/portal/reports" class="sidebar-nav-link" :class="{ active: isActive('/portal/reports') }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          </span>
          <span v-show="!sidebarCollapsed" class="nav-label">Reports</span>
        </router-link>
      </nav>

      <!-- Sidebar Footer: User -->
      <div class="sidebar-footer">
        <div class="sidebar-user" :title="userName">
          <div class="user-avatar">{{ userInitials }}</div>
          <div v-show="!sidebarCollapsed" class="user-info">
            <span class="user-name">{{ userName }}</span>
            <span class="user-email">{{ userEmail }}</span>
          </div>
        </div>
        <button v-show="!sidebarCollapsed" class="sidebar-logout-btn" @click="logout" title="Logout">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        </button>
      </div>
    </aside>

    <!-- Mobile Header -->
    <header class="portal-mobile-header">
      <button class="mobile-menu-btn" @click="mobileNavOpen = !mobileNavOpen">
        <svg v-if="!mobileNavOpen" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <span class="mobile-title">Client Portal</span>
      <button class="mobile-logout-btn" @click="logout" title="Logout">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </button>
    </header>

    <!-- Mobile Sidebar Overlay -->
    <div v-if="mobileNavOpen" class="mobile-overlay" @click="mobileNavOpen = false"></div>
    <aside v-if="mobileNavOpen" class="portal-sidebar mobile-sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">
          <img src="@/assets/logo-icon.svg" alt="Logo" class="sidebar-logo-icon" />
          <span class="sidebar-logo-text">Client Portal</span>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/portal" class="sidebar-nav-link" :class="{ active: isExactActive('/portal') }" @click="mobileNavOpen = false">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </span>
          <span class="nav-label">Dashboard</span>
        </router-link>
        <router-link to="/portal/tickets" class="sidebar-nav-link" :class="{ active: isActive('/portal/tickets') }" @click="mobileNavOpen = false">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          </span>
          <span class="nav-label">Support Tickets</span>
        </router-link>
        <router-link to="/portal/reports" class="sidebar-nav-link" :class="{ active: isActive('/portal/reports') }" @click="mobileNavOpen = false">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          </span>
          <span class="nav-label">Reports</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-user">
          <div class="user-avatar">{{ userInitials }}</div>
          <div class="user-info">
            <span class="user-name">{{ userName }}</span>
            <span class="user-email">{{ userEmail }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="portal-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { call } from '@/utils/frappe'

const route = useRoute()
const sidebarCollapsed = ref(false)
const mobileNavOpen = ref(false)
const notifications = ref({ pending_approvals: 0, unread_responses: 0, total: 0 })
let notifInterval = null

const userName = computed(() => {
  try {
    return window.frappe?.boot?.user?.full_name || window.frappe?.session?.user || 'Client'
  } catch {
    return 'Client'
  }
})

const userEmail = computed(() => {
  try {
    return window.frappe?.session?.user || ''
  } catch {
    return ''
  }
})

const userInitials = computed(() => {
  const name = userName.value
  if (!name || name === 'Client') return 'CL'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
})

function isExactActive(path) {
  return route.path === path
}

function isActive(path) {
  return route.path.startsWith(path)
}

function logout() {
  window.location.href = '/api/method/logout'
}

async function fetchNotifications() {
  try {
    const res = await call('next_pms.api.portal.get_portal_notifications')
    if (res) notifications.value = res
  } catch {
    // Silent fail
  }
}

onMounted(() => {
  fetchNotifications()
  notifInterval = setInterval(fetchNotifications, 60000)
})

onUnmounted(() => {
  if (notifInterval) clearInterval(notifInterval)
})
</script>

<style scoped>
.portal-layout {
  min-height: 100vh;
  display: flex;
  background: #f7f8fa;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ─── Sidebar ─── */
.portal-sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  transition: width 0.2s ease, min-width 0.2s ease;
  z-index: 100;
}

.portal-sidebar.collapsed {
  width: 64px;
  min-width: 64px;
}

.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
  min-height: 56px;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
}

.sidebar-logo-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}

.sidebar-logo-text {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.3px;
  white-space: nowrap;
}

.sidebar-toggle {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: #94a3b8;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.sidebar-toggle:hover { background: #f1f5f9; color: #334155; }

.collapsed .sidebar-toggle {
  margin: 0 auto;
}

/* ─── Navigation ─── */
.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-section-label {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.8px;
  padding: 4px 12px 8px;
}

.sidebar-nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
  position: relative;
}

.sidebar-nav-link:hover {
  background: #f1f5f9;
  color: #334155;
}

.sidebar-nav-link.active {
  background: #eff6ff;
  color: #2563eb;
}

.sidebar-nav-link.active svg {
  stroke: #2563eb;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
}

/* Notification badges */
.nav-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  margin-left: auto;
}

.nav-badge-amber {
  background: #f59e0b;
}

/* ─── Sidebar Footer ─── */
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e0e7ff;
  color: #4338ca;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-email {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-logout-btn {
  background: none;
  border: none;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  color: #94a3b8;
  transition: all 0.2s;
  flex-shrink: 0;
}
.sidebar-logout-btn:hover { background: #fee2e2; color: #ef4444; }

/* ─── Main Content ─── */
.portal-main {
  flex: 1;
  min-width: 0;
  padding: 28px 32px;
  overflow-y: auto;
  height: 100vh;
  -webkit-overflow-scrolling: touch;
}

/* ─── Mobile Header ─── */
.portal-mobile-header {
  display: none;
}

.mobile-overlay {
  display: none;
}

.mobile-sidebar {
  display: none;
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .portal-sidebar:not(.mobile-sidebar) {
    display: none;
  }

  .portal-mobile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    height: 52px;
    background: #fff;
    border-bottom: 1px solid #e5e7eb;
    position: sticky;
    top: 0;
    z-index: 90;
  }

  .mobile-menu-btn, .mobile-logout-btn {
    background: none;
    border: none;
    padding: 6px;
    cursor: pointer;
    color: #64748b;
    border-radius: 6px;
  }
  .mobile-menu-btn:hover, .mobile-logout-btn:hover { background: #f1f5f9; }

  .mobile-title {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
  }

  .mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 199;
  }

  .mobile-sidebar {
    display: flex !important;
    position: fixed;
    left: 0;
    top: 0;
    width: 260px;
    height: 100vh;
    z-index: 200;
    box-shadow: 4px 0 20px rgba(0,0,0,0.1);
  }

  .portal-layout {
    flex-direction: column;
  }

  .portal-main {
    height: auto;
    min-height: calc(100vh - 52px);
    padding: 16px;
  }
}
</style>
