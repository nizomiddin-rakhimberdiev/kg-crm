/**
 * Hisobotni topshirish va qabul qilish (Bosqich 13.6, brif §2, §8; ADR-42).
 *
 * Raqamlar bu yerda oʻzgarmaydi — faqat jarayon: izoh, topshirish, savol,
 * javob, qaytarish, qabul, tasdiq va faqat oʻqish uchun havola. Qaysi
 * tugma koʻrinishini server aytgan model va holat belgilaydi; ruxsatni
 * baribir backend tekshiradi.
 */

import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Clock, Link2, MessageSquare, Send, Undo2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { QueryError } from '@/components/ui/QueryError'
import { reportsApi, type PackUnit, type ReviewState } from '@/features/dashboard/api'
import { ApiError } from '@/lib/api/types'
import { formatDate, formatDateTime } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const STATUS: Record<ReviewState['status'], { label: string; tone: string }> = {
  draft: { label: t('Qoralama'), tone: 'bg-slate-100 text-slate-700' },
  submitted: { label: t('Topshirildi'), tone: 'bg-brand-50 text-brand-800' },
  resubmitted: { label: t('Qayta topshirildi'), tone: 'bg-brand-50 text-brand-800' },
  question: { label: t('Savol bor'), tone: 'bg-orik-50 text-orik-800' },
  returned: { label: t('Qaytarildi'), tone: 'bg-red-50 text-red-700' },
  accepted: { label: t('Qabul qilindi'), tone: 'bg-emerald-50 text-emerald-800' },
}

const EVENT: Record<string, string> = {
  note: t('Izoh'),
  submit: t('Topshirdi'),
  question: t('Savol'),
  answer: t('Javob'),
  accept: t('Qabul qildi'),
  return: t('Qaytardi'),
  approve: t('Tasdiqladi'),
}

const MODEL: Record<ReviewState['model'], string> = {
  A: t('A model: ega oʻzi tasdiqlaydi'),
  B: t('B model: boshqaruvchi topshiradi, rahbar qabul qiladi'),
  C: t('C model: filiallar topshiradi, ega konsolidatsiyani tasdiqlaydi'),
}

const inputClass =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

/** Bitta matn maydoni va tugma — izoh, savol, javob va sabab uchun. */
function InlineText({
  id,
  label,
  action,
  pending,
  onSubmit,
}: {
  id: string
  label: string
  action: string
  pending: boolean
  onSubmit: (text: string) => void
}) {
  const [text, setText] = useState('')
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (text.trim()) onSubmit(text.trim())
  }
  return (
    <form onSubmit={submit} className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-end">
      <div className="flex-1">
        <label htmlFor={id} className="mb-1 block text-xs font-medium text-slate-600">
          {label}
        </label>
        <input
          id={id}
          value={text}
          onChange={(e) => setText(e.target.value)}
          className={inputClass}
        />
      </div>
      <button
        type="submit"
        disabled={pending || !text.trim()}
        className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        {action}
      </button>
    </form>
  )
}

