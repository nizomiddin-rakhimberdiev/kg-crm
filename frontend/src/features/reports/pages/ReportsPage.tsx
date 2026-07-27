import {
  Wallet,
  Receipt,
  TrendingUp,
  CalendarCheck,
  AlertTriangle,
  CalendarDays,
  Building2,
  Users,
  Plus,
  FileDown,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, PageHeader, StatCard, Button } from '@/components/ui/primitives'

const finance = [
  { m: 'Yan', d: 38, x: 15 }, { m: 'Fev', d: 42, x: 17 }, { m: 'Mar', d: 40, x: 16 },
  { m: 'Apr', d: 45, x: 19 }, { m: 'May', d: 48, x: 18 }, { m: 'Iyn', d: 44, x: 20 },
  { m: 'Iyl', d: 52, x: 22 }, { m: 'Avg', d: 49, x: 19 }, { m: 'Sen', d: 46, x: 17 },
  { m: 'Okt', d: 51, x: 21 }, { m: 'Noy', d: 47, x: 18 }, { m: 'Dek', d: 53, x: 23 },
]

const payTypes = [
  { name: 'Plastik karta', value: 291.1, pct: '60%', color: '#2563eb' },
  { name: 'Naqd pul', value: 121.3, pct: '25%', color: '#14b8a6' },
  { name: "Bank o'tkazmasi", value: 72.8, pct: '15%', color: '#bfdbfe' },
]

const groups = ['Kamalak', 'Yulduzcha', 'Bilimdon', "Qaldirg'och"]
const days = ['DUSH', 'SESH', 'CHOR', 'PAY', 'JUM']
const heat: number[][] = [
  [90, 85, 70, 95, 88],
  [60, 75, 80, 65, 92],
  [40, 55, 60, 78, 70],
  [88, 92, 85, 90, 95],
]

