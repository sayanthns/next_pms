import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig(({ command, mode }) => {
  const native = mode === "native";
  return {
    plugins: [vue()],
    base: native ? "./" : command === "serve" ? "/" : "/assets/next_pms/frontend/",
    define: {
      "import.meta.env.VITE_NATIVE": JSON.stringify(native ? "1" : "0"),
    },
    build: {
      outDir: native
        ? path.resolve(__dirname, "dist-native")
        : path.resolve(__dirname, "../next_pms/public/frontend"),
      emptyOutDir: true,
      rollupOptions: {
        input: path.resolve(__dirname, "index.html"),
      },
      target: "es2020",
      sourcemap: false,
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    server: {
      port: 8081,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
        "/assets": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
        "/files": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
