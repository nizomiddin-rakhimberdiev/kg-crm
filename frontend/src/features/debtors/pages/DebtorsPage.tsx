import { useMemo, useState } from 'react'
import {
  Banknote,
  Users,
  AlertTriangle,
  TrendingUp,
  FileText,
  Send,
  Search,
  SlidersHorizontal,
  MessageSquare,
  ExternalLink,
  CheckCircle2,
  Clock,
  XCircle,
} from 'lucide-react'
import {
  Card,
  PageHeader,
  StatCard,
  Button,
  Badge,
  Avatar,
  Select,
  Pagination,
} from '@/components/ui/primitives'
import { formatMoney, formatUZS } from '@/lib/utils'

type SmsStatus = 'sent' | 'pending' | 'error'

interface Debtor {
  name: string
  id: string
  group: string
  debt: number
  days: number
  lastPayment: string
  sms: SmsStatus
}

const debtors: Debtor[] = [
  { name: "Azizbek G'ulomov", id: '#0026-1029', group: 'Katta guruh - A', debt: 2450000, days: 14, lastPayment: '12-May, 2024', sms: 'sent' },
  { name: 'Laylo Karimova', id: '#0026-2214', group: "O'rta guruh - B", debt: 4800000, days: 32, lastPayment: '04-April, 2024', sms: 'pending' },
  { name: 'Sardor Olimov', id: '#0026-3341', group: 'Kichik guruh', debt: 950000, days: 4, lastPayment: '25-May, 2024', sms: 'error' },
  { name: 'Malika Ergasheva', id: '#0026-4455', group: 'Tayyorlov guruhi', debt: 1200000, days: 8, lastPayment: '18-May, 2024', sms: 'sent' },
]

const smsBadge = {
  sent: { tone: 'success' as const, label: 'Yuborilgan', icon: CheckCircle2 },
  pending: { tone: 'warning' as const, label: 'Kutilyapti', icon: Clock },
  error: { tone: 'danger' as const, label: 'Xatolik', icon: XCircle },
}

