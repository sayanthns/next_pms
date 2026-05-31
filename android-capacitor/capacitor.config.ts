import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.eftpms.pms",
  appName: "Next PMS",
  webDir: "../frontend/dist-native",
  server: { androidScheme: "https", cleartext: false },
  android: { allowMixedContent: false },
};
export default config;
