/**
 * Sticky sarlavha.
 *
 * Scroll boshlanishi bilan fon quyuqlashadi — bu shunchaki effekt emas:
 * hero'ning ochiq foni ustida shaffof sarlavha o'qilmay qolardi.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { env } from '@/config/env'
import { cn } from '@/lib/utils'
import { Brand } from '../components/Brand'
import { copy, type Locale } from '../content'

export function Header({ locale }: { locale: Locale }) {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const t = copy[locale]
  const switchTo = locale === 'uz' ? 'ru' : 'uz'

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const nav = [
    ['#product', t.nav.product],
    ['#capabilities', t.nav.capabilities],
    ['#pricing', t.nav.pricing],
    ['#faq', t.nav.faq],
  ] as const

  // Ko'rinadigan matn qisqa ("RU"), ammo KIRISH NOMI to'liq: skrin-rider
  // "RU" ni o'qiganda foydalanuvchi bu til almashtirgich ekanini bilmaydi.
  const switchLabel = locale === 'uz' ? 'Русский' : "O‘zbekcha"
  const menuLabel = open
    ? locale === 'uz'
      ? 'Menyuni yopish'
      : 'Закрыть меню'
    : locale === 'uz'
      ? 'Menyuni ochish'
      : 'Открыть меню'

  return (
    <header
      className={cn(
        'sticky top-0 z-40 transition-colors duration-300',
        scrolled
          ? 'border-b border-slate-200/70 bg-white/85 backdrop-blur-xl'
          : 'border-b border-transparent bg-transparent',
      )}
    >
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 lg:px-8">
        <Link to={`/${locale}`} aria-label="Radix CRM">
          <Brand />
        </Link>

        <nav className="hidden items-center gap-7 lg:flex" aria-label="Asosiy navigatsiya">
          {nav.map(([href, label]) => (
            <a
              key={href}
              className="text-sm font-medium text-slate-600 transition hover:text-slate-950"
              href={href}
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <Link
            className="rounded-lg px-2.5 py-2 text-sm font-semibold text-slate-500 transition hover:text-slate-950"
            to={`/${switchTo}`}
            aria-label={switchLabel}
          >
            {locale === 'uz' ? 'RU' : 'UZ'}
          </Link>
          <a
            className="rounded-xl px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            href={env.appUrl}
          >
            {t.nav.login}
          </a>
          <a
            className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-px hover:bg-slate-800 hover:shadow-md"
            href="#demo"
          >
            {t.nav.demo}
          </a>
        </div>

        <button
          className="rounded-lg p-2 text-slate-700 lg:hidden"
          aria-label={menuLabel}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-100 bg-white px-5 py-4 lg:hidden">
          <nav className="grid gap-1" aria-label="Mobil navigatsiya">
            {nav.map(([href, label]) => (
              <a
                key={href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                href={href}
              >
                {label}
              </a>
            ))}
            <Link
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              to={`/${switchTo}`}
            >
              {switchLabel}
            </Link>
            <a
              className="mt-2 rounded-xl bg-slate-950 px-4 py-3 text-center text-sm font-semibold text-white"
              href={env.appUrl}
            >
              {t.nav.login}
            </a>
          </nav>
        </div>
      )}
    </header>
  )
}
