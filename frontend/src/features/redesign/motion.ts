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

/** [a, b] oralig'ini 0..1 ga normallashtiradi va qirqadi. */
export const span = (p: number, a: number, b: number) => Math.min(1, Math.max(0, (p - a) / (b - a)))

export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
