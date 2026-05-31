# Next PMS Android APK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a sideloadable, signed Android APK of the Next PMS SPA — bundled web assets, talking to `https://office.enfono.com` via token auth, wrapped in Capacitor, signed with the existing fatehhr keystore.

**Architecture:** A native build of the existing Vue SPA (relative base, own dist) is bundled into a Capacitor Android project. All native code paths are gated behind `isNative()` so the web build is byte-for-byte unchanged. Native auth uses Frappe api_key/secret (obtained via a new login endpoint, stored in Capacitor Preferences, mirrored to an in-memory token for synchronous request headers). Reference implementation: sibling project `fatehhr` at `/Users/sayanthns/Documents/fatehhr` (same stack, already ships a signed APK) — copy + adapt its proven scaffold and scripts.

**Tech Stack:** Capacitor 6, Vue 3 + Vite 5, Frappe v15. Toolchain on this Mac (verified): JDK 17 (Homebrew), Android SDK at `~/Library/Android/sdk` (export `ANDROID_HOME` for builds), Capacitor ships `gradlew` (no global gradle), node 24 / yarn 1.22. Keystore: `/Users/sayanthns/Documents/fatehhr/android-capacitor/keystore/fatehhr-release.keystore` (reuse).

**Spec:** `docs/superpowers/specs/2026-05-31-android-apk-design.md`

**Decisions (locked):** Capacitor • bundled dist • token auth (api_key/secret) • appId `com.eftpms.pms` / "Next PMS" • reuse fatehhr keystore + sideload • keep VAPID web push v1 (FCM = v2 risk).

**Key facts about the existing code:**
- `frontend/vite.config.*`: `base = command==="serve" ? "/" : "/assets/next_pms/frontend/"`, `outDir = ../next_pms/public/frontend`, `emptyOutDir: true`. The web build MUST keep this output.
- `frontend/src/utils/frappe.js`: `const BASE_URL = ""`; every request is `fetch(\`${BASE_URL}/api/...\`, {headers: getHeaders(), credentials: "include"})`; `getHeaders()` adds `X-Frappe-CSRF-Token`. This is cookie-session auth — must branch for native.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `next_pms/api/auth.py` (NEW) | `get_api_credentials(usr, pwd)` — validate login, return api_key/secret |
| `next_pms/api/test_auth.py` (NEW) | tests for the endpoint |
| `frontend/src/utils/native.js` (NEW) | `isNative()`, `API_BASE()`, token store (Preferences + in-memory), `initNativeAuth()` |
| `frontend/src/utils/frappe.js` (MODIFY) | absolute base + `Authorization: token` header in native |
| `frontend/src/views/NativeLogin.vue` (NEW) | native-only login screen |
| `frontend/src/main.js` (MODIFY) | init native auth before mount |
| `frontend/src/router/index.js` (MODIFY) | native guard → NativeLogin when no token |
| `frontend/vite.config.*` (MODIFY) | native build mode: relative base + separate outDir |
| `frontend/package.json` (MODIFY) | `build:native` script + `@capacitor/core`, `@capacitor/preferences` deps |
| `android-capacitor/` (NEW) | Capacitor project (config, package.json, android/) — modeled on fatehhr |
| `scripts/build-apk.sh` (NEW) | one-command build → signed APK |
| office `site_config.json` (server) | `allow_cors` for the Capacitor origin |

---

## Phase A — Backend native auth

### Task 1: `get_api_credentials` endpoint (TDD)

**Files:** Create `next_pms/api/auth.py`, `next_pms/api/test_auth.py`

