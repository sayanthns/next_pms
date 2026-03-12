<template>
  <div class="empty-state">
    <div class="empty-state-icon">{{ icon }}</div>
    <h3 class="empty-state-title">{{ title }}</h3>
    <p v-if="description" class="empty-state-description">{{ description }}</p>
    <router-link
      v-if="actionText && actionRoute"
      :to="actionRoute"
      class="empty-state-btn"
    >
      {{ actionText }}
    </router-link>
    <button
      v-else-if="actionText"
      class="empty-state-btn"
      @click="$emit('action')"
    >
      {{ actionText }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    default: '\uD83D\uDCCB',
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
  actionText: {
    type: String,
    default: '',
  },
  actionRoute: {
    type: String,
    default: '',
  },
})

defineEmits(['action'])
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
  min-height: 300px;
}

.empty-state-icon {
  font-size: 48px;
  margin-bottom: 16px;
  line-height: 1;
}

.empty-state-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e1e2e;
  margin-bottom: 8px;
}

.empty-state-description {
  font-size: 14px;
  color: #6b7280;
  max-width: 360px;
  line-height: 1.5;
  margin-bottom: 20px;
}

.empty-state-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.2s, box-shadow 0.2s;
}

.empty-state-btn:hover {
  background: #4f46e5;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}
</style>
