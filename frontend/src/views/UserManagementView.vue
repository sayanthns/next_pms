<template>
  <div class="user-mgmt-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">User Management</h1>
        <p class="page-subtitle">Manage PMS access and roles for your team</p>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ pmsUsers.length }}</span>
        <span class="stat-label">PMS Users</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ roleCounts.manager }}</span>
        <span class="stat-label">Managers</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ roleCounts.developer }}</span>
        <span class="stat-label">Developers</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ roleCounts.viewer + roleCounts.customer }}</span>
        <span class="stat-label">Viewers / Customers</span>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar">
      <div class="search-box">
        <svg class="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input v-model="searchQuery" type="text" placeholder="Search users..." class="search-input" />
      </div>
      <select v-model="filterAccess" class="filter-select">
        <option value="">All Users</option>
        <option value="pms">PMS Users Only</option>
        <option value="no-pms">Without PMS Access</option>
      </select>
      <select v-model="filterRole" class="filter-select">
        <option value="">All Roles</option>
        <option value="manager">Project Manager</option>
        <option value="developer">Developer</option>
        <option value="viewer">Viewer</option>
        <option value="customer">Customer</option>
      </select>
      <span v-if="filteredUsers.length !== allUsers.length" class="filter-count">
        {{ filteredUsers.length }} of {{ allUsers.length }}
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading users...</p>
    </div>

    <!-- User Table -->
    <div v-else class="user-table-wrap">
      <table class="user-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th style="width: 120px; text-align: center">PMS Access</th>
            <th style="width: 180px">Role</th>
            <th style="width: 120px">Last Active</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.name" class="user-row">
            <td>
              <div class="user-cell">
                <span class="user-avatar" :style="avatarStyle(user)">
                  <img v-if="user.user_image" :src="user.user_image" :alt="user.full_name" class="user-avatar-img" />
                  <span v-else>{{ getInitials(user.full_name || user.name) }}</span>
                </span>
                <span class="user-name">{{ user.full_name || user.name }}</span>
              </div>
            </td>
            <td class="user-email-cell">{{ user.email || user.name }}</td>
            <td style="text-align: center">
              <label class="toggle-switch" :class="{ disabled: togglingUser === user.name }">
                <input
                  type="checkbox"
                  :checked="user.has_pms_access"
                  :disabled="togglingUser === user.name"
                  @change="toggleAccess(user, $event.target.checked)"
                />
                <span class="toggle-slider"></span>
              </label>
            </td>
            <td>
              <select
                v-if="user.has_pms_access"
                :value="user.pms_role"
                class="role-select"
                :disabled="changingRole === user.name"
                @change="changeRole(user, $event.target.value)"
              >
                <option value="developer">Developer</option>
                <option value="manager">Project Manager</option>
                <option value="viewer">Viewer</option>
                <option value="customer">Customer</option>
              </select>
              <span v-else class="no-access-label">—</span>
            </td>
            <td class="last-active-cell">{{ user.last_active ? formatDate(user.last_active) : '—' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filteredUsers.length" class="empty-state">
        <p>{{ allUsers.length ? 'No users match your filters.' : 'No users found.' }}</p>
      </div>
    </div>

    <!-- AI Settings Section -->
    <div class="ai-settings-section">
      <h2 class="section-title-lg">AI Daily Report Settings</h2>
      <p class="section-desc">Configure LLM-powered daily work analysis emails</p>
      <div class="ai-form">
        <div class="ai-form-row">
          <div class="ai-field">
            <label class="ai-label">AI Provider</label>
            <select v-model="aiSettings.provider" class="ai-input" @change="onProviderChange">
              <option value="OpenAI">OpenAI</option>
              <option value="Claude">Claude</option>
            </select>
          </div>
          <div class="ai-field">
            <label class="ai-label">Model</label>
            <input v-model="aiSettings.model" type="text" class="ai-input" placeholder="e.g. gpt-4o" />
          </div>
        </div>
        <div class="ai-field">
          <label class="ai-label">API Key</label>
          <input
            v-model="aiSettings.apiKey"
            type="password"
            class="ai-input"
            :placeholder="aiSettings.apiKeySet ? '••••••••••• (key is set)' : 'Paste your API key'"
          />
        </div>
        <div class="ai-form-row">
          <div class="ai-field">
            <label class="ai-label">Recipient Email</label>
            <input v-model="aiSettings.recipient" type="email" class="ai-input" placeholder="sayanth@enfono.in" />
          </div>
          <div class="ai-field ai-field-toggle">
            <label class="ai-label">Enable Daily Report</label>
            <label class="toggle-wrap">
              <input type="checkbox" v-model="aiSettings.enabled" />
              <span class="toggle-slider"></span>
              <span class="toggle-text">{{ aiSettings.enabled ? 'Enabled' : 'Disabled' }}</span>
            </label>
          </div>
        </div>
        <hr class="ai-divider" />
        <h3 class="ai-subtitle">Working Hours & Weekly Summary</h3>
        <div class="ai-form-row">
          <div class="ai-field">
            <label class="ai-label">Working Hours / Day</label>
            <input v-model.number="aiSettings.workingHoursPerDay" type="number" min="1" max="24" step="0.5" class="ai-input" placeholder="8" />
          </div>
          <div class="ai-field ai-field-toggle">
            <label class="ai-label">Enable Weekly Summary</label>
            <label class="toggle-wrap">
              <input type="checkbox" v-model="aiSettings.weeklyEnabled" />
              <span class="toggle-slider"></span>
              <span class="toggle-text">{{ aiSettings.weeklyEnabled ? 'Enabled' : 'Disabled' }}</span>
            </label>
          </div>
        </div>
        <div class="ai-field">
          <label class="ai-label">Weekly Team Summary Recipient</label>
          <input v-model="aiSettings.weeklyRecipient" type="email" class="ai-input" placeholder="sayanth@enfono.in" />
        </div>

        <hr class="ai-divider" />
        <h3 class="ai-subtitle">Attendance Reminders</h3>
        <p class="section-desc">Staff who miss check-in/out get a reminder; managers below get one daily digest.</p>
        <div class="ai-form-row">
          <div class="ai-field ai-field-toggle">
            <label class="ai-label">Enable Attendance Reminders</label>
            <label class="toggle-wrap">
              <input type="checkbox" v-model="aiSettings.attendanceEnabled" />
              <span class="toggle-slider"></span>
              <span class="toggle-text">{{ aiSettings.attendanceEnabled ? 'Enabled' : 'Disabled' }}</span>
            </label>
          </div>
        </div>
        <div class="ai-field">
          <label class="ai-label">Manager Digest Recipients (comma-separated)</label>
          <input v-model="aiSettings.attendanceManagers" type="text" class="ai-input" placeholder="salman@enfono.com" />
        </div>

        <div class="ai-actions">
          <button class="ai-btn ai-btn-save" @click="saveAiSettings" :disabled="aiSaving">
            {{ aiSaving ? 'Saving...' : 'Save Settings' }}
          </button>
          <button class="ai-btn ai-btn-test" @click="sendTestReport" :disabled="aiTesting">
            {{ aiTesting ? 'Sending...' : 'Send Test Report' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <Transition name="toast">
      <div v-if="toast.show" class="toast" :class="'toast-' + toast.type">
        {{ toast.message }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const loading = ref(true)
const allUsers = ref([])
const searchQuery = ref('')
const filterAccess = ref('')
const filterRole = ref('')
const togglingUser = ref('')
const changingRole = ref('')
const toast = ref({ show: false, message: '', type: 'success' })

const pmsUsers = computed(() => allUsers.value.filter(u => u.has_pms_access))

const roleCounts = computed(() => {
  const counts = { manager: 0, developer: 0, viewer: 0, customer: 0 }
  pmsUsers.value.forEach(u => {
    if (u.pms_role && counts[u.pms_role] !== undefined) {
      counts[u.pms_role]++
    }
  })
  return counts
})

const filteredUsers = computed(() => {
  let users = allUsers.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    users = users.filter(u =>
      (u.full_name || '').toLowerCase().includes(q) ||
      (u.name || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q)
    )
  }
  if (filterAccess.value === 'pms') {
    users = users.filter(u => u.has_pms_access)
  } else if (filterAccess.value === 'no-pms') {
    users = users.filter(u => !u.has_pms_access)
  }
  if (filterRole.value) {
    users = users.filter(u => u.pms_role === filterRole.value)
  }
  return users
})

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

function avatarStyle(user) {
  if (user.user_image) return {}
  // Generate a consistent color from name
  const colors = ['#2563EB', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
  const hash = (user.name || '').split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  return { background: colors[hash % colors.length] }
}

function formatDate(d) {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function showToast(message, type = 'success') {
  toast.value = { show: true, message, type }
  setTimeout(() => { toast.value.show = false }, 3000)
}

async function toggleAccess(user, enable) {
  togglingUser.value = user.name
  try {
    await call('next_pms.api.users.toggle_pms_access', {
      user: user.name,
      enable: enable,
    })
    user.has_pms_access = enable
    if (enable && !user.pms_role) {
      user.pms_role = 'developer'
    }
    if (!enable) {
      user.pms_role = ''
    }
    showToast(
      enable
        ? `${user.full_name || user.name} now has PMS access`
        : `PMS access removed for ${user.full_name || user.name}`
    )
  } catch (e) {
    console.error('Failed to toggle access:', e)
    showToast('Failed to update access', 'error')
  } finally {
    togglingUser.value = ''
  }
}

async function changeRole(user, role) {
  changingRole.value = user.name
  try {
    await call('next_pms.api.users.set_pms_role', {
      user: user.name,
      role: role,
    })
    user.pms_role = role
    const roleLabels = { developer: 'Developer', manager: 'Project Manager', viewer: 'Viewer', customer: 'Customer' }
    showToast(`${user.full_name || user.name} is now ${roleLabels[role] || role}`)
  } catch (e) {
    console.error('Failed to change role:', e)
    showToast('Failed to update role', 'error')
  } finally {
    changingRole.value = ''
  }
}

// AI Settings
const aiSettings = ref({
  provider: 'OpenAI',
  apiKey: '',
  apiKeySet: false,
  model: 'gpt-4o',
  enabled: false,
  recipient: 'sayanth@enfono.in',
  workingHoursPerDay: 8,
  weeklyEnabled: true,
  weeklyRecipient: 'sayanth@enfono.in',
  attendanceEnabled: true,
  attendanceManagers: 'salman@enfono.com',
})
const aiSaving = ref(false)
const aiTesting = ref(false)

function onProviderChange() {
  if (aiSettings.value.provider === 'Claude') {
    aiSettings.value.model = 'claude-sonnet-4-20250514'
  } else {
    aiSettings.value.model = 'gpt-4o'
  }
}

async function loadAiSettings() {
  try {
    const data = await call('next_pms.api.settings.get_ai_settings')
    if (data) {
      aiSettings.value.provider = data.ai_provider || 'OpenAI'
      aiSettings.value.apiKeySet = data.ai_api_key_set || false
      aiSettings.value.model = data.ai_model || 'gpt-4o'
      aiSettings.value.enabled = data.daily_report_enabled || false
      aiSettings.value.recipient = data.daily_report_recipient || ''
      if (data.working_hours_per_day != null) aiSettings.value.workingHoursPerDay = data.working_hours_per_day
      aiSettings.value.weeklyEnabled = data.weekly_summary_enabled !== false
      aiSettings.value.weeklyRecipient = data.weekly_summary_recipient || ''
      aiSettings.value.attendanceEnabled = data.attendance_reminder_enabled !== false
      aiSettings.value.attendanceManagers = data.attendance_manager_recipients || ''
    }
  } catch (e) {
    console.error('Failed to load AI settings:', e)
  }
}

async function saveAiSettings() {
  aiSaving.value = true
  try {
    await call('next_pms.api.settings.save_ai_settings', {
      provider: aiSettings.value.provider,
      api_key: aiSettings.value.apiKey || '',
      model: aiSettings.value.model,
      enabled: aiSettings.value.enabled,
      recipient: aiSettings.value.recipient,
      working_hours_per_day: aiSettings.value.workingHoursPerDay,
      weekly_summary_enabled: aiSettings.value.weeklyEnabled,
      weekly_summary_recipient: aiSettings.value.weeklyRecipient,
      attendance_reminder_enabled: aiSettings.value.attendanceEnabled,
      attendance_manager_recipients: aiSettings.value.attendanceManagers,
    })
    if (aiSettings.value.apiKey) {
      aiSettings.value.apiKeySet = true
      aiSettings.value.apiKey = ''
    }
    showToast('AI settings saved successfully')
  } catch (e) {
    console.error('Failed to save AI settings:', e)
    showToast('Failed to save AI settings', 'error')
  } finally {
    aiSaving.value = false
  }
}

async function sendTestReport() {
  aiTesting.value = true
  try {
    const result = await call('next_pms.api.ai_report.generate_daily_report')
    if (result && result.success) {
      showToast('Test report sent! Check your email.')
    } else {
      showToast(result?.message || 'Failed to generate report', 'error')
    }
  } catch (e) {
    console.error('Failed to send test report:', e)
    showToast('Failed to send test report', 'error')
  } finally {
    aiTesting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    allUsers.value = await call('next_pms.api.users.get_pms_users')
  } catch (e) {
    console.error('Failed to load users:', e)
  } finally {
    loading.value = false
  }
  loadAiSettings()
})
</script>

<style scoped>
.user-mgmt-view {
  padding: 16px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-secondary); margin: 2px 0 0 0; }

/* Stats Row */
.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Filters Bar */
.filters-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 0 10px;
  flex: 1;
  min-width: 180px;
  max-width: 300px;
}

.search-icon { color: var(--text-tertiary); flex-shrink: 0; }

.search-input {
  border: none;
  outline: none;
  font-size: 13px;
  padding: 8px 0;
  width: 100%;
  background: transparent;
  color: var(--text-primary);
}

.search-input::placeholder { color: var(--text-tertiary); }

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

.filter-count {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Loading */
.loading-container { display: flex; flex-direction: column; align-items: center; padding: 80px 0; }
.spinner { width: 40px; height: 40px; border: 3px solid var(--border-default); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { margin-top: 16px; color: var(--text-secondary); font-size: 14px; }

/* User Table */
.user-table-wrap {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
}

.user-table th {
  text-align: left;
  padding: 10px 14px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-surface-active);
  border-bottom: 1px solid var(--border-default);
}

.user-table td {
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
}

.user-row {
  transition: background 0.1s;
}

.user-row:hover {
  background: var(--bg-surface-active);
}

/* User Cell */
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  overflow: hidden;
  flex-shrink: 0;
}

.user-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-name {
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-email-cell {
  color: var(--text-secondary);
  font-size: 13px;
}

.last-active-cell {
  color: var(--text-tertiary);
  font-size: 12px;
  white-space: nowrap;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  cursor: pointer;
}

.toggle-switch.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

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

.toggle-switch input:checked + .toggle-slider {
  background: #2563EB;
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

/* Role Select */
.role-select {
  padding: 5px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  cursor: pointer;
  width: 100%;
  max-width: 160px;
}

.role-select:focus {
  border-color: var(--color-primary);
}

.role-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-access-label {
  color: var(--text-placeholder);
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--text-tertiary);
  font-size: 14px;
}

/* Toast Notification */
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

.toast-success {
  background: var(--color-success);
}

.toast-error {
  background: var(--color-danger);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* AI Settings */
.ai-settings-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 24px;
  margin-top: 20px;
}

.section-title-lg {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.section-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 20px 0;
}

.ai-divider {
  border: none;
  border-top: 1px solid var(--border-default);
  margin: 22px 0 16px;
}

.ai-subtitle {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.ai-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.ai-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-field-toggle {
  justify-content: flex-start;
}

.ai-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.ai-input {
  padding: 9px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-surface);
  transition: border-color 0.15s;
  outline: none;
  font-family: inherit;
}

.ai-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.toggle-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.toggle-wrap input[type="checkbox"] {
  position: relative;
  width: 44px;
  height: 24px;
  appearance: none;
  background: var(--border-default);
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-wrap input[type="checkbox"]:checked {
  background: #2563EB;
}

.toggle-wrap input[type="checkbox"]::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: var(--bg-surface);
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
}

.toggle-wrap input[type="checkbox"]:checked::after {
  transform: translateX(20px);
}

.toggle-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.ai-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.ai-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.ai-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-btn-save {
  background: #2563EB;
  color: #fff;
}

.ai-btn-save:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.ai-btn-test {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.ai-btn-test:hover:not(:disabled) {
  background: var(--border-default);
}

@media (max-width: 768px) {
  .user-mgmt-view { padding: 12px 0; }
  .stats-row { flex-wrap: wrap; }
  .stat-card { min-width: calc(50% - 6px); }
  .filters-bar { flex-direction: column; align-items: stretch; }
  .search-box { max-width: 100%; }
  .user-table-wrap { overflow-x: auto; }
  .user-table { min-width: 600px; }
  .ai-form-row { grid-template-columns: 1fr; }
}
</style>
