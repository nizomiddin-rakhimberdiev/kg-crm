import { useEffect, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  BarChart3,
  Boxes,
  CalendarCheck,
  Check,
  ChevronDown,
  CircleDollarSign,
  ClipboardList,
  FileBarChart,
  LayoutDashboard,
  Menu,
  ShieldCheck,
  UsersRound,
  WalletCards,
  X,
} from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { env } from '@/config/env'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { marketingApi } from '../api'
import { copy, type Locale } from '../content'

const POLICY_VERSION = '2026-09'
const featureIcons = [UsersRound, WalletCards, CalendarCheck, ClipboardList, Boxes, FileBarChart]

const newSubmissionId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

// CRM ichidagi `formatUZS()` bu yerga mos emas: u vergul bilan
// ajratadi va "UZS" qo'shadi ("400,000 UZS") — bu ichki
// boshqaruv panelining formati. Public sahifadagi tarjima matni
// (content.ts) esa bo'sh joy bilan ajratadi va "so'm"/"сум"
// so'zini ishlatadi ("400 000 so'm"). Ikkalasini aralashtirish
// kalkulyatorni FAQ matni yonida nomuvofiq ko'rsatardi — aynan
// "premium, izchil" taassurotni buzadigan turdagi detal.
const CURRENCY_WORD: Record<Locale, string> = { uz: "so‘m", ru: "сум" }
const groupThousands = (value: number) => Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
const amount = (value: string | undefined, locale: Locale) =>
  value ? `${groupThousands(Number(value))} ${CURRENCY_WORD[locale]}` : '—'

function upsertMeta(selector: string, attribute: 'name' | 'property', key: string, value: string) {
  let element = document.head.querySelector<HTMLMetaElement>(selector)
  if (!element) {
    element = document.createElement('meta')
    element.setAttribute(attribute, key)
    document.head.appendChild(element)
  }
  element.content = value
}

function PublicSeo({ locale, page = 'home' }: { locale: Locale; page?: 'home' | 'privacy' | 'terms' }) {
  const t = copy[locale]
  useEffect(() => {
    const suffix = page === 'privacy' ? t.legal.privacy : page === 'terms' ? t.legal.terms : t.hero.title
    const title = `Radix CRM — ${suffix}`
    const description = page === 'home' ? t.hero.text : `${suffix} — Radix CRM.`
    const canonical = `https://radix-crm.uz/${locale}${page === 'home' ? '' : `/${page}`}`
    document.title = title
    document.documentElement.lang = locale
    upsertMeta('meta[name="description"]', 'name', 'description', description)
    upsertMeta('meta[property="og:title"]', 'property', 'og:title', title)
    upsertMeta('meta[property="og:description"]', 'property', 'og:description', description)
    upsertMeta('meta[property="og:type"]', 'property', 'og:type', 'website')
    upsertMeta('meta[name="twitter:card"]', 'name', 'twitter:card', 'summary')
    let link = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    if (!link) {
      link = document.createElement('link')
      link.rel = 'canonical'
      document.head.appendChild(link)
    }
    link.href = canonical
  }, [locale, page, t])
  return null
}

function Brand() {
  return (
    <span className="inline-flex items-center gap-2.5 font-bold tracking-tight text-slate-950">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-slate-950 text-white shadow-sm">
        <span className="text-base font-black">R</span>
      </span>
      <span>Radix CRM</span>
    </span>
  )
}

