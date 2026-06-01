// apps/next_pms/frontend/src/utils/native.js
// Native (Capacitor) helpers. On web, isNative() is false and nothing here changes behavior.
import { Preferences } from '@capacitor/preferences'

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

export async function setToken(token) {
  _token = token || null
  try {
    // Call Preferences methods directly — never `await` the plugin proxy itself
    // (awaiting the proxy probes `.then`, which Capacitor turns into a native
    // `then()` call → "Preferences.then() is not implemented on android").
    if (token) await Preferences.set({ key: 'pms_api_token', value: token })
    else await Preferences.remove({ key: 'pms_api_token' })
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
    const { value } = await Preferences.get({ key: 'pms_api_token' })
    _token = value || null
  } catch (e) {
    _token = null
  }
}
