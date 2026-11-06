import { defineConfig } from "vite";
export default defineConfig({
  build: {
    rollupOptions: { input: { game: "index.html", admin: "admin.html" } },
  },
  server: {
    proxy: {
      "/api": {
        target:
          (globalThis as any).process?.env.API_URL || "http://127.0.0.1:8000",
        ws: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
