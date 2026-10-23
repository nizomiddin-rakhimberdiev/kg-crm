/**
 * Bitta bog'cha — metama'lumot va tijorat amallari (docs/04 §19).
 *
 * Bu sahifada bola, to'lov yoki davomat qatori YO'Q va bo'lmaydi.
 * Operatsion ma'lumotni ko'rish uchun vaqt bilan cheklangan, sababi
 * yozilgan va **mijozga ko'rinadigan** ruxsat kerak — u ham shu yerdan
 * so'raladi, lekin ma'lumotni bu ekran ko'rsatmaydi (ADR-10).
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarRange, KeyRound, Layers, Pause, Play, Timer } from 'lucide-react'
import { ApiError } from '@/lib/api/types'
import { cn, formatDate, formatUZS } from '@/lib/utils'
import { platform } from '../api'
import { supportHandoff } from '@/lib/auth/supportSession'
import { usePlatformAuth } from '../PlatformAuthProvider'
import { STATUS_LABEL } from './PlatformOrganizationsPage'
import { INVOICE_STATUS, PAYMENT_TERM, PLAN, USAGE_METHOD, label } from '../labels'
import { Select } from '@/components/ui/Select'

const day = (iso: string | null) => formatDate(iso)

const INVOICE_TONE: Record<string, string> = {
  paid: 'bg-emerald-500/10 text-emerald-400',
  issued: 'border border-tosh-500/40 text-tosh-200',
  overdue: 'bg-red-500/10 text-red-400',
  cancelled: 'bg-slate-700/40 text-slate-400',
}

export default function PlatformOrganizationPage() {
  const { organizationId = '' } = useParams()
  const queryClient = useQueryClient()
  const { isAdmin } = usePlatformAuth()

  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [dialog, setDialog] = useState<'suspend' | 'trial' | 'grant' | 'term' | 'plan' | null>(null)
  const [term, setTerm] = useState('monthly')
  const [planCode, setPlanCode] = useState('')
  const [reason, setReason] = useState('')
  const [days, setDays] = useState(7)
  const [hours, setHours] = useState(2)

  const { data, isLoading } = useQuery({
    queryKey: ['platform', 'organization', organizationId],
    queryFn: () => platform.organization(organizationId),
    enabled: Boolean(organizationId),
  })
  // Rejalar ro'yxati — faqat "Rejani almashtirish" ochilganda kerak.
  const { data: plans } = useQuery({
    queryKey: ['platform', 'plans'],
    queryFn: () => platform.plans(),
    enabled: dialog === 'plan',
  })

  const done = (message: string) => {
    setError(null)
    setNotice(message)
    setDialog(null)
    setReason('')
    void queryClient.invalidateQueries({ queryKey: ['platform'] })
  }
  const fail = (err: unknown) => {
    setNotice(null)
    setError(err instanceof ApiError ? err.message : 'Amal bajarilmadi.')
  }

  const suspend = useMutation({
    mutationFn: () => platform.suspend(organizationId, reason),
    onSuccess: () => done("Obuna to'xtatildi. Mijoz ma'lumotini o'qiy oladi."),
    onError: fail,
  })
  const reactivate = useMutation({
    mutationFn: () => platform.reactivate(organizationId),
    onSuccess: () => done('Obuna tiklandi.'),
    onError: fail,
  })
  const extendTrial = useMutation({
    mutationFn: () => platform.extendTrial(organizationId, days, reason),
    onSuccess: () => done(`Sinov ${days} kunga uzaytirildi.`),
    onError: fail,
  })
  const changeTerm = useMutation({
    mutationFn: () => platform.changePaymentTerm(organizationId, term, reason),
    onSuccess: () =>
      done(`Toʻlov davri: ${label(PAYMENT_TERM, term)}. Keyingi davrdan kuchga kiradi.`),
    onError: fail,
  })
  const changePlan = useMutation({
    mutationFn: () => platform.changePlan(organizationId, planCode, reason),
    onSuccess: () => done(`Reja almashtirildi: ${label(PLAN, planCode)}. Keyingi hisobdan.`),
    onError: fail,
  })
  const grant = useMutation({
    mutationFn: () => platform.supportGrant(organizationId, reason, hours),
    onSuccess: () =>
      done(`Kirish ruxsati berildi (${hours} soat). Mijoz buni audit jurnalida ko'radi.`),
    onError: fail,
  })

  /**
   * Bog'cha tizimiga kirish.
   *
   * Token manzilga YOZILMAYDI — u `localStorage` orqali bir martalik
   * uzatiladi va mijoz ilovasi uni darhol o'chiradi. Yangi tabda
   * ochiladi: konsol ochiq qolsin, va ikki sessiya aralashmasin.
   */
  // Oyna BOSISH paytida ochiladi, manzil javobdan keyin qo'yiladi: aks
  // holda Safari kechikib ochilgan oynani bloklaydi.
  const enter = useMutation({
    mutationFn: (_tab: Window | null) => platform.supportSession(organizationId),
    onSuccess: (session, tab) => {
      supportHandoff.stash(session.access)
      const url = `${session.app_url}/support-entry`
      if (tab && !tab.closed) tab.location.href = url
      else window.open(url, '_blank', 'noopener')
      setError(null)
      setNotice(`${session.organization} tizimi yangi tabda ochildi (faqat o'qish).`)
    },
    onError: (err, tab) => {
      tab?.close()
      fail(err)
    },
  })

  if (isLoading || !data) {
    return <p className="text-sm text-slate-500">Yuklanmoqda…</p>
  }

  const subscription = data.subscription
  const [statusLabel, statusTone] = STATUS_LABEL[subscription?.status ?? ''] ?? [
    'Obunasiz',
    'bg-slate-700/40 text-slate-400',
  ]
  const isSuspended = subscription?.status === 'suspended'
  const isTrial = subscription?.status === 'trialing'

  const field =
    'w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-brand-500'

  return (
    <div className="space-y-6">
      <Link
        to="/platform/organizations"
        className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" />
        Bog'chalar
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{data.name}</h1>
          <p className="mt-1 text-sm text-slate-400">
            {data.contact_email}
            {data.contact_phone && ` · ${data.contact_phone}`} · {day(data.created_at)} dan beri
          </p>
        </div>
        <span className={cn('rounded-full px-3 py-1 text-sm font-medium', statusTone)}>
          {statusLabel}
        </span>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          {notice}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Hisoblanadigan bolalar', String(data.billable_children)],
          ['Reja', label(PLAN, subscription?.plan_code)],
          [
            "To'lov muddati",
            subscription
              ? `${label(PAYMENT_TERM, subscription.payment_term)}${
                  Number(subscription.discount_percent) > 0
                    ? ` (−${Number(subscription.discount_percent)}%)`
                    : ''
                }`
              : '—',
          ],
          [
            isTrial ? 'Sinov tugaydi' : 'Davr tugaydi',
            isTrial
              ? day(subscription?.trial_ends_at ?? null)
              : (subscription?.current_period_end ?? '—'),
          ],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <p className="text-xs text-slate-500">{label}</p>
            <p className="mt-1 text-lg font-semibold">{value}</p>
          </div>
        ))}
      </div>

      {/* --- Faollik va prognoz (PLAN 5.12) — faqat sonlar --- */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          [
            'Oxirgi faollik',
            data.activity.last_activity_at
              ? day(data.activity.last_activity_at)
              : 'Hali kirilmagan',
          ],
          [
            'Faol foydalanuvchilar (30 kun)',
            `${data.activity.active_users_30d} / ${data.activity.users_total}`,
          ],
          [
            'Taxminiy oylik',
            data.projection ? formatUZS(Number(data.projection.projected.total_amount)) : '—',
          ],
          [
            'Bolalar soni (oylar boʻyicha)',
            data.usage_history.length
              ? [...data.usage_history]
                  .reverse()
                  .slice(-6)
                  .map((row) => row.billable_children)
                  .join(' → ')
              : '—',
          ],
        ].map(([title, value]) => (
          <div key={title} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <p className="text-xs text-slate-500">{title}</p>
            <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>
      {data.projection && (
        <p className="-mt-3 text-xs text-slate-500">
          Taxminiy oylik — prognoz, hisob emas: mijoz oʻz "Obuna" sahifasida aynan shu raqamni
          koʻradi (eng yuqori {data.projection.peak_children} bola
          {data.projection.prepaid_base ? ', baza oldindan toʻlangan' : ''}).
        </p>
      )}

      {/* --- Amallar --- */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="text-sm font-semibold">Amallar</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setDialog(dialog === 'grant' ? null : 'grant')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium hover:bg-slate-800"
          >
            <KeyRound className="h-4 w-4" />
            Kirish ruxsatini so'rash
          </button>

          <button
            type="button"
            onClick={() => enter.mutate(window.open('', '_blank'))}
            disabled={enter.isPending}
            className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            {enter.isPending ? 'Ochilmoqda…' : "Bog'chaga kirish"}
          </button>

          {isAdmin && isTrial && (
            <button
              type="button"
              onClick={() => setDialog(dialog === 'trial' ? null : 'trial')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium hover:bg-slate-800"
            >
              <Timer className="h-4 w-4" />
              Sinovni uzaytirish
            </button>
          )}

          {isAdmin && subscription && !isSuspended && (
            <>
              <button
                type="button"
                onClick={() => {
                  setTerm(subscription.payment_term)
                  setDialog(dialog === 'term' ? null : 'term')
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium hover:bg-slate-800"
              >
                <CalendarRange className="h-4 w-4" />
                Toʻlov davri
              </button>
              <button
                type="button"
                onClick={() => {
                  setPlanCode(subscription.plan_code)
                  setDialog(dialog === 'plan' ? null : 'plan')
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium hover:bg-slate-800"
              >
                <Layers className="h-4 w-4" />
                Reja
              </button>
            </>
          )}

          {isAdmin && !isSuspended && (
            <button
              type="button"
              onClick={() => setDialog(dialog === 'suspend' ? null : 'suspend')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-red-900 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-950"
            >
              <Pause className="h-4 w-4" />
              Obunani to'xtatish
            </button>
          )}

          {isAdmin && isSuspended && (
            <button
              type="button"
              onClick={() => reactivate.mutate()}
              disabled={reactivate.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500"
            >
              <Play className="h-4 w-4" />
              Obunani tiklash
            </button>
          )}
        </div>

        {!isAdmin && (
          <p className="mt-3 text-xs text-slate-500">
            Obunani to'xtatish va sinovni uzaytirish — administrator huquqi. To'xtatish tijorat
            qarori, texnik yordam emas.
          </p>
        )}

        {dialog === 'grant' && (
          <div className="mt-4 space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            <p className="text-xs text-slate-400">
              Ruxsat vaqt bilan cheklanadi va <strong>mijozga ko'rinadi</strong>. U mijozning
              operatsion ma'lumotini ko'rish uchun oddiy bog'cha interfeysi orqali ishlash huquqini
              beradi — bu ekranda ma'lumot baribir ko'rinmaydi.
            </p>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Sabab (mijoz ko'radi) — masalan: hisob-faktura xatosi haqida murojaat"
              aria-label="Sabab (mijoz ko'radi) — masalan: hisob-faktura xatosi haqida murojaat"
              className={field}
            />
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-400">
                Muddat (soat)
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={hours}
                  onChange={(e) => setHours(Number(e.target.value))}
                  className={`${field} mt-1 w-24`}
                />
              </label>
              <button
                type="button"
                disabled={reason.trim().length < 3 || grant.isPending}
                onClick={() => grant.mutate()}
                className="mt-5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Ruxsat olish
              </button>
            </div>
          </div>
        )}

        {dialog === 'term' && (
          <div className="mt-4 space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            <p className="text-xs text-slate-400">
              Yangi davr <strong>keyingi hisobdan</strong> kuchga kiradi — yozilgan hisob
              oʻzgarmaydi. Mijoz bu oʻzgarishni oʻz audit jurnalida koʻradi.
            </p>
            <label className="block text-xs text-slate-400">
              Toʻlov davri
              <Select value={term} onChange={(e) => setTerm(e.target.value)} className="mt-1">
                {Object.entries(PAYMENT_TERM).map(([value, text]) => (
                  <option key={value} value={value}>
                    {text}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block text-xs text-slate-400">
              Sabab (mijoz koʻradi)
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className={`${field} mt-1`}
              />
            </label>
            <button
              type="button"
              disabled={reason.trim().length < 3 || changeTerm.isPending}
              onClick={() => changeTerm.mutate()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Saqlash
            </button>
          </div>
        )}

        {dialog === 'plan' && (
          <div className="mt-4 space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            <p className="text-xs text-slate-400">
              Rejaning <strong>amaldagi versiyasi</strong> olinadi. Yozilgan hisob oʻz rejasi bilan
              qoladi — yangisi keyingi hisobdan.
            </p>
            <label className="block text-xs text-slate-400">
              Reja
              <Select
                value={planCode}
                onChange={(e) => setPlanCode(e.target.value)}
                className="mt-1"
              >
                {[...new Set((plans ?? []).map((plan) => plan.code))].map((code) => (
                  <option key={code} value={code}>
                    {label(PLAN, code)}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block text-xs text-slate-400">
              Sabab (mijoz koʻradi)
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className={`${field} mt-1`}
              />
            </label>
            <button
              type="button"
              disabled={reason.trim().length < 3 || !planCode || changePlan.isPending}
              onClick={() => changePlan.mutate()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Almashtirish
            </button>
          </div>
        )}

        {dialog === 'trial' && (
          <div className="mt-4 space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Sabab — masalan: mijoz bayram kunlarida sinab ko'rolmadi"
              aria-label="Sabab — masalan: mijoz bayram kunlarida sinab ko'rolmadi"
              className={field}
            />
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-400">
                Kun
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className={`${field} mt-1 w-24`}
                />
              </label>
              <button
                type="button"
                disabled={reason.trim().length < 3 || extendTrial.isPending}
                onClick={() => extendTrial.mutate()}
                className="mt-5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Uzaytirish
              </button>
            </div>
          </div>
        )}

        {dialog === 'suspend' && (
          <div className="mt-4 space-y-3 rounded-lg border border-red-950 bg-red-950/30 p-4">
            <p className="text-xs text-red-300">
              To'xtatish mijozning yozish amallarini bloklaydi. Ma'lumot{' '}
              <strong>o'chirilmaydi va yashirilmaydi</strong> — u o'z tarixini ko'rib turadi va
              to'lagach qaytadi.
            </p>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Sabab — masalan: uch oy to'lov yo'q"
              aria-label="Sabab — masalan: uch oy to'lov yo'q"
              className={field}
            />
            <button
              type="button"
              disabled={reason.trim().length < 3 || suspend.isPending}
              onClick={() => suspend.mutate()}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50"
            >
              To'xtatishni tasdiqlash
            </button>
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold">Hisob-fakturalar</h2>
          <ul className="mt-3 divide-y divide-slate-800 border-t border-slate-800">
            {data.invoices.map((invoice) => (
              <li key={invoice.number} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="text-sm font-medium">{invoice.number}</p>
                  <p className="text-xs text-slate-500">
                    {day(invoice.issued_at)} · muddat {day(invoice.due_at)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">{formatUZS(Number(invoice.total_amount))}</p>
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs',
                      INVOICE_TONE[invoice.status] ?? 'bg-slate-700/40 text-slate-400',
                    )}
                  >
                    {label(INVOICE_STATUS, invoice.status)}
                  </span>
                </div>
              </li>
            ))}
            {data.invoices.length === 0 && (
              <li className="py-6 text-center text-sm text-slate-500">Hisob yozilmagan.</li>
            )}
          </ul>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold">Hisoblash dalili</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Har bir hisob ortidagi o'lchov — o'zgartirilmaydigan yozuv.
          </p>
          <ul className="mt-3 divide-y divide-slate-800 border-t border-slate-800">
            {data.usage_history.map((row) => (
              <li key={row.period} className="flex items-center justify-between py-2.5 text-sm">
                <span className="text-slate-400">
                  {row.period}
                  {row.method === 'manual_adjustment' && (
                    <span className="ml-2 rounded bg-amber-500/10 px-1.5 py-0.5 text-xs text-amber-400">
                      {label(USAGE_METHOD, row.method)}
                    </span>
                  )}
                </span>
                <span>
                  eng yuqori {row.peak_children} → <strong>{row.billable_children}</strong>
                  {!row.closed && <span className="ml-2 text-xs text-slate-500">(ochiq)</span>}
                </span>
              </li>
            ))}
            {data.usage_history.length === 0 && (
              <li className="py-6 text-center text-sm text-slate-500">O'lchov hali yo'q.</li>
            )}
          </ul>
        </section>
      </div>

      {/* --- Kirish ruxsatlari tarixi (PLAN 5.12) — tugaganlari bilan --- */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="text-sm font-semibold">Kirish ruxsatlari</h2>
        <p className="mt-0.5 text-xs text-slate-500">
          Tugagan va bekor qilinganlari ham — mijoz ham shu roʻyxatni koʻradi.
        </p>
        <ul className="mt-3 divide-y divide-slate-800 border-t border-slate-800">
          {data.grants.map((row) => (
            <li key={row.id} className="flex items-start justify-between gap-4 py-2.5 text-sm">
              <div className="min-w-0">
                <p className="truncate">{row.reason}</p>
                <p className="text-xs text-slate-500">
                  {row.platform_email} · {day(row.created_at)} → {day(row.expires_at)}
                </p>
              </div>
              <span
                className={cn(
                  'shrink-0 rounded-full px-2 py-0.5 text-xs',
                  row.is_active
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-slate-700/40 text-slate-400',
                )}
              >
                {row.is_active ? 'Faol' : row.revoked_at ? 'Bekor qilingan' : 'Tugagan'}
              </span>
            </li>
          ))}
          {data.grants.length === 0 && (
            <li className="py-6 text-center text-sm text-slate-500">Ruxsat soʻralmagan.</li>
          )}
        </ul>
      </section>
    </div>
  )
}
