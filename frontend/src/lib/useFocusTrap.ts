/**
 * Dialog ichida fokus (PLAN 10.15).
 *
 * `aria-modal="true"` ekranni oʻquvchiga "bu oyna ochiq, orqasidagi
 * narsa yoʻq" deydi — lekin KLAVIATURA baribir orqadagi tugmalarga
 * oʻtadi. Natijada Tab bosgan odam koʻrinmaydigan sahifada adashadi,
 * dialog yopilgach esa fokus sahifaning boshiga tushib qoladi va
 * uni ochgan tugma qayerda ekani bilinmaydi.
 *
 * Shuning uchun bitta joy: ochilganda fokus panelga kiradi, Tab
 * panel ichida aylanadi, yopilganda esa ochgan elementga qaytadi.
 * Ikkalasi ham — `Modal` ham, telefon menyusi ham — shu hook'ni
 * ishlatadi, aks holda qoida ulardan birida unutilardi.
 */

import { useEffect, useRef, type MutableRefObject } from 'react'

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function useFocusTrap<T extends HTMLElement>(open: boolean): MutableRefObject<T | null> {
  const ref = useRef<T | null>(null)

  useEffect(() => {
    if (!open) return
    const panel = ref.current
    if (!panel) return
    const returnTo = document.activeElement as HTMLElement | null

    const items = () =>
      [...panel.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
        (el) => el.offsetParent !== null || el === document.activeElement,
      )

    // Birinchi maydonga emas, panelning oʻziga: ochilishi bilan
    // klaviatura biror katakka yozib yubormasin.
    const first = items()[0]
    if (first) first.focus()
    else {
      panel.setAttribute('tabindex', '-1')
      panel.focus()
    }

    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return
      const list = items()
      if (list.length === 0) return
      const firstItem = list[0]
      const lastItem = list[list.length - 1]
      const active = document.activeElement
      if (event.shiftKey && (active === firstItem || !panel.contains(active))) {
        event.preventDefault()
        lastItem.focus()
      } else if (!event.shiftKey && active === lastItem) {
        event.preventDefault()
        firstItem.focus()
      }
    }

    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      // Yopilgach — ochgan tugmaga qaytamiz; u endi DOM'da boʻlmasa,
      // hech narsa qilmaymiz (sahifa oʻzgargan boʻlishi mumkin).
      if (returnTo && document.contains(returnTo)) returnTo.focus()
    }
  }, [open])

  return ref
}
