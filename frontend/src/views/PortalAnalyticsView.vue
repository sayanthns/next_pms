<template>
  <div class="portal-analytics">
    <div class="page-header">
      <div>
        <h1 class="page-title">Portal Analytics</h1>
        <p class="page-subtitle">Client portal usage, support tickets, and milestone approvals</p>
      </div>
      <button class="btn-refresh" @click="loadAnalytics" :disabled="loading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading && !data" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading analytics...</p>
    </div>

    <template v-if="data">
      <!-- Overview Stats -->
      <div class="stats-grid">
        <div class="stat-card stat-blue">
          <span class="stat-number">{{ data.overview.active_access }}</span>
          <span class="stat-label">Active Clients</span>
        </div>
        <div class="stat-card stat-green">
          <span class="stat-number">{{ data.overview.projects_with_portal }}</span>
          <span class="stat-label">Portal Projects</span>
        </div>
        <div class="stat-card stat-amber">
          <span class="stat-number">{{ data.tickets.open }}</span>
          <span class="stat-label">Open Tickets</span>
        </div>
        <div class="stat-card stat-purple">
          <span class="stat-number">{{ data.approvals.pending_reviews }}</span>
          <span class="stat-label">Pending Reviews</span>
        </div>
        <div class="stat-card stat-teal">
          <span class="stat-number">{{ data.approvals.approved }}</span>
          <span class="stat-label">Approved Milestones</span>
        </div>
        <div class="stat-card stat-red">
          <span class="stat-number">{{ data.approvals.changes_requested }}</span>
          <span class="stat-label">Changes Requested</span>
        </div>
      </div>

      <!-- Two Column Layout -->
      <div class="analytics-grid">
        <!-- Left: Ticket Priority Breakdown -->
        <div class="analytics-panel">
          <h3 class="panel-title">Open Tickets by Priority</h3>
          <div class="priority-bars">
            <div v-for="(count, priority) in data.tickets.by_priority" :key="priority" class="priority-row">
              <span class="priority-name">{{ priority }}</span>
              <div class="priority-bar-track">
                <div class="priority-bar-fill" :class="'bar-' + priority.toLowerCase()" :style="{ width: priorityBarWidth(count) }"></div>
              </div>
              <span class="priority-count">{{ count }}</span>
            </div>
          </div>
          <div class="ticket-summary">
            <div class="summary-item">
              <span class="summary-label">Total Tickets</span>
              <span class="summary-value">{{ data.tickets.total }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Customer Created</span>
              <span class="summary-value">{{ data.tickets.customer_created }}</span>
            </div>
          </div>
        </div>

        <!-- Right: Per-Project Summary -->
        <div class="analytics-panel">
          <h3 class="panel-title">Project Portal Summary</h3>
          <div v-if="data.project_summaries.length" class="project-summary-list">
            <div v-for="ps in data.project_summaries" :key="ps.project" class="project-summary-row">
              <router-link :to="`/project/${ps.project}`" class="project-summary-name">{{ ps.project_name }}</router-link>
              <div class="project-summary-stats">
                <span class="ps-badge ps-clients" title="Active clients">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                  {{ ps.active_clients }}
                </span>
                <span v-if="ps.open_tickets" class="ps-badge ps-tickets" title="Open tickets">
                  {{ ps.open_tickets }} tickets
                </span>
                <span v-if="ps.pending_reviews" class="ps-badge ps-reviews" title="Pending reviews">
                  {{ ps.pending_reviews }} reviews
                </span>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">No projects with portal access yet.</p>
        </div>
      </div>

      <!-- Recent Activity Row -->
      <div class="analytics-grid">
        <!-- Recent Logins -->
        <div class="analytics-panel">
          <h3 class="panel-title">Recent Client Logins</h3>
          <div v-if="data.recent_logins.length" class="activity-list">
            <div v-for="login in data.recent_logins" :key="login.client_email + login.project" class="activity-row">
              <div class="activity-avatar" :style="{ background: avatarColor(login.client_email) }">
                {{ initials(login.client_email) }}
              </div>
              <div class="activity-info">
                <span class="activity-user">{{ login.client_email }}</span>
                <span class="activity-detail">{{ login.project_name }}</span>
              </div>
              <span class="activity-time">{{ formatRelative(login.last_login) }}</span>
            </div>
          </div>
          <p v-else class="empty-text">No recent logins.</p>
        </div>

        <!-- Recent Tickets -->
        <div class="analytics-panel">
          <h3 class="panel-title">Recent Support Tickets</h3>
          <div v-if="data.recent_tickets.length" class="activity-list">
            <div v-for="ticket in data.recent_tickets" :key="ticket.name" class="activity-row clickable" @click="$router.push(`/task/${ticket.name}`)">
              <div class="ticket-indicator">
                <span class="priority-dot" :class="'dot-' + (ticket.priority || 'medium').toLowerCase()"></span>
              </div>
              <div class="activity-info">
                <span class="activity-user">{{ ticket.task_title }}</span>
                <span class="activity-detail">
                  {{ ticket.project_name }}
                  <span v-if="ticket.created_by_customer" class="customer-badge">Customer</span>
                </span>
              </div>
              <div class="ticket-status-col">
                <span class="ticket-status-badge" :class="statusClass(ticket.status)">{{ ticket.status }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">No support tickets yet.</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const data = ref(null)
const loading = ref(true)

onMounted(() => loadAnalytics())

async function loadAnalytics() {
  loading.value = true
  try {
    data.value = await call('next_pms.api.portal.get_portal_analytics')
  } catch (e) {
    console.error('Failed to load portal analytics:', e)
  } finally {
    loading.value = false
  }
}

function priorityBarWidth(count) {
  if (!data.value) return '0%'
  const max = Math.max(...Object.values(data.value.tickets.by_priority), 1)
  return Math.round((count / max) * 100) + '%'
}

function avatarColor(email) {
  const colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
  let hash = 0
  for (let i = 0; i < (email || '').length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function initials(email) {
  if (!email) return '?'
  const name = email.split('@')[0]
  const parts = name.split(/[._-]/)
  return parts.length >= 2 ? (parts[0][0] + parts[1][0]).toUpperCase() : name.substring(0, 2).toUpperCase()
}

function formatRelative(d) {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

function statusClass(status) {
  const map = {
    'To Do': 'ts-todo', 'In Progress': 'ts-progress', 'In Review': 'ts-review',
    'Done': 'ts-done', 'Cancelled': 'ts-cancelled', 'Backlog': 'ts-backlog',
  }
  return map[status] || 'ts-todo'
}
</script>

<style scoped>
.portal-analytics { padding: 16px 0; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;
}
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-secondary); margin: 2px 0 0; }

.btn-refresh {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border: 1px solid var(--border-default); border-radius: 8px;
  background: var(--bg-surface); color: var(--text-secondary); font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
}
.btn-refresh:hover { border-color: var(--color-primary); color: var(--color-primary); }
.btn-refresh:disabled { opacity: 0.5; }

.loading-container {
  display: flex; flex-direction: column; align-items: center; padding: 80px 0;
}
.spinner {
  width: 40px; height: 40px; border: 3px solid var(--border-default);
  border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { margin-top: 16px; color: var(--text-secondary); font-size: 14px; }

/* Stats Grid */
.stats-grid {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px;
  padding: 16px; display: flex; flex-direction: column; gap: 2px;
}
.stat-number { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 11px; color: var(--text-secondary); font-weight: 500; text-transform: uppercase; letter-spacing: 0.3px; }

.stat-blue { border-left: 3px solid #2563eb; }
.stat-green { border-left: 3px solid #10b981; }
.stat-amber { border-left: 3px solid #f59e0b; }
.stat-purple { border-left: 3px solid #8b5cf6; }
.stat-teal { border-left: 3px solid #14b8a6; }
.stat-red { border-left: 3px solid #ef4444; }

/* Grid */
.analytics-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;
}

.analytics-panel {
  background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px;
}
.panel-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 16px; }

/* Priority bars */
.priority-bars { display: flex; flex-direction: column; gap: 10px; }
.priority-row { display: flex; align-items: center; gap: 10px; }
.priority-name { font-size: 12px; font-weight: 500; color: var(--text-secondary); width: 60px; }
.priority-bar-track { flex: 1; height: 8px; background: var(--border-default); border-radius: 4px; overflow: hidden; }
.priority-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.bar-low { background: #94a3b8; }
.bar-normal { background: #3b82f6; }
.bar-medium { background: #f59e0b; }
.bar-high { background: #f97316; }
.bar-urgent { background: #dc2626; }
.bar-critical { background: #ef4444; }
.priority-count { font-size: 13px; font-weight: 600; color: var(--text-primary); width: 24px; text-align: right; }

.ticket-summary {
  display: flex; gap: 16px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-light);
}
.summary-item { display: flex; flex-direction: column; gap: 2px; }
.summary-label { font-size: 11px; color: var(--text-tertiary); }
.summary-value { font-size: 18px; font-weight: 700; color: var(--text-primary); }

/* Project Summary */
.project-summary-list { display: flex; flex-direction: column; gap: 8px; }
.project-summary-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-radius: 8px; transition: background 0.15s;
}
.project-summary-row:hover { background: var(--bg-surface-active); }
.project-summary-name { font-size: 13px; font-weight: 500; color: var(--color-primary); text-decoration: none; }
.project-summary-name:hover { text-decoration: underline; }
.project-summary-stats { display: flex; align-items: center; gap: 8px; }

.ps-badge {
  display: inline-flex; align-items: center; gap: 3px; font-size: 11px; font-weight: 500;
  padding: 2px 8px; border-radius: 12px;
}
.ps-clients { background: rgba(37, 99, 235, 0.08); color: #2563eb; }
.ps-tickets { background: rgba(239, 68, 68, 0.08); color: #ef4444; }
.ps-reviews { background: rgba(245, 158, 11, 0.08); color: #d97706; }

/* Activity lists */
.activity-list { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
.activity-row {
  display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px;
  transition: background 0.15s;
}
.activity-row.clickable { cursor: pointer; }
.activity-row:hover { background: var(--bg-surface-active); }

.activity-avatar {
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 11px; font-weight: 700; flex-shrink: 0;
}

.ticket-indicator { display: flex; align-items: center; justify-content: center; width: 32px; flex-shrink: 0; }
.priority-dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-critical { background: #ef4444; }
.dot-urgent { background: #dc2626; }
.dot-high { background: #f97316; }
.dot-medium { background: #f59e0b; }
.dot-normal { background: #3b82f6; }
.dot-low { background: #94a3b8; }

.activity-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.activity-user { font-size: 13px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.activity-detail { font-size: 11px; color: var(--text-tertiary); display: flex; align-items: center; gap: 6px; }
.activity-time { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; flex-shrink: 0; }

.customer-badge {
  display: inline-flex; font-size: 9px; font-weight: 600; padding: 1px 5px; border-radius: 4px;
  background: rgba(139, 92, 246, 0.1); color: #8b5cf6; text-transform: uppercase;
}

.ticket-status-col { flex-shrink: 0; }
.ticket-status-badge {
  display: inline-flex; padding: 2px 8px; border-radius: 12px; font-size: 10px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.2px;
}
.ts-todo { background: #f1f5f9; color: #64748b; }
.ts-progress { background: #eff6ff; color: #2563eb; }
.ts-review { background: #faf5ff; color: #9333ea; }
.ts-done { background: #dcfce7; color: #16a34a; }
.ts-cancelled { background: #fee2e2; color: #dc2626; }
.ts-backlog { background: #f8fafc; color: #94a3b8; }

.empty-text { font-size: 13px; color: var(--text-tertiary); text-align: center; padding: 20px; margin: 0; }

@media (max-width: 1024px) {
  .stats-grid { grid-template-columns: repeat(3, 1fr); }
  .analytics-grid { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
