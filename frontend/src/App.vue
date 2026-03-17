<template>
  <!-- Portal routes get their own layout (no sidebar) -->
  <router-view v-if="isPortalRoute" />

  <div v-else class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-mini': isDesktopCollapsed }">
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
          <router-link to="/task-report" class="nav-link" :class="{ active: isActive('/task-report') }">
            <span class="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            </span>
            <span v-show="!isDesktopCollapsed" class="nav-label">Task Report</span>
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

        <!-- Theme Toggle -->
        <div v-show="!isDesktopCollapsed" class="sidebar-theme-toggle" @click="toggleTheme" :title="theme === 'auto' ? 'Theme: Auto (System)' : theme === 'dark' ? 'Theme: Dark' : 'Theme: Light'">
          <span class="nav-icon">
            <!-- Sun icon (light mode) -->
            <svg v-if="theme === 'light'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            <!-- Moon icon (dark mode) -->
            <svg v-else-if="theme === 'dark'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            <!-- Auto icon (system) -->
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          </span>
          <span class="sidebar-theme-label">{{ theme === 'auto' ? 'Auto' : theme === 'dark' ? 'Dark' : 'Light' }}</span>
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
            <a href="#" @click.prevent="handleLogout" class="user-menu-item user-menu-logout">
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
      <!-- Offline banner -->
      <div v-if="!isOnline" class="offline-banner">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="1" y1="1" x2="23" y2="23"/><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/><path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/><path d="M10.71 5.05A16 16 0 0 1 22.56 9"/><path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>
        You are offline. Some features may be unavailable.
      </div>

      <!-- Push Notification Banner -->
      <div v-if="notificationStore.showPushBanner" class="push-banner">
        <div class="push-banner-content">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          <span>Enable push notifications to stay updated on tasks</span>
        </div>
        <div class="push-banner-actions">
          <button class="push-banner-enable" @click="enablePush">Enable</button>
          <button class="push-banner-dismiss" @click="notificationStore.dismissPushBanner()">Later</button>
        </div>
      </div>

      <!-- Global timer bar -->
      <div v-if="timerStore.isRunning" class="global-timer-bar">
        <div class="timer-bar-info">
          <span class="timer-bar-indicator"></span>
          <span class="timer-bar-task">{{ timerStore.currentTaskTitle || timerStore.currentTask }}</span>
          <span class="timer-bar-elapsed">{{ timerStore.elapsedFormatted }}</span>
        </div>
        <button class="timer-bar-stop" @click="handleGlobalStop">Stop</button>
      </div>

      <div class="content-area">
        <router-view />
      </div>
    </main>

    <!-- Mobile sidebar toggle (floating) — hidden when bottom nav is active -->
    <button
      v-if="sidebarCollapsed"
      class="mobile-menu-btn"
      @click="sidebarCollapsed = false"
    >
      &#9776;
    </button>

    <!-- Mobile Bottom Navigation -->
    <nav class="bottom-nav">
      <router-link to="/dashboard" class="bottom-nav-item" :class="{ active: isActive('/dashboard') }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        <span>Home</span>
      </router-link>
      <router-link v-if="settingsStore.sidebarPermissions.projects !== false" to="/projects" class="bottom-nav-item" :class="{ active: route.path === '/projects' }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        <span>Projects</span>
      </router-link>
      <router-link v-if="settingsStore.sidebarPermissions.timelogs !== false" to="/timelogs" class="bottom-nav-item" :class="{ active: isActive('/timelogs') }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span>Time Logs</span>
      </router-link>
      <router-link v-if="settingsStore.canViewAnalytics && settingsStore.sidebarPermissions.reports !== false" to="/reports" class="bottom-nav-item" :class="{ active: isActive('/reports') }">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        <span>Reports</span>
      </router-link>
      <button class="bottom-nav-item" :class="{ active: showMoreSheet }" @click="showMoreSheet = !showMoreSheet">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
        <span>More</span>
      </button>
    </nav>

    <!-- More Sheet Backdrop -->
    <div v-if="showMoreSheet" class="more-sheet-backdrop" @click="showMoreSheet = false"></div>

    <!-- More Sheet -->
    <Transition name="sheet">
      <div v-if="showMoreSheet" class="more-sheet">
        <div class="more-sheet-handle"></div>
        <div class="more-sheet-content">
          <!-- Navigation links -->
          <router-link v-if="settingsStore.sidebarPermissions.my_tasks !== false" to="/my-tasks" class="more-sheet-item" :class="{ active: isActive('/my-tasks') }">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            <span>My Tasks</span>
          </router-link>
          <router-link to="/task-report" class="more-sheet-item" :class="{ active: isActive('/task-report') }">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            <span>Task Report</span>
          </router-link>
          <router-link v-if="settingsStore.sidebarPermissions.settings !== false" to="/team" class="more-sheet-item" :class="{ active: isActive('/team') }">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span>Settings</span>
          </router-link>

          <div class="more-sheet-divider"></div>

          <!-- Check-in Toggle -->
          <div class="more-sheet-item" @click="handleCheckinToggle">
            <span class="more-sheet-checkin-dot" :class="{ 'checked-in': checkinStore.isCheckedIn }"></span>
            <span>{{ checkinStore.isCheckedIn ? 'Checked In' : 'Check In' }}</span>
            <span v-if="checkinStore.isCheckedIn && checkinStore.checkinData?.checkin_time" class="more-sheet-meta">Since {{ formatCheckinTime(checkinStore.checkinData.checkin_time) }}</span>
          </div>

          <!-- Theme toggle -->
          <div class="more-sheet-item" @click="toggleTheme">
            <svg v-if="theme === 'light'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            <svg v-else-if="theme === 'dark'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            <span>Theme: {{ theme === 'auto' ? 'Auto' : theme === 'dark' ? 'Dark' : 'Light' }}</span>
          </div>

          <!-- Notifications -->
          <div class="more-sheet-item" @click.stop="mobileNotifOpen = !mobileNotifOpen">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            <span>Notifications</span>
            <span v-if="notificationStore.unreadCount > 0" class="more-sheet-badge">
              {{ notificationStore.unreadCount > 9 ? '9+' : notificationStore.unreadCount }}
            </span>
            <svg :class="{ 'chevron-open': mobileNotifOpen }" class="more-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
          <div v-if="mobileNotifOpen" class="mobile-notif-list">
            <div v-if="notificationStore.notifications.length === 0" class="mobile-notif-empty">No notifications</div>
            <div
              v-for="n in notificationStore.notifications.slice(0, 10)"
              :key="n.name"
              class="mobile-notif-item"
              @click="handleMobileNotifClick(n)"
            >
              <div class="mobile-notif-msg">{{ n.subject }}</div>
              <div class="mobile-notif-meta">{{ timeAgo(n.creation) }}</div>
            </div>
            <button
              v-if="notificationStore.unreadCount > 0"
              class="mobile-notif-mark-all"
              @click.stop="notificationStore.markAllRead()"
            >Mark all read</button>
          </div>

          <!-- Enable Push Notifications -->
          <div v-if="!notificationStore.pushSubscribed" class="more-sheet-item" @click="enablePush">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/><line x1="12" y1="2" x2="12" y2="5"/></svg>
            <span style="color: #2563eb; font-weight: 600;">Enable Push Notifications</span>
          </div>

          <div class="more-sheet-divider"></div>

          <!-- User profile -->
          <div class="more-sheet-user">
            <span class="more-sheet-user-avatar">{{ userInitials }}</span>
            <div class="more-sheet-user-info">
              <span class="more-sheet-user-name">{{ userFullName }}</span>
              <span class="more-sheet-user-email">{{ currentUser }}</span>
            </div>
          </div>

          <!-- User actions -->
          <a href="/app" class="more-sheet-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            <span>Switch to Desk</span>
          </a>
          <a href="#" @click.prevent="handleLogout" class="more-sheet-item more-sheet-logout">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            <span>Log Out</span>
          </a>
        </div>
      </div>
    </Transition>

    <!-- Create Project Modal is in ProjectList.vue -->
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTimerStore } from '@/store/timer'
import { useNotificationStore } from '@/store/notifications'
import { useSettingsStore } from '@/store/settings'
import { useCheckinStore } from '@/store/checkin'
import { useOnlineStatus } from '@/composables/useOnlineStatus'
import { useTheme } from '@/composables/useTheme'
// CreateProjectModal is used only in ProjectList.vue

