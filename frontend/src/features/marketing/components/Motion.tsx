/**
 * Marketing sahifasining harakat primitivlari.
 *
 * Bitta qoida hammasidan ustun: **kontent harakatsiz ham ko'rinadi.**
 *
 * Avvalgi variant framer-motion `whileInView` bilan `opacity: 0` dan
 * boshlanardi. Haqiqiy brauzerda bu ishlaydi, lekin auditda ko'rindiki
 * `requestAnimationFrame` yurmaydigan har qanday muhitda — headless
 * skrinshot, havola preview'i, ehtimol qidiruv boti — hero'dan pastdagi
 * HAMMA bo'lim bo'sh qolardi. Ustiga uzun sahifaning oxirgi bo'limlari
 * observer kechiksa vaqt-vaqti bilan yashirin qolardi.
 *
 * Endi mexanizm teskari va uch qavat himoyalangan:
 *   1. Element ko'rinadigan holatda render bo'ladi. JS umuman ishlamasa —
 *      kontent bor.
 *   2. Yashirish klassi FAQAT JS'da, `useLayoutEffect` ichida qo'shiladi
 *      (birinchi paint'dan oldin — flash bo'lmaydi). Observer ko'rganda
 *      klass olinadi va CSS transition ochadi. Transition kompozitorda
 *      ishlaydi, JS rAF'iga muhtoj emas.
 *   3. Observer 1.2 s ichida ishlamasa — taymer baribir ochadi. Eng
 *      yomon holat "biroz kechroq ko'rindi", "hech qachon" emas.
 *
 * `prefers-reduced-motion` — CSS'da (`index.css`): harakat yo'q, kontent
 * darhol.
 */

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { useInView, useReducedMotion } from 'framer-motion'

const REVEAL_FALLBACK_MS = 1200

/**
 * Scroll bo'ylab ochiladigan blok.
 *
 * `delay` — qo'shni elementlarni ketma-ket ochish uchun (stagger). 80 ms
 * dan oshirmaslik kerak: ko'zga tashlanadigan kechikish "sayt sekin"
 * degan taassurot beradi.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = useReducedMotion()
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const [armed, setArmed] = useState(false)
  const [shown, setShown] = useState(false)

  // Paint'dan OLDIN yashiriladi — aks holda bir kadr ko'rinib, keyin
  // yo'qolib, keyin qayta paydo bo'lardi.
  useLayoutEffect(() => {
    if (!reduced) setArmed(true)
  }, [reduced])

  useEffect(() => {
    if (inView) setShown(true)
  }, [inView])

  useEffect(() => {
    if (!armed || shown) return
    const timer = window.setTimeout(() => setShown(true), REVEAL_FALLBACK_MS)
    return () => window.clearTimeout(timer)
  }, [armed, shown])

  const hidden = armed && !shown

  return (
    <div
      ref={ref}
      className={[className, 'reveal', hidden ? 'reveal-pending' : ''].filter(Boolean).join(' ')}
      style={delay ? { transitionDelay: `${delay}s` } : undefined}
    >
      {children}
    </div>
  )
}

/**
 * Ko'ringanda 0 dan sanaydigan raqam.
 *
 * Boshlang'ich qiymat — YAKUNIY raqam, 0 emas: sanoq ishlamasa ham
 * to'g'ri raqam turadi. Observer ko'rganda 0 ga tushib, yuqoriga sanaydi.
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
  const [value, setValue] = useState(to)

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

    setValue(0)
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [inView, reduced, to, duration])

  return (
    <span ref={ref} className={className}>
      {format(value)}
    </span>
  )
}
