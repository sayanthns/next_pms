<template>
  <div class="portal-tickets">
    <div class="tickets-header">
      <h1>Support Tickets</h1>
      <button class="btn-new-ticket" @click="showNewTicket = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Ticket
      </button>
    </div>

    <!-- Filters & View Toggle -->
    <div class="tickets-toolbar">
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
      <div class="view-toggle">
        <button class="view-btn" :class="{ active: ticketView === 'list' }" @click="ticketView = 'list'" title="List view">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
        </button>
        <button class="view-btn" :class="{ active: ticketView === 'kanban' }" @click="ticketView = 'kanban'" title="Board view">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="5" height="18" rx="1"/><rect x="10" y="3" width="5" height="12" rx="1"/><rect x="17" y="3" width="5" height="15" rx="1"/></svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="filteredTickets.length === 0 && ticketView === 'list'" class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
        <path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      <p>No support tickets found.</p>
    </div>

    <!-- List View -->
    <div v-else-if="ticketView === 'list'" class="tickets-list">
      <div
        v-for="t in filteredTickets"
        :key="t.name"
        class="ticket-card"
        @click="openTicket(t)"
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

    <!-- Kanban View -->
    <div v-else-if="ticketView === 'kanban' && !loading" class="ticket-kanban">
      <div v-for="col in ticketKanbanColumns" :key="col.key" class="kanban-col">
        <div class="kanban-col-header" :class="'kh-' + col.key">
          <span>{{ col.label }}</span>
          <span class="kanban-col-count">{{ ticketsByKanbanStatus(col.statuses).length }}</span>
        </div>
        <div class="kanban-col-body">
          <div
            v-for="t in ticketsByKanbanStatus(col.statuses)"
            :key="t.name"
            class="kanban-card"
            @click="openTicket(t)"
          >
            <span class="kanban-card-title">{{ t.task_title }}</span>
            <div class="kanban-card-meta">
              <span class="ticket-priority" :class="'tp-' + t.priority?.toLowerCase()">{{ t.priority }}</span>
              <span class="kanban-card-project">{{ t.project_name }}</span>
            </div>
          </div>
          <div v-if="ticketsByKanbanStatus(col.statuses).length === 0" class="kanban-empty">No tickets</div>
        </div>
      </div>
    </div>

    <!-- Ticket Detail Drawer -->
    <div v-if="selectedTicket" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer">
        <div class="drawer-header">
          <div>
            <h3>{{ ticketDetail?.task?.task_title || 'Loading...' }}</h3>
            <span v-if="ticketDetail" class="drawer-ticket-id">{{ ticketDetail.task.name }}</span>
          </div>
          <button class="drawer-close" @click="closeDrawer">&times;</button>
        </div>
        <div v-if="ticketLoading" class="loading-state small"><div class="spinner"></div></div>
        <div v-else-if="ticketDetail" class="drawer-body">
          <!-- Status & Priority -->
          <div class="drawer-meta">
            <span class="ticket-status" :class="'ts-' + ticketDetail.task.status?.toLowerCase().replace(/\s+/g, '-')">{{ ticketDetail.task.status }}</span>
            <span class="ticket-priority" :class="'tp-' + ticketDetail.task.priority?.toLowerCase()">{{ ticketDetail.task.priority }}</span>
            <span class="drawer-project">{{ ticketDetail.task.project_name || ticketDetail.task.project }}</span>
          </div>

          <!-- Description -->
          <div v-if="ticketDetail.task.description" class="drawer-section">
            <h4>Description</h4>
            <div class="description-content" v-html="ticketDetail.task.description"></div>
          </div>

          <!-- Assigned To -->
          <div v-if="ticketDetail.assignees?.length" class="drawer-section">
            <h4>Assigned To</h4>
            <div class="assignee-list">
              <span v-for="a in ticketDetail.assignees" :key="a.user" class="assignee-chip">{{ a.full_name }}</span>
            </div>
          </div>

          <!-- Due Date -->
          <div v-if="ticketDetail.task.due_date" class="drawer-section">
            <h4>Due Date</h4>
            <span>{{ formatDate(ticketDetail.task.due_date) }}</span>
          </div>

          <!-- Created -->
          <div class="drawer-section">
            <h4>Created</h4>
            <span>{{ formatDateTime(ticketDetail.task.creation) }}</span>
          </div>

          <!-- Comments -->
          <div class="drawer-section">
            <h4>Comments ({{ ticketDetail.comments?.length || 0 }})</h4>
            <div v-if="ticketDetail.comments?.length" class="comments-list">
              <div v-for="c in ticketDetail.comments" :key="c.name" class="comment-item">
                <div class="comment-header">
                  <span class="comment-author">{{ c.author_name }}</span>
                  <span class="comment-time">{{ formatDateTime(c.creation) }}</span>
                </div>
                <div class="comment-text">{{ c.content }}</div>
              </div>
            </div>
            <div class="comment-form">
              <textarea v-model="newComment" rows="3" placeholder="Add a comment..." class="comment-input"></textarea>
              <button class="btn-comment" @click="postComment" :disabled="!newComment.trim() || posting">
                {{ posting ? 'Posting...' : 'Post Comment' }}
              </button>
            </div>
          </div>

          <!-- Acknowledge button (for open tickets) -->
          <div v-if="ticketDetail.task.status === 'Done'" class="drawer-section acknowledge-section">
            <div class="acknowledge-banner">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              <span>This ticket has been resolved.</span>
            </div>
          </div>

          <!-- Files -->
          <div v-if="ticketDetail.files?.length" class="drawer-section">
            <h4>Attachments</h4>
            <a v-for="f in ticketDetail.files" :key="f.name" :href="f.file_url" target="_blank" class="file-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
              {{ f.file_name }}
            </a>
          </div>
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
            <option value="Normal">Normal</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Urgent">Urgent</option>
            <option value="Critical">Critical</option>
          </select>
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea v-model="newTicket.description" rows="4" class="form-input" placeholder="Describe the issue in detail..."></textarea>
        </div>
        <div class="form-group">
          <label>Attachments <span class="label-hint">(optional)</span></label>
          <div class="file-upload-area" @click="$refs.fileInput.click()" @dragover.prevent @drop.prevent="handleDrop">
            <input ref="fileInput" type="file" multiple @change="handleFiles" style="display:none" />
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
            <span>Click or drag files here</span>
          </div>
          <div v-if="selectedFiles.length" class="selected-files">
            <div v-for="(f, i) in selectedFiles" :key="i" class="selected-file">
              <span>{{ f.name }}</span>
              <button class="file-remove" @click.stop="selectedFiles.splice(i, 1)">&times;</button>
            </div>
          </div>
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
const ticketView = ref('list')

