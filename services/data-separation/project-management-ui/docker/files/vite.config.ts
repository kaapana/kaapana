// Plugins
import Vue from '@vitejs/plugin-vue'
// Utilities
import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(() => ({
  plugins: [Vue()],
  base: '/projects-ui',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // @kaapana/base-ui is an npm-linked file: dependency; make its vue/vuetify/axios
    // imports resolve to this app's copies (its own node_modules is absent in
    // the Docker build and must not win locally).
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  server: {
    port: 5174,
    host: true,
  },
  build: {
    outDir: 'dist',
  },
}))