const route = useRoute()
const router = useRouter()
const timerStore = useTimerStore()
const notificationStore = useNotificationStore()
const settingsStore = useSettingsStore()
const checkinStore = useCheckinStore()
const { isOnline } = useOnlineStatus()
const { theme, isDark, toggleTheme } = useTheme()
const isPortalRoute = computed(() => route.path.startsWith('/portal'))
const sidebarCollapsed = ref(true)
const showNotifications = ref(false)
const showUserMenu = ref(false)
const showMoreSheet = ref(false)
const mobileNotifOpen = ref(false)

// Auto-close More sheet on navigation
watch(() => route.path, () => {
  showMoreSheet.value = false
  mobileNotifOpen.value = false
})
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

async function handleLogout() {
  try {
    await fetch('/api/method/logout', { method: 'GET', credentials: 'include' })
  } catch (e) {
    // ignore network errors
  }
  window.location.href = '/login'
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

async function handleMobileNotifClick(n) {
  await notificationStore.markRead(n.name)
  showMoreSheet.value = false
  mobileNotifOpen.value = false
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

async function enablePush() {
  const success = await notificationStore.subscribeToPush()
  if (!success) {
    notificationStore.dismissPushBanner()
  }
}

async function handleGlobalStop() {
  try {
    await timerStore.stopTimer()
  } catch (err) {
    console.error('Failed to stop timer:', err)
  }
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
    // Only force-refresh settings if stale (> 60s since last load)
    settingsStore.fetchSettings(true)
    _startPeriodicRefresh()
  } else {
    _stopPeriodicRefresh()
  }
}

let refreshInterval = null

function _startPeriodicRefresh() {
  if (refreshInterval) return
  refreshInterval = setInterval(() => {
    checkinStore.fetchTodayCheckin()
    timerStore.fetchRunningTimer()
  }, 60000)
}

function _stopPeriodicRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

onMounted(() => {
  settingsStore.fetchSettings()
  checkinStore.fetchTodayCheckin()
  timerStore.fetchRunningTimer()
  notificationStore.startAutoRefresh()
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('visibilitychange', onVisibilityChange)

  // Periodic refresh every 60s for checkin and timer (pauses when tab hidden)
  _startPeriodicRefresh()

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
  _stopPeriodicRefresh()
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
  background: var(--bg-primary);
  color: var(--text-primary);
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
  background: var(--bg-surface);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
  border-right: 1px solid var(--border-default);
  transition: transform 0.25s ease;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--border-default);
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
  color: var(--text-secondary);
  font-size: 22px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}

.sidebar-toggle-mobile:hover {
  background: var(--bg-surface-hover);
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
  color: var(--text-tertiary);
  padding: 0 10px 10px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.nav-link:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.nav-link.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
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
  background: var(--bg-surface-active);
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
  color: var(--text-secondary);
  flex: 1;
}

.checkin-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(100, 116, 139, 0.3);
  border-top-color: var(--text-secondary);
  border-radius: 50%;
  animation: spin-checkin 0.6s linear infinite;
}

