import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/extension-manager-ui/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  server: {
    allowedHosts: true,
    port: 5173,
    host: true,
    strictPort: true,
    proxy: {
      '/extensions-api': {
        target: 'http://extension-manager-api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/extensions-api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
