<template>
  <CreateModal
    :show="show"
    title="Send Status Report"
    :submitLabel="sending ? 'Sending...' : 'Send Report'"
    :saving="sending"
    @close="$emit('close')"
    @submit="handleSend"
  >
    <div class="report-form">
      <div class="form-group">
        <label class="form-label">Report Date</label>
        <input v-model="reportDate" type="date" class="form-input" />
      </div>

      <div class="form-group">
        <label class="form-label">Recipients</label>
        <textarea
          v-model="recipients"
          class="form-input form-textarea"
          placeholder="Enter email addresses, separated by commas"
          rows="3"
        ></textarea>
        <p class="form-hint">Comma-separated email addresses</p>
      </div>

      <!-- Preview Section -->
      <div v-if="previewData" class="report-preview">
        <div class="preview-header">Preview</div>
        <div class="preview-stats">
          <div class="preview-stat">
            <span class="stat-value stat-done">{{ previewData.tasks_done_count }}</span>
            <span class="stat-label">Completed</span>
          </div>
          <div class="preview-stat">
            <span class="stat-value stat-progress">{{ previewData.tasks_in_progress_count }}</span>
            <span class="stat-label">In Progress</span>
          </div>
          <div class="preview-stat">
            <span class="stat-value stat-new">{{ previewData.tasks_new_count }}</span>
            <span class="stat-label">New</span>
          </div>
        </div>

        <div v-if="previewData.tasks_done.length" class="preview-section">
          <div class="preview-section-title done">Completed Today</div>
          <div v-for="t in previewData.tasks_done" :key="t.name" class="preview-task">
            {{ t.task_title }}
            <span class="task-assignee">{{ t.assignee_name || '' }}</span>
          </div>
        </div>

        <div v-if="previewData.tasks_in_progress.length" class="preview-section">
          <div class="preview-section-title progress">In Progress</div>
          <div v-for="t in previewData.tasks_in_progress" :key="t.name" class="preview-task">
            {{ t.task_title }}
            <span class="task-status-badge" :class="t.status === 'In Review' ? 'review' : ''">{{ t.status }}</span>
          </div>
        </div>

        <div v-if="previewData.tasks_new.length" class="preview-section">
          <div class="preview-section-title new">New Tasks</div>
          <div v-for="t in previewData.tasks_new" :key="t.name" class="preview-task">
            {{ t.task_title }}
            <span class="task-priority" :class="(t.priority || 'normal').toLowerCase()">{{ t.priority || 'Normal' }}</span>
          </div>
        </div>

        <div v-if="!previewData.tasks_done.length && !previewData.tasks_in_progress.length && !previewData.tasks_new.length" class="preview-empty">
          No task activity for this date.
        </div>

        <div class="preview-progress">
          <div class="progress-bar-wrap">
            <div class="progress-bar-fill" :style="{ width: previewData.progress_pct + '%' }"></div>
          </div>
          <div class="progress-text">{{ previewData.done_tasks }} of {{ previewData.total_tasks }} tasks complete ({{ previewData.progress_pct }}%)</div>
        </div>
      </div>

      <button
        v-if="!previewData && !loadingPreview"
        class="btn-preview"
        @click="loadPreview"
        :disabled="loadingPreview"
      >
        Load Preview
      </button>
      <div v-if="loadingPreview" class="loading-preview">Loading preview...</div>

      <div v-if="sendResult" class="send-result" :class="sendResult.success ? 'success' : 'error'">
        {{ sendResult.message }}
      </div>
    </div>
  </CreateModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { call } from '@/utils/frappe'
import CreateModal from './CreateModal.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  project: { type: Object, default: null },
})

const emit = defineEmits(['close'])

const reportDate = ref('')
const recipients = ref('')
const previewData = ref(null)
const loadingPreview = ref(false)
const sending = ref(false)
const sendResult = ref(null)

function getYesterday() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

watch(() => props.show, async (val) => {
  if (val && props.project) {
    reportDate.value = getYesterday()
    previewData.value = null
    sendResult.value = null
    sending.value = false

    // Load suggested recipients
    try {
      const suggestions = await call('next_pms.api.project_report.get_project_report_recipients', {
        project: props.project.name,
      })
      recipients.value = (suggestions || []).join(', ')
    } catch (e) {
      recipients.value = ''
    }

    // Auto-load preview
    loadPreview()
  }
})

watch(reportDate, () => {
  previewData.value = null
  loadPreview()
})

async function loadPreview() {
  if (!props.project || !reportDate.value) return
  loadingPreview.value = true
  try {
    const data = await call('next_pms.api.project_report.get_project_report_data', {
      project: props.project.name,
      date: reportDate.value,
    })
    previewData.value = data
  } catch (e) {
    console.error('Failed to load preview:', e)
  } finally {
    loadingPreview.value = false
  }
}

async function handleSend() {
  if (!recipients.value.trim()) {
    sendResult.value = { success: false, message: 'Please enter at least one recipient email.' }
    return
  }

  sending.value = true
  sendResult.value = null
  try {
    const result = await call('next_pms.api.project_report.send_project_report', {
      project: props.project.name,
      recipients: recipients.value,
      date: reportDate.value,
    })
    sendResult.value = result
  } catch (e) {
    sendResult.value = { success: false, message: e.message || 'Failed to send report.' }
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.report-form {
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

.form-input {
  padding: 9px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  font-family: inherit;
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.form-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin: 0;
}

/* Preview */
.report-preview {
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
}

.preview-header {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  padding: 10px 16px;
  background: var(--bg-surface-active, #f9fafb);
  border-bottom: 1px solid var(--border-default);
}

.preview-stats {
  display: flex;
  border-bottom: 1px solid var(--border-default);
}

.preview-stat {
  flex: 1;
  text-align: center;
  padding: 12px 8px;
  border-right: 1px solid var(--border-default);
}

.preview-stat:last-child {
  border-right: none;
}

.stat-value {
  display: block;
  font-size: 22px;
  font-weight: 800;
}

.stat-done { color: #059669; }
.stat-progress { color: #2563eb; }
.stat-new { color: #7c3aed; }

.stat-label {
  font-size: 10px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.preview-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light, #f3f4f6);
}

.preview-section-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.preview-section-title.done { color: #059669; }
.preview-section-title.progress { color: #2563eb; }
.preview-section-title.new { color: #7c3aed; }

.preview-task {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-primary);
  padding: 4px 0;
}

.task-assignee {
  font-size: 11px;
  color: var(--text-tertiary);
}

.task-status-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: #dbeafe;
  color: #2563eb;
}

.task-status-badge.review {
  background: #ede9fe;
  color: #7c3aed;
}

.task-priority {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.task-priority.urgent { background: #fee2e2; color: #dc2626; }
.task-priority.high { background: #fef3c7; color: #d97706; }
.task-priority.medium, .task-priority.normal { background: #dbeafe; color: #2563eb; }
.task-priority.low { background: #f3f4f6; color: #6b7280; }

.preview-empty {
  padding: 20px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
}

.preview-progress {
  padding: 12px 16px;
}

.progress-bar-wrap {
  height: 6px;
  background: var(--border-default);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-preview {
  padding: 8px 16px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: center;
}

.btn-preview:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
}

.loading-preview {
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
  padding: 12px 0;
}

.send-result {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.send-result.success {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.send-result.error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}
</style>
