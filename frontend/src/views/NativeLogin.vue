<template>
  <div class="native-login">
    <h1>Next PMS</h1>
    <input v-model="usr" type="email" placeholder="Email" autocomplete="username" />
    <input v-model="pwd" type="password" placeholder="Password" autocomplete="current-password" @keyup.enter="submit" />
    <button :disabled="busy" @click="submit">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
    <p v-if="err" class="err">{{ err }}</p>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '@/utils/frappe'
import { setToken } from '@/utils/native'
const router = useRouter()
const usr = ref(''); const pwd = ref(''); const busy = ref(false); const err = ref('')
async function submit() {
  if (!usr.value || !pwd.value) return
  busy.value = true; err.value = ''
  try {
    const r = await call('next_pms.api.auth.get_api_credentials', { usr: usr.value, pwd: pwd.value })
    const res = r?.message || r
    if (!res?.api_key) throw new Error('Login failed')
    await setToken(res.api_key + ':' + res.api_secret)
    router.replace('/')
  } catch (e) {
    err.value = 'Invalid credentials or no app access'
  } finally { busy.value = false }
}
</script>
<style scoped>
.native-login { max-width: 360px; margin: 18vh auto; display: flex; flex-direction: column; gap: 12px; padding: 0 20px; }
.native-login input, .native-login button { padding: 12px; font-size: 16px; border-radius: 8px; border: 1px solid #d1d5db; }
.native-login button { background: #2563EB; color: #fff; border: none; font-weight: 600; }
.err { color: #EF4444; font-size: 14px; }
</style>
