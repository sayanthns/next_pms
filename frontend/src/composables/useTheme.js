import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const STORAGE_KEY = 'pms-theme'
const THEME_LIGHT = 'light'
const THEME_DARK = 'dark'
const THEME_AUTO = 'auto'

// Shared reactive state (singleton across all component instances)
const preference = ref(THEME_LIGHT) // 'light' | 'dark' | 'auto'
const systemDark = ref(false)
let initialized = false

function getSystemDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

function applyTheme(isDark) {
  const html = document.documentElement
  if (isDark) {
    html.setAttribute('data-theme', 'dark')
  } else {
    html.removeAttribute('data-theme')
  }

  // Update PWA theme-color meta tag
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) {
    meta.setAttribute('content', isDark ? '#0f1117' : '#ffffff')
  }
}

/**
 * Theme management composable.
 * Supports light, dark, and auto (system) modes.
 * Persists preference to localStorage.
 */
export function useTheme() {
  const isDark = computed(() => {
    if (preference.value === THEME_AUTO) return systemDark.value
    return preference.value === THEME_DARK
  })

  let mediaQuery = null
  let mediaHandler = null

  function init() {
    if (initialized) return
    initialized = true

    // Read saved preference
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === THEME_DARK || saved === THEME_AUTO) {
      preference.value = saved
    }

    // Track system preference
    systemDark.value = getSystemDark()
    mediaQuery = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (mediaQuery) {
      mediaHandler = (e) => {
        systemDark.value = e.matches
      }
      mediaQuery.addEventListener('change', mediaHandler)
    }

    // Apply initial theme
    applyTheme(isDark.value)
  }

  // Watch for changes and apply
  watch(isDark, (dark) => {
    applyTheme(dark)
  })

  function setTheme(mode) {
    if (![THEME_LIGHT, THEME_DARK, THEME_AUTO].includes(mode)) return
    preference.value = mode
    localStorage.setItem(STORAGE_KEY, mode)
  }

  function toggleTheme() {
    // Cycle: light → dark → auto → light
    if (preference.value === THEME_LIGHT) {
      setTheme(THEME_DARK)
    } else if (preference.value === THEME_DARK) {
      setTheme(THEME_AUTO)
    } else {
      setTheme(THEME_LIGHT)
    }
  }

  onMounted(init)

  onUnmounted(() => {
    if (mediaQuery && mediaHandler) {
      mediaQuery.removeEventListener('change', mediaHandler)
    }
  })

  return {
    theme: preference,
    isDark,
    toggleTheme,
    setTheme,
  }
}
