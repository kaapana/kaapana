import { fileURLToPath, URL } from 'node:url'

import { defineConfig, type Plugin, type Connect } from 'vite'
import vue from '@vitejs/plugin-vue'

// Mirror traefik's strip-project-prefix middleware so the dev/preview servers
// (and the e2e suite) serve the app under /project/<short_id>/ like the
// platform does.
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
  base: '/federated-ui/',
  plugins: [vue(), stripProjectPrefix()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // @kaapana/base-ui is an npm-linked file: dependency; resolve its imports
    // to this app's copies.
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia'],
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  server: {
    port: 5000,
    host: true,
    allowedHosts: true,
  },
  build: {
    outDir: 'dist',
  },
})