const structure = [
  { name: 'Xodimlar oyligi', value: '124.5M', tone: 'bg-brand-600' },
  { name: 'Oziq-ovqat', value: '42.8M', tone: 'bg-teal-500' },
  { name: 'Ijara va Kommunal', value: '18.2M', tone: 'bg-amber-500' },
  { name: 'Boshqa', value: '6.9M', tone: 'bg-slate-400' },
]

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="mr-2 text-2xl font-bold tracking-tight text-slate-900">Tahlillar</h1>
          <FilterPill icon={CalendarDays} label="Yanvar 2024 - Dekabr 2024" />
          <FilterPill icon={Building2} label="Barcha filiallar" />
          <FilterPill icon={Users} label="Barcha guruhlar" />
        </div>
        <Button icon={Plus} data-sound="success" data-toast="Yangi hisobot yaratildi ✓">
          Hisobot yaratish
        </Button>
      </div>

      {/* KPI */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Jami tushum"
          value="485.2M"
          icon={Wallet}
          iconTone="info"
          delta="+9%"
          deltaTone="success"
          hint="O'tgan yildan"
          detail={{
            description: "2024-yil bo'yicha jami tushum 485.2 mln UZS — o'tgan yilга nisbatan 9% ko'p.",
            breakdown: [
              { label: 'Plastik karta (60%)', value: '291.1M', tone: 'success' },
              { label: 'Naqd pul (25%)', value: '121.3M', tone: 'success' },
              { label: "Bank o'tkazmasi (15%)", value: '72.8M', tone: 'success' },
            ],
            linkTo: '/payments',
            linkLabel: "To'lovlar",
          }}
        />
        <StatCard
          label="Jami xarajat"
          value="192.4M"
          icon={Receipt}
          iconTone="danger"
          delta="+4%"
          deltaTone="danger"
          hint="O'tgan yildan"
          detail={{
            description: "2024-yil bo'yicha jami xarajat 192.4 mln UZS.",
            breakdown: [
              { label: 'Xodimlar oyligi', value: '124.5M', tone: 'danger' },
              { label: 'Oziq-ovqat', value: '42.8M', tone: 'danger' },
              { label: 'Ijara va boshqa', value: '25.1M', tone: 'danger' },
            ],
            linkTo: '/expenses',
            linkLabel: 'Chiqimlar',
          }}
        />
        <StatCard
          label="Sof foyda"
          value="292.8M"
          icon={TrendingUp}
          iconTone="success"
          delta="+8.5%"
          deltaTone="success"
          hint="O'sish"
          detail={{
            description:
              'Sof foyda = tushum − xarajat = 485.2M − 192.4M = 292.8 mln UZS. Yillik o\'sish 8.5%.',
            breakdown: [
              { label: 'Jami tushum', value: '485.2M', tone: 'success' },
              { label: 'Jami xarajat', value: '-192.4M', tone: 'danger' },
            ],
          }}
        />
        <StatCard
          label="O'rtacha davomat"
          value="94.2%"
          icon={CalendarCheck}
          iconTone="teal"
          hint="Maqsad: 95%"
          detail={{
            description: "Yillik o'rtacha davomat 94.2% — maqsad (95%) ga deyarli erishildi.",
            breakdown: [
              { label: 'Eng yuqori (Qaldirg\'och)', value: '96.1%', tone: 'success' },
              { label: 'Eng past (Bilimdon)', value: '91.8%', tone: 'neutral' },
            ],
            linkTo: '/attendance',
            linkLabel: 'Davomat',
          }}
        />
        <StatCard
          label="Jami qarzdorlik"
          value="32.1M"
          icon={AlertTriangle}
          iconTone="warning"
          hint="48 ta o'quvchi"
          detail={{
            description: "Yil oxiriga 48 nafar o'quvchi bo'yicha 32.1 mln UZS qarzdorlik qoldi.",
            breakdown: [
              { label: 'Joriy oy', value: '18.4M', tone: 'neutral' },
              { label: 'Eski qarzlar', value: '13.7M', tone: 'danger' },
            ],
            linkTo: '/debtors',
            linkLabel: 'Qarzdorlar',
          }}
        />
      </div>

      {/* Charts row 1 */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Moliya dinamikasi</h2>
              <p className="text-sm text-slate-500">Tushum va xarajatlar (12 oy, mln UZS)</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" icon={FileDown} className="px-3 py-1.5 text-xs" data-toast="PDF hisobot yuklab olindi">PDF</Button>
              <Button variant="outline" icon={FileDown} className="px-3 py-1.5 text-xs" data-toast="Excel hisobot yuklab olindi">Excel</Button>
            </div>
          </div>
          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={finance} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef2f7" />
                <XAxis dataKey="m" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }} />
                <Bar dataKey="d" name="Daromad" fill="#1e40af" radius={[4, 4, 0, 0]} maxBarSize={16} />
                <Bar dataKey="x" name="Xarajat" fill="#fda4af" radius={[4, 4, 0, 0]} maxBarSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Donut */}
        <Card className="p-6">
          <h2 className="text-base font-bold text-slate-900">To'lov turlari</h2>
          <div className="relative mt-2 h-52">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={payTypes}
                  dataKey="value"
                  innerRadius={62}
                  outerRadius={88}
                  paddingAngle={2}
                  stroke="none"
                >
                  {payTypes.map((p) => (
                    <Cell key={p.name} fill={p.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-900">485M</p>
                <p className="text-[11px] uppercase tracking-wide text-slate-400">Umumiy</p>
              </div>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {payTypes.map((p) => (
              <div key={p.name} className="flex items-center gap-2 text-sm">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: p.color }} />
                <span className="flex-1 text-slate-600">
                  {p.name} <span className="text-slate-400">({p.pct})</span>
                </span>
                <span className="font-semibold text-slate-900">{p.value}M</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Charts row 2 */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Heatmap */}
        <Card className="lg:col-span-2 p-6">
          <h2 className="text-base font-bold text-slate-900">Haftalik davomat</h2>
          <p className="text-sm text-slate-500">Guruhlar bo'yicha (%)</p>
          <div className="mt-6 overflow-x-auto scrollbar-thin">
            <div className="min-w-[420px]">
              <div className="grid grid-cols-[110px_repeat(5,1fr)] gap-2 text-center">
                <div />
                {days.map((d) => (
                  <div key={d} className="text-[11px] font-semibold uppercase text-slate-400">
                    {d}
                  </div>
                ))}
                {groups.map((g, gi) => (
                  <FragmentRow key={g} label={g} values={heat[gi]} />
                ))}
              </div>
              <div className="mt-4 flex items-center justify-end gap-2 text-[11px] text-slate-400">
                <span>Past</span>
                {[0.2, 0.4, 0.6, 0.8, 1].map((o) => (
                  <span
                    key={o}
                    className="w-5 h-3 rounded-sm"
                    style={{ background: `rgba(37,99,235,${o})` }}
                  />
                ))}
                <span>Yaxshi</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Structure */}
        <Card className="p-6">
          <h2 className="text-base font-bold text-slate-900">Xarajatlar strukturasi</h2>
          <p className="text-sm text-slate-500">Yillik kategoriyalar</p>
          <div className="mt-5 grid grid-cols-2 gap-3">
            {structure.map((s) => (
              <div key={s.name} className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
                <span className={`inline-block w-2.5 h-2.5 rounded-full ${s.tone}`} />
                <p className="mt-2 text-lg font-bold text-slate-900">{s.value}</p>
                <p className="text-xs text-slate-500">{s.name}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

function FilterPill({ icon: Icon, label }: { icon: typeof CalendarDays; label: string }) {
  return (
    <button
      data-sound="open"
      data-toast={`${label} — tanlash (demo)`}
      data-toast-tone="info"
      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition-all hover:bg-slate-50 active:scale-95"
    >
      <Icon className="w-4 h-4 text-slate-400" />
      {label}
    </button>
  )
}

function FragmentRow({ label, values }: { label: string; values: number[] }) {
  return (
    <>
      <div className="flex items-center text-sm font-medium text-slate-600">{label}</div>
      {values.map((v, i) => (
        <div
          key={i}
          className="grid h-10 place-items-center rounded-lg text-xs font-semibold text-white/90"
          style={{ background: `rgba(37,99,235,${0.15 + (v / 100) * 0.85})` }}
        >
          {v}
        </div>
      ))}
    </>
  )
}