- [ ] **Step 1: Write the failing test** — `next_pms/api/test_auth.py`:
```python
# apps/next_pms/next_pms/api/test_auth.py
import frappe
from frappe.tests.utils import FrappeTestCase
from next_pms.api import auth


class TestAuth(FrappeTestCase):
    def test_valid_credentials_return_keys(self):
        # Administrator always exists in a test site
        frappe.set_user("Administrator")
        res = auth.get_api_credentials("Administrator", frappe.local.conf.admin_password or "admin")
        # Either returns keys, or raises on bad pw — here we just assert structure when ok
        self.assertIn("api_key", res)
        self.assertIn("api_secret", res)
        self.assertTrue(res["api_key"])

    def test_invalid_credentials_throw(self):
        with self.assertRaises(frappe.AuthenticationError):
            auth.get_api_credentials("Administrator", "definitely-wrong-pw-xyz")
```
(If the test site's admin password differs, the first test may need the real pw; the structure assertion is the point. The second test is the firm one.)

- [ ] **Step 2: Run, expect FAIL** — `bench --site mysite.local run-tests --module next_pms.api.test_auth` → `module ... has no attribute 'get_api_credentials'`.

- [ ] **Step 3: Implement** — `next_pms/api/auth.py`:
```python
# apps/next_pms/next_pms/api/auth.py
import frappe
from frappe import _
from frappe.utils.password import update_password  # noqa: F401  (kept for parity; not used)


@frappe.whitelist(allow_guest=True)
def get_api_credentials(usr, pwd):
    """Native-app login: validate username+password, return the user's API key/secret.

    allow_guest is required because this IS the login (no session yet). It does its own
    credential check via LoginManager and never leaks keys without a valid password.
    """
    if not usr or not pwd:
        frappe.throw(_("Username and password are required"), frappe.AuthenticationError)

    # Validate credentials (raises AuthenticationError on failure)
    login = frappe.auth.LoginManager()
    login.authenticate(user=usr, pwd=pwd)  # sets login.user on success, else raises
    user = login.user

    # Disallow portal/customer + disabled users from native app login
    user_type = frappe.db.get_value("User", user, "user_type")
    if user_type != "System User":
        frappe.throw(_("This account cannot use the mobile app"), frappe.AuthenticationError)

    api_key, api_secret = _ensure_api_keys(user)
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
    }


def _ensure_api_keys(user):
    """Return (api_key, api_secret), generating them if the user has none."""
    user_doc = frappe.get_doc("User", user)
    api_key = user_doc.api_key
    # api_secret is a Password field; generate a fresh secret if key missing
    if not api_key:
        from frappe.core.doctype.user.user import generate_keys
        # generate_keys returns {"api_secret": ...} and sets api_key on the user
        result = generate_keys(user)
        api_secret = result.get("api_secret")
        api_key = frappe.db.get_value("User", user, "api_key")
    else:
        api_secret = user_doc.get_password("api_secret")
    return api_key, api_secret
```
Note: `generate_keys` is `frappe.core.doctype.user.user.generate_keys`. Verify the exact return shape against the installed v15 (`bench --site mysite.local console` → inspect). If `get_password("api_secret")` fails when secret unset, regenerate via `generate_keys`.

- [ ] **Step 4: Run, expect PASS** — `bench --site mysite.local run-tests --module next_pms.api.test_auth`. Fix implementation if the key-generation API differs in this v15 (read `apps/frappe/frappe/core/doctype/user/user.py::generate_keys`).

- [ ] **Step 5: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add next_pms/api/auth.py next_pms/api/test_auth.py
git commit -m "feat: get_api_credentials native-login endpoint (api_key/secret)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase B — Frontend native layer (web build unaffected)

### Task 2: `native.js` — platform detection + token store

**Files:** Create `frontend/src/utils/native.js`

- [ ] **Step 1: Create the module**
```javascript
// apps/next_pms/frontend/src/utils/native.js
// Native (Capacitor) helpers. On web, isNative() is false and nothing here changes behavior.
const NATIVE = import.meta.env.VITE_NATIVE === '1'
// Single-tenant v1: the APK always talks to this ERP.
const NATIVE_API_BASE = 'https://office.enfono.com'

let _token = null  // in-memory "key:secret" for synchronous request headers

export function isNative() {
  if (NATIVE) return true
  // runtime fallback if the bundle wasn't built with the native flag
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
  } catch (e) { /* web / no plugin */ }
}

export async function clearToken() {
  await setToken(null)
}

export async function initNativeAuth() {
  // Load any stored token into memory so getHeaders() can use it synchronously.
  if (!isNative()) return
  try {
    const P = await _prefs()
    const { value } = await P.get({ key: 'pms_api_token' })
    _token = value || null
  } catch (e) { _token = null }
}
```

- [ ] **Step 2: Sanity** — `cd frontend && npx vite build --mode development >/dev/null 2>&1 || true` is not needed; just ensure no syntax error via `node --check src/utils/native.js` (ES module import syntax may warn — acceptable; the real check is the build in Task 8).

- [ ] **Step 3: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add frontend/src/utils/native.js
git commit -m "feat: native.js — Capacitor platform detection + token store

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 3: Patch `frappe.js` for absolute base + token header

**Files:** Modify `frontend/src/utils/frappe.js`

- [ ] **Step 1: Import native helpers + replace BASE_URL.** At the top of `frappe.js`, add:
```javascript
import { isNative, apiBase, getToken } from './native'
```
Replace `const BASE_URL = "";` with:
```javascript
function BASE() { return apiBase() }  // "" on web, absolute https on native
```
Then replace every `${BASE_URL}` usage with `${BASE()}` (there are several: the `call` fetch, `getList`, `getDoc`, and any others — grep `BASE_URL` and update each).

- [ ] **Step 2: Token header in `getHeaders`.** In `getHeaders()`, after the CSRF block, add:
```javascript
  if (isNative()) {
    const t = getToken()
    if (t) headers["Authorization"] = "token " + t
  }
```
(Leave CSRF logic for web. In native there's no cookie/CSRF; the token authenticates.)

- [ ] **Step 3: Verify no missed BASE_URL.** Run `grep -n "BASE_URL" frontend/src/utils/frappe.js` → expect no matches (all replaced with `BASE()`).

- [ ] **Step 4: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add frontend/src/utils/frappe.js
git commit -m "feat: frappe.js uses absolute base + token auth in native mode

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 4: NativeLogin view + router guard + app init

**Files:** Create `frontend/src/views/NativeLogin.vue`; modify `frontend/src/router/index.js`, `frontend/src/main.js`

- [ ] **Step 1: NativeLogin.vue**
```vue
<!-- apps/next_pms/frontend/src/views/NativeLogin.vue -->
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
```

- [ ] **Step 2: Router guard.** In `frontend/src/router/index.js`: register the route and a native guard.
Add to routes: `{ path: '/native-login', name: 'NativeLogin', component: () => import('@/views/NativeLogin.vue') }`.
Add import at top: `import { isNative, getToken } from '@/utils/native'`.
In the existing `router.beforeEach((to, from, next) => { ... })`, at the very top of the handler add:
```javascript
  if (isNative() && to.name !== 'NativeLogin' && !getToken()) {
    return next({ name: 'NativeLogin' })
  }
  if (isNative() && to.name === 'NativeLogin' && getToken()) {
    return next('/')
  }
```
(Keep all existing guard logic — e.g. the PMS Customer portal redirect — after this.)

- [ ] **Step 3: Init before mount.** In `frontend/src/main.js`, before `app.mount(...)`, await native auth:
```javascript
import { initNativeAuth } from '@/utils/native'
// ... existing app/router/pinia setup ...
initNativeAuth().finally(() => {
  app.mount('#app')
})
```
(If `main.js` already mounts synchronously, wrap the mount as above. Preserve plugin registration order — call initNativeAuth after `app.use(router)`/pinia, before mount.)

- [ ] **Step 4: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add frontend/src/views/NativeLogin.vue frontend/src/router/index.js frontend/src/main.js
git commit -m "feat: native login screen + router guard + init token before mount

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 5: Native vite build mode + deps

**Files:** Modify `frontend/vite.config.*`, `frontend/package.json`

- [ ] **Step 1: vite native mode.** In `frontend/vite.config.*`, make base + outDir depend on `mode === 'native'`. Replace the config function so:
```javascript
export default defineConfig(({ command, mode }) => {
  const native = mode === 'native'
  return {
    plugins: [vue()],
    base: native ? './' : (command === 'serve' ? '/' : '/assets/next_pms/frontend/'),
    define: { 'import.meta.env.VITE_NATIVE': JSON.stringify(native ? '1' : '0') },
    build: {
      outDir: native
        ? path.resolve(__dirname, 'dist-native')
        : path.resolve(__dirname, '../next_pms/public/frontend'),
      emptyOutDir: true,
    },
    // ...keep any existing server/proxy/resolve config unchanged...
  }
})
```
(Merge with the existing config object — keep `resolve.alias`, `server`, etc. Only base/outDir/define change by mode.)

- [ ] **Step 2: package.json.** Add to `scripts`: `"build:native": "vite build --mode native"`. Add to `dependencies`: `"@capacitor/core": "^6.1.0"`, `"@capacitor/preferences": "^6.0.0"`. Then `cd frontend && yarn install`.

- [ ] **Step 3: Verify both builds.**
  - Web (must be unchanged): `cd frontend && yarn build` → outputs to `../next_pms/public/frontend`, base `/assets/next_pms/frontend/`.
  - Native: `yarn build:native` → outputs to `frontend/dist-native`, `index.html` uses relative `./assets/...` paths, and `import.meta.env.VITE_NATIVE` is `'1'`. Confirm `grep -c './assets' dist-native/index.html` > 0.

- [ ] **Step 4: gitignore dist-native.** Add `frontend/dist-native/` to `.gitignore` (build artifact, not committed).

- [ ] **Step 5: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add frontend/vite.config.* frontend/package.json frontend/yarn.lock .gitignore
git commit -m "feat: native vite build mode (relative base, dist-native, VITE_NATIVE flag) + capacitor deps

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase C — Capacitor Android project

### Task 6: Scaffold `android-capacitor/` (model on fatehhr)

**Files:** Create `android-capacitor/package.json`, `android-capacitor/capacitor.config.ts`, generate `android-capacitor/android/`

- [ ] **Step 1: package.json** — `android-capacitor/package.json`:
```json
{
  "name": "next-pms-android",
  "private": true,
  "type": "module",
  "scripts": {
    "cap:copy": "npx cap copy android",
    "cap:sync": "npx cap sync android",
    "build:release": "cd android && ./gradlew assembleRelease --no-daemon"
  },
  "dependencies": {
    "@capacitor/android": "^6.1.0",
    "@capacitor/app": "^6.0.3",
    "@capacitor/cli": "^6.1.0",
    "@capacitor/core": "^6.1.0",
    "@capacitor/preferences": "^6.0.0"
  }
}
```

- [ ] **Step 2: capacitor.config.ts** — `android-capacitor/capacitor.config.ts`:
```typescript
import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.eftpms.pms",
  appName: "Next PMS",
  webDir: "../frontend/dist-native",   // the native build output
  server: { androidScheme: "https", cleartext: false },
  android: { allowMixedContent: false },
};
export default config;
```

- [ ] **Step 3: Install + add android.**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms/android-capacitor
yarn install
export ANDROID_HOME=$HOME/Library/Android/sdk
# native web build must exist first:
( cd ../frontend && yarn build:native )
npx cap add android
npx cap copy android
```
Expected: `android/` directory generated with `gradlew`. `cap copy` copies `dist-native` into `android/app/src/main/assets/public`.

- [ ] **Step 4: First debug build (smoke).**
```bash
cd android && export ANDROID_HOME=$HOME/Library/Android/sdk && ./gradlew assembleDebug --no-daemon
```
Expected: BUILD SUCCESSFUL; an unsigned debug APK at `android/app/build/outputs/apk/debug/app-debug.apk`. (Gradle will download dependencies on first run — allow time.)

- [ ] **Step 5: Commit** (commit the scaffold; the `android/` native project is large but fatehhr commits it — do the same so builds are reproducible). Add `android-capacitor/node_modules` and gradle caches to `.gitignore`:
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
printf "android-capacitor/node_modules/\nandroid-capacitor/android/.gradle/\nandroid-capacitor/android/app/build/\nandroid-capacitor/android/build/\n" >> .gitignore
git add .gitignore android-capacitor/package.json android-capacitor/capacitor.config.ts android-capacitor/android
git commit -m "feat: Capacitor Android scaffold (com.eftpms.pms, bundled dist-native)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase D — Signing + one-command build

### Task 7: Release signing config (env-driven, reuse fatehhr keystore)

**Files:** Modify `android-capacitor/android/app/build.gradle`

- [ ] **Step 1: Read fatehhr's signing patch for reference** — `cat /Users/sayanthns/Documents/fatehhr/scripts/_patch-build-gradle.py` and `/Users/sayanthns/Documents/fatehhr/android-capacitor/android/app/build.gradle` (the `signingConfigs`/`release` block). Mirror its env-var approach.

- [ ] **Step 2: Add signingConfigs to `android-capacitor/android/app/build.gradle`** inside `android { ... }`:
```gradle
    signingConfigs {
        release {
            def kp = System.getenv("PMS_KEYSTORE_PATH")
            if (kp != null) {
                storeFile file(kp)
                storePassword System.getenv("PMS_KEYSTORE_PW")
                keyAlias System.getenv("PMS_KEY_ALIAS")
                keyPassword System.getenv("PMS_KEY_PW")
            }
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
        }
    }
```
Also set `applicationId "com.eftpms.pms"` in `defaultConfig` (cap add sets it from appId, verify). Keep existing `buildTypes.release` content; merge `signingConfig` in.

- [ ] **Step 3: Determine the keystore alias.** Run:
```bash
keytool -list -v -keystore /Users/sayanthns/Documents/fatehhr/android-capacitor/keystore/fatehhr-release.keystore 2>/dev/null | grep -i "Alias name"
```
(You will be prompted for the keystore password — get it from the user / fatehhr `customers/.env.*` or `FATEHHR_KEYSTORE_PW`. Record the alias for `PMS_KEY_ALIAS`.) If the password isn't available, STOP and ask the user for the fatehhr keystore password + alias.

- [ ] **Step 4: Commit**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add android-capacitor/android/app/build.gradle
git commit -m "feat: env-driven release signing config

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 8: `build-apk.sh` → signed APK

**Files:** Create `scripts/build-apk.sh`

- [ ] **Step 1: Script** — `scripts/build-apk.sh`:
```bash
#!/usr/bin/env bash
# Build a signed Next PMS APK. Requires keystore secrets in the environment:
#   export PMS_KEYSTORE_PW=...  PMS_KEY_PW=...  PMS_KEY_ALIAS=...
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export PMS_KEYSTORE_PATH="${PMS_KEYSTORE_PATH:-/Users/sayanthns/Documents/fatehhr/android-capacitor/keystore/fatehhr-release.keystore}"
: "${PMS_KEYSTORE_PW:?set PMS_KEYSTORE_PW}"; : "${PMS_KEY_PW:?set PMS_KEY_PW}"; : "${PMS_KEY_ALIAS:?set PMS_KEY_ALIAS}"
VERSION="${1:-1.0.0}"

echo "▶ Native web build"
( cd "$REPO_ROOT/frontend" && yarn build:native )
echo "▶ cap copy"
( cd "$REPO_ROOT/android-capacitor" && npx cap copy android )
echo "▶ assembleRelease"
( cd "$REPO_ROOT/android-capacitor/android" && ./gradlew assembleRelease --no-daemon )
SRC="$REPO_ROOT/android-capacitor/android/app/build/outputs/apk/release/app-release.apk"
mkdir -p "$REPO_ROOT/dist-apk"
DEST="$REPO_ROOT/dist-apk/next-pms-${VERSION}.apk"
cp "$SRC" "$DEST"
echo "✅ $DEST"
echo "   adb install -r \"$DEST\""
```
`chmod +x scripts/build-apk.sh`. Add `dist-apk/` to `.gitignore`.

- [ ] **Step 2: Build the signed APK.**
```bash
export PMS_KEYSTORE_PW=...  PMS_KEY_PW=...  PMS_KEY_ALIAS=...   # from Task 7 step 3
bash scripts/build-apk.sh 1.0.0
```
Expected: `dist-apk/next-pms-1.0.0.apk` produced. Verify it's signed: `~/Library/Android/sdk/build-tools/*/apksigner verify --print-certs dist-apk/next-pms-1.0.0.apk`.

- [ ] **Step 3: Commit the script**
```bash
cd /Users/sayanthns/frappe-bench/apps/next_pms
git add scripts/build-apk.sh .gitignore
git commit -m "feat: build-apk.sh one-command signed APK build

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase E — Backend CORS + ship

### Task 9: CORS for the Capacitor origin + deploy backend

**Files:** office + enfono-office-new `site_config.json` (server)

- [ ] **Step 1: Determine the WebView origin.** On a connected device/emulator with the APK installed, inspect a failed request's `Origin` (Chrome `chrome://inspect` → the WebView). With `androidScheme: "https"` + `webDir` bundled, the origin is typically `https://localhost`. Confirm before configuring.

- [ ] **Step 2: Allow CORS on both PMS sites.** Frappe v15 reads `allow_cors` from site_config. Set it (manual, via control→Tailscale, both sites):
```bash
# per CLAUDE.md deploy access (control -> tailscale 100.104.220.9)
bench --site office set-config -p allow_cors '["https://localhost","capacitor://localhost"]'
bench --site enfono-office-new set-config -p allow_cors '["https://localhost","capacitor://localhost"]'
```
(Use the exact origin found in Step 1. `-p` writes a parsed JSON list.) Restart workers after.

- [ ] **Step 3: Deploy the backend auth endpoint.** Merge this branch → main, push, and on the office server (control→Tailscale): `git pull` → `bench --site office migrate && bench --site enfono-office-new migrate` (no schema change here, but harmless) → restart. The `get_api_credentials` endpoint then exists for the APK.

- [ ] **Step 4: Manual device verification.**
  - `adb install -r dist-apk/next-pms-1.0.0.apk`
  - Launch → NativeLogin → enter a System User's email + password → lands on dashboard.
  - Verify data loads (projects/tasks) over `Authorization: token`.
  - Airplane-mode → app shell still opens (bundled), shows a network error on data (expected).

---

## Web regression (MUST stay green)

- [ ] After all tasks: `cd frontend && yarn build` (web) → loads at `office.enfono.com/next-pms/`, cookie login works, no token path triggered (`isNative()` false). The web SPA must be unchanged. Re-deploy the web bundle as usual if these commits altered `public/frontend`.

---

## Self-Review

**Spec coverage:** Capacitor wrapper → Task 6. Bundled dist → Tasks 5/6. Absolute API base + token auth → Tasks 2/3. Native login + endpoint → Tasks 1/4. appId/keystore/sign → Tasks 6/7/8. CORS → Task 9. Web push kept (no change) ✓. Web-unaffected gating via `isNative()` → Tasks 2/3/4 ✓.

**Placeholders:** Real code in every code step. Task 7 step 3 (keystore password/alias) is a genuine human input — flagged as STOP-and-ask, not a placeholder. Task 9 step 1 (exact WebView origin) is verify-on-device, with the expected value given.

**Type/name consistency:** `isNative`/`apiBase`/`getToken`/`setToken`/`clearToken`/`initNativeAuth` defined in Task 2, imported identically in Tasks 3/4. `get_api_credentials(usr,pwd)` returns `{api_key, api_secret, user, full_name}` — consumed in Task 4 (`res.api_key`, `res.api_secret`). `VITE_NATIVE` define (Task 5) read in Task 2. `dist-native` outDir (Task 5) = `webDir` (Task 6). appId `com.eftpms.pms` consistent Tasks 6/7. ✓

**Risks (from spec):** auth touches all requests — gated behind `isNative()`, web path untouched (verify via web regression). Web push from bundled WebView may not deliver in background (v1 accepted; FCM = v2). Keystore password required (Task 7). CORS origin confirm-on-device (Task 9).
