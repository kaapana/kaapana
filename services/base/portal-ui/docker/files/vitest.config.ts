import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // Same reason as in vite.config.ts:
    // The linked @kaapana/base-ui must use this app's vue and vuetify
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/__tests__/*'],
    css: true,
    server: {
      deps: {
        // vuetify ships raw .css imports node can't load; base-ui is inlined
        // so the dedupe above applies to its imports as well.
        inline: ['vuetify', '@kaapana/base-ui'],
      },
    },
  },
})
