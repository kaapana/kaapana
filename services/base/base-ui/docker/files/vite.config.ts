import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Library build: an ESM bundle consumers import. The peers (and the optional
// @koumoul/vjsf) must never be bundled — vite lib mode does not externalize
// automatically, so they are listed under rollupOptions.external.
export default defineConfig({
  plugins: [vue()],
  // Keep import.meta.env.PROD unresolved in dist so the consuming view's own
  // build decides the dev/prod switch in authService.
  define: {
    'import.meta.env.PROD': 'import.meta.env.PROD',
  },
  build: {
    // per-entry CSS: the workflow-execution entry emits its own stylesheet
    cssCodeSplit: true,
    lib: {
      // the vjsf-free main index + the vjsf-dependent workflow-execution entry
      entry: {
        index: fileURLToPath(new URL('./src/index.ts', import.meta.url)),
        workflowExecution: fileURLToPath(new URL('./src/workflowExecution.ts', import.meta.url)),
      },
      formats: ['es'],
      fileName: (_format, name) => `${name}.js`,
    },
    rollupOptions: {
      // vjsf's CSS subpath is deliberately NOT externalized so it bundles into
      // workflowExecution.css.
      external: [
        'vue', /^vue\//, 'vuetify', /^vuetify\//, 'axios', '@kyvg/vue3-notification', 'pinia',
        '@koumoul/vjsf', '@koumoul/vjsf/compat/v2',
      ],
    },
  },
})
