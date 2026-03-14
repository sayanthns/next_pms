<template>
  <div class="user-detail-page">
    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading user...</p>
    </div>

    <template v-else-if="user">
      <!-- User Header -->
      <div class="user-header">
        <div class="header-left">
          <button class="back-btn" @click="router.push('/team')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <div class="avatar-lg" :style="{ background: getAvatarColor(user.email) }">
            <img v-if="user.user_image" :src="user.user_image" :alt="user.full_name" class="avatar-img" />
            <span v-else>{{ getInitials(user.full_name || user.email) }}</span>
          </div>
          <div class="header-info">
            <h1 class="user-name">{{ user.full_name || user.email }}</h1>
            <p class="user-email">{{ user.email }}</p>
          </div>
        </div>
        <div class="header-right">
          <span class="role-badge" :class="'role-' + user.pms_role">
            {{ roleLabel(user.pms_role) }}
          </span>
          <span
            class="checkin-status"
            :class="user.today_checkin?.is_active ? 'status-active' : (user.today_checkin ? 'status-out' : 'status-none')"
          >
            <span class="status-dot"></span>
            {{ checkinLabel(user) }}
          </span>
        </div>
      </div>

      <!-- Tab Bar -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="setTab(tab.key)"
        >
          <svg v-if="tab.icon === 'profile'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <svg v-else-if="tab.icon === 'attendance'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <svg v-else-if="tab.icon === 'projects'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <svg v-else-if="tab.icon === 'permissions'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">

        <!-- ═══ Profile & Rate ═══ -->
        <div v-if="activeTab === 'profile'" class="profile-tab">
          <div class="card">
            <h3 class="card-title">Profile Information</h3>
            <div class="profile-grid">
              <div class="profile-field">
                <label class="field-label">Full Name</label>
                <span class="field-value">{{ user.full_name || '—' }}</span>
              </div>
              <div class="profile-field">
                <label class="field-label">Email</label>
                <span class="field-value">{{ user.email }}</span>
              </div>
              <div class="profile-field">
                <label class="field-label">PMS Access</label>
                <div v-if="settingsStore.isAdmin" class="field-value">
                  <label class="toggle-switch" :class="{ disabled: togglingAccess }">
                    <input
                      type="checkbox"
                      :checked="user.has_pms_access"
                      :disabled="togglingAccess"
                      @change="toggleAccess($event.target.checked)"
                    />
                    <span class="toggle-slider"></span>
                  </label>
                  <span class="toggle-label">{{ user.has_pms_access ? 'Enabled' : 'Disabled' }}</span>
                </div>
                <span v-else class="field-value">{{ user.has_pms_access ? 'Enabled' : 'Disabled' }}</span>
              </div>
              <div class="profile-field">
                <label class="field-label">Role</label>
                <div v-if="settingsStore.isAdmin && user.has_pms_access" class="field-value">
                  <select
                    :value="user.pms_role"
                    class="role-select"
                    :disabled="changingRole"
                    @change="changeRole($event.target.value)"
                  >
                    <option value="developer">Developer</option>
                    <option value="manager">Project Manager</option>
                    <option value="viewer">Viewer</option>
                    <option value="customer">Customer</option>
                  </select>
                </div>
                <span v-else class="field-value">
                  <span class="role-badge inline" :class="'role-' + user.pms_role">
                    {{ roleLabel(user.pms_role) }}
                  </span>
                </span>
              </div>
              <div class="profile-field">
                <label class="field-label">Hourly Rate</label>
                <div class="rate-edit-wrap">
                  <span class="rate-currency">₹</span>
                  <input
                    type="number"
                    class="rate-edit-input"
                    :value="user.hourly_rate || 0"
                    min="0"
                    step="5"
                    @change="updateHourlyRate($event.target.value)"
                  />
                  <span class="rate-suffix">/hr</span>
                </div>
                <span class="rate-note">Rate changes apply to new time logs only</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══ Attendance ═══ -->
        <div v-if="activeTab === 'attendance'" class="attendance-tab">
          <!-- Today's Status -->
          <div class="card">
            <h3 class="card-title">Today's Status</h3>
            <div v-if="user.today_checkin" class="today-detail">
              <div class="today-item">
                <span class="today-label">Check-in</span>
                <span class="today-value">{{ formatTime(user.today_checkin.checkin_time) }}</span>
              </div>
              <div class="today-item">
                <span class="today-label">Check-out</span>
                <span class="today-value">{{ user.today_checkin.checkout_time ? formatTime(user.today_checkin.checkout_time) : 'Still active' }}</span>
              </div>
              <div class="today-item">
                <span class="today-label">Hours</span>
                <span class="today-value">{{ user.today_checkin.total_hours ? user.today_checkin.total_hours + 'h' : '—' }}</span>
              </div>
              <div class="today-item">
                <span class="today-label">Status</span>
                <span class="today-value">
                  <span class="checkin-status inline" :class="user.today_checkin.is_active ? 'status-active' : 'status-out'">
                    <span class="status-dot"></span>
                    {{ user.today_checkin.is_active ? 'Checked In' : 'Checked Out' }}
                  </span>
                </span>
              </div>
            </div>
            <p v-else class="no-data-text">No check-in recorded today</p>
          </div>

          <!-- Recent Attendance -->
          <div class="card">
            <div class="card-header-row">
              <h3 class="card-title">Recent Attendance</h3>
              <div class="filter-row">
                <select v-model="attendanceMonth" class="filter-select" @change="loadCheckins">
                  <option v-for="m in months" :key="m.value" :value="m.value">{{ m.label }}</option>
                </select>
                <select v-model="attendanceYear" class="filter-select" @change="loadCheckins">
                  <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
                </select>
              </div>
            </div>
            <div v-if="checkinsLoading" class="mini-loading">
              <div class="spinner-sm"></div>
              <span>Loading...</span>
            </div>
            <table v-else-if="checkins.length" class="history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Check-in</th>
                  <th>Check-out</th>
                  <th>Hours</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in checkins" :key="c.name">
                  <td>{{ formatDate(c.date) }}</td>
                  <td>{{ formatTime(c.checkin_time) }}</td>
                  <td>{{ c.checkout_time ? formatTime(c.checkout_time) : '—' }}</td>
                  <td>{{ c.total_hours ? c.total_hours + 'h' : '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="no-data-text">No attendance records for this period</p>
          </div>
        </div>

        <!-- ═══ Assigned Projects ═══ -->
        <div v-if="activeTab === 'projects'" class="projects-tab">
          <div v-if="projectsLoading" class="loading-container sm">
            <div class="spinner"></div>
            <p class="loading-text">Loading projects...</p>
          </div>
          <div v-else-if="projects.length" class="projects-list">
            <div v-for="p in projects" :key="p.project" class="project-card" @click="router.push(`/project/${p.project}`)">
              <div class="project-card-left">
                <span class="project-status-dot" :style="{ background: statusDotColor(p.project_status) }"></span>
                <div class="project-card-info">
                  <span class="project-card-name">{{ p.project_name || p.project }}</span>
                  <span class="project-card-status">{{ p.project_status }}</span>
                </div>
              </div>
              <span class="project-card-role">{{ p.role }}</span>
            </div>
          </div>
          <div v-else class="empty-state-box">
            <p>Not assigned to any projects</p>
          </div>
        </div>

        <!-- ═══ Permissions (Admin only) ═══ -->
        <div v-if="activeTab === 'permissions'" class="permissions-tab">
          <!-- Sidebar Menu Access -->
          <div class="card">
            <h3 class="card-title">Sidebar Menu Access</h3>
            <p class="card-desc">Control which sidebar menu items this user can see</p>
            <div class="perm-grid">
              <div v-for="item in sidebarItems" :key="item.key" class="perm-item">
                <span class="perm-label">{{ item.label }}</span>
                <label class="toggle-switch">
                  <input
                    type="checkbox"
                    :checked="permSidebar[item.key] !== false"
                    @change="permSidebar[item.key] = $event.target.checked"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>

          <!-- Project Tab Access -->
          <div class="card">
            <h3 class="card-title">Project Tab Access</h3>
            <p class="card-desc">Control which tabs inside projects this user can view</p>
            <div class="perm-grid">
              <div v-for="item in projectTabItems" :key="item.key" class="perm-item">
                <span class="perm-label">{{ item.label }}</span>
                <label class="toggle-switch">
                  <input
                    type="checkbox"
                    :checked="permProjectTabs[item.key] !== false"
                    @change="permProjectTabs[item.key] = $event.target.checked"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>

          <!-- Feature Access -->
          <div class="card">
            <h3 class="card-title">Feature Access</h3>
            <p class="card-desc">Control what this user can do across the system</p>
            <div class="perm-grid">
              <div v-for="item in featureItems" :key="item.key" class="perm-item">
                <span class="perm-label">{{ item.label }}</span>
                <label class="toggle-switch">
                  <input
                    type="checkbox"
                    :checked="permFeatures[item.key] !== false"
                    @change="permFeatures[item.key] = $event.target.checked"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>

          <div class="perm-actions">
            <button class="btn-save" :disabled="savingPerms" @click="savePermissions">
              {{ savingPerms ? 'Saving...' : 'Save Permissions' }}
            </button>
          </div>
        </div>

      </div>
    </template>

    <!-- Not Found -->
    <div v-else class="empty-state-box">
      <p>User not found</p>
      <button class="back-link" @click="router.push('/team')">Back to Team</button>
    </div>

    <!-- Toast -->
    <Transition name="toast">
      <div v-if="toast.show" class="toast" :class="'toast-' + toast.type">
        {{ toast.message }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { call } from '@/utils/frappe'
import { useSettingsStore } from '@/store/settings'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const route = useRoute()
const settingsStore = useSettingsStore()

// ── State ─────────────────────────────────────────────
const loading = ref(true)
const user = ref(null)

const activeTab = ref(route.query.tab || 'profile')

const tabs = computed(() => {
  const base = [
    { key: 'profile', label: 'Profile & Rate', icon: 'profile' },
    { key: 'attendance', label: 'Attendance', icon: 'attendance' },
    { key: 'projects', label: 'Assigned Projects', icon: 'projects' },
  ]
  if (settingsStore.isAdmin) {
    base.push({ key: 'permissions', label: 'Permissions', icon: 'permissions' })
  }
  return base
})

function setTab(tab) {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

// ── Toast ─────────────────────────────────────────────
const toast = ref({ show: false, message: '', type: 'success' })
function showToast(message, type = 'success') {
  toast.value = { show: true, message, type }
  setTimeout(() => { toast.value.show = false }, 3000)
}

// ── Load User Detail ──────────────────────────────────
async function loadUser() {
  loading.value = true
  try {
    const data = await call('next_pms.api.crud.get_user_detail', { user: props.id })
    user.value = data
    // Init permission state
    if (data) {
      Object.assign(permSidebar, data.sidebar_permissions || {})
      Object.assign(permProjectTabs, data.project_tab_permissions || {})
      Object.assign(permFeatures, data.feature_permissions || {})
    }
  } catch (e) {
    console.error('Failed to load user:', e)
    user.value = null
  } finally {
    loading.value = false
  }
}

// ── Profile & Rate ────────────────────────────────────
const togglingAccess = ref(false)
const changingRole = ref(false)

async function toggleAccess(enable) {
  togglingAccess.value = true
  try {
    await call('next_pms.api.users.toggle_pms_access', { user: props.id, enable })
    user.value.has_pms_access = enable
    if (enable && !user.value.pms_role) user.value.pms_role = 'developer'
    if (!enable) user.value.pms_role = ''
    showToast(enable ? 'PMS access enabled' : 'PMS access disabled')
  } catch (e) {
    console.error('Failed to toggle access:', e)
    showToast('Failed to update access', 'error')
  } finally {
    togglingAccess.value = false
  }
}

async function changeRole(role) {
  changingRole.value = true
  try {
    await call('next_pms.api.users.set_pms_role', { user: props.id, role })
    user.value.pms_role = role
    showToast(`Role changed to ${roleLabel(role)}`)
  } catch (e) {
    console.error('Failed to change role:', e)
    showToast('Failed to update role', 'error')
  } finally {
    changingRole.value = false
  }
}

async function updateHourlyRate(newRate) {
  const rate = parseFloat(newRate) || 0
  try {
    await call('next_pms.api.crud.set_user_hourly_rate', { user: props.id, rate })
    user.value.hourly_rate = rate
    showToast(`Rate updated to ₹${rate}/hr`)
  } catch (e) {
    console.error('Failed to update rate:', e)
    showToast('Failed to update rate', 'error')
  }
}

// ── Attendance ────────────────────────────────────────
const now = new Date()
const attendanceMonth = ref(now.getMonth()) // 0-based
const attendanceYear = ref(now.getFullYear())
const checkins = ref([])
const checkinsLoading = ref(false)

const months = [
  { value: 0, label: 'January' }, { value: 1, label: 'February' },
  { value: 2, label: 'March' }, { value: 3, label: 'April' },
  { value: 4, label: 'May' }, { value: 5, label: 'June' },
  { value: 6, label: 'July' }, { value: 7, label: 'August' },
  { value: 8, label: 'September' }, { value: 9, label: 'October' },
  { value: 10, label: 'November' }, { value: 11, label: 'December' },
]

const years = computed(() => {
  const y = new Date().getFullYear()
  return [y - 2, y - 1, y, y + 1]
})

async function loadCheckins() {
  checkinsLoading.value = true
  try {
    const m = attendanceMonth.value
    const y = attendanceYear.value
    const fromDate = `${y}-${String(m + 1).padStart(2, '0')}-01`
    const lastDay = new Date(y, m + 1, 0).getDate()
    const toDate = `${y}-${String(m + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
    const data = await call('next_pms.api.checkin.get_checkin_history', {
      user_filter: props.id,
      from_date: fromDate,
      to_date: toDate,
      limit: 100,
    })
    checkins.value = data || []
  } catch (e) {
    console.error('Failed to load checkins:', e)
    checkins.value = []
  } finally {
    checkinsLoading.value = false
  }
}

// ── Assigned Projects ─────────────────────────────────
const projects = ref([])
const projectsLoading = ref(false)

async function loadProjects() {
  projectsLoading.value = true
  try {
    const data = await call('next_pms.api.crud.get_user_project_memberships', { user: props.id })
    projects.value = data || []
  } catch (e) {
    console.error('Failed to load projects:', e)
    projects.value = []
  } finally {
    projectsLoading.value = false
  }
}

// ── Permissions ───────────────────────────────────────
const permSidebar = reactive({
  dashboard: true, projects: true, my_tasks: true,
  team: true, timelogs: true, reports: true,
})
const permProjectTabs = reactive({
  overview: true, tasks: true, backlog: true,
  team: true, files: true, timelogs: true, analytics: true,
})
const permFeatures = reactive({
  view_all_timelogs: true, view_all_projects: true,
  edit_project: true, edit_task: true,
  create_project: true, create_task: true,
})
const savingPerms = ref(false)

const sidebarItems = [
  { key: 'projects', label: 'Projects' },
  { key: 'my_tasks', label: 'My Tasks' },
  { key: 'settings', label: 'Settings' },
  { key: 'timelogs', label: 'Time Logs' },
  { key: 'reports', label: 'Reports' },
]

const projectTabItems = [
  { key: 'overview', label: 'Overview' },
  { key: 'tasks', label: 'Tasks' },
  { key: 'backlog', label: 'Backlog' },
  { key: 'team', label: 'Team' },
  { key: 'files', label: 'Files' },
  { key: 'timelogs', label: 'Time Logs' },
  { key: 'analytics', label: 'Analytics' },
]

const featureItems = [
  { key: 'view_all_timelogs', label: 'View All Time Logs' },
  { key: 'view_all_projects', label: 'View All Projects' },
  { key: 'edit_project', label: 'Edit Projects' },
  { key: 'edit_task', label: 'Edit Tasks' },
  { key: 'create_project', label: 'Create Projects' },
  { key: 'create_task', label: 'Create Tasks' },
]

async function savePermissions() {
  savingPerms.value = true
  try {
    await call('next_pms.api.permissions.save_user_permissions', {
      user: props.id,
      sidebar_permissions: JSON.stringify({ ...permSidebar }),
      project_tab_permissions: JSON.stringify({ ...permProjectTabs }),
      feature_permissions: JSON.stringify({ ...permFeatures }),
    })
    showToast('Permissions saved')
  } catch (e) {
    console.error('Failed to save permissions:', e)
    showToast('Failed to save permissions', 'error')
  } finally {
    savingPerms.value = false
  }
}

// ── Helpers ───────────────────────────────────────────
function roleLabel(role) {
  const labels = { manager: 'Manager', developer: 'Developer', viewer: 'Viewer', customer: 'Customer' }
  return labels[role] || role || 'Unknown'
}

function checkinLabel(member) {
  if (!member.today_checkin) return 'Not checked in'
  if (member.today_checkin.is_active) return 'Active'
  return 'Checked out'
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

function getAvatarColor(email) {
  const colors = ['#2563EB', '#14b8a6', '#F59E0B', '#EF4444', '#3b82f6', '#8b5cf6', '#ec4899', '#10b981', '#f97316', '#06b6d4']
  let hash = 0
  for (let i = 0; i < (email || '').length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function statusDotColor(status) {
  const map = { 'Active': '#10b981', 'In Progress': '#10b981', 'Planning': '#2563EB', 'Planned': '#2563EB', 'Completed': '#059669', 'On Hold': '#F59E0B' }
  return map[status] || '#9ca3af'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatTime(dtStr) {
  if (!dtStr) return '—'
  const date = new Date(dtStr)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
}

// ── Lazy load tabs ────────────────────────────────────
watch(activeTab, (tab) => {
  if (tab === 'attendance' && !checkins.value.length && !checkinsLoading.value) {
    loadCheckins()
  }
  if (tab === 'projects' && !projects.value.length && !projectsLoading.value) {
    loadProjects()
  }
})

// ── Init ──────────────────────────────────────────────
onMounted(async () => {
  await loadUser()
  // Pre-load the active tab data
  if (activeTab.value === 'attendance') loadCheckins()
  if (activeTab.value === 'projects') loadProjects()
})
</script>

<style scoped>
.user-detail-page {
  padding: 16px 0;
}

/* ── Loading ───────────────────────────────── */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.loading-container.sm { padding: 40px 0; }

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-text {
  margin-top: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

.mini-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.spinner-sm {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* ── Header ────────────────────────────────── */
.user-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.back-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.avatar-lg {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.header-info {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.user-email {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

/* ── Tab Bar ───────────────────────────────── */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--border-default);
  padding-bottom: 0;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
  white-space: nowrap;
}

.tab-btn:hover { color: var(--text-primary); background: var(--color-primary-bg); }
.tab-btn.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
.tab-btn svg { flex-shrink: 0; }

/* ── Cards ─────────────────────────────────── */
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 14px 0;
}

.card-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: -8px 0 14px 0;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  gap: 12px;
  flex-wrap: wrap;
}

.card-header-row .card-title { margin: 0; }

/* ── Role Badges ───────────────────────────── */
.role-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.role-badge.inline { margin: 0; }
.role-manager { background: var(--color-primary-bg); color: var(--color-primary); }
.role-developer { background: rgba(16, 185, 129, 0.1); color: var(--color-success); }
.role-viewer { background: rgba(245, 158, 11, 0.1); color: var(--color-warning); }
.role-customer { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }

/* ── Checkin Status ────────────────────────── */
.checkin-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.checkin-status.inline { min-width: auto; }

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-active { color: var(--color-success); }
.status-active .status-dot { background: var(--color-success); box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2); }
.status-out { color: var(--text-secondary); }
.status-out .status-dot { background: var(--text-tertiary); }
.status-none { color: var(--text-placeholder); }
.status-none .status-dot { background: var(--border-default); }

/* ── Profile Tab ───────────────────────────── */
.profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.profile-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.field-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.role-select {
  padding: 6px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  cursor: pointer;
  max-width: 180px;
}

.role-select:focus { border-color: var(--color-primary); }
.role-select:disabled { opacity: 0.5; cursor: not-allowed; }

.rate-edit-wrap {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 6px 10px;
  max-width: 160px;
  transition: border-color 0.15s;
}

.rate-edit-wrap:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.rate-currency { font-size: 12px; color: var(--text-tertiary); font-weight: 500; }
.rate-suffix { font-size: 11px; color: var(--text-tertiary); }

.rate-edit-input {
  width: 70px;
  border: none;
  outline: none;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  background: transparent;
  padding: 0;
  text-align: right;
}

.rate-edit-input::-webkit-inner-spin-button { opacity: 0; }

.rate-note {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

/* ── Toggle Switch ─────────────────────────── */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle-switch.disabled { opacity: 0.5; cursor: not-allowed; }

.toggle-switch input { opacity: 0; width: 0; height: 0; }

.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--border-default);
  border-radius: 22px;
  transition: background 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  left: 3px;
  bottom: 3px;
  background: var(--bg-surface);
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.toggle-switch input:checked + .toggle-slider { background: #2563EB; }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(18px); }

/* ── Attendance Tab ────────────────────────── */
.filter-row {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 7px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  cursor: pointer;
}

.filter-select:focus { border-color: var(--color-primary); }

.today-detail {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.today-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.today-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.today-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.history-table th {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  padding: 8px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.history-table td {
  padding: 8px 14px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
}

.history-table tr:last-child td { border-bottom: none; }

.no-data-text {
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 12px 0;
  margin: 0;
}

/* ── Projects Tab ──────────────────────────── */
.projects-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.project-card:hover {
  border-color: #c7d2fe;
  background: var(--bg-surface-active);
}

.project-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.project-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.project-card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.project-card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-card-status {
  font-size: 11px;
  color: var(--text-tertiary);
}

.project-card-role {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-bg);
  padding: 3px 10px;
  border-radius: 12px;
  white-space: nowrap;
}

/* ── Permissions Tab ───────────────────────── */
.perm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.perm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg-surface-active);
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.perm-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.perm-actions {
  margin-top: 8px;
}

.btn-save {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: #2563EB;
  color: #fff;
  transition: all 0.15s;
}

.btn-save:hover:not(:disabled) { background: var(--color-primary-hover); }
.btn-save:disabled { opacity: 0.6; cursor: not-allowed; }

/* ── Empty / Not Found ─────────────────────── */
.empty-state-box {
  text-align: center;
  padding: 60px 0;
  color: var(--text-tertiary);
  font-size: 14px;
}

.back-link {
  display: inline-block;
  margin-top: 12px;
  padding: 8px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.back-link:hover { background: var(--bg-surface-hover); }

/* ── Toast ─────────────────────────────────── */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.toast-success { background: var(--color-success); }
.toast-error { background: var(--color-danger); }

.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(10px); }
.toast-leave-to { opacity: 0; transform: translateY(10px); }
</style>
