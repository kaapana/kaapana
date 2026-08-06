/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_KAAPANA_BACKEND_ENDPOINT: string
  readonly VITE_NOTIFICATIONS_API_ENDPOINT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
