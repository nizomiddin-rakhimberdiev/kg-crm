/**
 * "Bu bola allaqachon bormi?" — qaror qoidasi (audit, 2026-10-21).
 *
 * Ogohlantirish BLOKLAMAYDI: egizaklarda ism va tugʻilgan sana
 * haqiqatan bir xil boʻlishi mumkin (PLAN 2.3). Lekin u ikki holatda
 * jim qolardi va shuning uchun bazada bir xil bolalar paydo boʻldi:
 *
 *  1. Tugʻilgan sana TALAB qilinardi — sanasiz kiritilgan (yoki
 *     importdan kelgan) bola hech qachon ogohlantirish bermasdi.
 *  2. Taqqoslash ekranda turgan sahifadagi 25 qatorga qarardi, ya'ni
 *     uchinchi sahifadagi bir xil bola koʻrinmasdi.
 *
 * Ikkinchisi chaqiruvchining ishi (serverdan ism boʻyicha qidirish);
 * birinchisi shu yerda: sana yetishmasa, ogohlantirish YOʻQOLMAYDI —
 * faqat ohangi yumshaydi.
 */

export interface DuplicateCandidate {
  id: string
  first_name: string
  last_name: string
  date_of_birth: string | null
  full_name: string
}

export interface DuplicateHit {
  child: DuplicateCandidate
  /** `same_birth_date` — ism ham, sana ham mos; `name_only` — sana noma'lum. */
  certainty: 'same_birth_date' | 'name_only'
}

interface FormNames {
  first_name: string
  last_name: string
  date_of_birth: string
}

const same = (left: string, right: string) =>
  left.trim().toLocaleLowerCase() === right.trim().toLocaleLowerCase()

export function findDuplicate(
  candidates: readonly DuplicateCandidate[],
  form: FormNames,
): DuplicateHit | null {
  if (!form.first_name.trim() || !form.last_name.trim()) return null

  let weak: DuplicateHit | null = null
  for (const child of candidates) {
    if (!same(child.first_name, form.first_name) || !same(child.last_name, form.last_name)) {
      continue
    }
    // Ikkalasining sanasi bor va ular boshqa — bu boshqa bola.
    if (child.date_of_birth && form.date_of_birth) {
      if (child.date_of_birth === form.date_of_birth) {
        return { child, certainty: 'same_birth_date' }
      }
      continue
    }
    // Sana noma'lum: ism mosligi ham yetarli sabab — lekin aniq
    // moslik topilsa, u ustun turadi, shuning uchun saqlab qoʻyamiz.
    weak ??= { child, certainty: 'name_only' }
  }
  return weak
}
