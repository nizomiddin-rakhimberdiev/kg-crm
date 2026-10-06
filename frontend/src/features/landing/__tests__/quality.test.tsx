/**
 * Sotuv sahifasining sifat darvozalari (PLAN 8.8).
 *
 * Bu xatolarning hech biri testni yiqitmasdi — ekranda esa koʻrinardi:
 * 12px kulrang matnning kontrasti 2.62 edi (AA 4.5 talab qiladi), mobil
 * menyu esa butunlay ochilmasdi. Shuning uchun ular shu yerda
 * qoʻriqlanadi.
 */

import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LandingPage } from '../pages/LandingPage'

vi.mock('@/features/marketing/api', () => ({
  marketingApi: { pricing: vi.fn().mockResolvedValue(null), createLead: vi.fn() },
}))

const SECTIONS = resolve(__dirname, '../sections')

/** Toʻq fon: u yerda `slate-400` ning kontrasti 5.09 — yetarli. */
const isOnDark = (el: Element) =>
  !!el.closest('[data-nav-dark]') ||
  !!el.closest('.bg-ildiz-900') ||
  !!el.closest('[class*="bg-ildiz-9"]')

describe('sotuv sahifasining sifati', () => {
  it('och fonda matn `slate-400`/`slate-300` bilan yozilmaydi (kontrast 2.62 < 4.5)', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/uz']}>
          <LandingPage locale="uz" />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const bad = [...container.querySelectorAll('*')]
      .filter((el) => {
        const cls = el.className?.toString() ?? ''
        // `placeholder:` va `group-data-[dark]` variantlari — boshqa holat.
        const faint = /(^|\s)text-slate-(300|400)(\s|$)/.test(cls)
        return faint && el.textContent?.trim() && !isOnDark(el)
      })
      .map((el) => (el.textContent ?? '').trim().slice(0, 30))
    expect(bad).toEqual([])
  })

  it('mobil menyu header ICHIDA emas — `backdrop-filter` uni 48px ga siqib qoʻyardi', () => {
    const nav = readFileSync(join(SECTIONS, 'Nav.tsx'), 'utf8')
    const headerEnd = nav.indexOf('</header>')
    const menu = nav.indexOf('{open && (')
    expect(headerEnd).toBeGreaterThan(0)
    expect(menu).toBeGreaterThan(headerEnd)
  })

  it('telefon chiplari va aloqa havolalari barmoq uchun yetarli (≥44px)', () => {
    expect(readFileSync(join(SECTIONS, 'Modules.tsx'), 'utf8')).toContain('min-h-[44px]')
    expect(readFileSync(resolve(__dirname, '../ui/Contacts.tsx'), 'utf8')).toContain('min-h-[44px]')
  })
})
