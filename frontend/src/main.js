import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { isNative, initNativeAuth } from "@/utils/native";
import "@/styles/theme.css";

// Native-only on-screen error catcher: if the app fails to render (blank screen
// on a phone with no devtools), show the error text in #app so it can be reported.
function showFatal(msg) {
  const el = document.getElementById("app");
  if (el && el.childElementCount === 0) {
    el.innerHTML =
      '<pre style="padding:16px;white-space:pre-wrap;font-size:13px;color:#b00020;">' +
      "Next PMS failed to start:\n\n" + String(msg) + "</pre>";
  }
}
if (isNative()) {
  window.addEventListener("error", (e) => showFatal(e.message || e.error || e));
  window.addEventListener("unhandledrejection", (e) => showFatal(e.reason || e));
}

const app = createApp(App);
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
