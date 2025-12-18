import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import type { Plugin } from 'vite'

export default defineConfig(() => ({
  base: "/workflow-ui",
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
    allowedHosts: ["e230-pc25.inet.dkfz-heidelberg.de"],
    port: 5173,
    host: true,
    strictPort: true,
    hmr: {
      protocol: 'wss',
      // Use clientPort so the browser connects to 443 through Traefik;
      // Vite still listens internally on 5173 and is proxied
      clientPort: 443,
      path: '/workflow-ui/@vite',
    },
  },
  build: {
    outDir: 'dist',
  },
}))