function Header({ locale }: { locale: Locale }) {
  const [open, setOpen] = useState(false)
  const t = copy[locale]
  const switchTo = locale === 'uz' ? 'ru' : 'uz'
  const nav = [
    ['#product', t.nav.product],
    ['#capabilities', t.nav.capabilities],
    ['#pricing', t.nav.pricing],
    ['#faq', t.nav.faq],
  ] as const
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 lg:px-8">
        <Link to={`/${locale}`} aria-label="Radix CRM"><Brand /></Link>
        <nav className="hidden items-center gap-6 lg:flex" aria-label="Asosiy navigatsiya">
          {nav.map(([href, label]) => <a key={href} className="text-sm font-medium text-slate-600 transition hover:text-slate-950" href={href}>{label}</a>)}
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          <Link className="rounded-lg px-2 py-2 text-sm font-semibold text-slate-600 hover:text-slate-950" to={`/${switchTo}`}>{locale === 'uz' ? 'Русский' : "O‘zbekcha"}</Link>
          <a className="rounded-xl px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100" href={env.appUrl}>{t.nav.login}</a>
          <a className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800" href="#demo">{t.nav.demo}</a>
        </div>
        <button className="rounded-lg p-2 text-slate-700 lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-slate-100 bg-white px-5 py-4 lg:hidden">
          <nav className="grid gap-1" aria-label="Mobile navigation">
            {nav.map(([href, label]) => <a key={href} onClick={() => setOpen(false)} className="rounded-lg px-3 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50" href={href}>{label}</a>)}
            <Link onClick={() => setOpen(false)} className="rounded-lg px-3 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50" to={`/${switchTo}`}>{locale === 'uz' ? 'Русский' : "O‘zbekcha"}</Link>
            <a className="mt-2 rounded-xl bg-slate-950 px-4 py-3 text-center text-sm font-semibold text-white" href={env.appUrl}>{t.nav.login}</a>
          </nav>
        </div>
      )}
    </header>
  )
}

