import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { isNative, initNativeAuth } from "@/utils/native";
import "@/styles/theme.css";
import "@/styles/mobile-force.css";

// Drive mobile layout from a class (not @media): some Android WebViews mis-apply
// @media even when matchMedia matches. Toggle html.is-mobile by viewport width.
function syncMobileClass() {
  const mobile = window.innerWidth <= 768;
  document.documentElement.classList.toggle("is-mobile", mobile);
}
syncMobileClass();
window.addEventListener("resize", syncMobileClass);
window.addEventListener("orientationchange", syncMobileClass);

// On-screen error catcher (web + native). Vue render/update errors otherwise blank
// the page with no devtools; show the real stack on a dismissible overlay so it can
// be read/reported, and act as a graceful error boundary. Built with safe DOM
// methods (textContent) — no innerHTML.
function showFatal(msg) {
  // Report server-side (deduped) so crashes are diagnosable from the Error Log.
  try {
    if (!window.__reported) window.__reported = {};
    const key = String(msg).slice(0, 200);
    if (!window.__reported[key]) {
      window.__reported[key] = 1;
      import("@/utils/frappe")
        .then((m) => m.call("next_pms.api.weekly_plan.log_client_error", { message: String(msg).slice(0, 4000), url: location.href }))
        .catch(() => {});
    }
  } catch (e) { /* ignore */ }
  try {
    const id = "wp-fatal-overlay";
    let el = document.getElementById(id);
    if (!el) {
      el = document.createElement("div");
      el.id = id;
      el.style.cssText =
        "position:fixed;inset:0;z-index:99999;background:#fff;overflow:auto;padding:16px;font-family:monospace";
      document.body.appendChild(el);
    }
    el.textContent = "";
    const h = document.createElement("h3");
    h.textContent = "Next PMS error (captured)";
    h.style.cssText = "color:#b00020;margin:0 0 8px";
    const pre = document.createElement("pre");
    pre.textContent = String(msg);
    pre.style.cssText = "white-space:pre-wrap;font-size:12px;color:#b00020;line-height:1.45";
    const btn = document.createElement("button");
    btn.textContent = "Dismiss";
    btn.style.cssText = "margin-top:10px;padding:6px 14px;cursor:pointer";
    btn.addEventListener("click", () => el.remove());
    el.appendChild(h);
    el.appendChild(pre);
    el.appendChild(btn);
  } catch (e) { /* ignore */ }
}
window.addEventListener("error", (e) => showFatal((e.error && e.error.stack) || e.message || e));
window.addEventListener("unhandledrejection", (e) => showFatal((e.reason && e.reason.stack) || e.reason));

const app = createApp(App);
app.config.errorHandler = (err, instance, info) => {
  showFatal((err && err.stack ? err.stack : err) + "\n\n[vue:" + info + "]");
};
app.use(createPinia());
app.use(router);
initNativeAuth()
  .catch(() => {})
  .finally(() => {
    try {
      app.mount("#app");
    } catch (e) {
      showFatal(e && e.stack ? e.stack : e);
    }
  });
