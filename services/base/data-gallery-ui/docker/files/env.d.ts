/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_KAAPANA_BACKEND_ENDPOINT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
