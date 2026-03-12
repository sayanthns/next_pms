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
const form = ref(getDefaultForm())

function getDefaultForm() {
  return {
    project_name: '',
    client: '',
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

watch(() => props.show, (val) => {
  if (val) {
    form.value = getDefaultForm()
    if (!customers.value.length) {
      loadCustomers()
    }
    nextTick(() => nameInput.value?.focus())
  }
})

async function handleSubmit() {
  if (!form.value.project_name.trim()) return
  if (!form.value.client) return
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
  color: #374151;
}

.required {
  color: #EF4444;
}

.form-input {
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #1a1a2e;
  background: #fff;
  transition: border-color 0.15s;
  outline: none;
  font-family: inherit;
}

.form-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
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
