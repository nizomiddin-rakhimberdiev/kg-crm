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

export const TENANT_PREFIX = 't'

/** `/t/quyosh/dashboard` → `quyosh`. Prefiks bo'lmasa `null`. */
export function slugFromPath(pathname: string = window.location.pathname): string | null {
  const [prefix, slug] = pathname.split('/').filter(Boolean)
  return prefix === TENANT_PREFIX && slug ? slug : null
}

/** React Router uchun `basename`. */
export function basenameFor(slug: string | null): string {
  return slug ? `/${TENANT_PREFIX}/${slug}` : '/'
}

/** Boshqa bog'cha manziliga to'liq yo'l. */
export function tenantPath(slug: string, path = '/dashboard'): string {
  return `/${TENANT_PREFIX}/${slug}${path}`
}

/**
 * Sahifa yuklanganidagi slug — bir marta hisoblanadi.
 *
 * `basename` router yaratilganda o'rnatiladi va keyin o'zgarmaydi,
 * shuning uchun boshqa bog'chaga o'tish TO'LIQ sahifa yangilanishini
 * talab qiladi (`window.location`). Bu kamchilik emas: ikki bog'cha —
 * ikki alohida sessiya, va ular orasida hech narsa qolmagani ma'qul.
 */
export const currentSlug = slugFromPath()
