/**
 * Bolaning yoshi guruhning oraligʻiga tushadimi (audit, 2026-10-21).
 *
 * Guruhda "1–3 yosh" yozilgan boʻlsa ham 4 yoshli bola jimgina
 * qoʻshilardi — maydon hech narsa qilmasdi va "nega u bor?" degan
 * savol javobsiz qolardi.
 *
 * **BLOKLAMAYDI.** Bogʻchada istisno koʻp: aka-ukani bir guruhda
 * qoldirish, joy yoʻqligi, oʻquv yili oʻrtasida oʻtish. Shuning uchun
 * javob — ogohlantirish: qaror mudiraning oʻzida qoladi.
 */

interface AgeRange {
  age_min?: number | null
  age_max?: number | null
}

/** Toʻlgan yosh (tugʻilgan kun oʻtmagan boʻlsa bir kam); sanasiz — `null`. */
export function ageOnDate(dateOfBirth: string, on: Date = new Date()): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateOfBirth)) return null
  const [year, month, day] = dateOfBirth.split('-').map(Number)
  let age = on.getFullYear() - year
  const monthIndex = on.getMonth() + 1
  if (monthIndex < month || (monthIndex === month && on.getDate() < day)) age -= 1
  return age
}

export interface AgeMismatch {
  age: number
  min: number | null
  max: number | null
}

/** Oraliqdan tashqarida boʻlsa — yoshi va chegaralari; aks holda `null`. */
export function ageOutsideGroup(
  group: AgeRange,
  dateOfBirth: string,
  on: Date = new Date(),
): AgeMismatch | null {
  const min = group.age_min ?? null
  const max = group.age_max ?? null
  if (min === null && max === null) return null
  const age = ageOnDate(dateOfBirth, on)
  if (age === null) return null
  if ((min !== null && age < min) || (max !== null && age > max)) return { age, min, max }
  return null
}
