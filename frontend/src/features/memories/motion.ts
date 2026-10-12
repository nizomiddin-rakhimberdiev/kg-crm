/**
 * Radix AI bo'limi harakat tili — framer-motion (Motion).
 *
 * Qoida marketing/Motion.tsx bilan bir xil: kontent harakatsiz ham to'liq
 * ko'rinadi, `prefers-reduced-motion` da animatsiya o'chadi. Hamma joyda bitta
 * "easeOut" egri chizig'i — ekran bo'ylab bir xil sezgi.
 */

import type { Transition, Variants } from 'framer-motion'

export const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

export const spring: Transition = { type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.38, ease: EASE } },
}

export const stagger = (delay = 0.045): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: delay, delayChildren: 0.04 } },
})

export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.92 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.28, ease: EASE } },
}
