import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig(() => ({
  base: '/',
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // @kaapana/base-ui is an npm-linked file: dependency
    // make its vue/vuetify imports resolve to this app's copies
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  // Backend calls are not proxied (see README, Development).
  server: {
    port: 5173,
    host: true,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
  },
}))
