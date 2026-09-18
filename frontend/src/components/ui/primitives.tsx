import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, Check, ChevronDown, ChevronLeft, ChevronRight, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Modal } from './Modal'

/* ------------------------------------------------------------------ Card */

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-slate-200 bg-white shadow-card',
        className,
      )}
      {...props}
    />
  )
}

/* ------------------------------------------------------------ PageHeader */

interface PageHeaderProps {
  title: string
  subtitle?: string
  children?: React.ReactNode // action buttons on the right
}

export function PageHeader({ title, subtitle, children }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  )
}

/* ---------------------------------------------------------------- Button */

type ButtonVariant = 'primary' | 'outline' | 'ghost' | 'success' | 'danger' | 'dark'

const buttonVariants: Record<ButtonVariant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700',
  outline: 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
  ghost: 'text-slate-600 hover:bg-slate-100',
  success: 'bg-emerald-600 text-white hover:bg-emerald-700',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  dark: 'bg-slate-900 text-white hover:bg-slate-800',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  icon?: LucideIcon
}

export function Button({
  variant = 'primary',
  icon: Icon,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-150 active:scale-[0.96] focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-50 disabled:active:scale-100',
        buttonVariants[variant],
        className,
      )}
      {...props}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {children}
    </button>
  )
}

/* ----------------------------------------------------------------- Badge */

export type BadgeTone =
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'neutral'
  | 'rose'
  | 'amber'
  | 'sky'
  | 'violet'
  | 'teal'

const badgeTones: Record<BadgeTone, string> = {
  success: 'bg-emerald-50 text-emerald-700',
  danger: 'bg-red-50 text-red-600',
  warning: 'bg-amber-50 text-amber-700',
  info: 'bg-brand-50 text-brand-700',
  neutral: 'bg-slate-100 text-slate-600',
  rose: 'bg-rose-50 text-rose-600',
  amber: 'bg-amber-50 text-amber-700',
  sky: 'bg-sky-50 text-sky-700',
  violet: 'bg-violet-50 text-violet-700',
  teal: 'bg-teal-50 text-teal-700',
}

interface BadgeProps {
  tone?: BadgeTone
  children: React.ReactNode
  className?: string
  dot?: boolean
}

export function Badge({ tone = 'neutral', children, className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap',
        badgeTones[tone],
        className,
      )}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

/* ---------------------------------------------------------------- Avatar */

const avatarColors = [
  'bg-brand-100 text-brand-700',
  'bg-rose-100 text-rose-700',
  'bg-amber-100 text-amber-700',
  'bg-emerald-100 text-emerald-700',
  'bg-violet-100 text-violet-700',
  'bg-sky-100 text-sky-700',
  'bg-teal-100 text-teal-700',
]

function initials(name: string): string {
  const parts = name.trim().split(/\s+/)
  return (parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')
}

function colorFor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return avatarColors[Math.abs(hash) % avatarColors.length]
}

interface AvatarProps {
  name: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Avatar({ name, size = 'md', className }: AvatarProps) {
  const sizes = {
    sm: 'w-8 h-8 text-[11px]',
    md: 'w-9 h-9 text-xs',
    lg: 'w-12 h-12 text-sm',
  }
  return (
    <div
      className={cn(
        'grid place-items-center rounded-full font-semibold uppercase shrink-0',
        sizes[size],
        colorFor(name),
        className,
      )}
    >
      {initials(name).toUpperCase()}
    </div>
  )
}

/* ----------------------------------------------------------- ProgressBar */

interface ProgressBarProps {
  value: number // 0..100
  tone?: 'success' | 'warning' | 'danger'
  className?: string
}

export function ProgressBar({ value, tone = 'success', className }: ProgressBarProps) {
  const tones = {
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    danger: 'bg-red-500',
  }
  return (
    <div className={cn('h-2 w-full overflow-hidden rounded-full bg-slate-100', className)}>
      <div
        className={cn('h-full rounded-full transition-all', tones[tone])}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}

/* ---------------------------------------------------------------- Switch */

interface SwitchProps {
  checked: boolean
  onChange: (value: boolean) => void
  disabled?: boolean
  /** Tugmaning ichida matn yo'q — skrinrider uchun nom shu yerdan beriladi. */
  label?: string
}

export function Switch({ checked, onChange, disabled, label }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      data-sound="toggle"
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30',
        checked ? 'bg-brand-600' : 'bg-slate-200',
        disabled && 'cursor-not-allowed opacity-50',
      )}
    >
      <span
        className={cn(
          'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform',
          checked ? 'translate-x-[22px]' : 'translate-x-0.5',
        )}
      />
    </button>
  )
}

/* ------------------------------------------------------------- StatCard */

export interface StatDetailRow {
  label: string
  value: string
  tone?: 'success' | 'danger' | 'neutral'
}

export interface StatDetailData {
  description?: string
  breakdown?: StatDetailRow[]
  linkTo?: string
  linkLabel?: string
}

interface StatCardProps {
  label: string
  value: string
  icon: LucideIcon
  iconTone?: BadgeTone
  delta?: string
  deltaTone?: 'success' | 'danger' | 'neutral'
  hint?: string
  detail?: StatDetailData
}

