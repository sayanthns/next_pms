<template>
  <teleport to="body">
    <transition name="modal">
      <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-panel">
          <div class="modal-header">
            <h2 class="modal-title">{{ title }}</h2>
            <button class="modal-close" @click="$emit('close')">&times;</button>
          </div>
          <div class="modal-body">
            <slot />
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="$emit('close')" :disabled="saving">
              Cancel
            </button>
            <button class="btn btn-primary" @click="$emit('submit')" :disabled="saving">
              <span v-if="saving" class="btn-spinner"></span>
              {{ saving ? 'Saving...' : submitLabel }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: 'Create' },
  submitLabel: { type: String, default: 'Create' },
  saving: { type: Boolean, default: false },
})

defineEmits(['close', 'submit'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  z-index: 2000;
}

.modal-panel {
  width: 480px;
  max-width: 100%;
  height: 100vh;
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
  animation: slide-in 0.25s ease;
}

@keyframes slide-in {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  line-height: 1;
}

.modal-close:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-default);
  flex-shrink: 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #2563EB;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #1D4ED8;
}

.btn-secondary {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--border-default);
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@media (max-width: 520px) {
  .modal-panel {
    width: 100%;
  }
}
</style>