@keyframes spin-checkin {
  to { transform: rotate(360deg); }
}

.checkin-time {
  font-size: 10px;
  color: var(--text-secondary);
  padding-left: 16px;
  margin-top: 2px;
}

/* ---- Sidebar Footer ---- */
.sidebar-footer {
  padding: 14px 18px;
  border-top: 1px solid var(--border-default);
}

/* ---- Theme Toggle ---- */
.sidebar-theme-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  margin-bottom: 6px;
}

.sidebar-theme-toggle:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.sidebar-theme-label {
  flex: 1;
}


/* ---- Sidebar Notification ---- */
.sidebar-notification {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  position: relative;
  margin-bottom: 10px;
}

.sidebar-notification:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
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
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  box-shadow: 0 4px 20px var(--shadow-lg);
  z-index: 1000;
  overflow: hidden;
}

.notification-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-default);
}

.notification-dropdown-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.notification-mark-all {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.notification-mark-all:hover {
  background: var(--color-primary-bg);
}

.notification-loading,
.notification-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.notification-list {
  max-height: 340px;
  overflow-y: auto;
}

.notification-item {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background 0.15s;
}

.notification-item:hover {
  background: var(--bg-surface-active);
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item-message {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.4;
  margin-bottom: 4px;
}

.notification-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--text-tertiary);
}