const ticketKanbanColumns = [
  { key: 'open', label: 'Open', statuses: ['To Do', 'Backlog'] },
  { key: 'progress', label: 'In Progress', statuses: ['In Progress'] },
  { key: 'review', label: 'In Review', statuses: ['In Review'] },
  { key: 'done', label: 'Resolved', statuses: ['Done'] },
]

function ticketsByKanbanStatus(statuses) {
  return filteredTickets.value.filter(t => statuses.includes(t.status))
}

// New ticket
const showNewTicket = ref(false)
const creating = ref(false)
const newTicket = ref({ project: '', title: '', priority: 'Medium', description: '' })
const selectedFiles = ref([])

// Ticket detail drawer
const selectedTicket = ref(null)
const ticketDetail = ref(null)
const ticketLoading = ref(false)
const newComment = ref('')
const posting = ref(false)

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

async function openTicket(t) {
  selectedTicket.value = t.name
  ticketLoading.value = true
  ticketDetail.value = null
  try {
    ticketDetail.value = await call('next_pms.api.portal.get_portal_task_detail', { task: t.name })
    // Enrich with project name
    if (ticketDetail.value?.task) {
      ticketDetail.value.task.project_name = t.project_name
    }
  } catch (e) {
    console.error('Failed to load ticket detail:', e)
  } finally {
    ticketLoading.value = false
  }
}

