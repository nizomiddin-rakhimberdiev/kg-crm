/**
 * Topbar'da tanlangan filial — React'dan tashqarida ham (API modullarida).
 *
 * `BranchProvider` har o'zgarishda shu yerga yozadi. Saqlanmaydi: sahifa
 * yangilansa "Barcha filiallar" bilan boshlanadi — provider bilan bir xil.
 */

let current: string | null = null

export const branchScope = {
  get: (): string | null => current,
  set: (id: string | null): void => {
    current = id
  },
}

/**
 * Filialga bog'langan yozuvni YARATISH so'roviga tanlangan filialni qo'shadi.
 *
 * Nega kerak: bir nechta filialli bog'chada ega "Gorkiy" filialini tanlab
 * tarif yoki guruh qo'shsa, backend qaysi filial ekanini bilishi shart
 * (`resolve_branch`). Avval ko'p formalar filialni umuman yubormasdi —
 * ega filialni tanlagan bo'lsa ham `422` olardi.
 *
 * Ochiq yordamchi, yashirin interceptor emas: qaysi so'rov filialni olib
 * ketishi chaqiruv joyida ko'rinib tursin. Filial tanlanmagan bo'lsa kalit
 * qo'shilmaydi — backend o'zi aniqlaydi (bitta filial yoki filialga
 * bog'langan xodim). Aniq `branch_id` berilgan so'rov o'zgarmaydi.
 */
export function withBranch<T extends object>(payload: T): T & { branch_id?: string } {
  const explicit = (payload as { branch_id?: string | null }).branch_id
  if (explicit) return payload
  return current ? { ...payload, branch_id: current } : payload
}
