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

// In-cluster development (see ../README.md) reaches the dev server through
// Traefik on 443, so the HMR client must connect there instead of to the dev
// server's own port.
const inClusterHmr = process.env.VITE_IN_CLUSTER_HMR === 'true'

// Without the platform gateway (docker-compose.yaml), the dev server forwards
// workflow-api calls to a local instance that serves them without the prefix.
const workflowApiTarget = process.env.WORKFLOW_API_PROXY_TARGET

export default defineConfig(() => ({
  base: '/workflow-ui/',
  plugins: [vue(), vueDevTools(), stripProjectPrefix()],
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
    allowedHosts: true as const,
    hmr: inClusterHmr
      ? { protocol: 'wss', clientPort: 443, path: '/workflow-ui/@vite' }
      : undefined,
    proxy: workflowApiTarget
      ? {
          '/workflow-api': {
            target: workflowApiTarget,
            rewrite: (path: string) => path.replace(/^\/workflow-api/, ''),
          },
        }
      : undefined,
  },
  build: {
    outDir: 'dist',
  },
}))
