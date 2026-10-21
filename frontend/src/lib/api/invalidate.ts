/**
 * Mutatsiyadan keyin nimani yangilash kerak — BITTA joyda (PLAN 1.5).
 *
 * Auditda "Hisob-faktura chiqarish" bosilgandan keyin doska eski
 * holida qolardi, chiqim tasdiqlangach "Shu oy (tasdiqlangan)" nol
 * bo'lib turaverardi. Sabab har safar bir xil: mutatsiya o'zi bilgan
 * bir-ikkita kalitni yangilardi, lekin pul BIR JOYDAN o'zgarib, O'NTA
 * ekranga ta'sir qiladi.
 *
 * Shuning uchun ro'yxat komponentda emas, shu yerda. Yangi ekran
 * qo'shilganda uni bitta joyga yozish yetadi va hech bir mutatsiya uni
 * "unutib" qolmaydi.
 *
 * Nega keng qamrov: TanStack Query faqat EKRANDA turgan so'rovlarni
 * qayta yuklaydi, qolganlari shunchaki "eskirgan" deb belgilanadi.
 * Ya'ni ortiqcha kalit qo'shishning narxi deyarli nol, tushib qolgan
 * kalitning narxi esa — ekranda turgan noto'g'ri raqam.
 */

import type { QueryClient } from '@tanstack/react-query'

/** Pul o'zgarganda ta'sirlanadigan barcha domenlar. */
const MONEY_DOMAINS = [
  'invoices',
  'payments',
  'debtors',
  'children', // bola kartasidagi balans
  'cash', // kassa qoplari
  'dashboard', // bosh sahifadagi ko'rsatkichlar
  'reports', // tushum/chiqim/foyda
  'insights', // Radix AI brifingi
  'ledger',
  'expenses',
  'payroll',
  // Ombor kalitlari `queryKeys` da `inventory` ostida EMAS — ular
  // alohida: `products`, `warehouses`, `movements`. Ilgari bu yerda
  // faqat `inventory` turardi, ya'ni mahsulot qo'shilgandan keyin
  // ro'yxat yangilanmasdi va foydalanuvchi ikkinchi marta bosardi
  // (audit, 2026-10-21). `inventory` ham qoladi: chiqim formasidagi
  // yetkazib beruvchilar ro'yxati shu prefiks bilan keladi.
  'inventory',
  'products',
  'warehouses',
  'movements',
  // Tarif o'zgarsa bolaga chiqadigan summa o'zgaradi.
  'tariffs',
] as const

/** Davomat o'zgarganda — qayta hisob hisob-fakturaga tushadi (ADR-19). */
const ATTENDANCE_DOMAINS = [
  'attendance',
  'absence-claims',
  'holidays',
  'invoices',
  'children',
  'debtors',
  'dashboard',
  'insights',
] as const

function invalidateDomains(
  queryClient: QueryClient,
  organizationId: string,
  domains: readonly string[],
): void {
  for (const domain of domains) {
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, domain] })
  }
}

/**
 * To'lov, qaytarish, hisob-faktura, chiqim, ombor harakati, oylik —
 * pulni qimirlatadigan HAR QANDAY amaldan keyin.
 */
export function invalidateMoney(queryClient: QueryClient, organizationId: string): void {
  invalidateDomains(queryClient, organizationId, MONEY_DOMAINS)
}

/** Davomat, bayram va kelmagan kunlar uchun qayta hisobdan keyin. */
export function invalidateAttendance(queryClient: QueryClient, organizationId: string): void {
  invalidateDomains(queryClient, organizationId, ATTENDANCE_DOMAINS)
}
