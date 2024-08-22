import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from "vite-plugin-vuetify";


// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    mimeTypes: {
      'application/typescript': ['ts']
    }
  }
})


// Plugins
// import vue from "@vitejs/plugin-vue";
// import vuetify, { transformAssetUrls } from "vite-plugin-vuetify";

// Utilities
// import { defineConfig } from "vite";
// import { fileURLToPath, URL } from "node:url";

// https://vitejs.dev/config/
// export default defineConfig({
//   plugins: [
//     vue({
//       template: { transformAssetUrls },
//     }),
//     // https://github.com/vuetifyjs/vuetify-loader/tree/next/packages/vite-plugin
//     vuetify({
//       autoImport: true,
//     }),
//   ],
//   define: { "process.env": {} },
//   base: "/persistence",
//   resolve: {
//     alias: {
//       "@": fileURLToPath(new URL("./src", import.meta.url)),
//     },
//     extensions: [".js", ".json", ".jsx", ".mjs", ".ts", ".tsx", ".vue"],
//   },
//   server: {
//     port: 3000,
//   },
// });
