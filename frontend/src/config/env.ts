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

export const env = {
  apiBaseUrl: required(
    'VITE_API_BASE_URL',
    import.meta.env.VITE_API_BASE_URL,
    'http://127.0.0.1:8000/api/v1',
  ),
  isDev: import.meta.env.DEV,
} as const
