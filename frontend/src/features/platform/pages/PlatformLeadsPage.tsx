/**
 * So'rovlar — saytdagi «Demo olish» formasidan kelgan arizalar.
 *
 * Bu ro'yxat platforma darajasida (tenant emas): ariza yuborgan bog'cha
 * hali mijoz emas. Sotuvchi holatni yuritadi — yangi → bog'lanildi →
 * mos keladi → yopildi — va qisqa izoh qoldiradi; har o'zgarish
 * platforma auditiga tushadi.
 *
 * Telefon `tel:` havola, WhatsApp — bitta tugma: ariza kelgach birinchi
 * ish qo'ng'iroq, ro'yxatni o'qish emas.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Inbox, MessageCircle, Phone } from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { platform, type Lead, type LeadStatus } from '../api'

const STATUS: Record<LeadStatus, { label: string; tone: string }> = {
  new: { label: 'Yangi', tone: 'bg-brand-600/20 text-brand-300' },
  contacted: { label: 'Bog‘lanildi', tone: 'bg-amber-500/15 text-amber-300' },
  qualified: { label: 'Mos keladi', tone: 'bg-emerald-500/15 text-emerald-300' },
  closed: { label: 'Yopildi', tone: 'bg-slate-700 text-slate-300' },
}
const ORDER: LeadStatus[] = ['new', 'contacted', 'qualified', 'closed']
const LANG: Record<Lead['language'], string> = { uz: 'UZ', ru: 'RU', en: 'EN' }

const when = (iso: string) =>
  new Date(iso).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })

function LeadRow({ lead }: { lead: Lead }) {
  const queryClient = useQueryClient()
  const [note, setNote] = useState(lead.note)
  const [nextCall, setNextCall] = useState(lead.next_call_at ?? '')
  const [error, setError] = useState<string | null>(null)

  const update = useMutation({
    mutationFn: ({
      status,
      text,
      call,
    }: {
      status: LeadStatus
      text?: string
      call?: string | null
    }) => platform.setLeadStatus(lead.id, status, text, call),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: ['platform', 'leads'] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Saqlab bo‘lmadi.'),
  })

  const digits = lead.phone.replace(/\D/g, '')

  return (
    <li className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-base font-semibold text-white">{lead.kindergarten_name}</p>
            <span
              className={cn(
                'rounded-full px-2 py-0.5 text-xs font-medium',
                STATUS[lead.status].tone,
              )}
            >
              {STATUS[lead.status].label}
            </span>
            <span className="rounded border border-slate-700 px-1.5 text-[11px] text-slate-400">
              {LANG[lead.language]}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-300">
            {lead.name} · {lead.city} · {lead.children_count} bola
          </p>
          {lead.message && (
            <p className="mt-2 max-w-2xl whitespace-pre-line rounded-lg bg-slate-800/60 px-3 py-2 text-sm text-slate-300">
              {lead.message}
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">
            Kelgan: {when(lead.created_at)}
            {lead.status_changed_at && ` · Holat: ${when(lead.status_changed_at)}`}
            {lead.next_call_at && (
              <span className="ml-1 text-amber-300">
                · Qo‘ng‘iroq: {lead.next_call_at.split('-').reverse().join('.')}
              </span>
            )}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <a
            href={`tel:${lead.phone}`}
            className="inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-slate-700 px-3 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            <Phone className="h-4 w-4" />
            {lead.phone}
          </a>
          <a
            href={`https://wa.me/${digits}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-emerald-700/60 px-3 text-sm font-medium text-emerald-300 hover:bg-emerald-900/30"
          >
            <MessageCircle className="h-4 w-4" />
            WhatsApp
          </a>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
        <label className="block text-xs font-medium text-slate-400">
          Izoh
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => note !== lead.note && update.mutate({ status: lead.status, text: note })}
            rows={2}
            maxLength={2000}
            placeholder="Masalan: ertaga 10:00 da qo‘ng‘iroq; narxni yubordim"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-brand-500"
          />
        </label>
        <div className="flex flex-wrap items-end gap-1.5">
          {/* "Ertaga qo'ng'iroq qilaman" degan izoh bir hafta o'tib
              ma'nosini yo'qotadi — sana yozib qo'yiladi. */}
          <label className="mr-2 block text-xs font-medium text-slate-400">
            Keyingi qo‘ng‘iroq
            <DateInput
              tone="dark"
              className="mt-1"
              value={nextCall}
              onChange={(iso) => {
                setNextCall(iso)
                update.mutate({ status: lead.status, call: iso || null })
              }}
            />
          </label>
          {ORDER.map((status) => (
            <button
              key={status}
              type="button"
              disabled={update.isPending || status === lead.status}
              onClick={() => update.mutate({ status, text: note })}
              className={cn(
                'min-h-10 rounded-lg px-3 text-sm font-medium transition-colors',
                status === lead.status
                  ? cn('cursor-default', STATUS[status].tone)
                  : 'border border-slate-700 text-slate-300 hover:bg-slate-800',
              )}
            >
              {STATUS[status].label}
            </button>
          ))}
        </div>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-400">
          {error}
        </p>
      )}
    </li>
  )
}

export default function PlatformLeadsPage() {
  const [filter, setFilter] = useState<LeadStatus | ''>('')
  const { data, isLoading, isError } = useQuery({
    queryKey: ['platform', 'leads', filter],
    queryFn: () => platform.leads(filter ? { status: filter } : undefined),
  })
  const items = data?.items ?? []
  const counts = data?.counts
  const total = counts ? ORDER.reduce((sum, key) => sum + counts[key], 0) : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">So‘rovlar</h1>
        <p className="mt-1 text-sm text-slate-400">
          Saytdagi «Demo olish» formasidan kelgan arizalar. Holatni yuriting — har o‘zgarish
          auditda.
        </p>
      </div>

      <div role="tablist" className="flex flex-wrap gap-1.5">
        <button
          type="button"
          role="tab"
          aria-selected={filter === ''}
          onClick={() => setFilter('')}
          className={cn(
            'min-h-10 rounded-lg px-3 text-sm font-medium',
            filter === '' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-800/60',
          )}
        >
          Hammasi{counts ? ` · ${total}` : ''}
        </button>
        {ORDER.map((status) => (
          <button
            key={status}
            type="button"
            role="tab"
            aria-selected={filter === status}
            onClick={() => setFilter(status)}
            className={cn(
              'min-h-10 rounded-lg px-3 text-sm font-medium',
              filter === status
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:bg-slate-800/60',
            )}
          >
            {STATUS[status].label}
            {counts ? ` · ${counts[status]}` : ''}
          </button>
        ))}
      </div>

      {isError && (
        <p role="alert" className="text-sm text-red-400">
          So‘rovlarni yuklab bo‘lmadi.
        </p>
      )}
      {isLoading && <p className="text-sm text-slate-500">Yuklanmoqda…</p>}

      {!isLoading && items.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-800 px-6 py-14 text-center">
          <Inbox className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">
            {filter ? 'Bu holatda so‘rov yo‘q.' : 'Hozircha so‘rov kelmagan.'}
          </p>
        </div>
      )}

      <ul className="space-y-3">
        {items.map((lead) => (
          <LeadRow key={lead.id} lead={lead} />
        ))}
      </ul>
    </div>
  )
}
