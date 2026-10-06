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

/**
 * Media so'rovini kuzatadi. Boshlang'ich qiymat ham `matchMedia` dan —
 * birinchi kadr darhol to'g'ri bo'lishi kerak, aks holda telefonda
 * desktop maketi bir zumga ko'rinib ketardi.
 */
export function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false,
  )
  useEffect(() => {
    const media = window.matchMedia(query)
    const onChange = () => setMatches(media.matches)
    onChange()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [query])
  return matches
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

/** Telefon (`sm` dan tor) — eng zich maket. */
export function usePhone(): boolean {
  return useMedia('(max-width: 639px)')
}

/**
 * Pinned ("scroll-jacking") sahna o'rniga oddiy blok kerakmi.
 *
 * Qoida bitta va u OYNANING o'lchamiga qarab chiqadi, qurilma turiga
 * emas: pinned sahna faqat haqiqiy desktop oynasida — eni ≥ 1024 px VA
 * bo'yi ≥ 700 px — ishlaydi.
 *
 * Nega bo'yi ham: ilgari chegara faqat 640 px edi, ya'ni yonboshlatilgan
 * telefon (844 × 390) ham, planshet ham pinned sahnalarni olardi. 390 px
 * balandlikdagi `h-screen` sahnada mahsulot paneli o'rtasidan kesilardi,
 * sahifa esa 25 800 px ga cho'zilardi — telefondagi 12 900 px ning ikki
 * baravari. Statik maket esa allaqachon bor va sinalgan.
 */
export function useStaticScene(): boolean {
  const reduced = useStatic()
  const desktop = useMedia('(min-width: 1024px) and (min-height: 700px)')
  return reduced || !desktop
}

/** [a, b] oralig'ini 0..1 ga normallashtiradi va qirqadi. */
export const span = (p: number, a: number, b: number) => Math.min(1, Math.max(0, (p - a) / (b - a)))

export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