function ProductPreview({ locale }: { locale: Locale }) {
  const t = copy[locale].preview
  return (
    <section id="product" className="scroll-mt-24 py-20 lg:py-28">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[.82fr_1.18fr] lg:items-center lg:px-8">
        <div>
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4">{t.title}</h2>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">{t.text}</p>
        </div>
        <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-slate-950 p-2 shadow-2xl shadow-slate-900/15">
          <div className="overflow-hidden rounded-[21px] bg-slate-50">
            <div className="flex h-12 items-center gap-2 border-b border-slate-200 bg-white px-4">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-300" /><span className="h-2.5 w-2.5 rounded-full bg-slate-300" /><span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
              <div className="ml-3 rounded-md bg-slate-100 px-3 py-1 text-[10px] font-medium text-slate-400">app.radix-crm.uz/dashboard</div>
            </div>
            <div className="grid min-h-[390px] grid-cols-[128px_1fr] sm:grid-cols-[158px_1fr]">
              <aside className="hidden border-r border-slate-200 bg-white p-4 sm:block">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-900"><span className="grid h-6 w-6 place-items-center rounded-md bg-brand-600 text-white">R</span> Radix CRM</div>
                <div className="mt-7 space-y-2">{['Dashboard', 'Bolalar', 'To‘lovlar', 'Davomat', 'Hisobotlar'].map((label, index) => <div key={label} className={cn('rounded-md px-2 py-1.5 text-[10px] font-medium', index === 0 ? 'bg-brand-50 text-brand-700' : 'text-slate-400')}>{label}</div>)}</div>
              </aside>
              <div className="p-4 sm:p-6">
                <div className="flex items-start justify-between"><div><p className="text-lg font-bold tracking-tight text-slate-900">{t.live}</p><p className="mt-1 text-[10px] text-slate-400">Radix CRM</p></div><span className="rounded-full bg-emerald-50 px-2 py-1 text-[9px] font-semibold text-emerald-700">● {locale === 'uz' ? 'Faol' : 'Активно'}</span></div>
                <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
                  {[[t.revenue, '18 500 000', 'text-brand-700 bg-brand-50'], [t.debt, '2 400 000', 'text-amber-700 bg-amber-50'], [t.attendance, '91%', 'text-emerald-700 bg-emerald-50'], [t.children, '142', 'text-violet-700 bg-violet-50']].map(([label, value, color]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-3 shadow-card"><span className={cn('inline-grid h-7 w-7 place-items-center rounded-lg text-xs', color)}>●</span><p className="mt-3 text-[9px] font-medium text-slate-400">{label}</p><p className="mt-1 text-sm font-bold text-slate-900">{value}</p></div>)}
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-[1.35fr_.65fr]"><div className="rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center justify-between"><p className="text-xs font-bold text-slate-800">{locale === 'uz' ? 'Moliyaviy dinamika' : 'Финансовая динамика'}</p><BarChart3 className="h-4 w-4 text-brand-600" /></div><div className="mt-6 flex h-28 items-end gap-2">{[34, 56, 43, 76, 61, 90, 79, 100].map((height, index) => <span key={index} className={cn('flex-1 rounded-t bg-brand-100', index === 7 && 'bg-brand-600')} style={{ height: `${height}%` }} />)}</div></div><div className="rounded-xl border border-slate-200 bg-white p-4"><p className="text-xs font-bold text-slate-800">{locale === 'uz' ? 'So‘nggi to‘lovlar' : 'Последние платежи'}</p><div className="mt-4 space-y-3">{['M. Karimova', 'A. Ismoilov', 'N. Rustamov'].map((name) => <div key={name} className="flex items-center justify-between text-[10px]"><span className="text-slate-500">{name}</span><span className="font-semibold text-emerald-700">+ 1 500 000</span></div>)}</div></div></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function PricingCalculator({ locale }: { locale: Locale }) {
  const t = copy[locale].pricing
  const [children, setChildren] = useState(50)
  const quote = useQuery({ queryKey: ['public-pricing', children], queryFn: () => marketingApi.pricing(children), staleTime: 60_000 })
  const data = quote.data
  return (
    <section id="pricing" className="scroll-mt-24 bg-slate-950 py-20 text-white lg:py-28">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[.9fr_1.1fr] lg:items-end lg:px-8">
        <div><p className="eyebrow !text-brand-300">{t.eyebrow}</p><h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">{t.title}</h2><p className="mt-5 max-w-xl leading-7 text-slate-300">{t.text}</p><div className="mt-8 border-l border-brand-400 pl-4 text-sm leading-6 text-slate-300">{t.policy}</div></div>
        <div className="rounded-[28px] bg-white p-5 text-slate-900 shadow-2xl shadow-black/20 sm:p-7">
          <label className="text-sm font-bold" htmlFor="children-count">{t.children}</label>
          <div className="mt-4 flex items-center gap-4"><input id="children-count" className="w-24 rounded-xl border border-slate-300 px-3 py-2.5 text-lg font-bold outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10" type="number" min="1" max="10000" value={children} onChange={(event) => setChildren(Math.max(1, Math.min(10000, Number(event.target.value) || 1)))} /><span className="text-sm text-slate-500">{locale === 'uz' ? 'bola' : 'детей'}</span></div>
          <input className="mt-5 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600" type="range" min="1" max="500" value={Math.min(children, 500)} onChange={(event) => setChildren(Number(event.target.value))} aria-label={locale === 'uz' ? 'Bolalar sonini slayder bilan sozlash' : 'Настроить количество детей ползунком'} />
          <div className="mt-7 grid gap-3 sm:grid-cols-3"><PriceCell label={t.monthly} value={quote.isLoading ? t.loading : amount(data?.monthly.total_amount, locale)} /><PriceCell label={t.annual} value={quote.isLoading ? t.loading : amount(data?.annual.total_amount, locale)} highlight /><PriceCell label={t.saving} value={quote.isLoading ? t.loading : amount(data?.annual_saving, locale)} /></div>
          <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-500"><span>{t.before}</span><strong className="text-slate-700">{quote.isLoading ? '—' : amount(data?.annual_before_discount, locale)}</strong></div>
          {quote.isError && <p role="alert" className="mt-3 text-xs text-red-600">{locale === 'uz' ? 'Hisobni yuklab bo‘lmadi. Qayta urinib ko‘ring.' : 'Не удалось загрузить расчёт. Попробуйте ещё раз.'}</p>}
          <p className="mt-5 text-xs leading-5 text-slate-400">{t.disclaimer}</p>
        </div>
      </div>
    </section>
  )
}

function PriceCell({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return <div className={cn('rounded-2xl p-4', highlight ? 'bg-brand-600 text-white' : 'bg-slate-50')}><p className={cn('text-xs font-medium', highlight ? 'text-brand-100' : 'text-slate-500')}>{label}</p><p className="mt-2 text-lg font-bold tracking-tight">{value}</p></div>
}

function LeadForm({ locale }: { locale: Locale }) {
  const t = copy[locale].form
  const [submissionId, setSubmissionId] = useState(newSubmissionId)
  const [state, setState] = useState<'idle' | 'sending' | 'success' | 'error'>('idle')
  const [error, setError] = useState('')
  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    // Forma ELEMENTINING O'ZI `await` dan OLDIN saqlanadi.
    //
    // `event.currentTarget` — React SyntheticEvent'ning xossasi, u
    // hodisa tarqatilishi tugagach `null` bo'ladi (bu haqiqiy DOM
    // xatti-harakati: brauzerning o'zida ham `currentTarget` faqat
    // sinxron dispatch paytida amal qiladi). `await`dan KEYIN unga
    // murojaat qilish — `formEl.reset()` — har doim `TypeError`
    // ko'tarardi, HATTO lead backend'da muvaffaqiyatli yaratilgan
    // taqdirda ham. Natija: har bir haqiqiy zayavka foydalanuvchiga
    // "Zayavkani yuborib bo'lmadi" deb ko'rsatilardi — pastdagi
    // `catch` bloki bu xatoni ushlab, muvaffaqiyatni xatoga
    // aylantirardi. Bu faqat testda emas, HAQIQIY brauzerda ham
    // sodir bo'ladigan xato edi.
    const formEl = event.currentTarget
    const form = new FormData(formEl)
    setState('sending'); setError('')
    try {
      await marketingApi.createLead({
        name: String(form.get('name') ?? ''), phone: String(form.get('phone') ?? ''), kindergarten_name: String(form.get('kindergarten_name') ?? ''), children_count: Number(form.get('children_count')), city: String(form.get('city') ?? ''), message: String(form.get('message') ?? ''), language: locale, consent: form.get('consent') === 'on', privacy_policy_version: POLICY_VERSION, submission_id: submissionId, website: String(form.get('website') ?? ''),
      })
      setState('success'); formEl.reset(); setSubmissionId(newSubmissionId())
    } catch (reason) {
      setState('error'); setError(reason instanceof ApiError ? reason.message : t.error)
    }
  }
  const fields = [['name', t.name, 'text'], ['phone', t.phone, 'tel'], ['kindergarten_name', t.kindergarten, 'text'], ['children_count', t.children, 'number'], ['city', t.city, 'text']] as const
  return <section id="demo" className="scroll-mt-24 py-20 lg:py-28"><div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[.78fr_1.22fr] lg:px-8"><div><p className="eyebrow">{t.eyebrow}</p><h2 className="section-title mt-4">{t.title}</h2><p className="mt-5 max-w-md leading-7 text-slate-600">{t.text}</p><div className="mt-8 flex items-center gap-3 text-sm text-slate-600"><ShieldCheck className="h-5 w-5 text-emerald-600" />{locale === 'uz' ? 'Faqat demo zayavkasini ko‘rib chiqish uchun.' : 'Только для обработки заявки на демо.'}</div></div><form className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-card sm:p-7" onSubmit={onSubmit}>{state === 'success' ? <div role="status" className="grid min-h-72 place-items-center text-center"><div><span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-50 text-emerald-600"><Check /></span><p className="mt-4 text-lg font-bold">{t.success}</p></div></div> : <><div className="grid gap-4 sm:grid-cols-2">{fields.map(([name, label, type]) => <label key={name} className={name === 'kindergarten_name' || name === 'city' ? '' : ''}>{label}<input required min={name === 'children_count' ? 1 : undefined} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3.5 py-3 text-sm outline-none transition placeholder:text-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10" name={name} type={type} inputMode={name === 'phone' ? 'tel' : name === 'children_count' ? 'numeric' : undefined} /></label>)}</div><label className="mt-4 block">{t.message}<textarea className="mt-1.5 min-h-24 w-full resize-y rounded-xl border border-slate-200 px-3.5 py-3 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10" name="message" maxLength={1000} /></label><label className="sr-only" aria-hidden="true">Website<input tabIndex={-1} autoComplete="off" name="website" /></label><label className="mt-5 flex cursor-pointer items-start gap-3 text-sm leading-5 text-slate-600"><input required className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-brand-600" type="checkbox" name="consent" /><span>{t.consent} <Link className="font-semibold text-brand-700 underline underline-offset-2" to={`/${locale}/privacy`}>{t.privacy}</Link></span></label>{state === 'error' && <p role="alert" className="mt-4 text-sm text-red-600">{error || t.error}</p>}<button disabled={state === 'sending'} className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60">{state === 'sending' ? t.sending : t.submit}<ArrowRight className="h-4 w-4" /></button></>}</form></div></section>
}

function Footer({ locale }: { locale: Locale }) {
  const t = copy[locale].footer
  return <footer className="border-t border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-10 sm:flex-row sm:items-end sm:justify-between lg:px-8"><div><Brand /><p className="mt-3 max-w-sm text-sm leading-6 text-slate-500">{t.product}</p></div><div className="flex flex-wrap gap-x-5 gap-y-3 text-sm font-medium text-slate-600"><Link to={`/${locale}/privacy`}>{t.privacy}</Link><Link to={`/${locale}/terms`}>{t.terms}</Link><a href={env.appUrl}>{t.login}</a></div></div><div className="mx-auto max-w-7xl border-t border-slate-100 px-5 py-5 text-xs text-slate-400 lg:px-8">{t.copyright}</div></footer>
}

export function MarketingPage({ locale }: { locale: Locale }) {
  const t = copy[locale]
  return <div className="marketing bg-white text-slate-900"><PublicSeo locale={locale} /><Header locale={locale} /><main><section className="overflow-hidden bg-[radial-gradient(circle_at_78%_22%,rgba(37,99,235,.12),transparent_25%),linear-gradient(180deg,#f8fbff_0%,#fff_72%)]"><div className="mx-auto grid max-w-7xl gap-12 px-5 py-20 lg:grid-cols-[.95fr_1.05fr] lg:items-center lg:px-8 lg:py-28"><div><p className="eyebrow">{t.hero.eyebrow}</p><h1 className="mt-5 max-w-2xl text-4xl font-bold tracking-[-.04em] text-slate-950 sm:text-5xl lg:text-6xl">{t.hero.title}</h1><p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">{t.hero.text}</p><div className="mt-8 flex flex-col gap-3 sm:flex-row"><a className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-slate-900/15 transition hover:bg-slate-800" href="#demo">{t.hero.primary}<ArrowRight className="h-4 w-4" /></a><a className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300" href="#capabilities">{t.hero.secondary}</a></div><p className="mt-5 text-xs text-slate-500">{t.hero.note}</p></div><div className="relative"><div className="absolute -inset-10 -z-0 rounded-full bg-brand-100/50 blur-3xl" /><div className="relative rounded-[30px] border border-slate-200 bg-white p-5 shadow-2xl shadow-brand-900/10"><div className="flex items-center justify-between border-b border-slate-100 pb-4"><Brand /><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700">{locale === 'uz' ? 'Boshqaruv markazi' : 'Центр управления'}</span></div><div className="mt-5 grid grid-cols-2 gap-3"><HeroMetric icon={CircleDollarSign} label={t.preview.revenue} value="18.5M" /><HeroMetric icon={UsersRound} label={t.preview.children} value="142" /><HeroMetric icon={CalendarCheck} label={t.preview.attendance} value="91%" /><HeroMetric icon={LayoutDashboard} label={t.preview.live} value="4" /></div><div className="mt-4 rounded-2xl bg-slate-950 p-5 text-white"><p className="text-xs text-slate-400">{locale === 'uz' ? 'Bugungi ustuvor vazifalar' : 'Задачи на сегодня'}</p><div className="mt-4 space-y-3">{[locale === 'uz' ? 'Davomatni yakunlash' : 'Завершить посещаемость', locale === 'uz' ? 'Qarzdorlikni ko‘rib chiqish' : 'Проверить задолженность', locale === 'uz' ? 'Ombor qoldig‘ini tekshirish' : 'Проверить остатки склада'].map((label) => <div key={label} className="flex items-center gap-3 text-sm"><span className="h-2 w-2 rounded-full bg-brand-400" />{label}</div>)}</div></div></div></div></div></section><div className="border-y border-slate-100 bg-slate-50"><p className="mx-auto max-w-7xl px-5 py-5 text-center text-sm font-medium text-slate-600 lg:px-8">{t.proof}</p></div><section className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28"><p className="eyebrow">{t.problems.eyebrow}</p><h2 className="section-title mt-4 max-w-3xl">{t.problems.title}</h2><div className="mt-10 grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 md:grid-cols-2">{t.problems.items.map((problem, index) => <div key={problem} className="bg-white p-6"><span className="text-xs font-bold text-brand-600">0{index + 1}</span><p className="mt-3 leading-7 text-slate-600">{problem}</p></div>)}</div></section><section id="capabilities" className="scroll-mt-24 bg-slate-50 py-20 lg:py-28"><div className="mx-auto max-w-7xl px-5 lg:px-8"><p className="eyebrow">{t.solution.eyebrow}</p><div className="mt-4 grid gap-5 lg:grid-cols-2"><h2 className="section-title">{t.solution.title}</h2><p className="max-w-xl self-end leading-7 text-slate-600">{t.solution.text}</p></div><h3 className="mt-14 text-xl font-bold tracking-tight">{t.featureTitle}</h3><div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{t.features.map((feature, index) => { const Icon = featureIcons[index]; return <article key={feature.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card"><span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-700"><Icon className="h-5 w-5" /></span><h4 className="mt-5 font-bold">{feature.title}</h4><p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p></article> })}</div></div></section><ProductPreview locale={locale} /><section className="bg-brand-50 py-20 lg:py-28"><div className="mx-auto max-w-7xl px-5 lg:px-8"><p className="eyebrow">{t.steps.eyebrow}</p><h2 className="section-title mt-4">{t.steps.title}</h2><div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">{t.steps.items.map((step) => <article key={step.title} className="rounded-2xl border border-brand-100 bg-white p-6"><p className="text-sm font-bold text-brand-700">{step.title}</p><p className="mt-4 text-sm leading-6 text-slate-600">{step.text}</p></article>)}</div></div></section><PricingCalculator locale={locale} /><section id="faq" className="scroll-mt-24 mx-auto max-w-4xl px-5 py-20 lg:py-28"><p className="eyebrow">{t.faq.eyebrow}</p><h2 className="section-title mt-4">{t.faq.title}</h2><div className="mt-10 divide-y divide-slate-200 border-y border-slate-200">{t.faq.items.map((item) => <details key={item.title} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-bold text-slate-900">{item.title}<ChevronDown className="h-5 w-5 shrink-0 text-slate-400 transition group-open:rotate-180" /></summary><p className="max-w-3xl pt-3 leading-7 text-slate-600">{item.text}</p></details>)}</div></section><LeadForm locale={locale} /></main><Footer locale={locale} /></div>
}

function HeroMetric({ icon: Icon, label, value }: { icon: typeof BarChart3; label: string; value: string }) {
  return <div className="rounded-xl border border-slate-100 bg-slate-50 p-3"><Icon className="h-4 w-4 text-brand-600" /><p className="mt-3 text-[10px] font-medium text-slate-400">{label}</p><p className="mt-1 text-lg font-bold tracking-tight">{value}</p></div>
}

export function MarketingEntry() {
  const host = window.location.hostname
  return host === env.publicHost || host === `www.${env.publicHost}` ? <Navigate replace to="/uz" /> : <Navigate replace to="/dashboard" />
}

export function LegalPage({ locale, page }: { locale: Locale; page: 'privacy' | 'terms' }) {
  const t = copy[locale]
  const sections = page === 'privacy' ? t.legal.privacySections : t.legal.termsSections
  const title = page === 'privacy' ? t.legal.privacy : t.legal.terms
  return <div className="min-h-screen bg-slate-50"><PublicSeo locale={locale} page={page} /><header className="border-b border-slate-200 bg-white"><div className="mx-auto flex h-[72px] max-w-4xl items-center justify-between px-5"><Link to={`/${locale}`}><Brand /></Link><Link className="text-sm font-semibold text-brand-700" to={`/${locale}`}>{t.legal.back}</Link></div></header><main className="mx-auto max-w-4xl px-5 py-14"><p className="eyebrow">Radix CRM</p><h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">{title}</h1><p className="mt-3 text-sm text-slate-500">{t.legal.updated}</p><div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 sm:p-9"><p className="text-sm text-slate-500">{env.legalEntityName || t.legal.operator}</p><div className="mt-8 space-y-8">{sections.map((section) => <section key={section.title}><h2 className="text-lg font-bold text-slate-900">{section.title}</h2><p className="mt-2 leading-7 text-slate-600">{section.text}</p></section>)}</div></div></main></div>
}
