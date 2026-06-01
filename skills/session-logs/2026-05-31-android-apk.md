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

## Update 2026-06-01 — signed release + backend deployed
- Backend deployed to office+enfono-office-new (main bc891f4): get_api_credentials LIVE (401 on bad creds), allow_cors set both sites.
- NEW EFTPMS keystore created (alias next-pms, SHA-256 f097c9fa…) — NOT fatehhr's. Keystore + password gitignored (android-capacitor/keystore/, SECRET-DO-NOT-COMMIT.env). Password also in user's password manager.
- Signing config (env-driven) + scripts/build-apk.sh added (main 4fab11a). Signed release built: dist-apk/next-pms-1.0.0.apk (3.2MB, apksigner-verified CN=Next PMS).
- Rebuild anytime: `bash scripts/build-apk.sh <version>`.
- PENDING: on-device login test; verify WebView Origin == allow_cors entry.

## Update 2026-06-01 — APK works, layout blocked on-device (PAUSED)
- APK fully functional: login (get_api_credentials token), data, signed pipeline (scripts/build-apk.sh). versionName visible (1.0.1+).
- BLOCKER: in the phone's Android System WebView (MIUI), the responsive layout doesn't apply — bottom-nav hidden, card grids overflow. Web/PWA renders identical CSS perfectly in Chrome.
- Confirmed NOT a code bug: built native CSS is byte-identical to web build; `@media (max-width:768px){.bottom-nav{display:flex}}` present; on-device diagnostic showed iw=369 mq768=true. So the WebView reports mobile width yet doesn't apply @media.
- Tried: hash-history fix (blank screen → fixed), Preferences static-import (Preferences.then crash → fixed), versionName bump, on-screen error catcher, and a class-based override (html.is-mobile + mobile-force.css, no @media) — user reports "same" on 1.0.4 (possibly stale install / or WebView dropping even class CSS / unverified).
- ROOT-CAUSE UNVERIFIABLE without on-device DevTools (chrome://inspect via USB). Next step when resumed: USB-debug the device, inspect the WebView DOM/CSS at runtime — do NOT keep blind-rebuilding.
- INTERIM: PWA (office.enfono.com/next-pms → Add to Home screen) is fully mobile-working — use that. APK not required for mobile use.
- Commits through main 705c2eb. mobile-force.css + main.js is-mobile toggle in place (web-safe, only <=768).