const iconToneClasses: Record<BadgeTone, string> = {
  success: 'bg-emerald-50 text-emerald-600',
  danger: 'bg-red-50 text-red-500',
  warning: 'bg-amber-50 text-amber-600',
  info: 'bg-brand-50 text-brand-600',
  neutral: 'bg-slate-100 text-slate-500',
  rose: 'bg-rose-50 text-rose-600',
  amber: 'bg-amber-50 text-amber-600',
  sky: 'bg-sky-50 text-sky-600',
  violet: 'bg-violet-50 text-violet-600',
  teal: 'bg-teal-50 text-teal-600',
}

export function StatCard({
  label,
  value,
  icon: Icon,
  iconTone = 'info',
  delta,
  deltaTone = 'neutral',
  hint,
  detail,
}: StatCardProps) {
  const [open, setOpen] = React.useState(false)
  const navigate = useNavigate()
  const deltaClass = {
    success: 'text-emerald-600',
    danger: 'text-red-500',
    neutral: 'text-slate-400',
  }[deltaTone]
  const rowClass = (tone?: 'success' | 'danger' | 'neutral') =>
    tone === 'success' ? 'text-emerald-600' : tone === 'danger' ? 'text-red-500' : 'text-slate-900'

  return (
    <>
      <button
        type="button"
        data-sound="open"
        onClick={() => setOpen(true)}
        className="group w-full rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md active:scale-[0.99]"
      >
        <div className="flex items-start justify-between">
          <div className={cn('grid place-items-center w-10 h-10 rounded-xl', iconToneClasses[iconTone])}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="flex items-center gap-2">
            {delta && <span className={cn('text-xs font-semibold', deltaClass)}>{delta}</span>}
            <ArrowUpRight className="w-4 h-4 text-slate-300 opacity-0 transition-opacity group-hover:opacity-100" />
          </div>
        </div>
        <p className="mt-4 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
        {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
      </button>

      <Modal open={open} onClose={() => setOpen(false)}>
        <div className="p-6">
          <div className="flex items-start gap-4 pr-8">
            <div className={cn('grid place-items-center w-12 h-12 rounded-2xl', iconToneClasses[iconTone])}>
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
              <p className="text-3xl font-bold text-slate-900">{value}</p>
              {(delta || hint) && (
                <p className="mt-0.5 text-sm">
                  {delta && <span className={cn('font-semibold', deltaClass)}>{delta}</span>}
                  {delta && hint && <span className="text-slate-300"> · </span>}
                  {hint && <span className="text-slate-400">{hint}</span>}
                </p>
              )}
            </div>
          </div>

          <p className="mt-5 text-sm leading-relaxed text-slate-600">
            {detail?.description ??
              "Bu ko'rsatkich real vaqt rejimida yangilanib turadi. To'liq ma'lumot uchun tegishli bo'limga o'ting."}
          </p>

          {detail?.breakdown && detail.breakdown.length > 0 && (
            <div className="mt-5 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Taqsimot</p>
              {detail.breakdown.map((row) => (
                <div
                  key={row.label}
                  className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-2.5"
                >
                  <span className="text-sm text-slate-600">{row.label}</span>
                  <span className={cn('text-sm font-semibold', rowClass(row.tone))}>{row.value}</span>
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 flex items-center justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Yopish
            </Button>
            {detail?.linkTo && (
              <Button
                data-sound="nav"
                onClick={() => {
                  setOpen(false)
                  navigate(detail.linkTo!)
                }}
              >
                {detail.linkLabel ?? "Batafsil ko'rish"} →
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  )
}

/* ------------------------------------------------------------ Pagination */

export interface PaginationProps {
  /** Joriy sahifa (1 dan). */
  page: number
  totalPages: number
  /** Jami yozuvlar soni — "1–25 / 105" uchun. */
  count: number
  pageSize: number
  onPageChange: (page: number) => void
  /** Berilsa, sahifa hajmi tanlovi ko'rsatiladi. */
  onPageSizeChange?: (size: number) => void
  pageSizeOptions?: number[]
  className?: string
}

/**
 * Sahifa raqamlari oynasi: 1 … 4 [5] 6 … 12.
 *
 * Har doim birinchi va oxirgi, joriy va uning ikki qo'shnisi
 * ko'rinadi; oraliq `null` (ko'p nuqta) bilan qisqaradi.
 */
function pageWindow(page: number, total: number): Array<number | null> {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = new Set<number>([1, total, page - 1, page, page + 1])
  const sorted = [...pages].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b)
  const result: Array<number | null> = []
  sorted.forEach((n, index) => {
    const previous = sorted[index - 1]
    if (previous !== undefined && n - previous > 1) result.push(null)
    result.push(n)
  })
  return result
}

/**
 * Server sahifalashi uchun boshqaruv (docs/04 §3: `page`, `page_size`).
 *
 * Holat TASHQARIDA yashaydi — komponent faqat chizadi va xabar beradi.
 * Shunda filtr o'zgarganda sahifani 1 ga qaytarish, URL bilan
 * sinxronlash kabi qarorlar chaqiruvchida qoladi.
 */
export function Pagination({
  page,
  totalPages,
  count,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100],
  className,
}: PaginationProps) {
  if (count === 0) return null

  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, count)
  const go = (next: number) => {
    const clamped = Math.min(Math.max(1, next), Math.max(1, totalPages))
    if (clamped !== page) onPageChange(clamped)
  }
  const navButton =
    'grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-500 transition-all hover:bg-slate-50 active:scale-90 disabled:opacity-40 disabled:active:scale-100'

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-sm',
        className,
      )}
    >
      <p className="text-slate-500 tabular-nums">
        <span className="font-medium text-slate-700">
          {from}–{to}
        </span>{' '}
        / {count}
      </p>

      <div className="ml-auto flex items-center gap-2">
        {onPageSizeChange && (
          <select
            aria-label="Sahifadagi qatorlar"
            value={pageSize}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-sm text-slate-600 outline-none focus:border-brand-500"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} tadan
              </option>
            ))}
          </select>
        )}

        {totalPages > 1 && (
          <nav aria-label="Sahifalar" className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => go(page - 1)}
              disabled={page <= 1}
              aria-label="Oldingi sahifa"
              className={navButton}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            {/* Raqamlar — `sm` dan boshlab; telefonda "3 / 12" yetarli. */}
            <div className="hidden items-center gap-1 sm:flex">
              {pageWindow(page, totalPages).map((n, index) =>
                n === null ? (
                  <span key={`gap-${index}`} className="w-6 text-center text-slate-300">
                    …
                  </span>
                ) : (
                  <button
                    key={n}
                    type="button"
                    onClick={() => go(n)}
                    aria-current={n === page ? 'page' : undefined}
                    className={cn(
                      'grid h-9 min-w-9 place-items-center rounded-lg px-2 text-sm font-medium transition-all active:scale-90 tabular-nums',
                      n === page
                        ? 'bg-brand-600 text-white'
                        : 'border border-slate-200 text-slate-500 hover:bg-slate-50',
                    )}
                  >
                    {n}
                  </button>
                ),
              )}
            </div>
            <span className="px-1 text-slate-500 tabular-nums sm:hidden">
              {page} / {totalPages}
            </span>

            <button
              type="button"
              onClick={() => go(page + 1)}
              disabled={page >= totalPages}
              aria-label="Keyingi sahifa"
              className={navButton}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </nav>
        )}
      </div>
    </div>
  )
}

