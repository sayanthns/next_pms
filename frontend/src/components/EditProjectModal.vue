<template>
  <CreateModal
    :show="show"
    title="Edit Project"
    submitLabel="Save Changes"
    :saving="saving"
    @close="$emit('close')"
    @submit="handleSubmit"
  >
    <form @submit.prevent="handleSubmit" class="form-fields">
      <div class="form-group">
        <label class="form-label">Project Name <span class="required">*</span></label>
        <input
          v-model="form.project_name"
          type="text"
          class="form-input"
          placeholder="Enter project name"
          required
          ref="nameInput"
        />
      </div>

      <div class="form-group">
        <label class="form-label">Client</label>
        <select v-model="form.client" class="form-input">
          <option value="" disabled>Select a client</option>
          <option
            v-for="c in customers"
            :key="c.name"
            :value="c.name"
          >
            {{ c.customer_name || c.name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Sales Order</label>
        <select v-model="form.sales_order" class="form-input">
          <option value="">— None —</option>
          <option v-for="so in salesOrders" :key="so.name" :value="so.name">
            {{ so.name }} — {{ so.customer }} ({{ so.grand_total }})
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Department</label>
        <select v-model="form.department" class="form-input">
          <option value="">No Department</option>
          <option v-for="d in departments" :key="d.name" :value="d.name">
            {{ d.department_name || d.name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Status</label>
        <select v-model="form.status" class="form-input">
          <option value="Planning">Planning</option>
          <option value="Active">Active</option>
          <option value="On Hold">On Hold</option>
          <option value="Completed">Completed</option>
        </select>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Start Date</label>
          <input v-model="form.start_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">End Date</label>
          <input v-model="form.end_date" type="date" class="form-input" />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Total Budget</label>
        <input
          v-model.number="form.total_budget"
          type="number"
          class="form-input"
          placeholder="0.00"
          min="0"
          step="0.01"
        />
      </div>

      <div class="form-group">
        <label class="form-label">Description</label>
        <textarea
          v-model="form.description"
          class="form-input form-textarea"
          placeholder="Brief project description..."
          rows="3"
        ></textarea>
      </div>

      <!-- Daily Report Settings -->
      <div class="report-toggle-group">
        <label class="portal-toggle-row">
          <input
            type="checkbox"
            v-model="form.auto_send_report"
            class="portal-checkbox"
          />
          <div class="portal-toggle-info">
            <span class="portal-toggle-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              Auto-Send Daily Report
            </span>
            <span class="portal-toggle-desc">Email a daily task status update to the recipients below (Mon-Sat, 8 AM)</span>
          </div>
        </label>
      </div>

      <div v-if="form.auto_send_report" class="form-group">
        <label class="form-label">Report Recipients</label>
        <textarea
          v-model="form.report_recipients"
          class="form-input form-textarea"
          placeholder="client@example.com, manager@example.com"
          rows="2"
        ></textarea>
        <p class="report-hint">Comma-separated email addresses</p>
      </div>

    </form>
  </CreateModal>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { call } from '@/utils/frappe'
import CreateModal from './CreateModal.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  project: { type: Object, default: null },
})

const emit = defineEmits(['close', 'updated'])

const nameInput = ref(null)
const saving = ref(false)
const customers = ref([])
const departments = ref([])
const salesOrders = ref([])
const form = ref(getDefaultForm())

function getDefaultForm() {
  return {
    project_name: '',
    client: '',
    department: '',
    status: 'Planning',
    start_date: '',
    end_date: '',
    total_budget: 0,
    description: '',
    sales_order: '',
    client_portal_enabled: false,
    auto_send_report: false,
    report_recipients: '',
  }
}

async function loadSalesOrders() {
  try {
    const rows = await call('frappe.client.get_list', {
      doctype: 'Sales Order',
      filters: { docstatus: 1 },
      fields: ['name', 'grand_total', 'customer'],
      limit_page_length: 0,
      order_by: 'creation desc',
    })
    salesOrders.value = Array.isArray(rows) ? rows : (rows?.message || [])
  } catch (e) {
    console.error('Failed to load sales orders:', e)
    salesOrders.value = []
  }
}

async function loadCustomers() {
  try {
    const result = await call('next_pms.api.crud.get_customers')
    customers.value = result || []
  } catch (e) {
    console.error('Failed to load customers:', e)
    customers.value = []
  }
}

async function loadDepartments() {
  try {
    const result = await call('next_pms.api.crud.get_departments')
    departments.value = result || []
  } catch (e) {
    console.error('Failed to load departments:', e)
    departments.value = []
  }
}

watch(() => props.show, (val) => {
  if (val && props.project) {
    form.value = {
      project_name: props.project.project_name || '',
      client: props.project.client || '',
      department: props.project.department || '',
      status: props.project.status || 'Planning',
      start_date: props.project.start_date || '',
      end_date: props.project.end_date || '',
      total_budget: props.project.total_budget || 0,
      description: props.project.description || '',
      sales_order: props.project.sales_order || '',
      client_portal_enabled: !!props.project.client_portal_enabled,
      auto_send_report: !!props.project.auto_send_report,
      report_recipients: props.project.report_recipients || '',
    }
    if (!customers.value.length) {
      loadCustomers()
    }
    if (!departments.value.length) {
      loadDepartments()
    }
    if (!salesOrders.value.length) {
      loadSalesOrders()
    }
    nextTick(() => nameInput.value?.focus())
  }
})

async function handleSubmit() {
  if (!form.value.project_name.trim()) return
  saving.value = true
  try {
    const result = await call('next_pms.api.crud.update_project', {
      project: props.project.name,
      fields: JSON.stringify({
        project_name: form.value.project_name.trim(),
        client: form.value.client || null,
        department: form.value.department || null,
        status: form.value.status,
        start_date: form.value.start_date || null,
        end_date: form.value.end_date || null,
        total_budget: form.value.total_budget || 0,
        description: form.value.description || '',
        sales_order: form.value.sales_order || null,
        client_portal_enabled: form.value.client_portal_enabled ? 1 : 0,
        auto_send_report: form.value.auto_send_report ? 1 : 0,
        report_recipients: form.value.report_recipients || '',
      }),
    })
    emit('updated', result)
  } catch (e) {
    console.error('Failed to update project:', e)
    alert('Failed to update project. Please try again.')
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

.form-textarea {
  resize: vertical;
  min-height: 72px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.report-toggle-group {
  padding-top: 8px;
  border-top: 1px solid var(--border-default, #e5e7eb);
}

.report-hint {
  font-size: 11px;
  color: var(--text-tertiary, #94a3b8);
  margin: 0;
}

.portal-toggle-group {
  padding-top: 8px;
  border-top: 1px solid var(--border-default, #e5e7eb);
}

.portal-toggle-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
}

.portal-checkbox {
  width: 36px;
  height: 20px;
  appearance: none;
  -webkit-appearance: none;
  background: #e2e8f0;
  border-radius: 10px;
  position: relative;
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
  margin-top: 2px;
}

.portal-checkbox:checked {
  background: #2563eb;
}

.portal-checkbox::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}

.portal-checkbox:checked::after {
  transform: translateX(16px);
}

.portal-toggle-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.portal-toggle-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  display: flex;
  align-items: center;
  gap: 6px;
}

.portal-toggle-desc {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  line-height: 1.4;
}
</style>
