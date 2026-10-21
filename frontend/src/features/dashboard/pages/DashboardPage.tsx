/**
 * Dashboard (docs/04 §14.1).
 *
 * Barcha raqamlar bitta chaqiruvdan keladi (`GET /dashboard`) va backend'da
 * keshlangan. To'rtta KPI'ni to'rtta so'rov bilan olish sahifani sekin
 * qilardi va har biri boshqa vaqtdagi holatni ko'rsatishi mumkin edi —
 * bir ekranda bir-biriga mos kelmaydigan raqamlar.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CalendarCheck, Coins, Package, Pencil, Users, Wallet } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { CashAdjustModal } from '@/features/cash/components/CashAdjustModal'
import { dashboardApi } from '@/features/dashboard/api'
import { BriefingSection } from '@/features/intelligence/components/BriefingSection'
import { navItems } from '@/config/navigation'
import { queryKeys } from '@/lib/api/queryKeys'
import type { DashboardKpis } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { groupAccounts } from '@/features/dashboard/cashGroups'
import { paymentMethodLabel } from '@/features/payments/methods'
import { BRAND, CHART } from '@/lib/brand'
import { axisMoney } from '@/lib/format'
import { cn, formatDateLong, formatDateTime, formatUZS } from '@/lib/utils'
import { t } from '@/lib/i18n'

const MONTHS = [
  t('Yan'),
  t('Fev'),
  t('Mar'),
  t('Apr'),
  t('May'),
  t('Iyn'),
  t('Iyl'),
  t('Avg'),
  t('Sen'),
  t('Okt'),
  t('Noy'),
  t('Dek'),
]

const shortMonth = (iso: string) => MONTHS[Number(iso.slice(5, 7)) - 1] ?? iso

interface TileProps {
  label: string
  value: string
  hint: string
  icon: typeof Users
  tone: string
  to?: string
  /** Qiymat sof raqammi? So'z aralashsa (`42 nafar`) mono yaramaydi. */
  mono?: boolean
}

/*
 * Telefonda kartochka — YOTIQ qator (PLAN 10.7).
 *
 * Tik joylashuvda bitta kartochka 330 px edi: toʻrtta raqamni
 * koʻrish uchun mudira toʻrt ekran varaqlardi, holbuki ular aynan
 * birga koʻrilishi kerak ("qarz 58 mln, tushum 0" — savol shu
 * ikkisining YONMA-YON turishidan tugʻiladi). `sm:` dan boshlab
 * ustunlar paydo boʻladi va eski tik koʻrinish qaytadi.
 */
function Tile({ label, value, hint, icon: Icon, tone, to, mono = true }: TileProps) {
  const body = (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-4 shadow-card transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md sm:p-5">
      <div className="flex items-center gap-3 sm:block">
        <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${tone}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 sm:mt-4">
          <p
            className={cn(
              'text-xl font-bold tracking-tight text-slate-900 sm:text-2xl',
              mono && 'num',
            )}
          >
            {value}
          </p>
          <p className="text-sm font-medium text-slate-600">{label}</p>
          <p className="mt-0.5 text-xs text-slate-500 sm:mt-1">{hint}</p>
        </div>
      </div>
    </div>
  )
  return to ? <Link to={to}>{body}</Link> : body
}

const ACCOUNT_COLORS: Record<string, string> = {
  cash: BRAND.nihol,
  terminal: BRAND.ildiz,
  bank: BRAND.orik,
  ewallet: CHART.niholSoft,
}

/** Guruh nomlari — qoplarning o'z nomlari emas (PLAN 7.3). */
const GROUP_LABELS: Record<'cash' | 'bank', string> = {
  cash: t('Naqd kassa'),
  bank: t('Bank hisobi'),
}

/**
 * "Hozirda qancha pulimiz bor" — bog'cha egasining birinchi savoli.
 *
 * Raqamning o'zi yetarli emas: uning ostida qanday hisoblangani ham,
 * qaysi qopda qancha turgani ham ko'rinadi (ADR-17). Aks holda raqam
 * kutganidan farq qilsa, uni tushuntirib bo'lmasdi va ishonchni
 * yo'qotardi.
 */
