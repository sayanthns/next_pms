<template>
  <div class="support-tickets-page">
    <div class="page-header">
      <div>
        <h1>Support Tickets</h1>
        <p class="page-desc">Manage customer support tickets across all projects</p>
      </div>
      <button class="btn-refresh" @click="loadTickets">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        Refresh
      </button>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ stats.total }}</span>
        <span class="stat-label">Total Tickets</span>
      </div>
      <div class="stat-card stat-open">
        <span class="stat-value">{{ stats.open }}</span>
        <span class="stat-label">Open</span>
      </div>
      <div class="stat-card stat-progress">
        <span class="stat-value">{{ stats.in_progress }}</span>
        <span class="stat-label">In Progress</span>
      </div>
      <div class="stat-card stat-done">
        <span class="stat-value">{{ stats.done }}</span>
        <span class="stat-label">Resolved</span>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-row">
      <div class="search-box">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="searchQuery" type="text" placeholder="Search tickets..." class="search-input" />
      </div>
      <select v-model="filterProject" class="filter-select">
        <option value="">All Projects</option>
        <option v-for="p in projectOptions" :key="p.name" :value="p.name">{{ p.project_name }}</option>
      </select>
      <select v-model="filterStatus" class="filter-select">
        <option value="">All Statuses</option>
        <option value="To Do">To Do</option>
        <option value="In Progress">In Progress</option>
        <option value="In Review">In Review</option>
        <option value="Done">Done</option>
      </select>
      <select v-model="filterPriority" class="filter-select">
        <option value="">All Priorities</option>
        <option value="Critical">Critical</option>
        <option value="High">High</option>
        <option value="Medium">Medium</option>
        <option value="Low">Low</option>
      </select>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="filteredTickets.length === 0" class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
      <p>No support tickets found.</p>
    </div>

    <!-- Tickets Table -->
    <div v-else class="tickets-table-wrap">
      <table class="tickets-table">
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Project</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Customer</th>
            <th>Comments</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in filteredTickets" :key="t.name" @click="$router.push(`/task/${t.name}`)">
            <td>
              <div class="ticket-title">{{ t.task_title }}</div>
              <div class="ticket-id">{{ t.name }}</div>
            </td>
            <td>{{ t.project_name }}</td>
            <td><span class="status-badge" :class="'sb-' + t.status?.toLowerCase().replace(/\s+/g, '-')">{{ t.status }}</span></td>
            <td><span class="priority-badge" :class="'pb-' + t.priority?.toLowerCase()">{{ t.priority }}</span></td>
            <td>{{ t.customer_created ? 'Customer' : 'Internal' }}</td>
            <td>{{ t.comment_count || 0 }}</td>
            <td>{{ formatDate(t.creation) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const tickets = ref([])
const projectOptions = ref([])
const loading = ref(true)
const searchQuery = ref('')
const filterProject = ref('')
const filterStatus = ref('')
const filterPriority = ref('')

const stats = computed(() => {
  const all = tickets.value
  return {
    total: all.length,
    open: all.filter(t => t.status === 'To Do').length,
    in_progress: all.filter(t => t.status === 'In Progress' || t.status === 'In Review').length,
    done: all.filter(t => t.status === 'Done').length,
  }
})

const filteredTickets = computed(() => {
  let result = tickets.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      (t.task_title || '').toLowerCase().includes(q) ||
      (t.name || '').toLowerCase().includes(q) ||
      (t.project_name || '').toLowerCase().includes(q)
    )
  }
  if (filterProject.value) result = result.filter(t => t.project === filterProject.value)
  if (filterStatus.value) result = result.filter(t => t.status === filterStatus.value)
  if (filterPriority.value) result = result.filter(t => t.priority === filterPriority.value)
  return result
})

onMounted(() => loadTickets())

async function loadTickets() {
  loading.value = true
  try {
    const [ticketsRes, projectsRes] = await Promise.all([
      call('next_pms.api.portal.get_all_support_tickets'),
      call('frappe.client.get_list', {
        doctype: 'PMS Project',
        fields: ['name', 'project_name'],
        filters: { client_portal_enabled: 1 },
        limit_page_length: 0,
        order_by: 'project_name asc',
      }),
    ])
    tickets.value = ticketsRes || []
    projectOptions.value = projectsRes || []
  } catch (e) {
    console.error('Failed to load support tickets:', e)
  } finally {
    loading.value = false
  }
}

function formatDate(d) {
  if (!d) return ''
  try { return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) } catch { return d }
}
</script>

<style scoped>
.support-tickets-page { max-width: 100%; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-header h1 { font-size: 22px; font-weight: 700; color: #1e293b; margin: 0; }
.page-desc { font-size: 13px; color: #64748b; margin: 4px 0 0; }

.btn-refresh {
  display: flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #e5e7eb;
  padding: 8px 16px; border-radius: 8px; font-size: 13px; color: #64748b; cursor: pointer; transition: all 0.2s;
}
.btn-refresh:hover { border-color: #2563eb; color: #2563eb; }

/* Stats */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.stat-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px;
  display: flex; flex-direction: column; gap: 2px;
}
.stat-value { font-size: 24px; font-weight: 700; color: #1e293b; }
.stat-label { font-size: 12px; color: #94a3b8; }
.stat-open { border-left: 3px solid #f59e0b; }
.stat-progress { border-left: 3px solid #2563eb; }
.stat-done { border-left: 3px solid #16a34a; }

/* Filters */
.filters-row { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.search-box {
  display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid #e5e7eb;
  border-radius: 8px; padding: 0 12px; flex: 1; min-width: 200px;
}
.search-input { border: none; outline: none; font-size: 13px; padding: 8px 0; width: 100%; background: transparent; }
.filter-select { padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; background: #fff; }

/* Table */
.tickets-table-wrap { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
.tickets-table { width: 100%; border-collapse: collapse; }
.tickets-table th {
  text-align: left; padding: 10px 16px; font-size: 11px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e5e7eb; background: #fafbfc;
}
.tickets-table td { padding: 12px 16px; font-size: 13px; color: #334155; border-bottom: 1px solid #f1f5f9; }
.tickets-table tr:last-child td { border-bottom: none; }
.tickets-table tbody tr { cursor: pointer; transition: background 0.15s; }
.tickets-table tbody tr:hover { background: #f8faff; }

.ticket-title { font-weight: 500; color: #1e293b; }
.ticket-id { font-size: 11px; color: #94a3b8; font-family: monospace; }

.status-badge, .priority-badge { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 6px; white-space: nowrap; }
.sb-to-do { background: #f1f5f9; color: #64748b; }
.sb-in-progress { background: #eff6ff; color: #2563eb; }
.sb-in-review { background: #faf5ff; color: #9333ea; }
.sb-done { background: #dcfce7; color: #16a34a; }
.sb-backlog { background: #f8fafc; color: #94a3b8; }

.pb-critical { background: #fef2f2; color: #dc2626; }
.pb-high { background: #fff7ed; color: #ea580c; }
.pb-medium { background: #fffbeb; color: #d97706; }
.pb-low { background: #f0fdf4; color: #16a34a; }

/* States */
.loading-state, .empty-state { display: flex; flex-direction: column; align-items: center; padding: 60px; color: #94a3b8; gap: 12px; }
.spinner { width: 28px; height: 28px; border: 3px solid #e5e7eb; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .filters-row { flex-direction: column; }
}
</style>
