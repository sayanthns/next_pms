<template>
  <div class="budget-widget">
    <div class="budget-header">
      <span class="budget-label">Budget</span>
      <span class="budget-percentage" :class="percentageClass">{{ displayUtilization }}%</span>
    </div>

    <div class="budget-bar">
      <div
        class="budget-bar-fill"
        :class="barClass"
        :style="{ width: clampedUtilization + '%' }"
      ></div>
    </div>

    <div class="budget-details">
      <div class="budget-detail">
        <span class="budget-detail-label">Total</span>
        <span class="budget-detail-value">{{ formatCurrency(totalBudget) }}</span>
      </div>
      <div class="budget-detail">
        <span class="budget-detail-label">Used</span>
        <span class="budget-detail-value budget-used">{{ formatCurrency(usedBudget) }}</span>
      </div>
      <div class="budget-detail">
        <span class="budget-detail-label">Remaining</span>
        <span class="budget-detail-value budget-remaining" :class="remainingClass">
          {{ formatCurrency(remaining) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSettingsStore } from '@/store/settings'

const settingsStore = useSettingsStore()

const props = defineProps({
  totalBudget: {
    type: Number,
    default: 0,
  },
  usedBudget: {
    type: Number,
    default: 0,
  },
  utilization: {
    type: Number,
    default: 0,
  },
})

const displayUtilization = computed(() => {
  if (props.utilization > 0) return Math.round(props.utilization)
  if (props.totalBudget === 0) return 0
  return Math.round((props.usedBudget / props.totalBudget) * 100)
})

const clampedUtilization = computed(() => {
  return Math.min(displayUtilization.value, 100)
})

const remaining = computed(() => {
  return props.totalBudget - props.usedBudget
})

const barClass = computed(() => {
  const u = displayUtilization.value
  if (u > 80) return 'bar-danger'
  if (u > 60) return 'bar-warning'
  return 'bar-success'
})

const percentageClass = computed(() => {
  const u = displayUtilization.value
  if (u > 80) return 'text-danger'
  if (u > 60) return 'text-warning'
  return 'text-success'
})

const remainingClass = computed(() => {
  return remaining.value < 0 ? 'text-danger' : ''
})

function formatCurrency(value) {
  return settingsStore.formatCurrency(value)
}
</script>

<style scoped>
.budget-widget {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
}

.budget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.budget-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e1e2e;
}

.budget-percentage {
  font-size: 14px;
  font-weight: 700;
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
}

/* Bar */
.budget-bar {
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
}

.budget-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.bar-success {
  background: #10b981;
}

.bar-warning {
  background: #F59E0B;
}

.bar-danger {
  background: #EF4444;
}

/* Details */
.budget-details {
  display: flex;
  gap: 16px;
}

.budget-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.budget-detail-label {
  font-size: 11px;
  font-weight: 500;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.budget-detail-value {
  font-size: 14px;
  font-weight: 600;
  color: #1e1e2e;
}

/* Color utility classes */
.text-success {
  color: #10b981;
}

.text-warning {
  color: #F59E0B;
}

.text-danger {
  color: #EF4444;
}
</style>
