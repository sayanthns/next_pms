<template>
  <div class="portal-project">
    <!-- Back button -->
    <button class="back-btn" @click="$router.push('/portal')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      Back to Dashboard
    </button>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Loading project...</span>
    </div>

    <template v-else-if="project">
      <!-- Project Header -->
      <div class="project-header">
        <div class="project-header-left">
          <h1>{{ project.project_name }}</h1>
          <span class="project-status" :class="statusClass(project.status)">{{ project.status }}</span>
        </div>
        <div class="project-header-right">
          <div class="header-stat">
            <span class="header-stat-value">{{ project.progress }}%</span>
            <span class="header-stat-label">Complete</span>
          </div>
          <div class="header-stat">
            <span class="header-stat-value">{{ project.completed_tasks }}/{{ project.total_tasks }}</span>
            <span class="header-stat-label">Tasks Done</span>
          </div>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="progress-bar-wrap">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: project.progress + '%' }"></div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span v-if="tab.count !== undefined" class="tab-count">{{ tab.count }}</span>
        </button>
      </div>

      <!-- Milestones Tab -->
      <div v-if="activeTab === 'milestones'" class="tab-content">
        <div v-if="milestones.length === 0" class="empty-tab">No milestones yet.</div>
        <div v-else class="milestones-list">
          <div v-for="m in milestones" :key="m.name" class="milestone-card">
            <div class="milestone-header">
              <h3>{{ m.sprint_name }}</h3>
              <div class="milestone-badges">
                <span class="m-status" :class="'ms-' + m.status?.toLowerCase()">{{ m.status }}</span>
                <span v-if="m.approval_status" class="m-approval" :class="'ma-' + approvalKey(m.approval_status)">
                  {{ m.approval_status }}
                </span>
              </div>
            </div>
            <p v-if="m.goal" class="milestone-goal">{{ m.goal }}</p>
            <div class="milestone-progress">
              <div class="progress-bar small">
                <div class="progress-fill" :style="{ width: milestoneProgress(m) + '%' }"></div>
              </div>
              <span class="milestone-tasks">{{ m.completed_tasks || 0 }}/{{ m.total_tasks || 0 }} tasks</span>
            </div>
            <div class="milestone-dates">
              <span v-if="m.start_date">{{ formatDate(m.start_date) }}</span>
              <span v-if="m.start_date && m.end_date"> - </span>
              <span v-if="m.end_date">{{ formatDate(m.end_date) }}</span>
            </div>

            <!-- Approval actions (only if Ready for Review) -->
            <div v-if="m.approval_status === 'Ready for Review'" class="milestone-actions">
              <button class="btn-approve" @click="approveMilestone(m)" :disabled="approving">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                Approve
              </button>
              <button class="btn-changes" @click="showChangesDialog(m)" :disabled="approving">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Request Changes
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Tasks Tab -->
      <div v-if="activeTab === 'tasks'" class="tab-content">
        <div class="tasks-filter">
          <select v-model="taskFilter" class="filter-select">
            <option value="">All Tasks</option>
            <option value="To Do">To Do</option>
            <option value="In Progress">In Progress</option>
            <option value="In Review">In Review</option>
            <option value="Done">Done</option>
          </select>
        </div>
        <div v-if="filteredTasks.length === 0" class="empty-tab">No tasks found.</div>
        <div v-else class="tasks-list">
          <div
            v-for="t in filteredTasks"
            :key="t.name"
            class="task-row"
            @click="openTask(t)"
          >
            <div class="task-info">
              <span class="task-name">{{ t.task_title }}</span>
              <span class="task-meta">
                <span class="task-id">{{ t.name }}</span>
                <span v-if="t.sprint" class="task-sprint">{{ sprintNameMap[t.sprint] || t.sprint }}</span>
              </span>
            </div>
            <div class="task-right">
              <span class="task-priority" :class="'tp-' + t.priority?.toLowerCase()">{{ t.priority }}</span>
              <span class="task-status-badge" :class="'ts-' + taskStatusKey(t.status)">{{ t.status }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Team Tab -->
      <div v-if="activeTab === 'team'" class="tab-content">
        <div v-if="team.length === 0" class="empty-tab">No team members.</div>
        <div v-else class="team-grid">
          <div v-for="m in team" :key="m.user" class="team-member-card">
            <div class="team-avatar">{{ initials(m.full_name) }}</div>
            <span class="team-name">{{ m.full_name }}</span>
          </div>
        </div>
      </div>

      <!-- Files Tab -->
      <div v-if="activeTab === 'files'" class="tab-content">
        <div v-if="files.length === 0 && links.length === 0" class="empty-tab">No files or links shared.</div>
        <div v-else>
          <div v-if="files.length" class="files-list">
            <h4>Files</h4>
            <a v-for="f in files" :key="f.name" :href="f.file_url" target="_blank" class="file-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span>{{ f.file_name }}</span>
            </a>
          </div>
          <div v-if="links.length" class="files-list" style="margin-top: 16px;">
            <h4>Links</h4>
            <a v-for="l in links" :key="l.name" :href="l.url" target="_blank" class="file-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
              <span>{{ l.title || l.url }}</span>
            </a>
          </div>
        </div>
      </div>
    </template>

    <!-- Changes Dialog -->
    <div v-if="changesDialog" class="dialog-overlay" @click.self="changesDialog = false">
      <div class="dialog-box">
        <h3>Request Changes</h3>
        <p>Describe the changes needed for <b>{{ changesTarget?.sprint_name }}</b>:</p>
        <textarea v-model="changesComment" rows="4" placeholder="Describe what needs to be changed..." class="dialog-textarea"></textarea>
        <div class="dialog-actions">
          <button class="btn-cancel" @click="changesDialog = false">Cancel</button>
          <button class="btn-submit" @click="submitChanges" :disabled="!changesComment.trim() || approving">
            Submit
          </button>
        </div>
      </div>
    </div>

    <!-- Task Detail Drawer -->
    <div v-if="selectedTask" class="drawer-overlay" @click.self="selectedTask = null">
      <div class="drawer">
        <div class="drawer-header">
          <h3>{{ taskDetail?.task?.task_title || 'Loading...' }}</h3>
          <button class="drawer-close" @click="selectedTask = null">&times;</button>
        </div>
        <div v-if="taskLoading" class="loading-state small"><div class="spinner"></div></div>
        <div v-else-if="taskDetail" class="drawer-body">
          <div class="drawer-meta">
            <span class="task-status-badge" :class="'ts-' + taskStatusKey(taskDetail.task.status)">{{ taskDetail.task.status }}</span>
            <span class="task-priority" :class="'tp-' + taskDetail.task.priority?.toLowerCase()">{{ taskDetail.task.priority }}</span>
            <span v-if="taskDetail.task.task_type" class="task-type-badge">{{ taskDetail.task.task_type }}</span>
          </div>
          <div v-if="taskDetail.task.description" class="drawer-section">
            <h4>Description</h4>
            <div class="description-content" v-html="taskDetail.task.description"></div>
          </div>
          <div v-if="taskDetail.assignees?.length" class="drawer-section">
            <h4>Assigned To</h4>
            <div class="assignee-list">
              <span v-for="a in taskDetail.assignees" :key="a.user" class="assignee-chip">{{ a.full_name }}</span>
            </div>
          </div>
          <div v-if="taskDetail.task.due_date" class="drawer-section">
            <h4>Due Date</h4>
            <span>{{ formatDate(taskDetail.task.due_date) }}</span>
          </div>

          <!-- Comments -->
          <div class="drawer-section">
            <h4>Comments ({{ taskDetail.comments?.length || 0 }})</h4>
            <div v-if="taskDetail.comments?.length" class="comments-list">
              <div v-for="c in taskDetail.comments" :key="c.name" class="comment-item">
                <div class="comment-author">{{ c.author_name }}</div>
                <div class="comment-text">{{ c.content }}</div>
                <div class="comment-time">{{ formatDateTime(c.creation) }}</div>
              </div>
            </div>
            <div class="comment-form">
              <textarea v-model="newComment" rows="2" placeholder="Add a comment..." class="comment-input"></textarea>
              <button class="btn-comment" @click="postComment" :disabled="!newComment.trim() || posting">
                {{ posting ? 'Posting...' : 'Post Comment' }}
              </button>
            </div>
          </div>

          <!-- Files -->
          <div v-if="taskDetail.files?.length" class="drawer-section">
            <h4>Attachments</h4>
            <a v-for="f in taskDetail.files" :key="f.name" :href="f.file_url" target="_blank" class="file-item small">
              {{ f.file_name }}
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { call } from '@/utils/frappe'

const route = useRoute()
const projectId = computed(() => route.params.id)

const loading = ref(true)
const project = ref(null)
const milestones = ref([])
const tasks = ref([])
const team = ref([])
const files = ref([])
const links = ref([])
const activeTab = ref('milestones')
const taskFilter = ref('')
const approving = ref(false)

// Task drawer
const selectedTask = ref(null)
const taskDetail = ref(null)
const taskLoading = ref(false)
const newComment = ref('')
const posting = ref(false)

// Changes dialog
const changesDialog = ref(false)
const changesTarget = ref(null)
const changesComment = ref('')

const sprintNameMap = computed(() => {
  const map = {}
  for (const m of milestones.value) {
    map[m.name] = m.sprint_name
  }
  return map
})

const tabs = computed(() => [
  { key: 'milestones', label: 'Milestones', count: milestones.value.length },
  { key: 'tasks', label: 'Tasks', count: tasks.value.length },
  { key: 'team', label: 'Team', count: team.value.length },
  { key: 'files', label: 'Files', count: files.value.length + links.value.length },
])

const filteredTasks = computed(() => {
  if (!taskFilter.value) return tasks.value
  return tasks.value.filter(t => t.status === taskFilter.value)
})

onMounted(() => loadProject())

watch(projectId, () => loadProject())

async function loadProject() {
  loading.value = true
  try {
    const res = await call('next_pms.api.portal.get_portal_project_detail', { project: projectId.value })
    if (res) {
      project.value = res.project
      milestones.value = res.milestones || []
      tasks.value = res.tasks || []
      team.value = res.team || []
      files.value = res.files || []
      links.value = res.links || []
    }
  } catch (e) {
    console.error('Failed to load portal project:', e)
  } finally {
    loading.value = false
  }
}

async function openTask(t) {
  selectedTask.value = t.name
  taskLoading.value = true
  taskDetail.value = null
  try {
    taskDetail.value = await call('next_pms.api.portal.get_portal_task_detail', { task: t.name })
  } catch (e) {
    console.error('Failed to load task:', e)
  } finally {
    taskLoading.value = false
  }
}

async function postComment() {
  if (!newComment.value.trim() || posting.value) return
  posting.value = true
  try {
    const res = await call('next_pms.api.portal.add_portal_comment', {
      task: selectedTask.value,
      content: newComment.value.trim(),
    })
    if (res) {
      if (!taskDetail.value.comments) taskDetail.value.comments = []
      taskDetail.value.comments.push(res)
      newComment.value = ''
    }
  } catch (e) {
    console.error('Failed to post comment:', e)
  } finally {
    posting.value = false
  }
}

async function approveMilestone(m) {
  approving.value = true
  try {
    await call('next_pms.api.portal.approve_milestone', { sprint: m.name })
    m.approval_status = 'Approved'
  } catch (e) {
    console.error('Approval failed:', e)
  } finally {
    approving.value = false
  }
}

function showChangesDialog(m) {
  changesTarget.value = m
  changesComment.value = ''
  changesDialog.value = true
}

async function submitChanges() {
  if (!changesComment.value.trim() || approving.value) return
  approving.value = true
  try {
    await call('next_pms.api.portal.request_milestone_changes', {
      sprint: changesTarget.value.name,
      comment: changesComment.value.trim(),
    })
    changesTarget.value.approval_status = 'Changes Requested'
    changesDialog.value = false
  } catch (e) {
    console.error('Request changes failed:', e)
  } finally {
    approving.value = false
  }
}

function statusClass(status) {
  const map = { 'Active': 'status-active', 'Completed': 'status-completed', 'On Hold': 'status-hold' }
  return map[status] || 'status-default'
}

function approvalKey(s) {
  return s?.toLowerCase().replace(/\s+/g, '-') || ''
}

function taskStatusKey(s) {
  return s?.toLowerCase().replace(/\s+/g, '-') || ''
}

function milestoneProgress(m) {
  if (!m.total_tasks) return 0
  return Math.round((m.completed_tasks / m.total_tasks) * 100)
}

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
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
.portal-project { max-width: 100%; }

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 8px 0;
  margin-bottom: 16px;
}
.back-btn:hover { color: #2563eb; }

/* Header */
.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}
.project-header h1 { font-size: 22px; font-weight: 700; color: #1e293b; margin: 0; }
.project-header-right { display: flex; gap: 24px; }
.header-stat { display: flex; flex-direction: column; align-items: center; }
.header-stat-value { font-size: 20px; font-weight: 700; color: #1e293b; }
.header-stat-label { font-size: 11px; color: #94a3b8; }

.project-status { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px; margin-left: 8px; }
.status-active { background: #dcfce7; color: #16a34a; }
.status-completed { background: #eff6ff; color: #2563eb; }
.status-hold { background: #fef9c3; color: #ca8a04; }
.status-default { background: #f1f5f9; color: #64748b; }

.progress-bar-wrap { margin-bottom: 20px; }
.progress-bar { height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; }
.progress-bar.small { height: 4px; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #2563eb, #3b82f6); border-radius: 3px; transition: width 0.5s; }

/* Tabs */
.tab-bar { display: flex; gap: 4px; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px; }
.tab-btn {
  background: none; border: none; padding: 10px 16px; font-size: 13px; font-weight: 500;
  color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s;
  display: flex; align-items: center; gap: 6px;
}
.tab-btn:hover { color: #334155; }
.tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; }
.tab-count { font-size: 11px; background: #f1f5f9; padding: 1px 6px; border-radius: 10px; }
.tab-btn.active .tab-count { background: #eff6ff; color: #2563eb; }

.empty-tab { text-align: center; padding: 40px; color: #94a3b8; font-size: 14px; }

/* Milestones */
.milestones-list { display: flex; flex-direction: column; gap: 12px; }
.milestone-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; }
.milestone-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px; }
.milestone-header h3 { font-size: 15px; font-weight: 600; color: #1e293b; margin: 0; }
.milestone-badges { display: flex; gap: 6px; flex-shrink: 0; }
.m-status, .m-approval { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 6px; }
.ms-planned { background: #f1f5f9; color: #64748b; }
.ms-active { background: #dcfce7; color: #16a34a; }
.ms-completed { background: #eff6ff; color: #2563eb; }
.ma-pending { background: #f1f5f9; color: #64748b; }
.ma-ready-for-review { background: #fffbeb; color: #d97706; }
.ma-approved { background: #dcfce7; color: #16a34a; }
.ma-changes-requested { background: #fef2f2; color: #dc2626; }

.milestone-goal { font-size: 13px; color: #64748b; margin: 0 0 8px; }
.milestone-progress { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.milestone-progress .progress-bar { flex: 1; }
.milestone-tasks { font-size: 11px; color: #94a3b8; white-space: nowrap; }
.milestone-dates { font-size: 11px; color: #94a3b8; }

.milestone-actions { display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #f1f5f9; }
.btn-approve, .btn-changes {
  display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; border: none;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s;
}
.btn-approve { background: #16a34a; color: #fff; }
.btn-approve:hover { background: #15803d; }
.btn-changes { background: #f1f5f9; color: #64748b; }
.btn-changes:hover { background: #e2e8f0; color: #334155; }

/* Tasks */
.tasks-filter { margin-bottom: 12px; }
.filter-select { padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; background: #fff; }
.tasks-list { display: flex; flex-direction: column; gap: 4px; }
.task-row {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 12px 16px; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
  cursor: pointer; transition: all 0.15s;
}
.task-row:hover { border-color: #2563eb; background: #fafbff; }
.task-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.task-name { font-size: 14px; font-weight: 500; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-meta { display: flex; gap: 8px; font-size: 11px; color: #94a3b8; }
.task-id { font-family: monospace; }
.task-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.task-priority, .task-status-badge { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 6px; }
.tp-critical { background: #fef2f2; color: #dc2626; }
.tp-high { background: #fff7ed; color: #ea580c; }
.tp-medium { background: #fffbeb; color: #d97706; }
.tp-low { background: #f0fdf4; color: #16a34a; }
.ts-to-do { background: #f1f5f9; color: #64748b; }
.ts-in-progress { background: #eff6ff; color: #2563eb; }
.ts-in-review { background: #faf5ff; color: #9333ea; }
.ts-done { background: #dcfce7; color: #16a34a; }
.ts-backlog { background: #f8fafc; color: #94a3b8; }

.task-type-badge { font-size: 11px; background: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 6px; }

/* Team */
.team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.team-member-card {
  display: flex; align-items: center; gap: 10px; padding: 12px; background: #fff;
  border: 1px solid #e5e7eb; border-radius: 10px;
}
.team-avatar {
  width: 36px; height: 36px; border-radius: 50%; background: #e0e7ff; color: #4338ca;
  font-size: 13px; font-weight: 600; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.team-name { font-size: 13px; font-weight: 500; color: #1e293b; }

/* Files */
.files-list h4 { font-size: 13px; font-weight: 600; color: #64748b; margin: 0 0 8px; }
.file-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #fff;
  border: 1px solid #e5e7eb; border-radius: 8px; text-decoration: none; color: #334155;
  font-size: 13px; margin-bottom: 4px; transition: border-color 0.15s;
}
.file-item:hover { border-color: #2563eb; color: #2563eb; }

/* Drawer */
.drawer-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 1000;
  display: flex; justify-content: flex-end;
}
.drawer {
  width: 480px; max-width: 90vw; background: #fff; height: 100vh; overflow-y: auto;
  box-shadow: -8px 0 24px rgba(0,0,0,0.1);
}
.drawer-header {
  display: flex; justify-content: space-between; align-items: center; padding: 20px;
  border-bottom: 1px solid #e5e7eb; position: sticky; top: 0; background: #fff; z-index: 1;
}
.drawer-header h3 { font-size: 16px; font-weight: 600; color: #1e293b; margin: 0; }
.drawer-close { background: none; border: none; font-size: 24px; cursor: pointer; color: #94a3b8; padding: 4px; }
.drawer-close:hover { color: #334155; }
.drawer-body { padding: 20px; }
.drawer-meta { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.drawer-section { margin-bottom: 20px; }
.drawer-section h4 { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 8px; }
.description-content { font-size: 13px; color: #334155; line-height: 1.6; }
.assignee-list { display: flex; flex-wrap: wrap; gap: 6px; }
.assignee-chip { font-size: 12px; background: #e0e7ff; color: #4338ca; padding: 3px 10px; border-radius: 12px; }

/* Comments */
.comments-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.comment-item { background: #f8fafc; border-radius: 8px; padding: 10px; }
.comment-author { font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 2px; }
.comment-text { font-size: 13px; color: #475569; line-height: 1.5; }
.comment-time { font-size: 11px; color: #94a3b8; margin-top: 4px; }
.comment-form { display: flex; flex-direction: column; gap: 8px; }
.comment-input { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 12px; font-size: 13px; resize: vertical; font-family: inherit; }
.comment-input:focus { outline: none; border-color: #2563eb; }
.btn-comment {
  align-self: flex-end; background: #2563eb; color: #fff; border: none; padding: 6px 16px;
  border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer;
}
.btn-comment:hover { background: #1d4ed8; }
.btn-comment:disabled { opacity: 0.5; cursor: not-allowed; }

/* Dialog */
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1100;
  display: flex; align-items: center; justify-content: center;
}
.dialog-box {
  background: #fff; border-radius: 12px; padding: 24px; width: 420px; max-width: 90vw;
  box-shadow: 0 20px 40px rgba(0,0,0,0.15);
}
.dialog-box h3 { font-size: 16px; font-weight: 600; margin: 0 0 8px; color: #1e293b; }
.dialog-box p { font-size: 13px; color: #64748b; margin: 0 0 12px; }
.dialog-textarea {
  width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; font-size: 13px;
  resize: vertical; font-family: inherit; box-sizing: border-box;
}
.dialog-textarea:focus { outline: none; border-color: #2563eb; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.btn-cancel { background: #f1f5f9; color: #64748b; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-submit { background: #dc2626; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-submit:hover { background: #b91c1c; }
.btn-submit:disabled { opacity: 0.5; }

/* Loading */
.loading-state { display: flex; flex-direction: column; align-items: center; padding: 60px; color: #94a3b8; gap: 12px; }
.loading-state.small { padding: 30px; }
.spinner { width: 28px; height: 28px; border: 3px solid #e5e7eb; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .project-header { flex-direction: column; }
  .project-header-right { flex-direction: row; gap: 16px; }
  .drawer { width: 100vw; }
}
</style>
