import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, the Vite server (5173) proxies API routes to the backend (8000) so the app can use
// relative URLs everywhere. In production FastAPI serves the build and the API on one origin,
// so the same relative URLs work without a proxy.
//
// This is plain JS (not vite.config.ts) on purpose: Vite 7's TypeScript-config loader fails
// to load under Alpine/musl in the Docker build ("config must export or return an object").
// A JS config is loaded natively as ESM, avoiding that transpilation step.
const API_TARGET = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/sessions': API_TARGET,
      '/providers': API_TARGET,
      '/upload': API_TARGET,
      '/reports': API_TARGET,
      '/health': API_TARGET,
    },
  },
})
