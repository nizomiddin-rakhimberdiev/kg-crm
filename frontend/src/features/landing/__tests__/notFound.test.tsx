/**
 * 404 — bitta tilda (audit 2026-11-12, J5).
 *
 * Uch tilda birga turgan sahifa "qaysi biri meniki?" degan savol bilan
 * ochilardi. Endi nginx manzil prefiksidan (`/ru/…`, `/en/…`) yoki
 * brauzer tilidan mos faylni beradi.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { copy } from '../content'
import { NotFoundPage } from '../pages/NotFoundPage'

describe('NotFoundPage', () => {
  it.each(['uz', 'ru', 'en'] as const)('%s — faqat oʻz tilida', (locale) => {
    render(<NotFoundPage locale={locale} />)
    const headings = screen.getAllByRole('heading')
    expect(headings).toHaveLength(1)
    expect(headings[0]).toHaveTextContent(copy[locale].notFound.title)
  })

  it('nginx har til uchun oʻz faylini beradi', () => {
    const conf = readFileSync(resolve(__dirname, '../../../../../deploy/nginx/tls.conf'), 'utf8')
    expect(conf).toMatch(/map \$uri \$kg_404_page/)
    const saas = readFileSync(
      resolve(__dirname, '../../../../../deploy/nginx/_spa_saas.conf'),
      'utf8',
    )
    expect(saas).toMatch(/error_page 404 \$kg_404_page;/)
  })
})

describe('FAQ raqami (audit 2026-11-12, J5)', () => {
  it('10-savol "010" emas, "10"', async () => {
    const { Faq } = await import('../sections/Faq')
    render(<Faq locale="uz" />)
    const numbers = screen.getAllByText(/^\d+$/).map((el) => el.textContent)
    expect(numbers).not.toContain('010')
    if (copy.uz.faq.items.length >= 10) expect(numbers).toContain('10')
  })
})
