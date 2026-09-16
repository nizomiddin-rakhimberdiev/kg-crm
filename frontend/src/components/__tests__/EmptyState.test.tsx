import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Users } from 'lucide-react'
import { EmptyState, EmptyRow } from '@/components/ui/EmptyState'

describe('EmptyState', () => {
  it('nima yo\'q, nega normal va keyingi qadamni aytadi', () => {
    render(
      <EmptyState
        icon={Users}
        title="Bola yo'q"
        hint="Excel orqali import qiling yoki bittalab qo'shing."
        action={<button>Bola qo'shish</button>}
      />,
    )
    expect(screen.getByText("Bola yo'q")).toBeInTheDocument()
    expect(screen.getByText(/Excel orqali/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /qo'shish/i })).toBeInTheDocument()
  })

  it('EmptyRow jadval ichida qoladi', () => {
    // `<div>` ni `<tbody>` ichiga qo'yib bo'lmaydi — brauzer uni
    // jadvaldan TASHQARIGA ko'chiradi va matn jadval ostida osilib
    // qoladi. Shuning uchun alohida variant kerak.
    const { container } = render(
      <table>
        <tbody>
          <EmptyRow colSpan={5} title="Hech narsa yo'q" />
        </tbody>
      </table>,
    )
    const cell = container.querySelector('tbody td')
    expect(cell).not.toBeNull()
    expect(cell?.getAttribute('colspan')).toBe('5')
    expect(cell?.textContent).toContain("Hech narsa yo'q")
  })
})
