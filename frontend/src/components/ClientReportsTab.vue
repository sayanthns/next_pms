<template>
  <div class="client-reports-tab">
    <div class="tab-header">
      <div>
        <h3 class="tab-title">Client Report Configurations</h3>
        <p class="tab-desc">Create combined reports for multiple projects and schedule auto-send</p>
      </div>
      <button class="btn btn-primary" @click="openCreateModal">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Report Config
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner-sm"></div>
      Loading configurations...
    </div>

    <div v-else-if="!configs.length" class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
      </div>
      <p>No report configurations yet.</p>
      <p class="empty-hint">Create one to combine multiple projects into a single status report email.</p>
    </div>

    <div v-else class="configs-grid">
      <div v-for="config in configs" :key="config.name" class="config-card">
        <div class="config-header">
          <h4 class="config-name">{{ config.report_name }}</h4>
          <span v-if="config.auto_send" class="auto-badge">Auto-Send</span>
        </div>

        <div class="config-projects">
          <span class="config-label">Projects:</span>
          <div class="project-chips">
            <span v-for="p in config.projects" :key="p.project" class="project-chip">
              {{ p.project_name }}
            </span>
          </div>
        </div>

        <div class="config-recipients">
          <span class="config-label">Recipients:</span>
          <span class="config-value">{{ config.recipients }}</span>
        </div>

        <div class="config-actions">
          <button class="action-btn action-send" @click="sendNow(config)" :disabled="config.sending">
            {{ config.sending ? 'Sending...' : 'Send Now' }}
          </button>
          <button class="action-btn action-edit" @click="editConfig(config)">Edit</button>
          <button class="action-btn action-delete" @click="deleteConfig(config)">Delete</button>
        </div>

        <div v-if="config.sendResult" class="send-result" :class="config.sendResult.success ? 'success' : 'error'">
          {{ config.sendResult.message }}
        </div>
      </div>
    </div>

    <ReportConfigModal
      :show="showModal"
      :config="editingConfig"
      @close="showModal = false"
      @saved="onConfigSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from '@/utils/frappe'
import ReportConfigModal from './ReportConfigModal.vue'

const configs = ref([])
const loading = ref(true)
const showModal = ref(false)
const editingConfig = ref(null)

onMounted(() => loadConfigs())

async function loadConfigs() {
  loading.value = true
  try {
    const result = await call('next_pms.api.project_report.get_report_configs')
    configs.value = (result || []).map(c => ({ ...c, sending: false, sendResult: null }))
  } catch (e) {
    console.error('Failed to load report configs:', e)
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  editingConfig.value = null
  showModal.value = true
}

function editConfig(config) {
  editingConfig.value = config
  showModal.value = true
}

async function deleteConfig(config) {
  if (!confirm(`Delete report config "${config.report_name}"?`)) return
  try {
    await call('next_pms.api.project_report.delete_report_config', { config_name: config.name })
    configs.value = configs.value.filter(c => c.name !== config.name)
  } catch (e) {
    console.error('Failed to delete config:', e)
    alert('Failed to delete configuration.')
  }
}

async function sendNow(config) {
  config.sending = true
  config.sendResult = null
  try {
    const projects = config.projects.map(p => p.project)
    const result = await call('next_pms.api.project_report.send_multi_project_report', {
      projects: JSON.stringify(projects),
      recipients: config.recipients,
      report_name: config.report_name,
    })
    config.sendResult = result
  } catch (e) {
    config.sendResult = { success: false, message: e.message || 'Failed to send report.' }
  } finally {
    config.sending = false
  }
}

function onConfigSaved() {
  showModal.value = false
  loadConfigs()
}
</script>

<style scoped>
.client-reports-tab {
  padding: 0;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.tab-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.tab-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  background: var(--color-primary, #2563eb);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-primary-hover, #1d4ed8);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 40px 0;
  justify-content: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.spinner-sm {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--text-secondary);
}

.empty-icon {
  margin-bottom: 16px;
  color: var(--text-tertiary);
}

.empty-hint {
  font-size: 13px;
  color: var(--text-tertiary);
}

.configs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.config-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.config-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.auto-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
  background: #ecfdf5;
  color: #059669;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.config-projects,
.config-recipients {
  margin-bottom: 10px;
}

.config-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  display: block;
  margin-bottom: 4px;
}

.project-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.project-chip {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  background: var(--color-primary-bg, #eff6ff);
  color: var(--color-primary, #2563eb);
  font-weight: 500;
}

.config-value {
  font-size: 12px;
  color: var(--text-secondary);
  word-break: break-all;
}

.config-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-light, #f3f4f6);
}

.action-btn {
  padding: 6px 14px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: var(--bg-surface);
  transition: all 0.15s;
}

.action-send {
  color: #2563eb;
  border-color: #bfdbfe;
}
.action-send:hover { background: #eff6ff; border-color: #2563eb; }
.action-send:disabled { opacity: 0.5; cursor: default; }

.action-edit {
  color: var(--text-primary);
}
.action-edit:hover { background: var(--bg-surface-hover); }

.action-delete {
  color: #dc2626;
  border-color: #fecaca;
}
.action-delete:hover { background: #fef2f2; border-color: #dc2626; }

.send-result {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.send-result.success {
  background: #ecfdf5;
  color: #059669;
}

.send-result.error {
  background: #fef2f2;
  color: #dc2626;
}
</style>
