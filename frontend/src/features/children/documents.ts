/**
 * Shartnoma faylini brauzerda oldindan tekshirish (2026-10-21) — tez javob
 * uchun. Oxirgi so'z serverda: u fayl ICHIDAGI imzoni ham ko'radi.
 */

import { DOCUMENT_SUFFIXES, MAX_DOCUMENT_BYTES } from '@/features/children/api'
import { t } from '@/lib/i18n'

export function documentProblem(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!DOCUMENT_SUFFIXES.some((suffix) => name.endsWith(suffix))) {
    return t('Faqat PDF, DOC yoki DOCX fayl biriktiriladi.')
  }
  if (file.size > MAX_DOCUMENT_BYTES) return t('Fayl 10 MB dan kichik boʻlishi kerak.')
  return null
}
