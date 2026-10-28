/**
 * Tanlagich (mijoz eʼtirozi, 2026-10-23).
 *
 * Birinchi urinishda native `<select>` qoldirilgan edi — yopiq holati
 * chiroyli, lekin OCHILGANDA brauzer oʻzining tizim roʻyxatini
 * chizadi: macOS'da u qora, maydon USTIGA tushadigan menyu. Mijoz
 * aynan shuni koʻrsatdi: "pastdan dropdown koʻrinishida chiroyli
 * formada chiqishi kk emasmidi?".
 *
 * Shuning uchun roʻyxatni oʻzimiz chizamiz. Lekin native elementdan
 * keladigan narsalar YOʻQOLMASLIGI kerak, va shu testlar aynan
 * ularni qoʻriqlaydi: klaviatura, harf bilan qidirish, `optgroup`,
 * oʻchirilgan variant, forma qiymati va `required` tekshiruvi.
 */

import { fireEvent, render, screen, within } from '@testing-library/react'
import { Building2 } from 'lucide-react'
import { describe, expect, it, vi } from 'vitest'
import { Select } from '../ui/Select'

/**
 * Qiymat hodisa ichida OʻQILADI, keyin emas: boshqariladigan
 * `<select>` da React oʻz qiymatini qayta tiklaydi, ya'ni keyin
 * oʻqilgan `event.target.value` eski qiymatni koʻrsatadi. Chaqiruvchi
 * kod ham aynan shunday yozilgan: `onChange={(e) => setX(e.target.value)}`.
 */
function three(extra: Record<string, unknown> = {}) {
  const seen: string[] = []
  const onChange = vi.fn((event: { target: HTMLSelectElement }) => seen.push(event.target.value))
  render(
    <Select aria-label="Guruh" value="b" onChange={onChange} {...extra}>
      <option value="a">Birinchi</option>
      <option value="b">Ikkinchi</option>
      <option value="c">Uchinchi</option>
    </Select>,
  )
  return { onChange, seen, trigger: screen.getByRole('combobox', { name: 'Guruh' }) }
}

