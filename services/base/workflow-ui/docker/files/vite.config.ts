import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { commonjsDeps } from '@koumoul/vjsf/utils/build.js'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  optimizeDeps: {
    include: commonjsDeps,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    allowedHosts: true,
    port: 80,
  },
  build: {
    outDir: 'dist',
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
})
