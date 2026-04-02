<template>
  <CreateModal
    :show="show"
    :title="config ? 'Edit Report Config' : 'New Report Config'"
    :submitLabel="saving ? 'Saving...' : 'Save Config'"
    :saving="saving"
    @close="$emit('close')"
    @submit="handleSave"
  >
    <div class="config-form">
      <div class="form-group">
        <label class="form-label">Report Name</label>
        <input
          v-model="form.report_name"
          type="text"
          class="form-input"
          placeholder="e.g. Weekly Client Update"
        />
      </div>

      <div class="form-group">
        <label class="form-label">Select Projects</label>
        <div v-if="loadingProjects" class="projects-loading">Loading projects...</div>
        <div v-else class="projects-list">
          <label
            v-for="proj in allProjects"
            :key="proj.name"
            class="project-check"
            :class="{ checked: form.projects.includes(proj.name) }"
          >
            <input
              type="checkbox"
              :value="proj.name"
              v-model="form.projects"
              class="check-input"
            />
            <span class="check-label">{{ proj.project_name }}</span>
            <span class="check-status" :class="(proj.status || '').toLowerCase().replace(/\s/g, '-')">{{ proj.status }}</span>
          </label>
          <div v-if="!allProjects.length" class="no-projects">No projects found.</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Recipients</label>
        <textarea
          v-model="form.recipients"
          class="form-input form-textarea"
          placeholder="Enter email addresses, separated by commas"
          rows="3"
        ></textarea>
        <p class="form-hint">Comma-separated email addresses</p>
      </div>

      <div class="form-group">
        <label class="auto-send-toggle">
          <input type="checkbox" v-model="form.auto_send" class="toggle-input" />
          <span class="toggle-label">Auto-send daily (Mon–Sat, 8 AM)</span>
        </label>
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
  config: { type: Object, default: null },
})

const emit = defineEmits(['close', 'saved'])

const allProjects = ref([])
const loadingProjects = ref(false)
const saving = ref(false)

const form = ref({
  report_name: '',
  projects: [],
  recipients: '',
  auto_send: false,
})

watch(() => props.show, async (val) => {
  if (val) {
    if (props.config) {
      form.value = {
        report_name: props.config.report_name || '',
        projects: (props.config.projects || []).map(p => p.project),
        recipients: props.config.recipients || '',
        auto_send: !!props.config.auto_send,
      }
    } else {
      form.value = { report_name: '', projects: [], recipients: '', auto_send: false }
    }
    await loadProjects()
  }
})

async function loadProjects() {
  loadingProjects.value = true
  try {
    allProjects.value = await call('next_pms.api.dashboard.get_all_projects_summary')
  } catch (e) {
    console.error('Failed to load projects:', e)
    allProjects.value = []
  } finally {
    loadingProjects.value = false
  }
}

async function handleSave() {
  if (!form.value.report_name.trim()) {
    alert('Please enter a report name.')
    return
  }
  if (!form.value.projects.length) {
    alert('Please select at least one project.')
    return
  }
  if (!form.value.recipients.trim()) {
    alert('Please enter at least one recipient email.')
    return
  }

  saving.value = true
  try {
    await call('next_pms.api.project_report.save_report_config', {
      report_name: form.value.report_name,
      projects: JSON.stringify(form.value.projects),
      recipients: form.value.recipients,
      auto_send: form.value.auto_send,
      config_name: props.config?.name || null,
    })
    emit('saved')
  } catch (e) {
    console.error('Failed to save config:', e)
    alert('Failed to save configuration.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.form-input {
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s;
}

.form-input:focus {
  border-color: var(--color-primary, #2563eb);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.form-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin: 0;
}

.projects-loading {
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 12px 0;
}

.projects-list {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.project-check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.1s;
  border-bottom: 1px solid var(--border-light, #f3f4f6);
}

.project-check:last-child {
  border-bottom: none;
}

.project-check:hover {
  background: var(--bg-surface-hover, #f9fafb);
}

.project-check.checked {
  background: var(--color-primary-bg, #eff6ff);
}

.check-input {
  accent-color: var(--color-primary, #2563eb);
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.check-label {
  font-size: 13px;
  color: var(--text-primary);
  flex: 1;
}

.check-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  background: #f3f4f6;
  color: #6b7280;
}

.check-status.active {
  background: #ecfdf5;
  color: #059669;
}

.check-status.planning {
  background: #eff6ff;
  color: #2563eb;
}

.check-status.on-hold {
  background: #fffbeb;
  color: #d97706;
}

.check-status.completed {
  background: #ecfdf5;
  color: #047857;
}

.no-projects {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
}

.auto-send-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 10px 0;
}

.toggle-input {
  accent-color: var(--color-primary, #2563eb);
  width: 16px;
  height: 16px;
}

.toggle-label {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}
</style>
