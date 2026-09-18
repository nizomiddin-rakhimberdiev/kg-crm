import type { Locale } from './content'

/** Sinov sahifasi manzillari — asosiy landing'dan alohida. */
export const ROOT = '/test-redesign'

export const basePath = (locale: Locale) => (locale === 'uz' ? ROOT : `${ROOT}/ru`)
