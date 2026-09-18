/**
 * Dashboard (docs/04 §14.1).
 *
 * Barcha raqamlar bitta chaqiruvdan keladi (`GET /dashboard`) va backend'da
 * keshlangan. To'rtta KPI'ni to'rtta so'rov bilan olish sahifani sekin
 * qilardi va har biri boshqa vaqtdagi holatni ko'rsatishi mumkin edi —
 * bir ekranda bir-biriga mos kelmaydigan raqamlar.
 */

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CalendarCheck, Package, Users, Wallet } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { dashboardApi } from '@/features/dashboard/api'
import { BriefingSection } from '@/features/intelligence/components/BriefingSection'
import { queryKeys } from '@/lib/api/queryKeys'
import { formatUZS } from '@/lib/utils'

const MONTHS = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']

const shortMonth = (iso: string) => MONTHS[Number(iso.slice(5, 7)) - 1] ?? iso

const when = (iso: string) =>
  new Date(iso).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })

interface TileProps {
  label: string
  value: string
  hint: string
  icon: typeof Users
  tone: string
  to?: string
}

function Tile({ label, value, hint, icon: Icon, tone, to }: TileProps) {
  const body = (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md">
      <div className={`grid h-10 w-10 place-items-center rounded-xl ${tone}`}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="mt-4 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-1 text-xs text-slate-400">{hint}</p>
    </div>
  )
  return to ? <Link to={to}>{body}</Link> : body
}

export default function DashboardPage() {
  const organizationId = useOrganizationId()

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
        Ko'rsatkichlarni yuklab bo'lmadi.
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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Boshqaruv paneli</h1>
        <p className="mt-1 text-sm text-slate-500">
          {data ? new Date(data.date).toLocaleDateString('uz-UZ', { dateStyle: 'long' }) : '—'}
        </p>
      </div>

      {/* Radix AI — kunlik brifing (docs/07 §11): KPI'lardan OLDIN, chunki
          "nimaga e'tibor berish kerak" umumiy raqamlardan muhimroq. */}
      <BriefingSection />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tile
          label="Faol bolalar"
          value={isLoading ? '…' : `${data?.active_children ?? 0} nafar`}
          hint="Ro'yxatdagi bolalar"
          icon={Users}
          tone="bg-sky-50 text-sky-600"
          to="/children"
        />
        <Tile
          label="Shu oy tushum"
          value={isLoading ? '…' : formatUZS(Number(data?.month_revenue ?? 0))}
          hint="Qabul qilingan to'lovlar"
          icon={Wallet}
          tone="bg-emerald-50 text-emerald-600"
          to="/payments"
        />
        <Tile
          label="Qarzdorlik"
          value={isLoading ? '…' : formatUZS(Number(data?.outstanding_debt ?? 0))}
          hint={`${data?.debtor_count ?? 0} nafar bola bo'yicha`}
          icon={AlertTriangle}
          tone="bg-red-50 text-red-600"
          to="/debtors"
        />
        <Tile
          label="Davomat (shu oy)"
          value={isLoading ? '…' : `${data?.attendance_month_pct ?? 0}%`}
          hint="Kelgan / belgilangan"
          icon={CalendarCheck}
          tone="bg-teal-50 text-teal-600"
          to="/attendance"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <h2 className="text-sm font-semibold text-slate-900">Tushum dinamikasi</h2>
          <p className="mt-0.5 text-xs text-slate-500">Oxirgi 6 oy, qabul qilingan to'lovlar</p>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                  tickFormatter={(v: number) => `${Math.round(v / 1_000_000)}mln`}
                />
                <Tooltip
                  formatter={(v: number) => formatUZS(v)}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                />
                <Bar dataKey="daromad" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
          <h2 className="text-sm font-semibold text-slate-900">Oxirgi to'lovlar</h2>
          <ul className="mt-4 space-y-3">
            {(data?.recent_payments ?? []).map((payment, index) => (
              <li key={`${payment.paid_at}-${index}`} className="flex items-center justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{payment.child}</p>
                  <p className="text-xs text-slate-400">{when(payment.paid_at)}</p>
                </div>
                <span className="shrink-0 text-sm font-semibold text-emerald-600">
                  {formatUZS(Number(payment.amount))}
                </span>
              </li>
            ))}
            {!isLoading && (data?.recent_payments ?? []).length === 0 && (
              <li className="py-6 text-center text-sm text-slate-400">
                Hozircha to'lov qabul qilinmagan.
              </li>
            )}
          </ul>

          {(data?.low_stock_count ?? 0) > 0 && (
            <Link
              to="/inventory"
              className="mt-5 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 hover:bg-amber-100"
            >
              <Package className="h-4 w-4 shrink-0" />
              {data?.low_stock_count} ta mahsulot minimumdan kam
            </Link>
          )}
        </section>
      </div>
    </div>
  )
}
