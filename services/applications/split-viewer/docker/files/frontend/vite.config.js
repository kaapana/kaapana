// vite.config.js / vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // Matches global.split_viewer_prefix in the Helm chart (Traefik strips this
  // prefix before the request reaches the backend, but the browser still
  // requests built assets at this absolute path, so it must be baked in here).
  base: '/split-viewer/',
  plugins: [
    react(),
    tailwindcss(),     // 💡 new line
  ],
  server: {
    proxy: {
      // Proxy requests from /dcm4chee-arc to your dcm4chee server
      '/dcm4chee-arc': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
