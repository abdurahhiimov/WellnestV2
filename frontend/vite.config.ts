import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/app/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8787",
      "/reports": "http://127.0.0.1:8787",
      "/oura": "http://127.0.0.1:8787",
      "/icons": "http://127.0.0.1:8787",
    },
  },
})
