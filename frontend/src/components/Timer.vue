<template>
  <div class="timer-wrapper">
    <!-- Another task's timer is running -->
    <div v-if="timerStore.isRunning && timerStore.currentTask !== taskName" class="timer-other">
      <span class="timer-other-indicator"></span>
      <span class="timer-other-text">
        Timer running on: <strong>{{ timerStore.currentTaskTitle || timerStore.currentTask }}</strong>
        &mdash; {{ timerStore.elapsedFormatted }}
      </span>
      <button class="timer-btn timer-stop" @click="handleStopOther">
        Stop &amp; Switch
      </button>
    </div>

    <!-- This task's timer is running -->
    <button
      v-else-if="timerStore.isRunning && timerStore.currentTask === taskName"
      class="timer-btn timer-stop"
      @click="handleStop"
    >
      <span class="timer-stop-icon">&#9632;</span>
      <span class="timer-elapsed">{{ timerStore.elapsedFormatted }}</span>
      <span class="timer-stop-label">&mdash; Stop</span>
    </button>

    <!-- No timer is running -->
    <button
      v-else
      class="timer-btn timer-start"
      @click="handleStart"
    >
      <span class="timer-play-icon">&#9654;</span>
      <span>Start Timer</span>
    </button>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useTimerStore } from '@/store/timer'

const props = defineProps({
  taskName: {
    type: String,
    required: true,
  },
  taskTitle: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['timerStarted', 'timerStopped'])

const timerStore = useTimerStore()

async function handleStart() {
  try {
    await timerStore.startTimer(props.taskName)
    emit('timerStarted')
  } catch (error) {
    console.error('Failed to start timer:', error)
  }
}

async function handleStop() {
  try {
    await timerStore.stopTimer()
    emit('timerStopped')
  } catch (error) {
    console.error('Failed to stop timer:', error)
  }
}

async function handleStopOther() {
  try {
    await timerStore.stopTimer()
    await timerStore.startTimer(props.taskName)
    emit('timerStarted')
  } catch (error) {
    console.error('Failed to switch timer:', error)
  }
}

function handleToggleTimer() {
  if (timerStore.isRunning && timerStore.currentTask === props.taskName) {
    handleStop()
  } else if (!timerStore.isRunning) {
    handleStart()
  }
}

onMounted(() => {
  window.addEventListener('pms:toggle-timer', handleToggleTimer)
})

onUnmounted(() => {
  window.removeEventListener('pms:toggle-timer', handleToggleTimer)
})
</script>

<style scoped>
.timer-wrapper {
  display: inline-flex;
  align-items: center;
}

.timer-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.2s;
}

.timer-start {
  background: #6366f1;
  color: white;
}

.timer-start:hover {
  background: #4f46e5;
}

.timer-stop {
  background: #EF4444;
  color: white;
  animation: pulse 2s infinite;
}

.timer-stop:hover {
  background: #dc2626;
}

.timer-elapsed {
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  font-size: 14px;
  font-weight: 600;
}

.timer-play-icon {
  font-size: 10px;
}

.timer-stop-icon {
  font-size: 10px;
}

.timer-stop-label {
  font-size: 12px;
  opacity: 0.9;
}

/* Other task timer info */
.timer-other {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
}

.timer-other-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f59e0b;
  animation: pulse-warning 2s infinite;
  flex-shrink: 0;
}

.timer-other-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timer-other-text strong {
  font-weight: 600;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

@keyframes pulse-warning {
  0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
  100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}
</style>
