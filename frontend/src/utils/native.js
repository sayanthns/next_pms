// apps/next_pms/frontend/src/utils/native.js
// Native (Capacitor) helpers. On web, isNative() is false and nothing here changes behavior.
const NATIVE = import.meta.env.VITE_NATIVE === '1'
// Single-tenant v1: the APK always talks to this ERP.
const NATIVE_API_BASE = 'https://office.enfono.com'

let _token = null // in-memory "key:secret" for synchronous request headers

export function isNative() {
  if (NATIVE) return true
  return typeof window !== 'undefined' && !!window.Capacitor?.isNativePlatform?.()
}

export function apiBase() {
  return isNative() ? NATIVE_API_BASE : ''
}

export function getToken() {
  return _token
}

async function _prefs() {
  const { Preferences } = await import('@capacitor/preferences')
  return Preferences
}

export async function setToken(token) {
  _token = token || null
  try {
    const P = await _prefs()
    if (token) await P.set({ key: 'pms_api_token', value: token })
    else await P.remove({ key: 'pms_api_token' })
  } catch (e) {
    /* web / plugin absent: in-memory only */
  }
}

export async function clearToken() {
  await setToken(null)
}

export async function initNativeAuth() {
  // Load any stored token into memory so getHeaders() can read it synchronously.
  if (!isNative()) return
  try {
    const P = await _prefs()
    const { value } = await P.get({ key: 'pms_api_token' })
    _token = value || null
  } catch (e) {
    _token = null
  }
}
