import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import type { Plugin } from 'vite'

export default defineConfig(() => ({
  base: "/extension-manager-ui",
  plugins: [
    vue(),
    vueDevTools(),    
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
      '/extension-manager-api': {
        target: 'http://extension-manager:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/extension-manager-api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
}))
