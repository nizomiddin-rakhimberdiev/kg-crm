/**
 * Dublikat bola ogohlantirishi (audit, 2026-10-21).
 *
 * Auditda ogohlantirish ishladi, lekin bazada uchta bir xil bola bor
 * edi — "boshqa yoʻl bilan kirgan, ehtimol tugʻilgan sana boʻsh
 * boʻlgan". Ikkita teshik bor edi: tekshiruv tugʻilgan sanani TALAB
 * qilardi, va u faqat ekranda turgan sahifadagi 25 qatorga qarardi.
 *
 * Bu yerda ikkinchi qism — qaror qoidasi. Birinchisi (serverdan
 * qidirish) `ChildrenPage` da.
 */

import { describe, expect, it } from 'vitest'
import { findDuplicate } from '@/features/children/duplicates'

const row = (
  first: string,
  last: string,
  date_of_birth: string | null,
  id = `${first}-${last}`,
) => ({ id, first_name: first, last_name: last, date_of_birth, full_name: `${last} ${first}` })

describe('findDuplicate', () => {
  it('ism va sana bir xil — aniq ogohlantirish', () => {
    const hit = findDuplicate([row('Ali', 'Valiyev', '2021-03-14')], {
      first_name: 'ali',
      last_name: ' Valiyev ',
      date_of_birth: '2021-03-14',
    })
    expect(hit?.certainty).toBe('same_birth_date')
  })

  it('ism bir xil, sana boshqa — bu boshqa bola', () => {
    expect(
      findDuplicate([row('Ali', 'Valiyev', '2021-03-14')], {
        first_name: 'Ali',
        last_name: 'Valiyev',
        date_of_birth: '2022-01-01',
      }),
    ).toBeNull()
  })

  it('bazadagi bolaning sanasi yoʻq — baribir ogohlantiradi', () => {
    const hit = findDuplicate([row('Ali', 'Valiyev', null)], {
      first_name: 'Ali',
      last_name: 'Valiyev',
      date_of_birth: '2021-03-14',
    })
    expect(hit?.certainty).toBe('name_only')
  })

  it('formada sana hali kiritilmagan — baribir ogohlantiradi', () => {
    const hit = findDuplicate([row('Ali', 'Valiyev', '2021-03-14')], {
      first_name: 'Ali',
      last_name: 'Valiyev',
      date_of_birth: '',
    })
    expect(hit?.certainty).toBe('name_only')
  })

  it('ism toʻliq kiritilmagan — hech narsa aytmaydi', () => {
    expect(
      findDuplicate([row('Ali', 'Valiyev', '2021-03-14')], {
        first_name: 'Ali',
        last_name: '',
        date_of_birth: '2021-03-14',
      }),
    ).toBeNull()
  })

  it('aniq moslik ism-moslikdan ustun', () => {
    const hit = findDuplicate(
      [row('Ali', 'Valiyev', null, 'a'), row('Ali', 'Valiyev', '2021-03-14', 'b')],
      { first_name: 'Ali', last_name: 'Valiyev', date_of_birth: '2021-03-14' },
    )
    expect(hit?.child.id).toBe('b')
    expect(hit?.certainty).toBe('same_birth_date')
  })
})
