import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { initNativeAuth } from "@/utils/native";
import "@/styles/theme.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
initNativeAuth().finally(() => {
  app.mount("#app");
});
