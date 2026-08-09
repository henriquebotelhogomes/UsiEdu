/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
  server: {
    port: 5173,
    proxy: {
      "/auth": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/chat": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // Deep-link/reload (T7.4): GET /chat serve o SPA; GET /chat/history e
        // POST /chat continuam para a API.
        bypass: (req) => {
          if (req.method === "GET" && (req.url === "/chat" || req.url?.startsWith("/chat?"))) {
            return "/index.html";
          }
        },
      },
      "/feedback": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});