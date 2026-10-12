/** Radix AI bo'limining umumiy bo'laklari: rasm, skelet, xato bloki, tab. */

import { type ReactNode } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { ImageOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ApiError } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { useAuthedImage } from '../hooks'

export function errorText(err: unknown): string {
  return err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')
}

export function AuthedImage({
  path,
  alt,
  className,
}: {
  path: string
  alt: string
  className?: string
}) {
  const { url, isLoading, isError } = useAuthedImage(path)
  if (isError) {
    return (
      <div className={cn('grid place-items-center bg-slate-100 text-slate-300', className)}>
        <ImageOff className="h-6 w-6" aria-label={t('Rasm yuklanmadi')} />
      </div>
    )
  }
  if (isLoading || !url) return <Skeleton className={className} />
  return <img src={url} alt={alt} className={className} loading="lazy" draggable={false} />
}

export function Skeleton({ className }: { className?: string }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      aria-hidden
      className={cn('rounded-xl bg-slate-100', className)}
      animate={reduce ? undefined : { opacity: [0.55, 1, 0.55] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <motion.div
      role="alert"
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {message}
    </motion.div>
  )
}

export function SectionTitle({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {hint && <p className="mt-0.5 text-sm text-slate-500">{hint}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  )
}

/** Faol tab ostida "sirpanuvchi" chiziq — `layoutId` bilan bitta element ko'chadi. */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { id: T; label: string; icon: ReactNode; badge?: number }[]
  value: T
  onChange: (id: T) => void
}) {
  return (
    <div
      role="tablist"
      className="scrollbar-thin flex gap-1 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-1.5 shadow-card"
    >
      {tabs.map((tab) => {
        const active = tab.id === value
        return (
          <button
            key={tab.id}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors',
              active ? 'text-white' : 'text-slate-600 hover:bg-slate-50',
            )}
          >
            {active && (
              <motion.span
                layoutId="memories-tab"
                className="absolute inset-0 rounded-xl bg-brand-600"
                transition={{ type: 'spring', stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-2">
              {tab.icon}
              {tab.label}
              {tab.badge ? (
                <span
                  className={cn(
                    'rounded-full px-1.5 text-[11px] font-semibold',
                    active ? 'bg-white/25 text-white' : 'bg-red-100 text-red-700',
                  )}
                >
                  {tab.badge}
                </span>
              ) : null}
            </span>
          </button>
        )
      })}
    </div>
  )
}
