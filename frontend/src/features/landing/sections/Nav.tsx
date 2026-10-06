/**
 * Yopishqoq navigatsiya — scroll'dan keyin ixchamlashadi.
 *
 * Telefonda panelda uchta narsa turadi: brend, BITTA haqiqiy chaqiriq va
 * menyu tugmasi. Ilgari u yerda til tanlagich (UZ RU EN) turardi va
 * panelning qariyb yarmini egallardi — ya'ni eng qimmat joy hech kim
 * bosmaydigan tugmaga berilgandi. Til endi menyu ichida, u yerda
 * ko'rinadigan joyi ham, nomi ham bor.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { env } from '@/config/env'
import { Brand } from '@/features/marketing/components/Brand'
import { copy, type Locale } from '../content'
import { basePath } from '../paths'
import { ContactList, HeaderContacts } from '../ui/Contacts'

const LOCALES = ['uz', 'ru', 'en'] as const satisfies readonly Locale[]

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
  //
  // Nishonlar RO'YXATI ham qayta yig'iladi (`MutationObserver`): bo'limlar
  // ekran o'lchamiga qarab boshqa daraxt chizadi, ya'ni kuzatilayotgan
  // element DOM'dan chiqib ketishi mumkin. Avval shu sabab to'q bo'lim
  // ustida panel oq bo'lib qolardi.
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    let observer: IntersectionObserver | null = null
    const overlapping = new Set<Element>()
    const arm = () => {
      observer?.disconnect()
      overlapping.clear()
      setDark(false)
      const targets = Array.from(document.querySelectorAll<HTMLElement>('[data-nav-dark]'))
      if (targets.length === 0) return
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

    let pending = 0
    const rearm = () => {
      window.clearTimeout(pending)
      pending = window.setTimeout(arm, 120)
    }
    const mutations = new MutationObserver(rearm)
    const main = document.querySelector('main')
    if (main) mutations.observe(main, { childList: true, subtree: true })
    window.addEventListener('resize', rearm)
    return () => {
      window.clearTimeout(pending)
      window.removeEventListener('resize', rearm)
      mutations.disconnect()
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
    ['#parents', t.parents],
    ['#pricing', t.pricing],
    ['#faq', t.faq],
  ] as const

  return (
    <>
      <header
        data-dark={dark || undefined}
        className={`group/nav fixed inset-x-0 top-0 z-50 transition-[background-color,box-shadow,backdrop-filter] duration-300 ${
          dark
            ? 'bg-ildiz-900/95 text-white backdrop-blur-md'
            : scrolled || open
              ? 'bg-white/95 shadow-[0_1px_0_0_rgba(27,36,33,0.06)] backdrop-blur-md'
              : 'bg-transparent'
        }`}
      >
        <div
          className={`mx-auto flex max-w-[1280px] items-center justify-between gap-2 px-5 transition-[height] duration-300 lg:px-8 ${
            scrolled ? 'h-[60px]' : 'h-[68px] lg:h-[76px]'
          }`}
        >
          {/*
          Logotipning rangi CSS bilan bo'yalmaydi — brendbuk buni taqiqlaydi.
          To'q bo'lim ustida B varianti (Nihol kvadrat, oq yozuv) chiziladi.
        */}
          {/*
          Balandlik 34 px dan PAST tushmaydi: brendbuk qoidasi bo'yicha
          undan kichik joyda `Logo` yozuvni olib tashlab, faqat belgini
          chizadi (`MIN_FULL_HEIGHT`) — ya'ni 32 px da sayt nomsiz
          qolardi. Chaqiriq esa qisqaradi: ruscha "Попробовать"
          panelni 35 px ga toshirgan edi.
        */}
          <Link to={basePath(locale)} aria-label="Radix CRM" className="shrink-0">
            <Brand variant={dark ? 'dark' : 'light'} height={scrolled ? 34 : 36} />
          </Link>

          <nav aria-label={t.menu} className="hidden items-center gap-1 lg:flex">
            {links.map(([href, label]) => (
              <a
                key={href}
                href={href}
                className="rounded-lg px-3 py-2 text-[15px] font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 group-data-[dark]/nav:text-slate-300 group-data-[dark]/nav:hover:bg-white/10 group-data-[dark]/nav:hover:text-white"
              >
                {label}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-2 lg:flex">
            {/* Aloqa — header'da (PLAN 5.7): raqam keng ekranda matn
              bilan, torroqda belgi; Telegram har doim belgi. */}
            <HeaderContacts locale={locale} />
            <LangSwitch locale={locale} className="mr-2" />
            <a
              href={env.loginUrl}
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-[15px] font-semibold text-slate-800 transition hover:bg-slate-100 group-data-[dark]/nav:text-white group-data-[dark]/nav:hover:bg-white/10"
            >
              {t.login}
              <ArrowUpRight className="h-4 w-4 text-slate-500" />
            </a>
            <a
              href={env.signupUrl}
              className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2 text-[15px] font-semibold text-white transition hover:bg-brand-700"
            >
              {t.trial}
            </a>
          </div>

          {/* Telefon: bitta chaqiriq + menyu. Til menyuning ichida.
            Yozuv qisqa shaklda — toʻlig'i 390 px panelni toshirardi. */}
          <div className="flex min-w-0 items-center gap-1.5 sm:gap-2 lg:hidden">
            <a
              href={env.signupUrl}
              className="inline-flex h-10 min-w-0 max-w-[46vw] shrink items-center justify-center overflow-hidden text-ellipsis whitespace-nowrap rounded-lg bg-brand-600 px-3 text-[14px] font-semibold text-white"
            >
              {t.trialShort}
            </a>
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
      </header>

      {/*
        Menyu header'ning ICHIDA emas — bu tuzatish, ko'rinish emas.
        Header'da `backdrop-filter: blur()` bor, filtrli element esa
        `fixed` bolalari uchun yangi "containing block" yaratadi: panel
        ekranga emas, 60 px balandlikdagi panelga nisbatan joylashib,
        atigi 48 px bo'lib qolardi va menyuning deyarli hammasi
        ko'rinmasdi. Birodar element sifatida u yana ekranga bog'lanadi.
      */}
      {open && (
        // `100dvh` emas, `inset-0` + `top` — brauzer paneli yig'ilganda
        // menyu ekrandan chiqib ketmasin; pastda esa barmoq uchun joy
        // (`safe-area`), aks holda oxirgi havola iPhone chizig'i ostida
        // qolardi.
        <div
          className={`fixed inset-x-0 bottom-0 z-40 overflow-y-auto overscroll-contain bg-white px-5 pb-[calc(2rem+env(safe-area-inset-bottom))] pt-4 lg:hidden ${
            scrolled ? 'top-[60px]' : 'top-[68px]'
          }`}
        >
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
              href={env.signupUrl}
              className="inline-flex min-h-[52px] items-center justify-center rounded-xl bg-brand-600 text-base font-semibold text-white"
            >
              {t.trial}
            </a>
            <a
              href="#demo"
              onClick={() => setOpen(false)}
              className="inline-flex min-h-[52px] items-center justify-center rounded-xl border border-slate-200 text-base font-semibold text-slate-800"
            >
              {t.demo}
            </a>
            <a
              href={env.loginUrl}
              className="inline-flex min-h-[52px] items-center justify-center gap-1 rounded-xl text-base font-semibold text-slate-600"
            >
              {t.login}
              <ArrowUpRight className="h-4 w-4 text-slate-500" />
            </a>
          </div>
          <LangSwitch locale={locale} className="mt-6 w-full justify-between" />
          {/* Telefonda header'ga joy yo'q — aloqa menyuning oxirida. */}
          <ContactList locale={locale} className="mt-8 border-t border-slate-100 px-1 pt-6" />
        </div>
      )}
    </>
  )
}

/**
 * Til tanlagich — uch til bitta guruhda. Havola (`<Link>`), tugma emas:
 * har til o'z manzilida (`/uz`, `/ru`, `/en`) va qidiruv tizimi ham shu
 * havolalarni ko'radi. Telefonda u menyu ichida, to'liq enlikda —
 * barmoq uchun 44px dan baland.
 */
function LangSwitch({ locale, className = '' }: { locale: Locale; className?: string }) {
  const t = copy[locale].nav
  return (
    <nav
      aria-label={t.language}
      className={`flex items-center rounded-lg border border-slate-200 p-0.5 text-[13px] font-semibold group-data-[dark]/nav:border-white/20 ${className}`}
    >
      {LOCALES.map((l) => (
        <Link
          key={l}
          to={basePath(l)}
          hrefLang={l}
          aria-current={l === locale ? 'page' : undefined}
          className={`grid min-h-[44px] flex-1 place-items-center rounded-md px-2.5 transition lg:min-h-0 lg:flex-none lg:py-1 ${
            l === locale
              ? 'bg-slate-950 text-white group-data-[dark]/nav:bg-white group-data-[dark]/nav:text-slate-950'
              : 'text-slate-500 hover:text-slate-950 group-data-[dark]/nav:text-slate-300 group-data-[dark]/nav:hover:text-white'
          }`}
        >
          {t.lang[l]}
        </Link>
      ))}
    </nav>
  )
}
