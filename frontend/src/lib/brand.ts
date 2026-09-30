/**
 * Brend ranglari — JS tomon uchun (Brendbuk 1.1 · 04).
 *
 * Tailwind sinflari yetmaydigan joylar uchun: Recharts diagrammalari,
 * inline `style`, canvas. Sinf yozib bo'ladigan joyda esa shu fayl
 * emas, `tailwind.config.js` dagi shkalalar ishlatiladi.
 *
 * Qattiq yozilgan `#6366f1` kabi qiymatlar aynan shu sababli qoldirilmadi:
 * ular Tailwind qamrovidan tashqarida edi va rebrendingda ekranlarda
 * ko'k bo'lib qolib ketardi.
 */

export const BRAND = {
  ildiz: '#12352F',
  nihol: '#2E9E6B',
  orik: '#F29B55',
  sut: '#F6F7F4',
  tosh: '#1B2421',
  /** Qarzdorlik ogohlantirishi — brend rangi emas, tizim ichida. */
  qarz: '#B45F1E',
} as const

/** Diagramma yuzalari — Tailwind shkalalaridan olingan oraliq qiymatlar. */
export const CHART = {
  grid: '#dde1db', // tosh-200
  axis: '#98a398', // tosh-400
  surface: '#ffffff',
  ildizMid: '#2f6257', // ildiz-500 — to'q yashil, och fonda o'qiladi
  niholSoft: '#79c4a4', // nihol-300
} as const

/**
 * Ketma-ket segmentlar uchun tartib — YORQINLIK bo'yicha almashadi
 * (yorqin yashil → deyarli qora yashil → o'rik → och yalpiz), shunda
 * yonma-yon turgan bo'laklar rangni ajratolmaydigan ko'z uchun ham
 * farq qiladi.
 */
export const CHART_SEQUENCE = [
  BRAND.nihol,
  BRAND.ildiz,
  BRAND.orik,
  CHART.niholSoft,
  CHART.ildizMid,
  BRAND.qarz,
] as const
