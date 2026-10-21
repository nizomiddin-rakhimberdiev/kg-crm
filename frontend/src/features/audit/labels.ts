/**
 * Audit jurnalidagi yorliqlar — amal, obyekt turi va maydon nomlari.
 *
 * Komponentdan ALOHIDA, chunki ular backend bilan yonma-yon turishi
 * kerak: yorligʻi yoʻq qiymat jurnalda XOM koʻrinadi. Auditda bir
 * ustunda ikki til turardi — "view" va "Yangilandi" (2026-10-21), va
 * sabab shu edi: backend yangi amal yozdi, yorliq qoʻshilmadi.
 * `__tests__/labels.test.ts` endi buni backend manbasi bilan
 * solishtiradi.
 */

import { t } from '@/lib/i18n'

export const ACTION_LABELS: Record<string, [string, string]> = {
  login: [t('Kirish'), 'bg-slate-100 text-slate-600'],
  login_failed: [t('Kirish urinishi'), 'bg-amber-50 text-amber-700'],
  // Xavfsizlik hodisalari (PLAN 5.2, 5.3, 5.5). Ular jadvalda XOM
  // nom bilan chiqib turardi: `ACTION` da yo'q qiymat shunchaki
  // o'zini ko'rsatadi, va o'qiyotgan odam uchun `login_blocked`
  // hech narsa demaydi.
  login_blocked: [t('Kirish bloklandi'), 'bg-red-50 text-red-700'],
  password_reset_requested: [t('Parol tiklash soʻraldi'), 'bg-amber-50 text-amber-700'],
  password_reset: [t('Parol tiklandi'), 'bg-amber-50 text-amber-700'],
  invite_accepted: [t('Taklif qabul qilindi'), 'bg-emerald-50 text-emerald-700'],
  two_factor_enabled: [t('2FA yoqildi'), 'bg-emerald-50 text-emerald-700'],
  two_factor_disabled: [t('2FA oʻchirildi'), 'bg-red-50 text-red-700'],
  two_factor_backup_used: [t('Zaxira kodi ishlatildi'), 'bg-amber-50 text-amber-700'],
  two_factor_codes_renewed: [t('Zaxira kodlari yangilandi'), 'bg-amber-50 text-amber-700'],
  logout: [t('Chiqish'), 'bg-slate-100 text-slate-600'],
  signup: [t('Roʻyxatdan oʻtish'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  password_change: [t('Parol oʻzgardi'), 'bg-amber-50 text-amber-700'],
  create: [t('Yaratildi'), 'bg-emerald-50 text-emerald-700'],
  update: [t('Yangilandi'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  delete: [t('Oʻchirildi'), 'bg-red-50 text-red-700'],
  // Bosqich 13.5–13.6: hisobotni topshirish va ochilishi. Ilgari
  // ular yorliqsiz edi va jadvalda "view" deb turardi.
  approve: [t('Tasdiqlandi'), 'bg-emerald-50 text-emerald-700'],
  reject: [t('Rad etildi'), 'bg-red-50 text-red-700'],
  view: [t('Koʻrildi'), 'bg-slate-100 text-slate-600'],
}

export const ENTITY_LABELS: Record<string, string> = {
  child: t('Bola'),
  enrollment: t('Guruhga biriktirish'),
  group: t('Guruh'),
  guardian: t('Vasiy'),
  employee: t('Xodim'),
  product: t('Mahsulot'),
  tariff: t('Tarif'),
  cash_account: t('Kassa'),
  absence_claim: t('Kelmagan kun daʼvosi'),
  notification: t('Bildirishnoma'),
  notification_template: t('Xabar shabloni'),
  subscription: t('Obuna'),
  support_grant: t('Qoʻllab-quvvatlash ruxsati'),
  child_import: t('Bolalar importi'),
  payment: t('Toʻlov'),
  invoice: t('Hisob-faktura'),
  invoice_run: t('Hisob-faktura generatsiyasi'),
  discount: t('Chegirma'),
  expense: t('Chiqim'),
  stock_movement: t('Stok harakati'),
  system_setting: t('Sozlama'),
  user: t('Foydalanuvchi'),
  role: t('Rol'),
  branch: t('Filial'),
  organization: t('Tashkilot'),
  payroll_run: t('Oylik hisoblash'),
  // Qolgan turlar — backendda yoziladigan hammasi. Roʻyxat
  // `__tests__/labels.test.ts` bilan toʻliq saqlanadi.
  absence_kind: t('Kelmaslik turi'),
  bank_statement: t('Bank koʻchirmasi'),
  bank_statement_line: t('Koʻchirma qatori'),
  budget: t('Byudjet'),
  cash_count: t('Kassa sanogʻi'),
  cash_handover: t('Kassani topshirish'),
  cash_transfer: t('Hisoblar orasida oʻtkazma'),
  child_document: t('Bola hujjati'),
  child_guardian: t('Bola va vasiy bogʻlanishi'),
  child_pause: t('Joyni saqlash'),
  employee_advance: t('Xodimga avans'),
  insight: t('Tahlil xulosasi'),
  invoice_write_off: t('Qarzni hisobdan chiqarish'),
  journal: t('Buxgalteriya jurnali'),
  lead: t('Murojaat'),
  merchant_credential: t('Toʻlov tizimi kaliti'),
  money_operation: t('Pul amali'),
  month_close: t('Oyni yopish'),
  payment_fiscal: t('Fiskal chek'),
  payment_settlement: t('Toʻlovni hisobga olish'),
  platform_user: t('Platforma xodimi'),
  refresh_token: t('Sessiya kaliti'),
  refund: t('Pul qaytarish'),
  report_annual: t('Yillik hisobot'),
  report_pack: t('Oylik hisobot toʻplami'),
  report_review: t('Hisobotni topshirish'),
  report_share_link: t('Hisobot havolasi'),
  report_snapshot: t('Hisobot surati'),
  setting: t('Sozlama'),
  subscription_payment: t('Obuna toʻlovi'),
  support_session: t('Qoʻllab-quvvatlash sessiyasi'),
  tax_obligation: t('Soliq majburiyati'),
  tax_preset: t('Soliq rejimi namunasi'),
}

/**
 * Oʻzgargan maydonning nomi — odam tilida (PLAN 4.4).
 *
 * Auditda bu ustun `status: "archived", reason: "…"` koʻrinishida
 * edi: inglizcha kalit va JSON. Jurnalni mudira oʻqiydi, va u
 * maydon nomlarini bilishi kerak emas.
 */
export const FIELD_LABELS: Record<string, string> = {
  status: t('Holat'),
  reason: t('Sabab'),
  amount: t('Summa'),
  name: t('Nomi'),
  from: t('Nimadan'),
  to: t('Nimaga'),
  before: t('Oldin'),
  after: t('Keyin'),
  child: t('Bola'),
  group: t('Guruh'),
  guardian: t('Vasiy'),
  employee: t('Xodim'),
  product: t('Mahsulot'),
  tariff: t('Tarif'),
  invoice: t('Hisob-faktura'),
  payment: t('Toʻlov'),
  cash_account: t('Kassa'),
  role: t('Rol'),
  method: t('Usul'),
  direction: t('Yoʻnalish'),
  movement_type: t('Harakat turi'),
  fields: t('Maydonlar'),
  permissions: t('Ruxsatlar'),
  archived: t('Arxivlangan'),
  reactivated: t('Qayta faollashtirilgan'),
  reversed: t('Qaytarilgan'),
  revoked: t('Bekor qilingan'),
  suspended: t('Toʻxtatilgan'),
  forced: t('Majburan'),
  days: t('Kunlar'),
  until: t('Qachongacha'),
  expires_at: t('Amal qilish muddati'),
  total_net: t('Sof summa'),
  payouts: t('Toʻlovlar soni'),
  created: t('Yaratildi'),
  skipped: t('Oʻtkazib yuborildi'),
  recalculated: t('Qayta hisoblandi'),
  email: t('Email'),
  slug: t('Manzil nomi'),
  severity: t('Jiddiylik'),
  kind: t('Turi'),
  type: t('Turi'),
  telegram: t('Telegram'),
  self_profile: t('Oʻz profili'),
  sessions_closed: t('Yopilgan sessiyalar'),
  password_reset: t('Parol tiklandi'),
  invite_accepted: t('Taklif qabul qilindi'),
  backup_codes: t('Zaxira kodlari'),
  remaining: t('Qolgani'),
  factor: t('Omil'),
  trial_extended_days: t('Sinov uzaytirildi (kun)'),
  n: t('Soni'),
  batch: t('Partiya'),
  credit: t('Kredit'),
  movement: t('Harakat'),
  id: t('Identifikator'),
  key: t('Kalit'),
  reopened_from: t('Qaytib ochildi'),
}

/** JSON emas, odam oʻqiydigan qiymat. */
export function fieldValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? t('ha') : t('yoʻq')
  if (Array.isArray(value)) return value.map((item) => fieldValue(item)).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
