<template>
  <div class="portal-tickets">
    <div class="tickets-header">
      <h1>Support Tickets</h1>
      <button class="btn-new-ticket" @click="showNewTicket = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Ticket
      </button>
    </div>

    <!-- Filters -->
    <div class="tickets-filters">
      <select v-model="filterProject" class="filter-select">
        <option value="">All Projects</option>
        <option v-for="p in projectOptions" :key="p.name" :value="p.name">{{ p.project_name }}</option>
      </select>
      <select v-model="filterStatus" class="filter-select">
        <option value="">All Statuses</option>
        <option value="open">Open</option>
        <option value="done">Done</option>
      </select>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="filteredTickets.length === 0" class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
        <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      <p>No support tickets found.</p>
    </div>

    <div v-else class="tickets-list">
      <div
        v-for="t in filteredTickets"
        :key="t.name"
        class="ticket-card"
        @click="$router.push(`/portal/project/${t.project}`)"
      >
        <div class="ticket-top">
          <span class="ticket-id">{{ t.name }}</span>
          <span class="ticket-status" :class="'ts-' + t.status?.toLowerCase().replace(/\s+/g, '-')">{{ t.status }}</span>
        </div>
        <h3 class="ticket-title">{{ t.task_title }}</h3>
        <div class="ticket-meta">
          <span class="ticket-project">{{ t.project_name }}</span>
          <span class="ticket-priority" :class="'tp-' + t.priority?.toLowerCase()">{{ t.priority }}</span>
          <span class="ticket-date">{{ formatDate(t.creation) }}</span>
          <span v-if="t.comment_count" class="ticket-comments">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
            {{ t.comment_count }}
          </span>
        </div>
      </div>
    </div>

    <!-- New Ticket Dialog -->
    <div v-if="showNewTicket" class="dialog-overlay" @click.self="showNewTicket = false">
      <div class="dialog-box">
        <h3>Create Support Ticket</h3>
        <div class="form-group">
          <label>Project</label>
          <select v-model="newTicket.project" class="form-input">
            <option value="">Select a project</option>
            <option v-for="p in projectOptions" :key="p.name" :value="p.name">{{ p.project_name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Title</label>
          <input v-model="newTicket.title" class="form-input" placeholder="Brief description of the issue" />
        </div>
        <div class="form-group">
          <label>Priority</label>
          <select v-model="newTicket.priority" class="form-input">
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea v-model="newTicket.description" rows="4" class="form-input" placeholder="Describe the issue in detail..."></textarea>
        </div>
        <div class="dialog-actions">
          <button class="btn-cancel" @click="showNewTicket = false">Cancel</button>
          <button class="btn-submit" @click="createTicket" :disabled="!canSubmit || creating">
            {{ creating ? 'Creating...' : 'Create Ticket' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const tickets = ref([])
const projectOptions = ref([])
const loading = ref(true)
const filterProject = ref('')
const filterStatus = ref('')

// New ticket
const showNewTicket = ref(false)
const creating = ref(false)
const newTicket = ref({ project: '', title: '', priority: 'Medium', description: '' })

const canSubmit = computed(() => newTicket.value.project && newTicket.value.title.trim())

const filteredTickets = computed(() => {
  let result = tickets.value
  if (filterProject.value) result = result.filter(t => t.project === filterProject.value)
  if (filterStatus.value === 'open') result = result.filter(t => !['Done', 'Cancelled'].includes(t.status))
  if (filterStatus.value === 'done') result = result.filter(t => t.status === 'Done')
  return result
})

onMounted(async () => {
  try {
    const [ticketsRes, projectsRes] = await Promise.all([
      call('next_pms.api.portal.get_portal_tickets'),
      call('next_pms.api.portal.get_portal_projects'),
    ])
    tickets.value = ticketsRes || []
    projectOptions.value = (projectsRes || []).map(p => ({ name: p.name, project_name: p.project_name }))
  } catch (e) {
    console.error('Failed to load tickets:', e)
  } finally {
    loading.value = false
  }
})

async function createTicket() {
  if (!canSubmit.value || creating.value) return
  creating.value = true
  try {
    const res = await call('next_pms.api.portal.create_support_ticket', {
      project: newTicket.value.project,
      title: newTicket.value.title.trim(),
      description: newTicket.value.description.trim(),
      priority: newTicket.value.priority,
    })
    if (res) {
      // Add to list
      const projectName = projectOptions.value.find(p => p.name === newTicket.value.project)?.project_name || ''
      tickets.value.unshift({
        ...res,
        project: newTicket.value.project,
        project_name: projectName,
        comment_count: 0,
      })
      showNewTicket.value = false
      newTicket.value = { project: '', title: '', priority: 'Medium', description: '' }
    }
  } catch (e) {
    console.error('Failed to create ticket:', e)
  } finally {
    creating.value = false
  }
}

function formatDate(d) {
  if (!d) return ''
  try { return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) } catch { return d }
}
</script>

<style scoped>
.portal-tickets { max-width: 100%; }

.tickets-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.tickets-header h1 { font-size: 20px; font-weight: 700; color: #1e293b; margin: 0; }

.btn-new-ticket {
  display: flex; align-items: center; gap: 6px; background: #2563eb; color: #fff; border: none;
  padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s;
}
.btn-new-ticket:hover { background: #1d4ed8; }

.tickets-filters { display: flex; gap: 8px; margin-bottom: 16px; }
.filter-select { padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; background: #fff; }

.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center; padding: 60px; color: #94a3b8; gap: 12px;
}
.spinner { width: 28px; height: 28px; border: 3px solid #e5e7eb; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.tickets-list { display: flex; flex-direction: column; gap: 8px; }

.ticket-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px;
  cursor: pointer; transition: all 0.15s;
}
.ticket-card:hover { border-color: #2563eb; box-shadow: 0 2px 8px rgba(37,99,235,0.06); }

.ticket-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ticket-id { font-size: 11px; color: #94a3b8; font-family: monospace; }

.ticket-status { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 6px; }
.ts-to-do { background: #f1f5f9; color: #64748b; }
.ts-in-progress { background: #eff6ff; color: #2563eb; }
.ts-in-review { background: #faf5ff; color: #9333ea; }
.ts-done { background: #dcfce7; color: #16a34a; }
.ts-backlog { background: #f8fafc; color: #94a3b8; }

.ticket-title { font-size: 15px; font-weight: 600; color: #1e293b; margin: 0 0 8px; }

.ticket-meta { display: flex; align-items: center; gap: 10px; font-size: 12px; color: #94a3b8; flex-wrap: wrap; }

.ticket-priority { font-size: 11px; font-weight: 500; padding: 1px 6px; border-radius: 4px; }
.tp-critical { background: #fef2f2; color: #dc2626; }
.tp-high { background: #fff7ed; color: #ea580c; }
.tp-medium { background: #fffbeb; color: #d97706; }
.tp-low { background: #f0fdf4; color: #16a34a; }

.ticket-comments { display: flex; align-items: center; gap: 3px; }

/* Dialog */
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1100;
  display: flex; align-items: center; justify-content: center;
}
.dialog-box {
  background: #fff; border-radius: 12px; padding: 24px; width: 480px; max-width: 90vw;
  box-shadow: 0 20px 40px rgba(0,0,0,0.15);
}
.dialog-box h3 { font-size: 17px; font-weight: 600; margin: 0 0 16px; color: #1e293b; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 4px; }
.form-input {
  width: 100%; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px;
  font-family: inherit; box-sizing: border-box;
}
.form-input:focus { outline: none; border-color: #2563eb; }
textarea.form-input { resize: vertical; }

.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.btn-cancel { background: #f1f5f9; color: #64748b; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-submit { background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-submit:hover { background: #1d4ed8; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
