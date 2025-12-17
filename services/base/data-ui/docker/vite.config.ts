import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.BASE_URL || '/data-ui/',
  plugins: [vue(), vuetify({ autoImport: true })],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/data-api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        ws: true,
        rewrite: path => path.replace(/^\/data-api/, '')
      },
    },
  },
})
