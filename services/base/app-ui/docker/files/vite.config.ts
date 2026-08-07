import { fileURLToPath, URL } from 'node:url'

import { defineConfig, type Plugin, type Connect } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

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

export default defineConfig(() => ({
  base: '/app-ui/',
  plugins: [vue(), vueDevTools(), stripProjectPrefix()],
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
    port: 5000,
    host: true,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
  },
}))