export default function DebtorsPage() {
  const [search, setSearch] = useState('')
  const [group, setGroup] = useState('all')
  const [amountF, setAmountF] = useState('all')
  const [daysF, setDaysF] = useState('all')

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return debtors.filter((d) => {
      const matchSearch =
        !q || d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q)
      const matchGroup = group === 'all' || d.group === group
      const matchAmount =
        amountF === 'all' || (amountF === '1m' ? d.debt > 1_000_000 : d.debt > 3_000_000)
      const matchDays = daysF === 'all' || (daysF === '30' ? d.days > 30 : d.days > 60)
      return matchSearch && matchGroup && matchAmount && matchDays
    })
  }, [search, group, amountF, daysF])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Qarzdorlar Ro'yxati"
        subtitle="To'lovni amalga oshirmagan barcha bolalar va ularning holati"
      >
        <Button variant="outline" icon={FileText} data-toast="SMS shablonlari ochildi (demo)" data-toast-tone="info">
          SMS Shablonlari
        </Button>
        <Button variant="success" icon={Send} data-sound="success" data-toast="Barcha 34 qarzdorga SMS yuborildi ✓">
          Barcha qarzdorlarga SMS yuborish
        </Button>
      </PageHeader>

      {/* KPI */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Jami qarzdorlik"
          value={formatUZS(42500000)}
          icon={Banknote}
          iconTone="danger"
          delta="+13%"
          deltaTone="danger"
          detail={{
            description:
              "Barcha qarzdor bolalar bo'yicha umumiy qarzdorlik 42 500 000 UZS — o'tgan oyga nisbatan 13% oshdi.",
            breakdown: [
              { label: 'Katta guruh - A', value: '15 200 000', tone: 'danger' },
              { label: "O'rta guruh - B", value: '18 400 000', tone: 'danger' },
              { label: 'Kichik / Tayyorlov', value: '8 900 000', tone: 'danger' },
            ],
          }}
        />
        <StatCard
          label="Qarzdorlar soni"
          value="34 nafar"
          icon={Users}
          iconTone="info"
          detail={{
            description: "Hozirda 34 nafar bola to'lovni o'z vaqtida amalga oshirmagan.",
            breakdown: [
              { label: '1–15 kun kechikkan', value: '18 nafar' },
              { label: '15–30 kun kechikkan', value: '8 nafar' },
              { label: '30+ kun kechikkan', value: '8 nafar', tone: 'danger' },
            ],
          }}
        />
        <StatCard
          label="Kechikayotganlar (>30 kun)"
          value="8"
          icon={AlertTriangle}
          iconTone="danger"
          delta="Kritik"
          deltaTone="danger"
          detail={{
            description:
              '8 nafar bola 30 kundan ortiq kechikkan — bular ustuvor ravishda ota-onalar bilan bog\'lanishni talab qiladi.',
            breakdown: [
              { label: 'Laylo Karimova', value: '32 kun', tone: 'danger' },
              { label: "Boshqa 7 nafar", value: '30–45 kun', tone: 'danger' },
            ],
          }}
        />
        <StatCard
          label="Yig'ib olingan (Shu oy)"
          value={formatUZS(156000000)}
          icon={TrendingUp}
          iconTone="success"
          delta="82%"
          deltaTone="success"
          detail={{
            description:
              "Shu oyda qarzdorlardan jami 156 000 000 UZS yig'ib olindi — bu rejaning 82% ini tashkil qiladi.",
            breakdown: [
              { label: 'SMS eslatma orqali', value: '98 000 000', tone: 'success' },
              { label: "Qo'ng'iroq orqali", value: '58 000 000', tone: 'success' },
            ],
            linkTo: '/reports',
            linkLabel: 'Hisobotlar',
          }}
        />
      </div>

      {/* Filters + table */}
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row lg:items-end">
          <div className="relative flex-1">
            <label className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Qidiruv
            </label>
            <div className="relative mt-1.5">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Ism yoki ID bo'yicha..."
                className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
            </div>
          </div>
          <Select
            label="Guruh"
            className="lg:w-44"
            value={group}
            onChange={setGroup}
            options={[
              { label: 'Barcha guruhlar', value: 'all' },
              { label: 'Katta guruh - A', value: 'Katta guruh - A' },
              { label: "O'rta guruh - B", value: "O'rta guruh - B" },
              { label: 'Kichik guruh', value: 'Kichik guruh' },
              { label: 'Tayyorlov guruhi', value: 'Tayyorlov guruhi' },
            ]}
          />
          <Select
            label="Qarz summasi"
            className="lg:w-44"
            value={amountF}
            onChange={setAmountF}
            options={[
              { label: 'Barchasi', value: 'all' },
              { label: '1 mln dan yuqori', value: '1m' },
              { label: '3 mln dan yuqori', value: '3m' },
            ]}
          />
          <Select
            label="Kechikkan kunlar"
            className="lg:w-44"
            value={daysF}
            onChange={setDaysF}
            options={[
              { label: 'Barchasi', value: 'all' },
              { label: '> 30 kun', value: '30' },
              { label: '> 60 kun', value: '60' },
            ]}
          />
        </div>

        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">
                  <input type="checkbox" className="rounded border-slate-300" />
                </th>
                <th className="px-6 py-3">Bola</th>
                <th className="px-6 py-3">Qarzdorlik summasi</th>
                <th className="px-6 py-3">Kechikkan kunlar</th>
                <th className="px-6 py-3">Oxirgi to'lov</th>
                <th className="px-6 py-3">SMS holati</th>
                <th className="px-6 py-3 text-right">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((d) => {
                const s = smsBadge[d.sms]
                return (
                  <tr key={d.id} className="hover:bg-slate-50/60">
                    <td className="px-6 py-4">
                      <input type="checkbox" className="rounded border-slate-300" />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <Avatar name={d.name} />
                        <div>
                          <p className="font-medium text-slate-800">{d.name}</p>
                          <p className="text-xs text-slate-400">
                            ID: {d.id} · {d.group}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-bold text-red-600">{formatMoney(d.debt)} UZS</span>
                    </td>
                    <td className="px-6 py-4">
                      <Badge tone={d.days > 10 ? 'danger' : 'warning'}>{d.days} kun</Badge>
                    </td>
                    <td className="px-6 py-4 text-slate-500">{d.lastPayment}</td>
                    <td className="px-6 py-4">
                      <Badge tone={s.tone}>
                        <s.icon className="w-3.5 h-3.5" />
                        {s.label}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          data-sound="success"
                          data-toast={`${d.name}ga eslatma SMS yuborildi ✓`}
                          className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-slate-100 hover:text-brand-600 active:scale-90"
                        >
                          <MessageSquare className="w-4 h-4" />
                        </button>
                        <button
                          data-toast={`${d.name} — batafsil ma'lumot (demo)`}
                          data-toast-tone="info"
                          className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-slate-100 hover:text-brand-600 active:scale-90"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-14 text-center text-sm text-slate-400">
                    Qarzdor topilmadi. Qidiruv yoki filtrni o'zgartiring.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-6 pb-4">
          <Pagination
            label={`${filtered.length} ta qarzdor ko'rsatilmoqda`}
            pages={1}
            current={1}
          />
        </div>
      </Card>
    </div>
  )
}
