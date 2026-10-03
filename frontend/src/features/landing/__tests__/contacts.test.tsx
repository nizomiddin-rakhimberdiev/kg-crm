/**
 * Aloqa bloki, demo javobi va "Mijozlar fikri" joyi (PLAN 5.7).
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { CONTACT, formatPhone, telegramUrl } from '@/config/contact'
import { Lead } from '../sections/Lead'
import { Testimonials } from '../sections/Testimonials'
import { ContactList, LegalLine } from '../ui/Contacts'

vi.mock('@/features/marketing/api', () => ({
  marketingApi: { createLead: vi.fn().mockResolvedValue({}) },
}))

describe('aloqa', () => {
  it('raqam oʻqiladigan koʻrinishda va bosilganda qoʻngʻiroq qiladi', () => {
    render(<ContactList locale="uz" />)
    const phone = screen.getByText('+998 94 726 77 26')
    expect(phone.closest('a')).toHaveAttribute('href', 'tel:+998947267726')
    expect(screen.getByText('+998 95 076 77 26').closest('a')).toHaveAttribute(
      'href',
      'tel:+998950767726',
    )
    expect(screen.getByText(`@${CONTACT.telegram}`).closest('a')).toHaveAttribute(
      'href',
      telegramUrl,
    )
    expect(screen.getByText(CONTACT.email).closest('a')).toHaveAttribute(
      'href',
      `mailto:${CONTACT.email}`,
    )
  })

  it('faqat Oʻzbekiston formatidagi raqamlar chiqadi', () => {
    // Format xatosi (`+999…`) ochiq saytga chiqmasin: notoʻgʻri raqam
    // mijozni begona odamga qoʻngʻiroq qildiradi.
    for (const phone of CONTACT.phones) {
      expect(phone).toMatch(/^\+998\d{9}$/)
    }
    expect(formatPhone('+998950767726')).toBe('+998 95 076 77 26')
  })

  it('yuridik qator toʻldirilmagan boʻlsa umuman chiqmaydi', () => {
    // `.env` da VITE_LEGAL_* yoʻq — saytda "{{STIR}}" yoki boʻsh
    // "STIR" yorligʻi koʻrinmasligi kerak.
    const { container } = render(<LegalLine locale="uz" />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('Mijozlar fikri', () => {
  it('maʼlumot yoʻq ekan — blok chizilmaydi', () => {
    const { container } = render(<Testimonials locale="uz" />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('demo formasi', () => {
  it('yuborilgandan keyin 24 soat va Telegram tugmasi koʻrinadi', async () => {
    const { container } = render(
      <MemoryRouter>
        <Lead locale="uz" />
      </MemoryRouter>,
    )
    const fill = (name: string, value: string) => {
      const field = container.querySelector(`[name="${name}"]`)
      if (field) fireEvent.change(field, { target: { value } })
    }
    fill('name', 'Aziz')
    fill('phone', '+998901234567')
    fill('kindergarten_name', 'Quyosh')
    fill('children_count', '40')
    fill('city', 'Toshkent')
    const consent = container.querySelector('[name="consent"]')
    if (consent) fireEvent.click(consent)
    fireEvent.submit(container.querySelector('form') as HTMLFormElement)

    await waitFor(() => expect(screen.getByText('24 soat ichida bogʻlanamiz.')).toBeInTheDocument())
    expect(screen.getByText('Telegramda yozish').closest('a')).toHaveAttribute('href', telegramUrl)
  })
})
