<template>
  <teleport to="body">
    <transition name="confirm-fade">
      <div v-if="show" class="confirm-overlay" @click.self="$emit('cancel')">
        <div class="confirm-dialog">
          <div class="confirm-header">
            <div class="confirm-icon" :class="{ danger: confirmDanger }">
              <svg v-if="confirmDanger" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            <h3 class="confirm-title">{{ title }}</h3>
          </div>
          <p class="confirm-message">{{ message }}</p>
          <ul v-if="details && details.length" class="confirm-details">
            <li v-for="(d, i) in details" :key="i">{{ d }}</li>
          </ul>
          <div class="confirm-actions">
            <button class="cbtn cbtn-cancel" @click="$emit('cancel')" :disabled="loading">Cancel</button>
            <button
              class="cbtn"
              :class="confirmDanger ? 'cbtn-danger' : 'cbtn-primary'"
              @click="$emit('confirm')"
              :disabled="loading"
            >
              <span v-if="loading" class="cbtn-spinner"></span>
              {{ loading ? 'Deleting...' : confirmLabel }}
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
  title: { type: String, default: 'Confirm' },
  message: { type: String, default: 'Are you sure?' },
  details: { type: Array, default: () => [] },
  confirmLabel: { type: String, default: 'Confirm' },
  confirmDanger: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}

.confirm-dialog {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  width: 440px;
  max-width: calc(100vw - 32px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  animation: confirm-pop 0.2s ease;
}

@keyframes confirm-pop {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.confirm-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.confirm-icon.danger {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.confirm-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.confirm-message {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 8px 0;
}

.confirm-details {
  margin: 8px 0 16px 0;
  padding: 12px 16px 12px 32px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  font-size: 13px;
  color: #991b1b;
  list-style-type: disc;
}

.confirm-details li {
  margin: 2px 0;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.cbtn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.cbtn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cbtn-cancel {
  background: #f3f4f6;
  color: #374151;
}

.cbtn-cancel:hover:not(:disabled) {
  background: #e5e7eb;
}

.cbtn-primary {
  background: #2563EB;
  color: #fff;
}

.cbtn-primary:hover:not(:disabled) {
  background: #1D4ED8;
}

.cbtn-danger {
  background: #EF4444;
  color: #fff;
}

.cbtn-danger:hover:not(:disabled) {
  background: #DC2626;
}

.cbtn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: cspin 0.6s linear infinite;
}

@keyframes cspin {
  to { transform: rotate(360deg); }
}

/* Transition */
.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.2s ease;
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}
</style>