function closeDrawer() {
  selectedTicket.value = null
  ticketDetail.value = null
  newComment.value = ''
}

async function postComment() {
  if (!newComment.value.trim() || posting.value) return
  posting.value = true
  try {
    const res = await call('next_pms.api.portal.add_portal_comment', {
      task: selectedTicket.value,
      content: newComment.value.trim(),
    })
    if (res) {
      if (!ticketDetail.value.comments) ticketDetail.value.comments = []
      ticketDetail.value.comments.push(res)
      newComment.value = ''
      // Update comment count in the list
      const ticket = tickets.value.find(t => t.name === selectedTicket.value)
      if (ticket) ticket.comment_count = (ticket.comment_count || 0) + 1
    }
  } catch (e) {
    console.error('Failed to post comment:', e)
  } finally {
    posting.value = false
  }
}

function handleFiles(e) {
  const files = Array.from(e.target.files || [])
  selectedFiles.value.push(...files)
}

function handleDrop(e) {
  const files = Array.from(e.dataTransfer.files || [])
  selectedFiles.value.push(...files)
}

async function uploadFiles(taskName) {
  for (const file of selectedFiles.value) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('task', taskName)
      formData.append('cmd', 'next_pms.api.portal.upload_portal_attachment')
      await fetch('/api/method/next_pms.api.portal.upload_portal_attachment', {
        method: 'POST',
        headers: { 'X-Frappe-CSRF-Token': window.frappe?.csrf_token || '' },
        body: formData,
      })
    } catch (e) {
      console.error('Failed to upload file:', file.name, e)
    }
  }
}

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
      // Upload attachments if any
      if (selectedFiles.value.length && res.name) {
        await uploadFiles(res.name)
      }
      const projectName = projectOptions.value.find(p => p.name === newTicket.value.project)?.project_name || ''
      tickets.value.unshift({
        ...res,
        project: newTicket.value.project,
        project_name: projectName,
        comment_count: 0,
      })
      showNewTicket.value = false
      newTicket.value = { project: '', title: '', priority: 'Medium', description: '' }
      selectedFiles.value = []
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

function formatDateTime(d) {
  if (!d) return ''
  try { return new Date(d).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) } catch { return d }
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