.notification-item-doctype {
  background: var(--bg-surface-hover);
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
  color: var(--text-secondary);
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
  background: var(--bg-surface-hover);
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
  color: var(--text-primary);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-user-email {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-user-chevron {
  color: var(--text-secondary);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.sidebar-user:hover .sidebar-user-chevron {
  color: var(--text-primary);
}

/* User Menu Dropdown */
.user-menu-dropdown {
  position: absolute;
  left: calc(100% + 8px);
  bottom: 0;
  width: 200px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  box-shadow: 0 4px 20px var(--shadow-lg);
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
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
  cursor: pointer;
}

.user-menu-item:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.user-menu-item svg {
  flex-shrink: 0;
  color: var(--text-secondary);
}

.user-menu-item:hover svg {
  color: var(--text-primary);
}

.user-menu-divider {
  height: 1px;
  background: var(--border-default);
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

/* ---- Offline Banner ---- */
.offline-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #fbbf24;
  color: #92400e;
  text-align: center;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.offline-banner svg {
  flex-shrink: 0;
}

/* Push Notification Banner */
.push-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(135deg, #eff6ff, #e0f2fe);
  border-bottom: 1px solid #bfdbfe;
  padding: 10px 16px;
  font-size: 13px;
  color: #1e40af;
}
.push-banner-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.push-banner-content svg {
  flex-shrink: 0;
}
.push-banner-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.push-banner-enable {
  padding: 5px 14px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.push-banner-enable:hover {
  background: #1d4ed8;
}
.push-banner-dismiss {
  padding: 5px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}
.push-banner-dismiss:hover {
  background: rgba(0,0,0,0.05);
}

/* ---- Main Content ---- */
.main-content {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-primary);
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
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
  line-height: 1;
}

.sidebar-toggle-desktop:hover {
  background: var(--bg-surface-hover);
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

/* ---- Bottom Nav (hidden on desktop) ---- */
.bottom-nav {
  display: none;
}

.more-sheet-backdrop {
  display: none;
}

.more-sheet {
  display: none;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  /* Hide sidebar and old mobile elements */
  .sidebar {
    transform: translateX(-240px) !important;
  }

  .sidebar-toggle-mobile {
    display: none !important;
  }

  .sidebar-toggle-desktop {
    display: none !important;
  }

  .sidebar-mini .sidebar {
    transform: translateX(-240px) !important;
  }

  .sidebar-mini .main-content {
    margin-left: 0;
  }

  .main-content {
    margin-left: 0;
  }

  .sidebar-overlay {
    display: none !important;
  }

  .mobile-menu-btn {
    display: none !important;
  }

  /* ---- Bottom Nav Bar ---- */
  .bottom-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--bg-surface);
    border-top: 1px solid var(--border-default);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    height: calc(56px + env(safe-area-inset-bottom, 0px));
    align-items: flex-start;
  }

  .bottom-nav-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 8px 0;
    height: 56px;
    background: none;
    border: none;
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 10px;
    font-weight: 500;
    cursor: pointer;
    transition: color 0.15s;
    -webkit-tap-highlight-color: transparent;
  }

  .bottom-nav-item.active {
    color: var(--color-primary);
  }

  .bottom-nav-item svg {
    flex-shrink: 0;
  }

  /* Content padding for bottom nav */
  .content-area {
    padding: 16px 16px calc(56px + env(safe-area-inset-bottom, 0px) + 16px);
  }

  .global-timer-bar {
    padding: 8px 16px;
  }

  .timer-bar-task {
    max-width: 160px;
  }

  /* ---- More Sheet ---- */
  .more-sheet-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: var(--overlay-bg);
    z-index: 200;
  }

  .more-sheet {
    display: block;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 201;
    background: var(--bg-surface);
    border-radius: 16px 16px 0 0;
    max-height: 75vh;
    overflow-y: auto;
    padding-bottom: env(safe-area-inset-bottom, 0px);
    box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.15);
  }

  .more-sheet-handle {
    width: 36px;
    height: 4px;
    background: var(--border-default);
    border-radius: 2px;
    margin: 10px auto;
  }

  .more-sheet-content {
    padding: 4px 16px 16px;
  }

  .more-sheet-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 12px;
    border-radius: 10px;
    color: var(--text-primary);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
  }

  .more-sheet-item:active {
    background: var(--bg-surface-hover);
  }

  .more-sheet-item.active {
    color: var(--color-primary);
    background: var(--color-primary-bg);
  }

  .more-sheet-item svg {
    flex-shrink: 0;
    color: var(--text-secondary);
  }

  .more-sheet-item.active svg {
    color: var(--color-primary);
  }

  .more-sheet-divider {
    height: 1px;
    background: var(--border-default);
    margin: 6px 0;
  }

  .more-sheet-badge {
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
    margin-left: auto;
  }

  .more-sheet-checkin-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #ef4444;
    flex-shrink: 0;
  }

  .more-sheet-checkin-dot.checked-in {
    background: #10b981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
  }

  .more-sheet-meta {
    font-size: 12px;
    color: var(--text-secondary);
    margin-left: auto;
  }

  .more-sheet-user {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 12px;
  }

  .more-sheet-user-avatar {
    width: 36px;
    height: 36px;
    min-width: 36px;
    border-radius: 50%;
    background: #2563EB;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
  }

  .more-sheet-user-info {
    display: flex;
    flex-direction: column;
  }

  .more-sheet-user-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .more-sheet-user-email {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .more-sheet-logout {
    color: #ef4444 !important;
  }

  .more-sheet-logout svg {
    color: #ef4444 !important;
  }

  /* Sheet slide-up transition */
  .sheet-enter-active {
    transition: transform 0.3s ease-out;
  }
  .sheet-leave-active {
    transition: transform 0.2s ease-in;
  }
  .sheet-enter-from,
  .sheet-leave-to {
    transform: translateY(100%);
  }

  /* Mobile notification list */
  .more-chevron {
    margin-left: auto;
    transition: transform 0.2s;
    flex-shrink: 0;
  }
  .more-chevron.chevron-open {
    transform: rotate(180deg);
  }
  .mobile-notif-list {
    padding: 0 12px 8px;
  }
  .mobile-notif-empty {
    padding: 12px;
    text-align: center;
    font-size: 13px;
    color: var(--text-secondary);
  }
  .mobile-notif-item {
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .mobile-notif-item:active {
    background: var(--bg-surface-hover);
  }
  .mobile-notif-msg {
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.4;
  }
  .mobile-notif-meta {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 2px;
  }
  .mobile-notif-mark-all {
    display: block;
    width: 100%;
    padding: 8px;
    margin-top: 4px;
    border: none;
    border-radius: 8px;
    background: var(--bg-surface-hover);
    color: var(--color-primary);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    text-align: center;
  }
}
</style>
