// Plugins
import Components from 'unplugin-vue-components/vite'
import Vue from '@vitejs/plugin-vue'
import Vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'
import ViteFonts from 'unplugin-fonts/vite'
// Utilities
import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(() => ({
  plugins: [
    Vue({
      template: { transformAssetUrls },
    }),
    // https://github.com/vuetifyjs/vuetify-loader/tree/master/packages/vite-plugin#readme
    Vuetify({
      autoImport: true,
    }),
    Components(),
    ViteFonts({
      google: {
        families: [ {
          name: 'Roboto',
          styles: 'wght@100;300;400;500;700;900',
        }],
      },
    }),
  ],
  define: { 'process.env': {} },
  base: "/projects-ui",
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
    port: 5174,
    host: true,
  },
  build: {
    outDir: 'dist',
  },
}))
