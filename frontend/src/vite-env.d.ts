/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  /** `saas` (sukut) yoki `standalone` — docs/02 ADR-13. */
  readonly VITE_DEPLOYMENT_MODE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
