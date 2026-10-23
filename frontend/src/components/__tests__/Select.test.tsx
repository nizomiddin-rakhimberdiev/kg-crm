/**
 * Tanlagich (mijoz eʼtirozi, 2026-10-23).
 *
 * Ilovadagi 86 ta `<select>` har biri oʻz klassi bilan yozilgan edi:
 * balandligi har xil, fokus halqasi baʼzisida bor baʼzisida yoʻq,
 * strelkasi esa brauzerniki — ya'ni Chrome'da bir xil, Safari'da
 * boshqacha. Mijoz buni "umuman standart xolatda emas" deb yozdi.
 *
 * Yechim **native `<select>` ning oʻzi**, faqat kiyimi bizniki
 * (`appearance-none` + oʻz strelkamiz). Sabab `DateInput` dagi bilan
 * bir xil: klaviatura, harf bilan qidirish, skrinrider va telefondagi
 * tizim tanlagichi — bularning hammasi native elementdan BEPUL
 * keladi, qayta yozilgan ro'yxat esa ularning har birini yoʻqotadi.
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { Building2 } from 'lucide-react'
import { describe, expect, it, vi } from 'vitest'
import { Select } from '../ui/Select'

describe('Select', () => {
  it('native `select` boʻlib qoladi — roli ham, qiymati ham', () => {
    render(
      <Select aria-label="Guruh" value="b" onChange={vi.fn()}>
        <option value="a">Birinchi</option>
        <option value="b">Ikkinchi</option>
      </Select>,
    )
    const field = screen.getByRole('combobox', { name: 'Guruh' }) as HTMLSelectElement
    expect(field.tagName).toBe('SELECT')
    expect(field.value).toBe('b')
  })

  it('tanlov chaqiruvchiga uzatiladi', () => {
    const onChange = vi.fn()
    render(
      <Select aria-label="Guruh" value="a" onChange={onChange}>
        <option value="a">Birinchi</option>
        <option value="b">Ikkinchi</option>
      </Select>,
    )
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'b' } })
    expect(onChange).toHaveBeenCalled()
  })

  it('guruhlangan roʻyxat (`optgroup`) ishlaydi', () => {
    render(
      <Select aria-label="Toifa" defaultValue="meat">
        <optgroup label="Oziq-ovqat">
          <option value="meat">Goʻsht</option>
        </optgroup>
      </Select>,
    )
    expect(screen.getByRole('group', { name: 'Oziq-ovqat' })).toBeTruthy()
  })

  it('strelka sichqonchani ushlab qolmaydi', () => {
    const { container } = render(
      <Select aria-label="Guruh">
        <option value="a">Birinchi</option>
      </Select>,
    )
    const chevron = container.querySelector('svg')
    expect(chevron?.getAttribute('aria-hidden')).toBe('true')
    expect(chevron?.parentElement?.className).toContain('pointer-events-none')
  })

  it('oʻchirilgan maydon oʻqilishi mumkin, lekin tanlanmaydi', () => {
    render(
      <Select aria-label="Guruh" disabled>
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect((screen.getByRole('combobox') as HTMLSelectElement).disabled).toBe(true)
  })

  it('yonidagi matn maydoni bilan bir xil balandlik', () => {
    render(
      <Select aria-label="Guruh">
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(screen.getByRole('combobox').className).toContain('h-10')
  })

  it('zich qator uchun kichik oʻlcham', () => {
    render(
      <Select aria-label="Guruh" size="sm">
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(screen.getByRole('combobox').className).toContain('h-9')
  })
})

describe('Select kengligi', () => {
  it('sukut boʻyicha oʻrash butun kenglikni oladi', () => {
    const { container } = render(
      <Select aria-label="Guruh">
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(container.firstElementChild?.className).toContain('w-full')
  })

  it('chaqiruvchining kengligi ustun turadi', () => {
    const { container } = render(
      <Select aria-label="Guruh" className="w-28">
        <option value="a">Birinchi</option>
      </Select>,
    )
    const cls = container.firstElementChild?.className ?? ''
    expect(cls).toContain('w-28')
    expect(cls).not.toContain('w-full')
  })
})

describe('Select belgisi', () => {
  it('chap belgi qoʻyilganda matn uning ostiga kirmaydi', () => {
    const { container } = render(
      <Select aria-label="Filial" icon={Building2}>
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(screen.getByRole('combobox').className).toContain('pl-9')
    // Ikkita belgi: chapdagi bino va oʻngdagi strelka.
    expect(container.querySelectorAll('svg')).toHaveLength(2)
  })

  it('belgisiz holatda faqat strelka qoladi', () => {
    const { container } = render(
      <Select aria-label="Filial">
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(screen.getByRole('combobox').className).toContain('pl-3')
    expect(container.querySelectorAll('svg')).toHaveLength(1)
  })
})
