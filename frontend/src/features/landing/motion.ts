/**
 * Scroll-hikoya uchun harakat yordamchilari.
 *
 * Qoida (marketing/Motion.tsx bilan bir xil): kontent harakatsiz ham
 * ko'rinadi. Scroll-scrub sahnalarida progress = 0 holati — to'liq,
 * ma'noli kadr; `prefers-reduced-motion` da sahna oxirgi holatida turadi.
 */

import { useEffect, useState, type RefObject } from 'react'
import { useReducedMotion, useScroll, type MotionValue } from 'framer-motion'

export { CountUp, Reveal } from '@/features/marketing/components/Motion'

/** Planshet va telefon — pinned sahnalar qisqaradi, 3D chuqurlik o'chadi. */
export function useCompact(query = '(max-width: 1023px)'): boolean {
  const [compact, setCompact] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false,
  )
  useEffect(() => {
    const media = window.matchMedia(query)
    const onChange = () => setCompact(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [query])
  return compact
}

/**
 * Pinned sahna progressi: tashqi konteyner balandligi N×100vh, ichkarisi
 * `sticky top-0 h-screen`. Progress 0 → sahna ekranga kirdi, 1 → chiqdi.
 */
export function useScene(ref: RefObject<HTMLElement>): MotionValue<number> {
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  return scrollYProgress
}

/** Reduced-motion: sahna scrub'siz, oxirgi kadrda. */
export function useStatic(): boolean {
  return useReducedMotion() ?? false
}

/** Telefon (`sm` dan tor). Planshet `useCompact` da qoladi. */
export function usePhone(): boolean {
  return useCompact('(max-width: 639px)')
}

/**
 * Pinned sahna o'rniga oddiy blok kerakmi (PLAN 5.7).
 *
 * Telefonda pinned sahnalar sahifani 26 600 px ga cho'zardi (390 px
 * kenglikda ~30 ekran): har bir sahna 2–4 ekran scroll masofasini
 * egallaydi, mazmuni esa bitta ekranga sig'adi. Statik shakl — reduced-
 * motion uchun allaqachon bor va sinalgan blok (akkordeon, ro'yxat), ya'ni
 * yangi dizayn emas, mavjudining telefonga ham berilishi. Planshet
 * (640–1023 px) pinned sahnalarda qoladi — u yerda ular sig'adi.
 */
export function useStaticScene(): boolean {
  const reduced = useStatic()
  const phone = usePhone()
  return reduced || phone
}

/** [a, b] oralig'ini 0..1 ga normallashtiradi va qirqadi. */
export const span = (p: number, a: number, b: number) => Math.min(1, Math.max(0, (p - a) / (b - a)))

export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

/**
 * Gorizontal chip qatorida faol elementni markazga keltiradi — FAQAT
 * gorizontal. `scrollIntoView` overflow-hidden sticky konteynerni vertikal
 * ham surib yuborardi (kichik ekranda kontent sig'maganda).
 */
export function centerInStrip(el: HTMLElement | null) {
  const strip = el?.parentElement
  if (!el || !strip) return
  const left = el.offsetLeft - (strip.clientWidth - el.offsetWidth) / 2
  strip.scrollTo({ left: Math.max(0, left), behavior: 'smooth' })
}
