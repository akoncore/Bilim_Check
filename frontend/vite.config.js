import { defineConfig } from "vite";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  server: {
    proxy: { "/api": process.env.BACKEND_URL || "http://localhost:8000" },
  },
});
