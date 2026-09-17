/**
 * Brend motivi — chizilib boradigan ildiz tizimi.
 *
 * Nega aynan ildiz: "radix" lotinchada ildiz degani, va bog'cha uchun bu
 * tasodifiy emas — kuchli poydevor, undan o'sish. Bu sahifadagi yagona
 * "o'ziga xos" grafik element, shuning uchun u boshqa hech qayerda
 * takrorlanmaydi va boshqa bezaklar uning yonida jim turadi.
 *
 * Shakl DETERMINISTIK quriladi (`Math.random` yo'q): har ochilishda bir
 * xil chiqadi. Tasodifiy shakl "har safar boshqacha sayt" taassurotini
 * berardi va skrinshot/thumbnail ham har safar boshqa bo'lardi.
 */

import { memo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

type Segment = { d: string; depth: number }

/**
 * Ildizni rekursiv quradi: har bir shox ikkiga bo'linadi, qisqaradi va
 * ozgina yon tomonga og'adi. Burchaklar qo'lda tanlangan — tabiiy
 * ko'rinishi uchun ular bir xil emas.
 */
function buildRoots(): Segment[] {
  const segments: Segment[] = []

  const grow = (x: number, y: number, angle: number, length: number, depth: number) => {
    if (depth > 4 || length < 7) return

    const x2 = x + Math.cos(angle) * length
    const y2 = y + Math.sin(angle) * length
    // Nazorat nuqtasi shoxni ozgina egadi — to'g'ri chiziq "sxema"
    // bo'lib ko'rinadi, egri chiziq esa o'sayotgan narsaga o'xshaydi.
    const cx = x + Math.cos(angle - 0.25) * length * 0.55
    const cy = y + Math.sin(angle - 0.25) * length * 0.55

    segments.push({ d: `M ${x} ${y} Q ${cx} ${cy} ${x2} ${y2}`, depth })

    const spread = 0.42 - depth * 0.05
    grow(x2, y2, angle - spread, length * 0.74, depth + 1)
    grow(x2, y2, angle + spread * 1.15, length * 0.68, depth + 1)
  }

  // Uchta asosiy ildiz pastga qarab tarqaladi (SVG'da y pastga o'sadi).
  grow(100, 96, Math.PI / 2 - 0.5, 34, 0)
  grow(100, 96, Math.PI / 2, 40, 0)
  grow(100, 96, Math.PI / 2 + 0.52, 34, 0)

  return segments
}

const ROOTS = buildRoots()

export const RootMotif = memo(function RootMotif({ className }: { className?: string }) {
  const reduced = useReducedMotion()

  return (
    <svg
      className={className}
      viewBox="0 0 200 200"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="radix-root-fade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.55" />
          <stop offset="60%" stopColor="#2563eb" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Poya va kurtak — ildizdan yuqoriga. */}
      <motion.path
        d="M 100 96 L 100 58"
        stroke="#2563eb"
        strokeWidth="2.4"
        strokeLinecap="round"
        initial={reduced ? false : { pathLength: 0 }}
        animate={reduced ? undefined : { pathLength: 1 }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
      />
      <motion.path
        d="M 100 72 C 100 60, 110 54, 120 54 C 120 64, 112 72, 100 72 Z"
        fill="#2563eb"
        fillOpacity="0.9"
        initial={reduced ? false : { opacity: 0, scale: 0.6 }}
        animate={reduced ? undefined : { opacity: 1, scale: 1 }}
        style={{ transformOrigin: '100px 72px' }}
        transition={{ duration: 0.5, delay: 0.55, ease: 'easeOut' }}
      />
      <motion.path
        d="M 100 82 C 100 70, 90 64, 80 64 C 80 74, 88 82, 100 82 Z"
        fill="#2563eb"
        fillOpacity="0.55"
        initial={reduced ? false : { opacity: 0, scale: 0.6 }}
        animate={reduced ? undefined : { opacity: 1, scale: 1 }}
        style={{ transformOrigin: '100px 82px' }}
        transition={{ duration: 0.5, delay: 0.7, ease: 'easeOut' }}
      />

      {/* Ildizlar — chuqurroq shox kechroq va ingichkaroq chiziladi. */}
      {ROOTS.map((segment, index) => (
        <motion.path
          key={index}
          d={segment.d}
          stroke="url(#radix-root-fade)"
          strokeWidth={Math.max(0.7, 2.2 - segment.depth * 0.42)}
          strokeLinecap="round"
          initial={reduced ? false : { pathLength: 0 }}
          animate={reduced ? undefined : { pathLength: 1 }}
          transition={{
            duration: 0.9,
            delay: 0.25 + segment.depth * 0.18,
            ease: 'easeOut',
          }}
        />
      ))}
    </svg>
  )
})
