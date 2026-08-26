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
  base: '/workflow-execution-ui/',
  plugins: [vue(), vueDevTools(), stripProjectPrefix()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // @kaapana/base-ui is an npm-linked file: dependency; resolve its imports to
    // this app's copies. vjsf is deduped too — a second vjsf/ajv instance at
    // runtime breaks json-layout.
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia', '@koumoul/vjsf'],
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  // @json-layout/* ship raw ESM that default-imports CJS deps (ajv, debug, ...);
  // pre-bundle so the dev server gets proper default-export interop (rollup
  // already handles this in prod builds).
  optimizeDeps: {
    include: [
      '@koumoul/vjsf',
      '@json-layout/core',
      '@json-layout/vocabulary',
      'ajv',
      'ajv/dist/2019.js',
      'ajv-formats',
      'ajv-errors',
      'ajv-i18n',
      'debug',
    ],
  },
  server: {
    allowedHosts: true,
    port: 5000,
    host: true,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
  },
}))
