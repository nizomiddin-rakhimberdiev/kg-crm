/**
 * Tiplashtirilgan muhit o'zgaruvchilari (docs/05 §17).
 *
 * `import.meta.env` ga faqat shu yerdan murojaat qilinadi — shunda
 * yetishmayotgan o'zgaruvchi ilova butun boshli ishlagandan keyin emas,
 * boot paytida aniqlanadi.
 */

const required = (key: string, value: string | undefined, fallback?: string): string => {
  const resolved = value ?? fallback
  if (!resolved) {
    throw new Error(`Muhit o'zgaruvchisi yetishmayapti: ${key}`)
  }
  return resolved
}

/**
 * Deploy rejimi — backenddagi `apps/core/deployment.py` bilan JUFT
 * (docs/02 ADR-13). Ikkalasi bir xil `.env` dan oziqlanishi shart:
 * frontend "obuna yo'q" deb ko'rsatib, backend uni talab qilsa,
 * foydalanuvchi sababi ko'rinmaydigan `402` ga urilardi.
 *
 * Build VAQTIDA yoziladi (Vite `import.meta.env`), runtime'da emas —
 * shuning uchun rejim o'zgarsa SPA qayta yig'ilishi kerak.
 */
const deploymentMode =
  import.meta.env.VITE_DEPLOYMENT_MODE === 'standalone' ? 'standalone' : 'saas'

export const env = {
  apiBaseUrl: required(
    'VITE_API_BASE_URL',
    import.meta.env.VITE_API_BASE_URL,
    'http://127.0.0.1:8000/api/v1',
  ),
  deploymentMode,
  /** Bitta bog'cha uchun alohida o'rnatilgan nusxa (ADR-13). */
  isStandalone: deploymentMode === 'standalone',
  // Public saytdan CRM'ga o'tish bitta joyda sozlanadi. Build paytida
  // yoziladi; productionda `https://app.radix-crm.uz` bo'ladi.
  appUrl: required('VITE_APP_URL', import.meta.env.VITE_APP_URL, window.location.origin),
  publicHost: import.meta.env.VITE_PUBLIC_HOST ?? 'radix-crm.uz',
  legalEntityName: import.meta.env.VITE_LEGAL_ENTITY_NAME ?? '',
  isDev: import.meta.env.DEV,
} as const
