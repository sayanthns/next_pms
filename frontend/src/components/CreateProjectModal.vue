<template>
  <CreateModal
    :show="show"
    title="New Project"
    submitLabel="Create Project"
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
        <label class="form-label">Client <span class="required">*</span></label>
        <select v-model="form.client" class="form-input" required>
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
        <label class="form-label">Total Budget <span class="required">*</span></label>
        <input
          v-model.number="form.total_budget"
          type="number"
          class="form-input"
          placeholder="0.00"
          min="0.01"
          step="0.01"
          required
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
    </form>
  </CreateModal>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { call } from '@/utils/frappe'
import CreateModal from './CreateModal.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'created'])

const nameInput = ref(null)
const saving = ref(false)
const customers = ref([])
const departments = ref([])
const form = ref(getDefaultForm())

function getDefaultForm() {
  return {
    project_name: '',
    client: '',
    department: '',
    status: 'Planning',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    total_budget: 0,
    description: '',
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
  if (val) {
    form.value = getDefaultForm()
    if (!customers.value.length) {
      loadCustomers()
    }
    if (!departments.value.length) {
      loadDepartments()
    }
    nextTick(() => nameInput.value?.focus())
  }
})

async function handleSubmit() {
  if (!form.value.project_name.trim()) return
  if (!form.value.client) return
  if (!form.value.total_budget || form.value.total_budget <= 0) {
    alert('Total Budget is required and must be greater than 0')
    return
  }
  saving.value = true
  try {
    const result = await call('next_pms.api.crud.create_project', {
      project_name: form.value.project_name.trim(),
      client: form.value.client,
      status: form.value.status,
      start_date: form.value.start_date || null,
      end_date: form.value.end_date || null,
      total_budget: form.value.total_budget || 0,
      description: form.value.description || null,
      department: form.value.department || null,
    })
    emit('created', result)
  } catch (e) {
    console.error('Failed to create project:', e)
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
</style>
