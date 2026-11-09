import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In dev the frontend runs on its own port, so /api calls are forwarded to
    // the backend. In production FastAPI serves the built files on one origin.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
