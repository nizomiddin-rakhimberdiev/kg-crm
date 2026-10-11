/**
 * Parolning minimal uzunligi — BITTA joyda (PLAN 11.10).
 *
 * Ilgari uchta raqam yashardi: backend 8 (Django sukuti), profil
 * sahifasi 10, qolgan uchta parol oʻrnatish ekranida esa umuman
 * tekshiruv yoʻq edi. Oxirgisi eng yomoni — odam parol yozadi,
 * tugmani bosadi va serverdan tushunarsiz xato oladi.
 *
 * Raqam backend bilan bogʻlangan: `src/__tests__/password.test.ts`
 * uni `config/settings/base.py` dagi `min_length` bilan solishtiradi,
 * yaʼni ikkalasi ajralib keta olmaydi.
 *
 * Nega 12: tizim bolalarning shaxsiy maʼlumotini va pulni saqlaydi,
 * OWASP ASVS shunday ilova uchun 12 ni talab qiladi. Murakkablik
 * qoidasi ataylab yoʻq — aynan u parolni qogʻozga yozishga majbur
 * qiladi, uzunlik esa qilmaydi.
 */

export const MIN_PASSWORD_LENGTH = 12

/** Yozilayotgan parol hali kaltami? Boʻsh maydon "kalta" emas. */
export const passwordTooShort = (value: string): boolean =>
  value.length > 0 && value.length < MIN_PASSWORD_LENGTH