describe('Select — yopiq holat', () => {
  it('tanlangan variantning NOMINI koʻrsatadi', () => {
    const { trigger } = three()
    expect(trigger).toHaveTextContent('Ikkinchi')
  })

  it('roʻyxat yopiq boʻlsa — hech qanday listbox yoʻq', () => {
    three()
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('formaga qiymat native maydon orqali boradi', () => {
    three({ name: 'group' })
    const native = document.querySelector('select[name="group"]') as HTMLSelectElement
    expect(native).toBeTruthy()
    expect(native.value).toBe('b')
  })

  it('`required` native maydonda qoladi — forma yuborilmaydi', () => {
    render(
      <form aria-label="forma">
        <Select aria-label="Guruh" name="group" required defaultValue="">
          <option value="">— tanlanmagan —</option>
          <option value="a">Birinchi</option>
        </Select>
      </form>,
    )
    const form = screen.getByRole('form') as HTMLFormElement
    expect(form.checkValidity()).toBe(false)
  })
})

describe('Select — ochilgan roʻyxat', () => {
  it('bosilganda pastda roʻyxat chiqadi', () => {
    const { trigger } = three()
    fireEvent.click(trigger)
    const list = screen.getByRole('listbox')
    expect(within(list).getAllByRole('option')).toHaveLength(3)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
  })

  it('variant bosilganda `e.target.value` bilan xabar beradi', () => {
    const { trigger, seen } = three()
    fireEvent.click(trigger)
    fireEvent.click(screen.getByRole('option', { name: 'Uchinchi' }))
    expect(seen).toEqual(['c'])
  })

  it('tanlanganida roʻyxat yopiladi', () => {
    const { trigger } = three()
    fireEvent.click(trigger)
    fireEvent.click(screen.getByRole('option', { name: 'Birinchi' }))
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('tanlangan variant belgilanadi', () => {
    const { trigger } = three()
    fireEvent.click(trigger)
    expect(screen.getByRole('option', { name: 'Ikkinchi' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('guruh sarlavhasi tanlab boʻlmaydigan boʻlib qoladi', () => {
    render(
      <Select aria-label="Toifa" defaultValue="meat">
        <optgroup label="Oziq-ovqat">
          <option value="meat">Goʻsht</option>
        </optgroup>
      </Select>,
    )
    fireEvent.click(screen.getByRole('combobox'))
    expect(screen.getByRole('group', { name: 'Oziq-ovqat' })).toBeTruthy()
    expect(screen.getAllByRole('option')).toHaveLength(1)
  })

  it('oʻchirilgan variant tanlanmaydi', () => {
    const onChange = vi.fn()
    render(
      <Select aria-label="Oy" value="1" onChange={onChange}>
        <option value="1">Yanvar</option>
        <option value="2" disabled>
          Fevral
        </option>
      </Select>,
    )
    fireEvent.click(screen.getByRole('combobox'))
    fireEvent.click(screen.getByRole('option', { name: 'Fevral' }))
    expect(onChange).not.toHaveBeenCalled()
  })
})

describe('Select — klaviatura', () => {
  it('pastga strelka roʻyxatni ochadi', () => {
    const { trigger } = three()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    expect(screen.getByRole('listbox')).toBeTruthy()
  })

  it('strelka bilan yurib, Enter bilan tanlanadi', () => {
    const { trigger, seen } = three()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    fireEvent.keyDown(trigger, { key: 'ArrowDown' }) // b → c
    fireEvent.keyDown(trigger, { key: 'Enter' })
    expect(seen).toEqual(['c'])
  })

  it('Escape yopadi va tanlovni oʻzgartirmaydi', () => {
    const { trigger, onChange } = three()
    fireEvent.click(trigger)
    fireEvent.keyDown(trigger, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(onChange).not.toHaveBeenCalled()
  })

  it('harf bilan qidirish — native elementdagidek', () => {
    const { trigger, seen } = three()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    fireEvent.keyDown(trigger, { key: 'u' }) // "Uchinchi"
    fireEvent.keyDown(trigger, { key: 'Enter' })
    expect(seen).toEqual(['c'])
  })

  it('Home va End chekkalarga olib boradi', () => {
    const { trigger, seen } = three()
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    fireEvent.keyDown(trigger, { key: 'End' })
    fireEvent.keyDown(trigger, { key: 'Enter' })
    expect(seen).toEqual(['c'])
  })
})

describe('Select — ochilganda tanlangani koʻrinadi', () => {
  /*
   * Panel faqat oʻrni hisoblangandan keyin chiziladi, ya'ni ochilish
   * paytida u hali DOM'da yoʻq. Shu sababli surish effekti `rect` ga
   * ham bogʻlangan — aks holda oktabr tanlangan boʻlsa ham roʻyxat
   * "Yanvar" dan ochilardi (brauzerda shunday boʻlgan edi).
   */
  it("faol qator belgilanadi, ya'ni unga surish mumkin", () => {
    render(
      <Select aria-label="Oy" value="10">
        {Array.from({ length: 12 }, (_, index) => (
          <option key={index + 1} value={String(index + 1)}>
            {`Oy ${index + 1}`}
          </option>
        ))}
      </Select>,
    )
    fireEvent.click(screen.getByRole('combobox'))
    const active = document.querySelector('[data-active="true"]')
    expect(active?.textContent).toContain('Oy 10')
  })
})

describe('Select — koʻrinish', () => {
  it('yonidagi matn maydoni bilan bir xil balandlik', () => {
    const { trigger } = three()
    expect(trigger.className).toContain('h-10')
  })

  it('zich qator uchun kichik oʻlcham', () => {
    render(
      <Select aria-label="Guruh" size="sm">
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(screen.getByRole('combobox').className).toContain('h-9')
  })

  it('chap belgi qoʻyilganda matn uning ostiga kirmaydi', () => {
    render(
      <Select aria-label="Filial" icon={Building2}>
        <option value="a">Birinchi</option>
      </Select>,
    )
    expect(screen.getByRole('combobox').className).toContain('pl-9')
  })

  it('oʻchirilgan maydon ochilmaydi', () => {
    render(
      <Select aria-label="Guruh" disabled>
        <option value="a">Birinchi</option>
      </Select>,
    )
    const trigger = screen.getByRole('combobox')
    expect(trigger).toBeDisabled()
    fireEvent.click(trigger)
    expect(screen.queryByRole('listbox')).toBeNull()
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

describe('Select — variantlar komponentdan kelganda', () => {
  /**
   * Mijozda guruh roʻyxati BOʻSH chiqdi (`/t/orientaltest`, 2026-10-28):
   * "guruh bor, lekin bola qoʻshayotganda chiqmadi".
   *
   * Sabab — roʻyxat React bolalarini oʻqirdi va faqat toʻgʻridan-toʻgʻri
   * yozilgan `<option>` ni tanirdi. `<GroupOptions/>` kabi KOMPONENT esa
   * oʻsha paytda hali element: uning ichidagi variantlarni faqat React
   * chizgandan keyin, DOM biladi. Yashirin native maydonda ular bor edi —
   * ya'ni forma ishlardi, roʻyxat esa boʻsh koʻrinardi.
   */
  function Variants() {
    return (
      <>
        <option value="">— guruhsiz —</option>
        <option value="g1">Quyoshcha</option>
        <option value="g2" disabled>
          Yulduzcha — toʻlgan
        </option>
      </>
    )
  }

  it('komponent qaytargan variantlarni roʻyxatda koʻrsatadi', () => {
    render(
      <Select aria-label="Guruh" value="" onChange={() => {}}>
        <Variants />
      </Select>,
    )
    fireEvent.click(screen.getByRole('combobox', { name: 'Guruh' }))
    const list = screen.getByRole('listbox')
    expect(within(list).getAllByRole('option')).toHaveLength(3)
    expect(within(list).getByText('Quyoshcha')).toBeTruthy()
  })

  it('komponent ichidagi oʻchirilgan variant oʻchirilgan qoladi', () => {
    const onChange = vi.fn()
    render(
      <Select aria-label="Guruh" value="" onChange={onChange}>
        <Variants />
      </Select>,
    )
    fireEvent.click(screen.getByRole('combobox', { name: 'Guruh' }))
    const list = screen.getByRole('listbox')
    fireEvent.click(within(list).getByText('Yulduzcha — toʻlgan'))
    expect(onChange).not.toHaveBeenCalled()
  })
})
