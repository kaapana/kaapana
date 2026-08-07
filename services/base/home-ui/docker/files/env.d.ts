/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_KAAPANA_BACKEND_ENDPOINT: string
  readonly VITE_APP_NOTIFICATIONS_API_ENDPOINT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module 'vue3-apexcharts'
