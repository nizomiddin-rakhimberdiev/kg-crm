/**
 * Bog'chaning manzili — frontenddagi YAGONA joy.
 *
 * Backenddagi `apps/core/tenant_address.py` bilan juft: u havolalarni
 * quradi (SMS, hisob-faktura), bu esa brauzerda ularni o'qiydi. Ikkalasi
 * bir xil shaklni biladi — `/t/<slug>` — va subdomenga o'tilganda
 * ikkalasi ham shu ikki fayldan o'zgaradi.
 *
 * MUHIM: bu manzil **tenant mexanizmi emas**. Tashkilot JWT ichidagi
 * `organization_id` dan aniqlanadi va uni Postgres RLS majburlaydi
 * (docs/04 §1). URL'dagi slug'ni hech kim ishonchli deb qabul qilmaydi:
 * `/t/beta/dashboard` ga kirgan alfa foydalanuvchisi beta ma'lumotini
 * KO'RMAYDI — u shunchaki o'z manziliga qaytariladi. Slug bu yerda
 * brending va kirish nuqtasi, ruxsat emas.
 */

import { env } from '@/config/env'

export const TENANT_PREFIX = 't'

/** `/t/quyosh/dashboard` → `quyosh`. Prefiks bo'lmasa `null`. */
export function slugFromPath(pathname: string = window.location.pathname): string | null {
  const [prefix, slug] = pathname.split('/').filter(Boolean)
  return prefix === TENANT_PREFIX && slug ? slug : null
}

/**
 * Ilova qaysi yo'ldan boshlanishi (Vite `base`).
 *
 * Odatda `/`. Demo nusxasi esa mavjud domenning bir qismida yashaydi
 * (`radix-crm.uz/private`) — o'shanda Vite `base` `/private/` bo'ladi
 * va React Router ham xuddi shu prefiksni bilishi kerak, aks holda
 * har bir ichki havola `/dashboard` ga (ya'ni SaaS saytiga) olib
 * ketardi.
 */
function appBasePath(): string {
  const base = import.meta.env.BASE_URL || '/'
  const trimmed = base.replace(/\/+$/, '')
  return trimmed || '/'
}

/** React Router uchun `basename`. */
export function basenameFor(slug: string | null): string {
  // Standalone'da bog'cha bitta va `/t/<slug>` prefiksi yo'q (ADR-13) —
  // ilova o'zi o'rnatilgan yo'lning ildizida yashaydi.
  if (env.isStandalone) {
    return appBasePath()
  }
  return slug ? `/${TENANT_PREFIX}/${slug}` : '/'
}

/** Boshqa bog'cha manziliga to'liq yo'l. */
export function tenantPath(slug: string, path = '/dashboard'): string {
  return `/${TENANT_PREFIX}/${slug}${path}`
}

/**
 * Kirishdan keyin foydalanuvchini o'z bog'chasi manziliga ko'chirish
 * kerakmi.
 *
 * Alohida funksiya, chunki bu qaror bir marta JIMGINA buzilgan: standalone
 * o'rnatmada ham ishlab, foydalanuvchini kirishi bilan `/t/<slug>` ga —
 * ya'ni butunlay boshqa o'rnatmaga — uloqtirgan. U yerda uning hisobi
 * yo'q, shuning uchun login sahifasi qaytadan ochilgan va tashqaridan bu
 * "parol noto'g'ri" bo'lib ko'ringan.
 */
/**
 * Sahifa yuklanganidagi slug — bir marta hisoblanadi.
 *
 * `basename` router yaratilganda o'rnatiladi va keyin o'zgarmaydi,
 * shuning uchun boshqa bog'chaga o'tish TO'LIQ sahifa yangilanishini
 * talab qiladi (`window.location`). Bu kamchilik emas: ikki bog'cha —
 * ikki alohida sessiya, va ular orasida hech narsa qolmagani ma'qul.
 */
// Prerender (Node) da `window` yo'q — sotuv sahifasi tenant'siz.
export const currentSlug = typeof window !== 'undefined' ? slugFromPath() : null

export function shouldLandOnTenantAddress(
  slug: string | null,
  atSlug: string | null = currentSlug,
): boolean {
  // Standalone: bog'cha bitta, manzil bitta — ko'chiradigan joy yo'q.
  if (env.isStandalone) return false
  return Boolean(slug) && slug !== atSlug
}