export function ReviewPanel({ at }: { at: PackUnit }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const key = ['org', organizationId, 'reports', 'review', at.year, at.month, at.branch ?? null]
  const review = useQuery({ queryKey: key, queryFn: () => reportsApi.review(at) })
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'question' | 'return' | 'share' | null>(null)
  const [questionPath, setQuestionPath] = useState('summary')
  const [shareLabel, setShareLabel] = useState('')
  const [shareDays, setShareDays] = useState('14')
  const [sharedUrl, setSharedUrl] = useState<string | null>(null)

  const refresh = () => {
    setError(null)
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'reports'] })
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const act = useMutation({
    mutationFn: ({
      step,
      body,
    }: {
      step: Parameters<typeof reportsApi.reviewAct>[1]
      body?: Record<string, string>
    }) => reportsApi.reviewAct(at, step, body),
    onSuccess: () => {
      setMode(null)
      refresh()
    },
    onError: fail,
  })
  const share = useMutation({
    mutationFn: () => reportsApi.share(at, shareLabel.trim(), Number(shareDays) || 14),
    onSuccess: (data) => {
      setSharedUrl(data.url)
      setShareLabel('')
      setMode(null)
      refresh()
    },
    onError: fail,
  })
  const revoke = useMutation({
    mutationFn: (id: string) => reportsApi.revokeShare(id),
    onSuccess: refresh,
    onError: fail,
  })

  if (review.isError)
    return <QueryError error={review.error} onRetry={() => void review.refetch()} />
  const data = review.data
  if (!data) return null

  const leader = can('reports.approve')
  const open = ['submitted', 'resubmitted', 'question'].includes(data.status)
  const approves = data.model === 'A' || data.consolidation
  const canSubmit = !approves && ['draft', 'returned'].includes(data.status)
  const questions = data.events.filter((event) => event.kind === 'question')
  const answered = new Set(data.events.filter((e) => e.kind === 'answer').map((e) => e.parent))
  const status = STATUS[data.status]

  return (
    <section
      aria-label={t('Hisobot jarayoni')}
      className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn('rounded-full px-2.5 py-1 text-xs font-semibold', status.tone)}>
          {status.label}
        </span>
        <span className="text-sm text-slate-600">{MODEL[data.model]}</span>
        {data.snapshot && (
          <span className="text-xs text-slate-500">
            v{data.snapshot.version} · {formatDate(data.snapshot.created_at)}
          </span>
        )}
        <span
          className={cn(
            'ml-auto flex items-center gap-1 text-xs',
            data.late ? 'font-semibold text-red-700' : 'text-slate-500',
          )}
        >
          <Clock className="h-3.5 w-3.5" aria-hidden />
          {data.late
            ? t('Muddat oʻtdi: {date}', { date: formatDate(data.deadline) })
            : t('Muddat: {date}', { date: formatDate(data.deadline) })}
        </span>
      </div>

      {data.changed && (
        <p className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-800">
          {t('Topshirilgandan keyin maʼlumot oʻzgardi — keyingi topshirish yangi versiya boʻladi.')}
        </p>
      )}
      {data.acceptors.length > 0 && data.status !== 'draft' && !approves && (
        <p className="text-xs text-slate-500">
          {t('Qabul qiladi: {names}. Qabul qildi: {done}.', {
            names: data.acceptors.join(', '),
            done: data.accepted_by.join(', ') || '—',
          })}
        </p>
      )}

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {data.blockers.length > 0 && data.status !== 'accepted' && (
        <div className="rounded-xl border border-orik-200 bg-orik-50/40 p-3">
          <p className="text-sm font-medium text-slate-800">
            {t('Topshirish uchun izoh kerak — {n} ta', { n: data.blockers.length })}
          </p>
          <ul className="mt-2 space-y-3">
            {data.blockers.map((blocker) => (
              <li key={blocker.path} className="text-sm">
                <p className="font-medium text-slate-900">
                  {blocker.title}
                  <span className="ml-1 text-xs font-normal text-slate-500">
                    {blocker.kind === 'check' ? t('tekshiruv') : t('Diqqat')}
                  </span>
                </p>
                {blocker.detail && <p className="text-xs text-slate-600">{blocker.detail}</p>}
                <InlineText
                  id={`note-${blocker.path}`}
                  label={t('Izoh')}
                  action={t('Saqlash')}
                  pending={act.isPending}
                  onSubmit={(text) =>
                    act.mutate({ step: 'note', body: { path: blocker.path, text } })
                  }
                />
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {canSubmit && (
          <button
            type="button"
            disabled={!data.ready || act.isPending}
            onClick={() => act.mutate({ step: 'submit' })}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            <Send className="h-4 w-4" aria-hidden />
            {data.status === 'returned' ? t('Qayta topshirish') : t('Topshirish')}
          </button>
        )}
        {approves && leader && (data.status !== 'accepted' || data.changed) && (
          <button
            type="button"
            disabled={!data.ready || act.isPending}
            onClick={() => act.mutate({ step: 'approve' })}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            {t('Tasdiqladim')}
          </button>
        )}
        {!approves && open && leader && data.can_accept && (
          <button
            type="button"
            disabled={data.status === 'question' || act.isPending}
            onClick={() => act.mutate({ step: 'accept' })}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            {t('Qabul qildim')}
          </button>
        )}
        {!approves && open && leader && (
          <>
            <button
              type="button"
              onClick={() => setMode(mode === 'question' ? null : 'question')}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <MessageSquare className="h-4 w-4" aria-hidden />
              {t('Savol berish')}
            </button>
            <button
              type="button"
              onClick={() => setMode(mode === 'return' ? null : 'return')}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <Undo2 className="h-4 w-4" aria-hidden />
              {t('Qaytarish')}
            </button>
          </>
        )}
        {data.snapshot && leader && (
          <button
            type="button"
            onClick={() => setMode(mode === 'share' ? null : 'share')}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Link2 className="h-4 w-4" aria-hidden />
            {t('Ulashish')}
          </button>
        )}
      </div>

      {mode === 'question' && (
        <div className="rounded-xl bg-slate-50 p-3">
          <label htmlFor="question-path" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Qaysi raqam haqida')}
          </label>
          <select
            id="question-path"
            value={questionPath}
            onChange={(event) => setQuestionPath(event.target.value)}
            className={inputClass}
          >
            {[
              ['summary', t('Xulosa')],
              ['revenue.chain.collected', t('Yigʻilgan pul')],
              ['revenue.chain.debt', t('Qarz')],
              ['expenses', t('Chiqimlar')],
              ['payroll', t('Oylik maosh')],
              ['cash_bank', t('Kassa va bank')],
              ['pnl.current.operating_profit', t('Operatsion foyda')],
              ['position', t('Holat')],
            ].map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <InlineText
            id="question-text"
            label={t('Savol')}
            action={t('Yuborish')}
            pending={act.isPending}
            onSubmit={(text) =>
              act.mutate({ step: 'question', body: { path: questionPath, text } })
            }
          />
        </div>
      )}
      {mode === 'return' && (
        <div className="rounded-xl bg-slate-50 p-3">
          <InlineText
            id="return-reason"
            label={t('Qaytarish sababi')}
            action={t('Qaytarish')}
            pending={act.isPending}
            onSubmit={(text) => act.mutate({ step: 'return', body: { text } })}
          />
        </div>
      )}
      {mode === 'share' && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (shareLabel.trim()) share.mutate()
          }}
          className="grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-[1fr_8rem_auto] sm:items-end"
        >
          <div>
            <label htmlFor="share-label" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Kim uchun')}
            </label>
            <input
              id="share-label"
              value={shareLabel}
              onChange={(event) => setShareLabel(event.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="share-days" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Necha kun')}
            </label>
            <input
              id="share-days"
              type="number"
              min={1}
              max={90}
              value={shareDays}
              onChange={(event) => setShareDays(event.target.value)}
              className={inputClass}
            />
          </div>
          <button
            type="submit"
            disabled={share.isPending || !shareLabel.trim()}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t('Havola yaratish')}
          </button>
        </form>
      )}
      {sharedUrl && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm">
          <p className="font-medium text-emerald-900">
            {t('Havola tayyor — u faqat hozir koʻrinadi, nusxa oling:')}
          </p>
          <p className="mt-1 break-all font-mono text-xs text-slate-800">{sharedUrl}</p>
          <button
            type="button"
            onClick={() => void navigator.clipboard?.writeText(sharedUrl)}
            className="mt-2 text-xs font-medium text-brand-700"
          >
            {t('Nusxa olish')}
          </button>
        </div>
      )}

      {questions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('Savollar')}
          </h4>
          {questions.map((question) => {
            const reply = data.events.find((event) => event.parent === question.id)
            return (
              <div key={question.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                <p className="text-xs text-slate-500">
                  {question.author} · {formatDateTime(question.created_at)} ·{' '}
                  <span className="font-mono">{question.path}</span>
                </p>
                <p className="mt-0.5 text-slate-900">{question.text}</p>
                {reply ? (
                  <p className="mt-2 border-l-2 border-brand-200 pl-2 text-slate-700">
                    {reply.text}
                    <span className="ml-1 text-xs text-slate-500">— {reply.author}</span>
                  </p>
                ) : (
                  !answered.has(question.id) && (
                    <InlineText
                      id={`answer-${question.id}`}
                      label={t('Javob')}
                      action={t('Javob berish')}
                      pending={act.isPending}
                      onSubmit={(text) =>
                        act.mutate({ step: 'answer', body: { question: question.id, text } })
                      }
                    />
                  )
                )}
              </div>
            )
          })}
        </div>
      )}

      {data.share_links.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium text-slate-700">
            {t('Ulashilgan havolalar — {n}', { n: data.share_links.length })}
          </summary>
          <ul className="mt-2 space-y-1">
            {data.share_links.map((link) => (
              <li key={link.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className={cn(link.revoked && 'text-slate-400 line-through')}>
                  {link.label} · v{link.version} · {t('{n} marta ochildi', { n: link.opened })} ·{' '}
                  {t('{date} gacha', { date: formatDate(link.expires_at) })}
                </span>
                {!link.revoked && leader && (
                  <button
                    type="button"
                    onClick={() => revoke.mutate(link.id)}
                    className="text-xs font-medium text-red-700"
                  >
                    {t('Bekor qilish')}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          {t('Tarix va ochilishlar')}
        </summary>
        <ul className="mt-2 space-y-1">
          {data.events.map((event) => (
            <li key={event.id} className="text-slate-700">
              <span className="text-xs text-slate-500">{formatDateTime(event.created_at)}</span>{' '}
              <span className="font-medium">{event.author}</span> —{' '}
              {EVENT[event.kind] ?? event.kind}
              {event.version ? ` (v${event.version})` : ''}
              {event.path && (
                <span className="ml-1 font-mono text-xs text-slate-500">{event.path}</span>
              )}
              {event.text && <span className="ml-1">«{event.text}»</span>}
            </li>
          ))}
          {data.opens.map((row) => (
            <li key={`${row.user}-${row.at}`} className="text-slate-500">
              <span className="text-xs">{formatDateTime(row.at)}</span> {row.user} —{' '}
              {t('ochdi ({format})', { format: row.format })}
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
