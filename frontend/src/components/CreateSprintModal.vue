<template>
  <CreateModal
    :show="show"
    title="New Sprint"
    submitLabel="Create Sprint"
    :saving="saving"
    @close="$emit('close')"
    @submit="handleSubmit"
  >
    <form @submit.prevent="handleSubmit" class="form-fields">
      <div class="form-group">
        <label class="form-label">Sprint Name <span class="required">*</span></label>
        <input
          v-model="form.sprint_name"
          type="text"
          class="form-input"
          placeholder="e.g. Sprint 5"
          required
          ref="nameInput"
        />
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
        <label class="form-label">Sprint Goal</label>
        <textarea
          v-model="form.goal"
          class="form-input form-textarea"
          placeholder="What should this sprint achieve?"
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
  projectId: { type: String, required: true },
})

const emit = defineEmits(['close', 'created'])

const nameInput = ref(null)
const saving = ref(false)
const form = ref(getDefaultForm())

function getDefaultForm() {
  return {
    sprint_name: '',
    start_date: '',
    end_date: '',
    goal: '',
  }
}

watch(() => props.show, (val) => {
  if (val) {
    form.value = getDefaultForm()
    nextTick(() => nameInput.value?.focus())
  }
})

async function handleSubmit() {
  if (!form.value.sprint_name.trim()) return
  saving.value = true
  try {
    const result = await call('next_pms.api.crud.create_sprint', {
      project: props.projectId,
      sprint_name: form.value.sprint_name.trim(),
      start_date: form.value.start_date || null,
      end_date: form.value.end_date || null,
      goal: form.value.goal || null,
    })
    emit('created', result)
  } catch (e) {
    console.error('Failed to create sprint:', e)
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
