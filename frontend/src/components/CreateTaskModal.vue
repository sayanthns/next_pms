<template>
  <CreateModal
    :show="show"
    title="New Task"
    submitLabel="Create Task"
    :saving="saving"
    @close="$emit('close')"
    @submit="handleSubmit"
  >
    <form @submit.prevent="handleSubmit" class="form-fields">
      <div class="form-group">
        <label class="form-label">Task Title <span class="required">*</span></label>
        <input
          v-model="form.task_title"
          type="text"
          class="form-input"
          placeholder="Enter task title"
          required
          ref="titleInput"
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Priority</label>
          <select v-model="form.priority" class="form-input">
            <option value="Low">Low</option>
            <option value="Normal">Normal</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Urgent">Urgent</option>
            <option value="Critical">Critical</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Status</label>
          <select v-model="form.status" class="form-input">
            <option value="Backlog">Backlog</option>
            <option value="To Do">To Do</option>
            <option value="In Progress">In Progress</option>
            <option value="In Review">In Review</option>
            <option value="Done">Done</option>
          </select>
        </div>
      </div>

      <!-- Multi-User Assignee Picker -->
      <div class="form-group">
        <label class="form-label">Assign To</label>
        <div class="assignee-picker">
          <!-- Selected assignees -->
          <div v-if="selectedAssignees.length" class="selected-assignees">
            <div
              v-for="user in selectedAssignees"
              :key="user.user"
              class="assignee-chip"
            >
              <span class="assignee-chip-avatar">{{ getInitials(user.full_name || user.user) }}</span>
              <span class="assignee-chip-name">{{ user.full_name || user.user }}</span>
              <button type="button" class="assignee-chip-remove" @click="removeAssignee(user.user)">&times;</button>
            </div>
          </div>

          <!-- Search input -->
          <div class="assignee-search-wrap">
            <input
              v-model="userSearch"
              type="text"
              class="form-input assignee-search"
              placeholder="Search and select team members..."
              @focus="showUserDropdown = true"
              @input="showUserDropdown = true"
            />
          </div>

          <!-- Dropdown -->
          <div v-if="showUserDropdown && filteredUsers.length" class="user-dropdown">
            <div
              v-for="user in filteredUsers"
              :key="user.user"
              class="user-option"
              :class="{ selected: isSelected(user.user) }"
              @mousedown.prevent="toggleAssignee(user)"
            >
              <span class="user-option-avatar">{{ getInitials(user.full_name || user.user) }}</span>
              <div class="user-option-info">
                <span class="user-option-name">{{ user.full_name || user.user }}</span>
                <span class="user-option-email">{{ user.user }}</span>
              </div>
              <span v-if="isSelected(user.user)" class="user-option-check">✓</span>
            </div>
          </div>
          <div v-if="showUserDropdown && !filteredUsers.length && userSearch" class="user-dropdown">
            <div class="user-option-empty">No users found</div>
          </div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Reviewer</label>
        <select v-model="form.reviewer" class="form-input">
          <option value="">None</option>
          <option v-for="u in teamMembers" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
        </select>
      </div>

      <div class="form-group" v-if="sprints && sprints.length">
        <label class="form-label">Sprint</label>
        <select v-model="form.sprint" class="form-input">
          <option value="">No Sprint</option>
          <option
            v-for="s in sprints"
            :key="s.name"
            :value="s.name"
          >
            {{ s.sprint_name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Task Type</label>
        <select v-model="form.task_type" class="form-input">
          <option value="">None</option>
          <option value="Feature">Feature</option>
          <option value="Bug">Bug</option>
          <option value="Improvement">Improvement</option>
          <option value="Research">Research</option>
          <option value="Documentation">Documentation</option>
          <option value="Meeting">Meeting</option>
          <option value="Bench Task">Bench Task</option>
          <option value="R&D Task">R&amp;D Task</option>
          <option value="Support">Support</option>
          <option value="Support Ticket">Support Ticket</option>
        </select>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Estimated Hours <span class="required">*</span></label>
          <input
            v-model.number="form.estimated_hours"
            type="number"
            class="form-input"
            placeholder="0"
            min="0.5"
            step="0.5"
            required
          />
        </div>
        <div class="form-group">
          <label class="form-label">Due Date <span class="required">*</span></label>
          <input v-model="form.due_date" type="date" class="form-input" required />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Description</label>
        <RichTextEditor v-model="form.description" />
      </div>

      <div class="form-group">
        <label class="form-label">Attachments</label>
        <label class="file-upload-area" :class="{ 'has-files': attachedFiles.length }">
          <input
            type="file"
            multiple
            class="file-input-hidden"
            @change="handleFileSelect"
            ref="fileInputRef"
          />
          <div v-if="!attachedFiles.length" class="file-upload-placeholder">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span>Click to attach files or drag & drop</span>
          </div>
        </label>
        <div v-if="attachedFiles.length" class="attached-files">
          <div v-for="(f, i) in attachedFiles" :key="i" class="attached-file">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span class="attached-file-name">{{ f.name }}</span>
            <span class="attached-file-size">{{ formatFileSize(f.size) }}</span>
            <button type="button" class="attached-file-remove" @click="removeFile(i)">&times;</button>
          </div>
        </div>
      </div>
    </form>
  </CreateModal>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { call } from '@/utils/frappe'
import CreateModal from './CreateModal.vue'
import RichTextEditor from './RichTextEditor.vue'
import { eventBus, EVENTS } from '@/utils/eventBus'

const props = defineProps({
  show: { type: Boolean, default: false },
  projectId: { type: String, required: true },
  sprints: { type: Array, default: () => [] },
  defaultStatus: { type: String, default: 'Backlog' },
  defaultSprint: { type: String, default: '' },
})

const emit = defineEmits(['close', 'created'])

const titleInput = ref(null)
const fileInputRef = ref(null)
const saving = ref(false)
const form = ref(getDefaultForm())
const availableUsers = ref([])
const teamMembers = ref([])
const selectedAssignees = ref([])
const userSearch = ref('')
const showUserDropdown = ref(false)
const attachedFiles = ref([])

function getTodayDate() {
  const d = new Date()
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
}

function getDefaultForm() {
  return {
    task_title: '',
    priority: 'Medium',
    status: props.defaultStatus || 'Backlog',
    sprint: props.defaultSprint || '',
    task_type: '',
    reviewer: '',
    estimated_hours: 0,
    due_date: getTodayDate(),
    description: '',
  }
}

function handleFileSelect(event) {
  const files = event.target.files
  if (!files) return
  for (const f of files) {
    attachedFiles.value.push(f)
  }
}

function removeFile(index) {
  attachedFiles.value.splice(index, 1)
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return Math.round(size * 10) / 10 + ' ' + units[i]
}

async function uploadTaskAttachments(taskName) {
  const csrf = document.cookie.split('; ').find(c => c.startsWith('csrf_token='))?.split('=')[1]
    || (window.frappe && window.frappe.csrf_token) || ''
  for (const file of attachedFiles.value) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doctype', 'PMS Task')
    formData.append('docname', taskName)
    formData.append('is_private', '1')
    try {
      await fetch('/api/method/upload_file', {
        method: 'POST',
        headers: csrf ? { 'X-Frappe-CSRF-Token': csrf } : {},
        credentials: 'include',
        body: formData,
      })
    } catch (e) {
      console.error('Failed to upload attachment:', file.name, e)
    }
  }
}

const filteredUsers = computed(() => {
  const search = userSearch.value.toLowerCase()
  return availableUsers.value.filter(u => {
    const name = (u.full_name || '').toLowerCase()
    const email = (u.user || '').toLowerCase()
    return name.includes(search) || email.includes(search)
  })
})

function isSelected(user) {
  return selectedAssignees.value.some(a => a.user === user)
}

function toggleAssignee(user) {
  if (isSelected(user.user)) {
    removeAssignee(user.user)
  } else {
    selectedAssignees.value.push(user)
  }
}

function removeAssignee(userId) {
  selectedAssignees.value = selectedAssignees.value.filter(a => a.user !== userId)
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

async function loadUsers() {
  try {
    const members = await call('next_pms.api.crud.get_project_members', {
      project: props.projectId,
    })
    if (members && members.length) {
      availableUsers.value = members
    } else {
      const allUsers = await call('next_pms.api.crud.get_all_users')
      availableUsers.value = (allUsers || []).map(u => ({
        user: u.name,
        full_name: u.full_name,
        user_image: u.user_image,
      }))
    }
    // Load team members for reviewer dropdown
    const allUsers = await call('next_pms.api.crud.get_all_users')
    teamMembers.value = allUsers || []
  } catch (e) {
    console.error('Failed to load users:', e)
    // Fallback to all users
    try {
      const allUsers = await call('next_pms.api.crud.get_all_users')
      availableUsers.value = (allUsers || []).map(u => ({
        user: u.name,
        full_name: u.full_name,
        user_image: u.user_image,
      }))
    } catch (e2) {
      availableUsers.value = []
    }
  }
}

function handleDocumentClick(e) {
  if (!e.target.closest('.assignee-picker')) {
    showUserDropdown.value = false
  }
}

watch(() => props.show, (val) => {
  if (val) {
    form.value = getDefaultForm()
    selectedAssignees.value = []
    attachedFiles.value = []
    userSearch.value = ''
    showUserDropdown.value = false
    loadUsers()
    nextTick(() => titleInput.value?.focus())
    document.addEventListener('click', handleDocumentClick)
  } else {
    document.removeEventListener('click', handleDocumentClick)
  }
})

async function handleSubmit() {
  if (!form.value.task_title.trim()) return
  if (!form.value.estimated_hours || form.value.estimated_hours <= 0) {
    alert('Estimated Hours is required')
    return
  }
  if (!form.value.due_date) {
    alert('Due Date is required')
    return
  }
  saving.value = true
  try {
    const assigneeEmails = selectedAssignees.value.map(a => a.user)
    const result = await call('next_pms.api.crud.create_task', {
      project: props.projectId,
      task_title: form.value.task_title.trim(),
      priority: form.value.priority,
      status: form.value.status,
      assignees: JSON.stringify(assigneeEmails),
      sprint: form.value.sprint || null,
      task_type: form.value.task_type || null,
      reviewer: form.value.reviewer || null,
      estimated_hours: form.value.estimated_hours || 0,
      due_date: form.value.due_date || null,
      description: form.value.description || null,
    })
    // Upload attachments after task is created
    if (attachedFiles.value.length && result?.name) {
      await uploadTaskAttachments(result.name)
    }
    eventBus.emit(EVENTS.TASK_CREATED, result)
    emit('created', result)
  } catch (e) {
    console.error('Failed to create task:', e)
    const msg = e?.messages ? JSON.parse(e.messages)?.[0] : (e?.message || 'Failed to create task')
    alert(typeof msg === 'string' ? msg : 'Failed to create task. Please try again.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--color-danger);
}

.form-input {
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

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

/* Assignee Picker */
.assignee-picker {
  position: relative;
}

.selected-assignees {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.assignee-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px 4px 4px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 20px;
  font-size: 12px;
  color: #1e40af;
}

.assignee-chip-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.assignee-chip-name {
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assignee-chip-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  display: flex;
  align-items: center;
}

.assignee-chip-remove:hover {
  color: var(--color-danger);
}

.assignee-search-wrap {
  position: relative;
}

.assignee-search {
  width: 100%;
}

.user-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 200px;
  overflow-y: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 50;
  margin-top: 4px;
}

.user-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.1s;
}

.user-option:hover {
  background: var(--bg-surface-active);
}

.user-option.selected {
  background: #EFF6FF;
}

.user-option-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-option-info {
  flex: 1;
  min-width: 0;
}

.user-option-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.user-option-email {
  display: block;
  font-size: 11px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-option-check {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.user-option-empty {
  padding: 16px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* Description Textarea */
.form-textarea {
  resize: vertical;
  min-height: 80px;
  line-height: 1.5;
  font-family: inherit;
}

/* File Upload */
.file-input-hidden {
  display: none;
}

.file-upload-area {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  border: 2px dashed var(--border-default);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.file-upload-area:hover {
  border-color: var(--color-primary);
  background: rgba(37, 99, 235, 0.03);
}

.file-upload-area.has-files {
  padding: 8px;
  border-style: solid;
  border-width: 1px;
}

.file-upload-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.attached-files {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.attached-file {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-surface-active);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
}

.attached-file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-weight: 500;
}

.attached-file-size {
  flex-shrink: 0;
  color: var(--text-tertiary);
  font-size: 11px;
}

.attached-file-remove {
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.attached-file-remove:hover {
  color: var(--color-danger);
}
</style>
