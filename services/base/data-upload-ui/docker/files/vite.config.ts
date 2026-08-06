import { fileURLToPath, URL } from 'node:url'

import { defineConfig, type Plugin, type Connect } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

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
  base: '/data-upload-ui/',
  plugins: [vue(), vuetify({ autoImport: true }), stripProjectPrefix()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // @kaapana/base-ui is an npm-linked file: dependency whose own node_modules
    // is absent in the Docker build — force its imports to this app's copies.
    // vjsf too: a second vjsf/ajv instance at runtime breaks json-layout.
    dedupe: ['vue', 'vuetify', 'axios', '@kyvg/vue3-notification', 'pinia', '@koumoul/vjsf'],
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  server: {
    allowedHosts: true,
    port: 5000,
    host: true,
  },
  // @koumoul/vjsf pulls @json-layout/* — raw ESM that default-imports CJS deps
  // (ajv, debug). Pre-bundle so the dev server gets default-export interop;
  // rollup already handles this in prod builds.
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
  build: {
    outDir: 'dist',
  },
}))
