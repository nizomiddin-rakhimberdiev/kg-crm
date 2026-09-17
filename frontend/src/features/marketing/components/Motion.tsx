/**
 * Marketing sahifasining harakat primitivlari.
 *
 * Ikkita qoida butun fayl bo'ylab amal qiladi:
 *
 * 1. **Harakat — bezak, kontent emas.** Har bir blok animatsiyasiz ham
 *    to'liq o'qiladigan holatda render bo'ladi. `opacity: 0` da observer
 *    ishga tushishini kutib turgan matn — bu bo'sh sahifa xavfi: observer
 *    ishlamasa (eski brauzer, thumbnail tortish, matn indekslash) sahifa
 *    butunlay bo'sh qoladi. Shuning uchun `whileInView` ishlatiladi va
 *    `once: true` bilan bir marta ochiladi.
 *
 * 2. **`prefers-reduced-motion` — majburiy.** Vestibulyar buzilishi bor
 *    odam uchun scroll bo'ylab sakrab turadigan sahifa jismonan noqulay.
 *    Bu holatda hamma narsa darhol, harakatsiz ko'rinadi.
 */

import { useEffect, useRef, useState, type ReactNode } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * Scroll bo'ylab ochiladigan blok.
 *
 * `delay` — qo'shni elementlarni ketma-ket ochish uchun (stagger). Uni
 * 60-80 ms dan oshirmaslik kerak: ko'zga tashlanadigan kechikish
 * "sayt sekin" degan taassurot beradi.
 */
export function Reveal({
  children,
  delay = 0,
  y = 20,
  className,
}: {
  children: ReactNode
  delay?: number
  y?: number
  className?: string
}) {
  const reduced = useReducedMotion()

  if (reduced) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.55, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

/**
 * Ko'ringanda 0 dan sanaydigan raqam.
 *
 * `requestAnimationFrame` bilan — `setInterval` kadrlarga tushmaydi va
 * sanoq sakrab ko'rinadi.
 */
export function CountUp({
  to,
  duration = 1400,
  format = (value: number) => String(Math.round(value)),
  className,
}: {
  to: number
  duration?: number
  format?: (value: number) => string
  className?: string
}) {
  const reduced = useReducedMotion()
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const [value, setValue] = useState(reduced ? to : 0)

  useEffect(() => {
    if (reduced || !inView) return
    let frame = 0
    const start = performance.now()

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration)
      // easeOutExpo — oxirida sekinlashadi, ya'ni raqam "qo'nadi".
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      setValue(to * eased)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [inView, reduced, to, duration])

  return (
    <span ref={ref} className={className}>
      {format(value)}
    </span>
  )
}