/* --------------------------------------------------------------- Select */

export interface SelectOption {
  label: string
  value: string
}

interface SelectProps {
  label?: string
  options: SelectOption[]
  value?: string
  defaultValue?: string
  onChange?: (value: string) => void
  placeholder?: string
  className?: string
}

/** Custom, animated dropdown (replaces the native <select>) — styled to match
 *  the rest of the UI, keyboard/mouse friendly, closes on outside click. */
export function Select({
  label,
  options,
  value,
  defaultValue,
  onChange,
  placeholder = 'Tanlang',
  className,
}: SelectProps) {
  const [open, setOpen] = React.useState(false)
  const [internal, setInternal] = React.useState<string | undefined>(
    defaultValue ?? options[0]?.value,
  )
  const ref = React.useRef<HTMLDivElement>(null)
  const selectedValue = value ?? internal
  const selected = options.find((o) => o.value === selectedValue)

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const pick = (v: string) => {
    setInternal(v)
    onChange?.(v)
    setOpen(false)
  }

  return (
    <div className="flex flex-col gap-1.5" ref={ref}>
      {label && (
        <label className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          {label}
        </label>
      )}
      <div className={cn('relative', className)}>
        <button
          type="button"
          data-sound="open"
          onClick={() => setOpen((o) => !o)}
          className={cn(
            'flex w-full items-center justify-between gap-2 rounded-lg border bg-white px-3 py-2 text-sm transition-colors',
            open ? 'border-brand-400 ring-2 ring-brand-500/20' : 'border-slate-200 hover:border-slate-300',
          )}
        >
          <span className={selected ? 'text-slate-700' : 'text-slate-400'}>
            {selected?.label ?? placeholder}
          </span>
          <ChevronDown
            className={cn('w-4 h-4 shrink-0 text-slate-400 transition-transform', open && 'rotate-180')}
          />
        </button>

        <AnimatePresence>
          {open && (
            <motion.ul
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="absolute z-30 mt-1.5 w-full overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-xl"
            >
              {options.map((o) => {
                const active = o.value === selectedValue
                return (
                  <li key={o.value}>
                    <button
                      type="button"
                      data-sound="toggle"
                      onClick={() => pick(o.value)}
                      className={cn(
                        'flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors',
                        active
                          ? 'bg-brand-50 font-medium text-brand-700'
                          : 'text-slate-600 hover:bg-slate-50',
                      )}
                    >
                      {o.label}
                      {active && <Check className="w-4 h-4 text-brand-600" />}
                    </button>
                  </li>
                )
              })}
            </motion.ul>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
