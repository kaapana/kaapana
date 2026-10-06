import { fileURLToPath, URL } from 'node:url'

import { defineConfig, type Connect, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

function stripProjectPrefix(): Plugin {
  const rewrite: Connect.NextHandleFunction = (req, _res, next) => {
    req.url = req.url!.replace(/^\/project\/[^/]+\//, '/')
    next()
  }
  return {
    name: 'strip-project-prefix',
    configureServer(server) {
      server.middlewares.use(rewrite)
    },
    configurePreviewServer(server) {
      server.middlewares.use(rewrite)
    },
  }
}

export default defineConfig({
  base: '/data-ui/',
  plugins: [vue(), stripProjectPrefix()],
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
      '/data-api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/data-api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
