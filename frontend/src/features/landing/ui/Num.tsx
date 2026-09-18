/**
 * Qiymati o'zgarganda eskisidan yangisiga "yugurib" o'tadigan raqam.
 *
 * `CountUp` bir marta (ko'ringanda) sanaydi; bu esa har o'zgarishda —
 * scroll-sahnalarda holat almashganda raqam sakramaydi, o'tadi.
 */

import { useEffect } from 'react'
import { animate, motion, useMotionValue, useTransform } from 'framer-motion'
import { groupThousands } from '../content'

export function Num({
  value,
  format = groupThousands,
  className = '',
  duration = 0.6,
}: {
  value: number
  format?: (v: number) => string
  className?: string
  duration?: number
}) {
  const mv = useMotionValue(value)
  const text = useTransform(mv, (v) => format(v))
  useEffect(() => {
    const controls = animate(mv, value, { duration, ease: 'easeOut' })
    return () => controls.stop()
  }, [mv, value, duration])
  return <motion.span className={className}>{text}</motion.span>
}
