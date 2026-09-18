/**
 * Yopishqoq navigatsiya — scroll'dan keyin ixchamlashadi.
 *
 * Shaffof yuza + blur faqat scroll'dan keyin: birinchi ekranda u sof oq,
 * chunki hero'ning o'zi oq va blur hech narsani yaxshilamaydi.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { env } from '@/config/env'
import { Brand } from '@/features/marketing/components/Brand'
import { copy, type Locale } from '../content'
import { basePath } from '../paths'

export function Nav({ locale }: { locale: Locale }) {
  const t = copy[locale].nav
  const [scrolled, setScrolled] = useState(false)
  const [dark, setDark] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // To'q fondagi bo'lim (`data-nav-dark`) navigatsiya ostiga kelganda
  // panel ham to'qlashadi — oq matn oq yuzada yo'qolmasin, to'q bo'lim
  // ustida och yuza "yopishtirilgan" ko'rinmasin. Kuzatuv maydoni —
  // faqat ekranning yuqori 60px chizig'i.
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const targets = Array.from(document.querySelectorAll<HTMLElement>('[data-nav-dark]'))
    if (targets.length === 0) return
    let observer: IntersectionObserver | null = null
    const overlapping = new Set<Element>()
    const arm = () => {
      observer?.disconnect()
      overlapping.clear()
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) overlapping.add(entry.target)
            else overlapping.delete(entry.target)
          }
          setDark(overlapping.size > 0)
        },
        { rootMargin: `0px 0px -${Math.max(0, window.innerHeight - 60)}px 0px`, threshold: 0 },
      )
      targets.forEach((el) => observer?.observe(el))
    }
    arm()
    window.addEventListener('resize', arm)
    return () => {
      window.removeEventListener('resize', arm)
      observer?.disconnect()
    }
  }, [])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])

  const links = [
    ['#product', t.product],
    ['#capabilities', t.capabilities],
    ['#pricing', t.pricing],
    ['#faq', t.faq],
  ] as const

  const other: Locale = locale === 'uz' ? 'ru' : 'uz'

  return (
    <header
      data-dark={dark || undefined}
      className={`group/nav fixed inset-x-0 top-0 z-50 transition-[background-color,box-shadow,backdrop-filter] duration-300 ${
        dark
          ? 'bg-[#0B1730]/85 text-white backdrop-blur-md'
          : scrolled
            ? 'bg-white/85 shadow-[0_1px_0_0_rgba(15,23,42,0.06)] backdrop-blur-md'
            : 'bg-transparent'
      }`}
    >
      <div
        className={`mx-auto flex max-w-[1280px] items-center justify-between px-5 transition-[height] duration-300 lg:px-8 ${
          scrolled ? 'h-[60px]' : 'h-[76px]'
        }`}
      >
        <Link
          to={basePath(locale)}
          aria-label="Radix CRM"
          className="shrink-0 group-data-[dark]/nav:[&>span]:text-white group-data-[dark]/nav:[&>span>span:first-child]:bg-white group-data-[dark]/nav:[&>span>span:first-child]:text-slate-950"
        >
          <Brand />
        </Link>

        <nav aria-label="Asosiy" className="hidden items-center gap-1 lg:flex">
          {links.map(([href, label]) => (
            <a
              key={href}
              href={href}
              className="rounded-lg px-3.5 py-2 text-[15px] font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 group-data-[dark]/nav:text-slate-300 group-data-[dark]/nav:hover:bg-white/10 group-data-[dark]/nav:hover:text-white"
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <div className="mr-2 flex items-center rounded-lg border border-slate-200 p-0.5 text-[13px] font-semibold group-data-[dark]/nav:border-white/20">
            {(['uz', 'ru'] as const).map((l) => (
              <Link
                key={l}
                to={basePath(l)}
                aria-current={l === locale ? 'page' : undefined}
                className={`rounded-md px-2.5 py-1 transition ${
                  l === locale
                    ? 'bg-slate-950 text-white group-data-[dark]/nav:bg-white group-data-[dark]/nav:text-slate-950'
                    : 'text-slate-500 hover:text-slate-950 group-data-[dark]/nav:text-slate-300 group-data-[dark]/nav:hover:text-white'
                }`}
              >
                {t.lang[l]}
              </Link>
            ))}
          </div>
          <a
            href={env.loginUrl}
            className="inline-flex items-center gap-1 rounded-lg px-3.5 py-2 text-[15px] font-semibold text-slate-800 transition hover:bg-slate-100 group-data-[dark]/nav:text-white group-data-[dark]/nav:hover:bg-white/10"
          >
            {t.login}
            <ArrowUpRight className="h-4 w-4 text-slate-400" />
          </a>
          <a
            href="#demo"
            className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2 text-[15px] font-semibold text-white transition hover:bg-brand-700"
          >
            {t.demo}
          </a>
        </div>

        <div className="flex items-center gap-2 lg:hidden">
          <Link
            to={basePath(other)}
            className="grid h-11 min-w-11 place-items-center rounded-lg border border-slate-200 px-2 text-[13px] font-semibold text-slate-700 group-data-[dark]/nav:border-white/20 group-data-[dark]/nav:text-white"
          >
            {t.lang[other]}
          </Link>
          <button
            type="button"
            aria-expanded={open}
            aria-label={open ? t.close : t.menu}
            onClick={() => setOpen((v) => !v)}
            className="grid h-11 w-11 place-items-center rounded-lg text-slate-800 hover:bg-slate-100 group-data-[dark]/nav:text-white group-data-[dark]/nav:hover:bg-white/10"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="fixed inset-x-0 bottom-0 top-[60px] z-40 overflow-y-auto bg-white px-5 pb-8 pt-4 lg:hidden">
          <nav className="grid gap-1" aria-label={t.menu}>
            {links.map(([href, label]) => (
              <a
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className="rounded-xl px-4 py-3.5 text-lg font-semibold text-slate-900 hover:bg-slate-50"
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="mt-6 grid gap-3">
            <a
              href="#demo"
              onClick={() => setOpen(false)}
              className="inline-flex min-h-[52px] items-center justify-center rounded-xl bg-brand-600 text-base font-semibold text-white"
            >
              {t.demo}
            </a>
            <a
              href={env.loginUrl}
              className="inline-flex min-h-[52px] items-center justify-center rounded-xl border border-slate-200 text-base font-semibold text-slate-800"
            >
              {t.login}
            </a>
          </div>
        </div>
      )}
    </header>
  )
}
