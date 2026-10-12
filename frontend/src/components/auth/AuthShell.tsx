/**
 * Kirish va ro'yxatdan o'tish sahifalari uchun umumiy qobiq.
 *
 * Katta ekranda ikki ustun: chapda brend paneli (to'q Ildiz fon, suzuvchi
 * kartochkalar), o'ngda forma. Telefonda faqat forma — brend paneli
 * yashiriladi, logotip tepada qoladi.
 *
 * Harakat framer-motion'da va `prefers-reduced-motion` ni hurmat qiladi:
 * u yoqilgan bo'lsa suzish va kirish animatsiyasi o'chadi, kontent
 * darhol ko'rinadi.
 */

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { ArrowLeft, CalendarCheck, Sparkles, Wallet } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { LanguageSwitch } from '@/components/layout/LanguageSwitch'
import { locale, t } from '@/lib/i18n'

const EASE = [0.16, 1, 0.3, 1] as const

const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
}

const rise: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } },
}

function FloatCard({
  icon,
  title,
  value,
  className,
  delay,
  still,
}: {
  icon: ReactNode
  title: string
  value: string
  className: string
  delay: number
  still: boolean
}) {
  return (
    <motion.div
      initial={still ? false : { opacity: 0, y: 24, scale: 0.96 }}
      animate={
        still
          ? { opacity: 1 }
          : { opacity: 1, y: [0, -8, 0], scale: 1 }
      }
      transition={
        still
          ? undefined
          : {
              opacity: { duration: 0.8, delay, ease: EASE },
              scale: { duration: 0.8, delay, ease: EASE },
              y: { duration: 6, delay: delay + 0.8, repeat: Infinity, ease: 'easeInOut' },
            }
      }
      className={`absolute flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white shadow-soft backdrop-blur-md ${className}`}
    >
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/15 text-nihol-200">
        {icon}
      </span>
      <span>
        <span className="block text-xs text-white/70">{title}</span>
        <span className="num block text-base font-semibold">{value}</span>
      </span>
    </motion.div>
  )
}

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  wide = false,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
  /** Signup kabi uzun formalar uchun kengroq ustun. */
  wide?: boolean
}) {
  const still = useReducedMotion() ?? false

  return (
    <div className="grid min-h-screen bg-sut lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      {/* Brend paneli */}
      <aside className="mesh-dark relative hidden overflow-hidden lg:block" aria-hidden="true">
        <div className="absolute inset-0 [background-image:radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.08)_1px,transparent_0)] [background-size:26px_26px] [mask-image:linear-gradient(to_bottom,black,transparent_85%)]" />
        <div className="relative flex h-full flex-col justify-between p-12 xl:p-16">
          <Logo height={40} variant="dark" />

          <div className="relative hidden min-h-[360px] [@media(min-height:820px)]:block">
            <FloatCard
              icon={<CalendarCheck className="h-5 w-5" />}
              title={t('Bugungi davomat')}
              value="87%"
              className="left-0 top-0"
              delay={0.2}
              still={still}
            />
            <FloatCard
              icon={<Wallet className="h-5 w-5" />}
              title={t("To'lov qabul qilindi")}
              value="+1 500 000"
              className="left-24 top-28 xl:left-36"
              delay={0.45}
              still={still}
            />
            <FloatCard
              icon={<Sparkles className="h-5 w-5" />}
              title="Radix AI"
              value={t('3 ta rasm ota-onaga yuborildi')}
              className="left-4 top-56 xl:left-12"
              delay={0.7}
              still={still}
            />
          </div>

          <motion.div
            variants={stagger}
            initial={still ? false : 'hidden'}
            animate="show"
            className="max-w-md"
          >
            <motion.h2
              variants={rise}
              className="text-balance font-display text-4xl font-extrabold leading-[1.1] tracking-[-0.03em] text-white"
            >
              {t("Bog'changiz — bitta tizimda")}
            </motion.h2>
            <motion.p variants={rise} className="mt-4 text-base leading-7 text-white/75">
              {t("Bolalar, to'lovlar, davomat va Radix AI — hammasi bir joyda.")}
            </motion.p>
          </motion.div>
        </div>
      </aside>

      {/* Forma ustuni */}
      <main className="mesh-light relative flex flex-col px-5 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <Link
            to={`/${locale}`}
            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-tosh-500 transition hover:bg-white/70 hover:text-tosh-900"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('Bosh sahifa')}
          </Link>
          <LanguageSwitch size="md" />
        </div>

        <div className="flex flex-1 items-center justify-center py-8">
          <motion.div
            variants={stagger}
            initial={still ? false : 'hidden'}
            animate="show"
            className={`w-full ${wide ? 'max-w-xl' : 'max-w-[420px]'}`}
          >
            <motion.div variants={rise} className="mb-8 lg:hidden">
              <Logo height={36} />
            </motion.div>

            <motion.h1
              variants={rise}
              className="font-display text-[2rem] font-extrabold leading-tight tracking-[-0.03em] text-ildiz-900"
            >
              {title}
            </motion.h1>
            {subtitle && (
              <motion.p variants={rise} className="mt-2 text-[15px] leading-6 text-tosh-500">
                {subtitle}
              </motion.p>
            )}

            <motion.div variants={rise} className="glass mt-7 rounded-3xl p-6 sm:p-8">
              {children}
            </motion.div>

            {footer && (
              <motion.div variants={rise} className="mt-6 text-center text-sm text-tosh-500">
                {footer}
              </motion.div>
            )}
          </motion.div>
        </div>
      </main>
    </div>
  )
}
