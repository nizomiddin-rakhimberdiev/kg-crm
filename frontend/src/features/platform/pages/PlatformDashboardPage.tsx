/**
 * Vendor ish ro'yxati — "bugun kimga qo'ng'iroq qilish kerak?"
 *
 * Bu ekran solo asoschi uchun kunlik boshlanish nuqtasi, shuning uchun
 * u chiroyli grafik emas, **ro'yxat**: tugayotgan sinovlar va muddati
 * o'tgan hisoblar. Grafik nimadir sodir bo'lganini aytadi; ro'yxat esa
 * nima QILISH kerakligini.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, Building2, Clock, Wallet } from 'lucide-react'
import { formatDate, formatUZS } from '@/lib/utils'
import { platform } from '../api'

const day = (iso: string) =>
  formatDate(iso)

const daysLeft = (iso: string) =>
  Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000))

function Tile({
  label,
  value,
  hint,
  icon: Icon,
  tone,
}: {
  label: string
  value: string
  hint?: string
  icon: typeof Building2
  tone: string
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className={`grid h-9 w-9 place-items-center rounded-lg ${tone}`}>
        <Icon className="h-4 w-4" />
      </div>
      <p className="mt-3 text-2xl font-bold tracking-tight">{value}</p>
      <p className="text-sm text-slate-400">{label}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export default function PlatformDashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['platform', 'work-list'],
    queryFn: platform.workList,
    refetchInterval: 60_000,
  })

  if (isError) {
    return (
      <div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
        Ma'lumotni yuklab bo'lmadi.
      </div>
    )
  }

  const counts = data?.counts
  const trials = data?.trials_ending ?? []
  const overdue = data?.overdue_invoices ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Ish ro'yxati</h1>
        <p className="mt-1 text-sm text-slate-400">
          Bugun e'tibor talab qiladigan narsalar.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tile
          label="Faol obunalar"
          value={isLoading ? '…' : String(counts?.active ?? 0)}
          hint={`jami ${counts?.total ?? 0} ta bog'cha`}
          icon={Building2}
          tone="bg-emerald-500/10 text-emerald-400"
        />
        <Tile
          label="Sinov davrida"
          value={isLoading ? '…' : String(counts?.trialing ?? 0)}
          hint={`${trials.length} tasi tugayapti`}
          icon={Clock}
          tone="bg-sky-500/10 text-sky-400"
        />
        <Tile
          label="To'lanmagan hisoblar"
          value={isLoading ? '…' : formatUZS(Number(data?.unpaid_total ?? 0))}
          hint={`${overdue.length} ta muddati o'tgan`}
          icon={Wallet}
          tone="bg-amber-500/10 text-amber-400"
        />
        <Tile
          label="To'xtatilgan"
          value={isLoading ? '…' : String(counts?.suspended ?? 0)}
          hint="faqat o'qish rejimida"
          icon={AlertTriangle}
          tone="bg-red-500/10 text-red-400"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold">Tugayotgan sinovlar</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Konvertatsiya oynasi — qo'ng'iroq qilish uchun eng yaxshi payt.
          </p>
          <ul className="mt-4 divide-y divide-slate-800 border-t border-slate-800">
            {trials.map((row) => {
              const left = daysLeft(row.trial_ends_at)
              return (
                <li key={row.organization_id} className="flex items-center justify-between py-2.5">
                  <Link
                    to={`/platform/organizations/${row.organization_id}`}
                    className="text-sm font-medium hover:text-brand-400"
                  >
                    {row.organization}
                  </Link>
                  <span
                    className={
                      left <= 2 ? 'text-sm font-semibold text-red-400' : 'text-sm text-slate-400'
                    }
                  >
                    {left} kun
                  </span>
                </li>
              )
            })}
            {!isLoading && trials.length === 0 && (
              <li className="py-6 text-center text-sm text-slate-500">
                Yaqin kunlarda tugaydigan sinov yo'q.
              </li>
            )}
          </ul>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold">Muddati o'tgan hisoblar</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Eng ko'p kechikkani birinchi.
          </p>
          <ul className="mt-4 divide-y divide-slate-800 border-t border-slate-800">
            {overdue.map((row) => (
              <li key={row.number} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <Link
                    to={`/platform/organizations/${row.organization_id}`}
                    className="block truncate text-sm font-medium hover:text-brand-400"
                  >
                    {row.organization}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {row.number} · {day(row.due_at)}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-sm font-semibold">
                    {formatUZS(Number(row.total_amount))}
                  </p>
                  <p className="text-xs text-red-400">{row.days_late} kun kechikdi</p>
                </div>
              </li>
            ))}
            {!isLoading && overdue.length === 0 && (
              <li className="py-6 text-center text-sm text-slate-500">
                Muddati o'tgan hisob yo'q.
              </li>
            )}
          </ul>
        </section>
      </div>
    </div>
  )
}
