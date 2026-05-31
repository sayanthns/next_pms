# Session Log — May 31, 2026 (Android APK)

Branch `feature/android-apk`. Spec `docs/superpowers/specs/2026-05-31-android-apk-design.md`; plan `docs/superpowers/plans/2026-05-31-android-apk.md`. Subagent-driven. Phases A–C done; signing + CORS/device deferred.

## Done (Phases A–C)
- **Backend auth** (`next_pms/api/auth.py`): `get_api_credentials(usr, pwd)` — `allow_guest`, `@rate_limit(key="usr", limit=10, seconds=300)`. Validates via `frappe.utils.password.check_password` (LoginManager() breaks in CLI), System Users only, returns/generates api_key+api_secret (inlined generate_keys logic — the real one is `only_for("System Manager")`, blocked for guest). Test `test_auth.py`.
- **Native frontend layer** (all gated behind `isNative()` → web byte-identical):
  - `frontend/src/utils/native.js` — `isNative`/`apiBase`/`getToken`/`setToken`/`clearToken`/`initNativeAuth`. Token kept in Capacitor Preferences + in-memory mirror (headers are sync).
  - `frontend/src/utils/frappe.js` — `BASE()` = `apiBase()` ("" web / `https://office.enfono.com` native); `Authorization: token key:secret` in native.
  - `frontend/src/views/NativeLogin.vue` + router guard (native + no token → NativeLogin) + `main.js` `initNativeAuth()` before mount.
  - `vite.config.js` — `--mode native`: base `./`, outDir `frontend/dist-native`, `VITE_NATIVE=1` define. Deps `@capacitor/core`, `@capacitor/preferences`.
- **Capacitor scaffold** (`android-capacitor/`): appId `com.eftpms.pms`, "Next PMS", `webDir ../frontend/dist-native`. `cap add android` generated `android/`. **Debug APK built**: `android-capacitor/android/app/build/outputs/apk/debug/app-debug.apk` (4.03 MB, debug-signed). Toolchain (JDK17 + SDK platform-34/build-tools-34) was already complete.

## Deferred
- **Signed release** (plan Tasks 7–8): needs the fatehhr keystore password + alias (`/Users/sayanthns/Documents/fatehhr/android-capacitor/keystore/fatehhr-release.keystore`). `scripts/build-apk.sh` + env-driven signing config NOT yet added.
- **Backend deploy + CORS** (Task 9): `get_api_credentials` not yet on office/enfono-office-new; `allow_cors` (likely `https://localhost`) not set. The debug APK can't log in until both done.
- **On-device test**: not run (no device here).
- **Web push** in bundled WebView: v1 risk (FCM = v2).

## Notes / gotchas
- `frappe.rate_limit` doesn't exist — use `from frappe.rate_limiter import rate_limit`.
- `native.js` dynamic-imports `@capacitor/preferences`; that broke the WEB build until the dep was installed (APK5 had to come before deploy). On web it's a lazy chunk never executed.
- Implementer set `mysite.local` Administrator pw to `NextPmsApk!2026` while testing auth (local dev only).
- `cap add` needs `typescript` devDep (config is `.ts`).
- stale `frontend/package-lock.json` (npm) coexists with yarn.lock — repo uses yarn; consider deleting.

## Next session
1. Get keystore pw+alias → add signing config + `build-apk.sh` → signed release APK.
2. Deploy auth endpoint to office + enfono-office-new + set `allow_cors` → sideload + device-test login.
