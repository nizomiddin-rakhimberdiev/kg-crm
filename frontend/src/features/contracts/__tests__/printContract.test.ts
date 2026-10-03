/**
 * Printing a contract (PLAN 6.5): the text goes in as text. A value typed
 * into a child's card must never become markup on a print-out.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { printContract } from '../api'

describe('printContract', () => {
  afterEach(() => vi.restoreAllMocks())

  it('writes the text as a text node and opens the print dialog', () => {
    const doc = document.implementation.createHTMLDocument('')
    const fake = { document: doc, focus: vi.fn(), print: vi.fn() }
    vi.spyOn(window, 'open').mockReturnValue(fake as unknown as Window)

    printContract({ number: 'SH-2026-0001', rendered_text: 'Bola: <b>Ali</b>\n<script>x</script>' })

    expect(doc.title).toBe('SH-2026-0001')
    expect(doc.querySelector('pre')?.textContent).toContain('<b>Ali</b>')
    expect(doc.querySelector('b')).toBeNull()
    expect(doc.querySelector('script')).toBeNull()
    expect(fake.print).toHaveBeenCalled()
  })

  it('does nothing when the browser blocks the window', () => {
    vi.spyOn(window, 'open').mockReturnValue(null)
    expect(() => printContract({ number: 'x', rendered_text: 'y' })).not.toThrow()
  })
})
