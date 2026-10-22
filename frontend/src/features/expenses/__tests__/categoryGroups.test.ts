/**
 * Chiqim toifalari — guruhlangan roʻyxat (audit, 2026-10-21).
 *
 * Toifalar bazada IKKI darajali ("Oziq-ovqat → Goʻsht"), lekin
 * tanlagichlarda yassi roʻyxat boʻlib chiqardi: 24 ta nom alifbo
 * tartibida ham emas, ota-toifasi ham koʻrinmaydi. Mudira ularning
 * orasidan kerakligini izlab yurardi.
 */

import { describe, expect, it } from 'vitest'
import { groupCategories } from '@/features/expenses/categoryGroups'

const row = (id: string, name: string, parent_name: string | null = null) => ({
  id,
  name,
  parent_name,
})

describe('groupCategories', () => {
  it('ota-toifa boʻyicha guruhlaydi', () => {
    const groups = groupCategories([
      row('1', 'Goʻsht', 'Oziq-ovqat'),
      row('2', 'Elektr', 'Kommunal'),
      row('3', 'Non', 'Oziq-ovqat'),
    ])
    expect(groups.map((group) => group.label)).toEqual(['Kommunal', 'Oziq-ovqat'])
    expect(groups[1].items.map((item) => item.name)).toEqual(['Goʻsht', 'Non'])
  })

  it('ota-toifasi yoʻqlari oxirida, oʻz guruhisiz', () => {
    const groups = groupCategories([row('1', 'Ijara'), row('2', 'Goʻsht', 'Oziq-ovqat')])
    expect(groups.map((group) => group.label)).toEqual(['Oziq-ovqat', ''])
    expect(groups[1].items.map((item) => item.name)).toEqual(['Ijara'])
  })

  it('guruhlar va ichidagilar alifbo tartibida', () => {
    const groups = groupCategories([
      row('1', 'Suv', 'Kommunal'),
      row('2', 'Gaz', 'Kommunal'),
      row('3', 'Bozor', 'Oziq-ovqat'),
    ])
    expect(groups[0].items.map((item) => item.name)).toEqual(['Gaz', 'Suv'])
  })

  it('boʻsh roʻyxat — boʻsh natija', () => {
    expect(groupCategories([])).toEqual([])
  })
})
