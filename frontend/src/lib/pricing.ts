/**
 * Radix obunasining narxi — YAGONA formula (PLAN 1.11).
 *
 * Auditda platforma konsolidagi "Taxminiy oylik" 42 bolali bog'chaga
 * ham, 0 bolaliga ham 500 000 ko'rsatdi. Sabab: sahifa narxni o'zi
 * hisoblardi (`const base = 500_000`, `steps * 80_000`) — ya'ni
 * tizimda narxning ikkinchi nusxasi bor edi va u ADR-12 dan oldingi
 * ishga tushirish narxida qotib qolgan edi.
 *
 * **Haqiqat manbai — backend** (`apps/subscriptions/pricing.py`).
 * Mijozga yuboriladigan hisob o'sha yerda hisoblanadi va saytdagi
 * kalkulyator ham `/public/pricing` orqali o'shani so'raydi. Bu fayl
 * faqat vendor konsolidagi TAXMIN uchun: u ro'yxatdagi o'nlab
 * bog'chaning har biri uchun server so'rovini kutmasligi kerak.
 *
 * Shuning uchun formulaning to'g'riligini test qo'riqlaydi
 * (`features/platform/__tests__/pricing.test.ts`), plan qiymatlari esa
 * backenddagi `subscription_plan` qatori bilan bir xil bo'lishi kerak.
 */

/** ADR-12 (2026-09-16): 400 000 / 50 bola, har boshlangan 10 bolaga +50 000. */
export const PLAN = {
  basePrice: 400_000,
  includedChildren: 50,
  overageStepChildren: 10,
  overageStepPrice: 50_000,
} as const

export type PricingPlan = typeof PLAN

/**
 * Hisoblanadigan bolalar soni.
 *
 * Kiritilgan son bir vaqtning o'zida eng past chegara: 12 bolasi bor
 * bog'cha ham bazani to'laydi. Bu chegirma emas, daromad poli —
 * xizmatning o'zi bolalar soniga qarab arzonlashmaydi.
 */
export const billableChildren = (children: number, plan: PricingPlan = PLAN): number =>
  Math.max(Math.trunc(children) || 0, plan.includedChildren)

/**
 * Ortiqcha qadamlar — TEPAGA yaxlitlanadi.
 *
 * Bitta ortiqcha bola ham to'liq qadamni yoqadi. Aks holda 51 va 59
 * bola bir xil to'lardi, keyin 60-bolada hisob birdan sakrardi.
 */
export const overageSteps = (children: number, plan: PricingPlan = PLAN): number => {
  const extra = Math.max(0, billableChildren(children, plan) - plan.includedChildren)
  return Math.ceil(extra / plan.overageStepChildren)
}

/** Bir oylik to'lov (chegirmasiz). */
export const monthlyEstimate = (children: number, plan: PricingPlan = PLAN): number =>
  plan.basePrice + overageSteps(children, plan) * plan.overageStepPrice