function CashPanel({
  cash,
  incomeByMethod,
  isLoading,
}: {
  cash: DashboardKpis['cash']
  incomeByMethod: DashboardKpis['income_by_method']
  isLoading: boolean
}) {
  const { can } = useCan()
  const [adjusting, setAdjusting] = useState(false)
  const balance = Number(cash?.balance ?? 0)
  // To'rtta qop ikkita guruh bo'lib ko'rsatiladi (PLAN 7.3) — jadvalda
  // ular avvalgidek alohida (ADR-17).
  const accountGroups = groupAccounts(cash?.accounts)
  const methods = incomeByMethod ?? []
  const parts: Array<{ label: string; value: number; sign: string; tone: string }> = [
    {
      label: t('Jami tushum'),
      value: Number(cash?.income ?? 0),
      sign: '+',
      tone: 'text-emerald-600',
    },
    {
      label: t('Chiqimlar'),
      value: Number(cash?.expenses ?? 0),
      sign: '−',
      tone: 'text-slate-600',
    },
    {
      label: t('Oylik maosh'),
      value: Number(cash?.payroll ?? 0),
      sign: '−',
      tone: 'text-slate-600',
    },
  ]

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-ildiz-50 text-ildiz-700">
              <Coins className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600">{t('Kassadagi qoldiq')}</p>
              <p className="text-xs text-slate-500">{t('Bogʻcha ochilganidan beri')}</p>
            </div>
          </div>
          <p
            className={cn(
              'num mt-3 text-3xl font-bold tracking-tight',
              balance < 0 ? 'text-red-600' : 'text-slate-900',
            )}
          >
            {isLoading ? '…' : formatUZS(balance)}
          </p>
        </div>

        <dl className="grid flex-1 gap-2 sm:min-w-[16rem] sm:max-w-sm">
          {parts.map((part) => (
            <div key={part.label} className="flex items-baseline justify-between gap-3">
              <dt className="text-sm text-slate-500">{part.label}</dt>
              <dd className={cn('text-sm font-semibold tabular-nums', part.tone)}>
                {/* Nol oldidan ishora qo'yilmaydi: "− 0 UZS" degan yozuv
                    pul chiqqandek ko'rinardi, aslida esa hech narsa
                    bo'lmagan. */}
                {isLoading
                  ? '…'
                  : part.value === 0
                    ? formatUZS(0)
                    : `${part.sign} ${formatUZS(part.value)}`}
              </dd>
            </div>
          ))}
        </dl>
      </div>
      {/* Qoplar kesimi — mijozning aynan so'ragan savoli: naqd
          qancha, plastikda qancha, bankda qancha (ADR-17). */}
      {accountGroups.length > 0 && (
        <ul className="mt-4 grid gap-2 border-t border-slate-100 pt-4 sm:grid-cols-2">
          {accountGroups.map((group) => (
            <li
              key={group.key}
              className="flex items-center gap-2.5 rounded-xl border border-slate-200 px-3 py-2.5"
            >
              <span
                className="grid h-8 w-8 shrink-0 place-items-center rounded-lg"
                style={{
                  backgroundColor: `${ACCOUNT_COLORS[group.key]}1a`,
                  color: ACCOUNT_COLORS[group.key],
                }}
              >
                <Coins className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs text-slate-500">
                  {GROUP_LABELS[group.key]}
                </span>
                <span
                  className={cn(
                    'num block text-sm font-semibold',
                    group.balance < 0 ? 'text-red-600' : 'text-slate-900',
                  )}
                >
                  {isLoading ? '…' : formatUZS(group.balance)}
                </span>
                {/* Guruhga nima kirgani — "bankda nega buncha ko'p?"
                    degan savol javobsiz qolmasin. */}
                {group.parts.length > 1 && (
                  <span className="block truncate text-xs text-slate-500">
                    {group.parts.join(' · ')}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Shu oyda qaysi yo'l bilan qancha pul kelgan (PLAN 7.3).
          Manba Hisobotlar sahifasi bilan bir xil. */}
      {methods.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('Shu oy tushumi — qaysi yoʻl bilan')}
          </p>
          <ul className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {methods.map((row) => (
              <li key={row.method} className="rounded-xl border border-slate-200 px-3 py-2">
                <span className="block truncate text-xs text-slate-500">
                  {paymentMethodLabel(row.method)}
                </span>
                <span className="num block text-sm font-semibold text-slate-900">
                  {formatUZS(Number(row.total))}
                </span>
                <span className="block text-xs text-slate-500">
                  {t('{n} ta toʻlov', { n: row.count })}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-3 text-xs text-slate-500">
        {t(
          'Pul haqiqatan qimirlagan yozuvlardan hisoblanadi. Hisoblangan, lekin hali berilmagan oylik bu yerda hali kassada turgan pul — foyda-zarar hisobotida esa u allaqachon xarajat.',
        )}
      </p>

      {/*
        Qoldiqni toʻgʻrilash (ADR-29).

        Bogʻcha tizimga yil oʻrtasida keladi va seyfdagi pul hech
        qayerda yoʻq boʻladi — natijada qoldiq manfiyga tushadi.
        Tugma aynan shu yerda: notoʻgʻri raqam koʻrinadigan joyda.
      */}
      {can('payments.update') && (
        <button
          type="button"
          onClick={() => setAdjusting(true)}
          className="mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-slate-200 px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          <Pencil className="h-4 w-4 text-slate-500" />
          {t('Qoldiqni toʻgʻrilash')}
        </button>
      )}

      {adjusting && <CashAdjustModal onClose={() => setAdjusting(false)} />}
    </section>
  )
}

/**
 * Ruxsati tor rol uchun — ochiq bo'limlarga havolalar.
 *
 * Boshqaruv paneli ko'rsatkichlarning qisqartmasi: rolida ularning
 * birortasi bo'lmasa, ekran butunlay bo'sh qolardi. Bunday odam ham
 * kirishi bilan O'ZIGA ochiq ishni ko'rishi kerak.
 */
function QuickLinks() {
  const { can } = useCan()
  const open = navItems.filter((item) =>
    (Array.isArray(item.permission) ? item.permission : [item.permission]).some((code) =>
      can(code),
    ),
  )
  if (open.length === 0) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <h2 className="text-sm font-semibold text-slate-900">{t('Sizga ochiq boʻlimlar')}</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {open.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="flex items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md"
          >
            <item.icon className="h-4 w-4 shrink-0 text-slate-500" />
            {item.label}
          </Link>
        ))}
      </div>
    </section>
  )
}

export default function DashboardPage() {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  // Backend har bir bo'lakni o'z ruxsati bilan qo'riqlaydi va ruxsatsizini
  // javobga UMUMAN qo'shmaydi (docs/02 §11.2). Shu yerda ham o'sha qoida:
  // bo'sh "0 so'm" kartochka ko'rsatish o'rniga blok butunlay chizilmaydi.
  //
  // Nega muhim: bog'cha egasi qo'lda rol yasaganda (masalan "Tarbiyachi" —
  // faqat bolalar, guruhlar, davomat) ekran avval yarim bo'sh, yarmi
  // xato bo'lib ko'rinardi.
  const showChildren = can('children.read')
  const showAttendance = can('attendance.read')
  const showFinance = can('payments.read') || can('debtors.read')
  const showCash = can('payments.read') && can('expenses.read') && can('payroll.read')
  // Moliya IKKITA kartochka beradi (tushum va qarzdorlik) — to'r ustunlari
  // shuning uchun bayroqlar soniga emas, kartochkalar soniga qarab.
  const tileCount = (showChildren ? 1 : 0) + (showFinance ? 2 : 0) + (showAttendance ? 1 : 0)

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.dashboard(organizationId),
    queryFn: dashboardApi.kpis,
    // Backend 2 daqiqa keshlaydi; frontend ham shuncha kutadi, aks holda
    // har fokusda so'rov ketib, o'sha keshlangan javob qaytaverardi.
    staleTime: 120_000,
  })

  if (isError) {
    return (
      <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
        {t('Koʻrsatkichlarni yuklab boʻlmadi.')}
      </div>
    )
  }

  const trend = (data?.revenue_trend ?? []).map((row) => ({
    month: shortMonth(row.month),
    daromad: Number(row.total),
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {t('Boshqaruv paneli')}
        </h1>
        <p className="mt-1 text-sm text-slate-500">{data ? formatDateLong(data.date) : '—'}</p>
      </div>

      {/* Radix AI — kunlik brifing (docs/07 §11): KPI'lardan OLDIN, chunki
          "nimaga e'tibor berish kerak" umumiy raqamlardan muhimroq. */}
      <BriefingSection />

      {showCash && (
        <CashPanel
          cash={data?.cash}
          incomeByMethod={data?.income_by_method}
          isLoading={isLoading}
        />
      )}

      <div
        className={cn(
          'grid gap-4 sm:grid-cols-2',
          tileCount >= 4 ? 'xl:grid-cols-4' : tileCount === 3 ? 'xl:grid-cols-3' : 'xl:grid-cols-2',
        )}
      >
        {showChildren && (
          <Tile
            label={t('Faol bolalar')}
            value={isLoading ? '…' : t('{v} nafar', { v: data?.active_children ?? 0 })}
            hint={t('Roʻyxatdagi bolalar')}
            icon={Users}
            mono={false}
            tone="bg-nihol-50 text-nihol-600"
            to="/children"
          />
        )}
        {showFinance && (
          <>
            <Tile
              label={t('Shu oy tushum')}
              value={isLoading ? '…' : formatUZS(Number(data?.month_revenue ?? 0))}
              hint={t('Qabul qilingan toʻlovlar')}
              icon={Wallet}
              tone="bg-nihol-100 text-nihol-700"
              to="/payments"
            />
            <Tile
              label={t('Jami qarz')}
              value={isLoading ? '…' : formatUZS(Number(data?.outstanding_debt ?? 0))}
              hint={t('{v} nafar bola boʻyicha', { v: data?.debtor_count ?? 0 })}
              icon={AlertTriangle}
              tone="bg-orik-100 text-orik-700"
              to="/debtors"
            />
          </>
        )}
        {showAttendance && (
          <Tile
            label={t('Davomat (shu oy)')}
            value={isLoading ? '…' : `${data?.attendance_month_pct ?? 0}%`}
            hint={t('Kelgan / belgilangan')}
            icon={CalendarCheck}
            tone="bg-ildiz-50 text-ildiz-700"
            to="/attendance"
          />
        )}
      </div>

      {tileCount === 0 && <QuickLinks />}

      {showFinance && (
        <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h2 className="text-sm font-semibold text-slate-900">{t('Tushum dinamikasi')}</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {t('Oxirgi 6 oy, qabul qilingan toʻlovlar')}
            </p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
                  <XAxis
                    dataKey="month"
                    tickLine={false}
                    axisLine={false}
                    fontSize={12}
                    tick={{ fill: CHART.label }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    fontSize={12}
                    tick={{ fill: CHART.label }}
                    tickFormatter={(v: number) => axisMoney(v)}
                  />
                  <Tooltip
                    formatter={(v: number) => formatUZS(v)}
                    contentStyle={{
                      borderRadius: 12,
                      border: `1px solid ${CHART.grid}`,
                      fontSize: 13,
                    }}
                  />
                  <Bar dataKey="daromad" fill={BRAND.nihol} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h2 className="text-sm font-semibold text-slate-900">{t('Oxirgi toʻlovlar')}</h2>
            <ul className="mt-4 space-y-3">
              {(data?.recent_payments ?? []).map((payment, index) => (
                <li
                  key={`${payment.paid_at}-${index}`}
                  className="flex items-center justify-between"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">{payment.child}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(payment.paid_at)}</p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold text-emerald-600">
                    {formatUZS(Number(payment.amount))}
                  </span>
                </li>
              ))}
              {!isLoading && (data?.recent_payments ?? []).length === 0 && (
                <li className="py-6 text-center text-sm text-slate-500">
                  {t('Hozircha toʻlov qabul qilinmagan.')}
                </li>
              )}
            </ul>

            {(data?.low_stock_count ?? 0) > 0 && (
              <Link
                to="/inventory"
                className="mt-5 flex min-h-11 items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 hover:bg-amber-100"
              >
                <Package className="h-4 w-4 shrink-0" />
                {t('{low_stock_count} ta mahsulot minimumdan kam', {
                  low_stock_count: data?.low_stock_count,
                })}
              </Link>
            )}
          </section>
        </div>
      )}

      {/* Moliyasiz rol (masalan Davomat menejeri) uchun ombor ogohlantirishi
          alohida turadi — u yuqoridagi to'lovlar kartochkasi ichida edi. */}
      {!showFinance && (data?.low_stock_count ?? 0) > 0 && (
        <Link
          to="/inventory"
          className="flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 hover:bg-amber-100"
        >
          <Package className="h-4 w-4 shrink-0" />
          {t('{low_stock_count} ta mahsulot minimumdan kam', {
            low_stock_count: data?.low_stock_count,
          })}
        </Link>
      )}
    </div>
  )
}
