/**
 * ErrorBoundary (P1-006).
 *
 * Usiz React 18 ushlanmagan xatoda butun daraxtni yechadi va
 * foydalanuvchi OQ EKRAN ko'radi — xabarsiz, tugmasiz.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { ErrorBoundary } from '../ErrorBoundary'

function Boom({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) throw new Error('ataylab yiqilgan komponent')
  return <p>tinch holat</p>
}

beforeEach(() => {
  // React ushlangan xatoni baribir konsolga yozadi — testda bu shovqin.
  vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('ErrorBoundary', () => {
  it("xato bo'lmasa bolalarni ko'rsatadi", () => {
    render(
      <ErrorBoundary>
        <p>normal mazmun</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText('normal mazmun')).toBeInTheDocument()
  })

  it("xato bo'lsa oq ekran emas, XABAR ko'rsatadi", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Sahifa ochilmadi')).toBeInTheDocument()
    // Foydalanuvchida yo'l qolishi kerak — boshi berk ko'cha bo'lmasin.
    expect(screen.getByRole('button', { name: /qayta urinish/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sahifani yangilash/i })).toBeInTheDocument()
  })

  it('ichki xato tashqariga chiqmaydi', () => {
    // Chegara o'z ishini qilsa, `render` istisno KO'TARMASLIGI kerak.
    expect(() =>
      render(
        <ErrorBoundary>
          <Boom />
        </ErrorBoundary>,
      ),
    ).not.toThrow()
  })

  it('"qayta urinish" holatni tiklaydi', async () => {
    function Toggle() {
      const [broken, setBroken] = useState(true)
      return (
        <>
          <button onClick={() => setBroken(false)}>tuzat</button>
          <ErrorBoundary>
            <Boom shouldThrow={broken} />
          </ErrorBoundary>
        </>
      )
    }

    render(<Toggle />)
    expect(screen.getByText('Sahifa ochilmadi')).toBeInTheDocument()

    await userEvent.click(screen.getByText('tuzat'))
    await userEvent.click(screen.getByRole('button', { name: /qayta urinish/i }))

    expect(screen.getByText('tinch holat')).toBeInTheDocument()
  })
})