.tickets-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 8px; flex-wrap: wrap; }
.tickets-filters { display: flex; gap: 8px; }
.filter-select { padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; background: #fff; }
.view-toggle { display: flex; gap: 2px; background: #f1f5f9; border-radius: 6px; padding: 2px; }
.view-btn {
  background: none; border: none; padding: 5px 8px; border-radius: 4px; cursor: pointer;
  color: #94a3b8; display: flex; align-items: center; transition: all 0.15s;
}
.view-btn:hover { color: #334155; }
.view-btn.active { background: #fff; color: #2563eb; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }

/* Kanban */
.ticket-kanban { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.kanban-col { min-width: 0; }
.kanban-col-header {
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  padding: 8px 10px; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;
}
.kh-open { background: #f1f5f9; color: #64748b; }
.kh-progress { background: #eff6ff; color: #2563eb; }
.kh-review { background: #faf5ff; color: #9333ea; }
.kh-done { background: #f0fdf4; color: #16a34a; }
.kanban-col-count { font-size: 10px; background: rgba(0,0,0,0.08); padding: 1px 6px; border-radius: 8px; }
.kanban-col-body { background: #fafbfc; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; padding: 8px; min-height: 80px; display: flex; flex-direction: column; gap: 6px; }
.kanban-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px;
  cursor: pointer; transition: all 0.15s;
}
.kanban-card:hover { border-color: #2563eb; box-shadow: 0 2px 6px rgba(37,99,235,0.08); }
.kanban-card-title { font-size: 13px; font-weight: 500; color: #1e293b; display: block; margin-bottom: 6px; line-height: 1.3; }
.kanban-card-meta { display: flex; gap: 6px; align-items: center; }
.kanban-card-project { font-size: 10px; color: #94a3b8; }
.kanban-empty { text-align: center; color: #cbd5e1; font-size: 12px; padding: 16px 0; }

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
.tp-urgent { background: #fef2f2; color: #dc2626; }
.tp-high { background: #fff7ed; color: #ea580c; }
.tp-medium { background: #fffbeb; color: #d97706; }
.tp-normal { background: #eff6ff; color: #3b82f6; }
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

.label-hint { font-weight: 400; color: #94a3b8; }
.file-upload-area {
  border: 2px dashed #e5e7eb; border-radius: 8px; padding: 16px; text-align: center;
  cursor: pointer; transition: border-color 0.2s; display: flex; flex-direction: column; align-items: center; gap: 6px;
  font-size: 13px; color: #94a3b8;
}
.file-upload-area:hover { border-color: #2563eb; color: #64748b; }
.selected-files { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
.selected-file {
  display: flex; justify-content: space-between; align-items: center; padding: 6px 10px;
  background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 12px; color: #334155;
}
.file-remove { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 16px; padding: 0 4px; }
.file-remove:hover { color: #ef4444; }

/* Drawer */
.drawer-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 1000;
  display: flex; justify-content: flex-end;
}
.drawer {
  width: 520px; max-width: 90vw; background: #fff; height: 100vh; overflow-y: auto;
  box-shadow: -8px 0 24px rgba(0,0,0,0.1);
}
.drawer-header {
  display: flex; justify-content: space-between; align-items: flex-start; padding: 20px;
  border-bottom: 1px solid #e5e7eb; position: sticky; top: 0; background: #fff; z-index: 1;
}
.drawer-header h3 { font-size: 16px; font-weight: 600; color: #1e293b; margin: 0; }
.drawer-ticket-id { font-size: 11px; color: #94a3b8; font-family: monospace; }
.drawer-close { background: none; border: none; font-size: 24px; cursor: pointer; color: #94a3b8; padding: 4px; line-height: 1; }
.drawer-close:hover { color: #334155; }
.drawer-body { padding: 20px; }
.drawer-meta { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.drawer-project { font-size: 12px; color: #64748b; background: #f1f5f9; padding: 2px 8px; border-radius: 6px; }
.drawer-section { margin-bottom: 20px; }
.drawer-section h4 { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 8px; }
.description-content { font-size: 13px; color: #334155; line-height: 1.6; }
.assignee-list { display: flex; flex-wrap: wrap; gap: 6px; }
.assignee-chip { font-size: 12px; background: #e0e7ff; color: #4338ca; padding: 3px 10px; border-radius: 12px; }

/* Comments */
.comments-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.comment-item { background: #f8fafc; border-radius: 8px; padding: 10px; }
.comment-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.comment-author { font-size: 12px; font-weight: 600; color: #334155; }
.comment-time { font-size: 11px; color: #94a3b8; }
.comment-text { font-size: 13px; color: #475569; line-height: 1.5; }
.comment-form { display: flex; flex-direction: column; gap: 8px; }
.comment-input { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 12px; font-size: 13px; resize: vertical; font-family: inherit; }
.comment-input:focus { outline: none; border-color: #2563eb; }
.btn-comment {
  align-self: flex-end; background: #2563eb; color: #fff; border: none; padding: 6px 16px;
  border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer;
}
.btn-comment:hover { background: #1d4ed8; }
.btn-comment:disabled { opacity: 0.5; cursor: not-allowed; }

/* Acknowledge */
.acknowledge-section { margin-top: 8px; }
.acknowledge-banner {
  display: flex; align-items: center; gap: 10px; padding: 12px 16px;
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: #16a34a;
}

/* File items */
.file-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #fff;
  border: 1px solid #e5e7eb; border-radius: 8px; text-decoration: none; color: #334155;
  font-size: 13px; margin-bottom: 4px; transition: border-color 0.15s;
}
.file-item:hover { border-color: #2563eb; color: #2563eb; }

.loading-state.small { padding: 30px; }

@media (max-width: 768px) {
  .drawer { width: 100vw; }
}
</style>
