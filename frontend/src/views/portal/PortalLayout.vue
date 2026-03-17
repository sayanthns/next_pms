<template>
  <div class="portal-layout">
    <!-- Top Navigation Bar -->
    <header class="portal-header">
      <div class="portal-header-inner">
        <div class="portal-logo">
          <img src="@/assets/logo-icon.svg" alt="Logo" class="portal-logo-icon" />
          <span class="portal-logo-text">Client Portal</span>
        </div>
        <nav class="portal-nav">
          <router-link to="/portal" class="portal-nav-link" :class="{ active: isActive('/portal') }" exact>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            <span>Dashboard</span>
          </router-link>
          <router-link to="/portal/tickets" class="portal-nav-link" :class="{ active: isActive('/portal/tickets') }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <span>Support Tickets</span>
          </router-link>
        </nav>
        <div class="portal-user">
          <span class="portal-user-name">{{ userName }}</span>
          <button class="portal-logout-btn" @click="logout" title="Logout">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Mobile Nav Toggle -->
    <button class="portal-mobile-nav-toggle" @click="mobileNavOpen = !mobileNavOpen">
      <svg v-if="!mobileNavOpen" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>

    <!-- Mobile Nav Dropdown -->
    <div v-if="mobileNavOpen" class="portal-mobile-nav" @click="mobileNavOpen = false">
      <router-link to="/portal" class="portal-mobile-nav-link">Dashboard</router-link>
      <router-link to="/portal/tickets" class="portal-mobile-nav-link">Support Tickets</router-link>
    </div>

    <!-- Main Content -->
    <main class="portal-main">
      <router-view />
    </main>

    <!-- Footer -->
    <footer class="portal-footer">
      <span>Powered by Next PMS</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mobileNavOpen = ref(false)

const userName = computed(() => {
  // Get from Frappe session
  try {
    return window.frappe?.boot?.user?.full_name || window.frappe?.session?.user || 'Client'
  } catch {
    return 'Client'
  }
})

function isActive(path) {
  if (path === '/portal') return route.path === '/portal'
  return route.path.startsWith(path)
}

function logout() {
  window.location.href = '/api/method/logout'
}
</script>

<style scoped>
.portal-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Header */
.portal-header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.portal-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.portal-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.portal-logo-icon {
  width: 28px;
  height: 28px;
}

.portal-logo-text {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.3px;
}

/* Navigation */
.portal-nav {
  display: flex;
  gap: 4px;
}

.portal-nav-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.portal-nav-link:hover {
  background: #f1f5f9;
  color: #334155;
}

.portal-nav-link.active {
  background: #eff6ff;
  color: #2563eb;
}

.portal-nav-link.active svg {
  stroke: #2563eb;
}

/* User section */
.portal-user {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.portal-user-name {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.portal-logout-btn {
  background: none;
  border: none;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  color: #94a3b8;
  transition: all 0.2s;
}

.portal-logout-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* Mobile nav */
.portal-mobile-nav-toggle {
  display: none;
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 200;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 48px;
  height: 48px;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(37,99,235,0.3);
  cursor: pointer;
}

.portal-mobile-nav {
  display: none;
  position: fixed;
  bottom: 80px;
  right: 20px;
  z-index: 200;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  padding: 8px;
  min-width: 180px;
}

.portal-mobile-nav-link {
  display: block;
  padding: 10px 16px;
  text-decoration: none;
  color: #334155;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: background 0.15s;
}

.portal-mobile-nav-link:hover {
  background: #f1f5f9;
}

/* Main */
.portal-main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 24px;
}

/* Footer */
.portal-footer {
  text-align: center;
  padding: 16px;
  font-size: 12px;
  color: #94a3b8;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

/* Responsive */
@media (max-width: 768px) {
  .portal-nav {
    display: none;
  }

  .portal-mobile-nav-toggle {
    display: flex;
  }

  .portal-mobile-nav {
    display: block;
  }

  .portal-header-inner {
    padding: 0 16px;
  }

  .portal-main {
    padding: 16px;
  }

  .portal-user-name {
    display: none;
  }
}
</style>
