import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig(({ command }) => ({
  base: "/extension-manager-ui",
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
    // Only ship the Vue devtools in dev (vite serve), never in the production build.
    ...(command === 'serve' ? [vueDevTools()] : []),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
    extensions: [
      '.js',
      '.json',
      '.jsx',
      '.mjs',
      '.ts',
      '.tsx',
      '.vue',
    ],
  },
  server: {
    allowedHosts: ['localhost', '127.0.0.1'],
    port: 5173,
    host: true,
    strictPort: true,
    proxy: {
      '/extensions-api': {
        target: 'http://extension-manager:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/extensions-api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
}))
