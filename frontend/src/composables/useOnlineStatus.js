import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Reactive online/offline status composable.
 * Returns { isOnline } — a ref that tracks navigator.onLine.
 */
export function useOnlineStatus() {
  const isOnline = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)

  function update() {
    isOnline.value = navigator.onLine
  }

  onMounted(() => {
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
  })

  onUnmounted(() => {
    window.removeEventListener('online', update)
    window.removeEventListener('offline', update)
  })

  return { isOnline }
}
