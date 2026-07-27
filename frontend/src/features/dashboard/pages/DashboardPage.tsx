import {
  Users,
  Wallet,
  AlertTriangle,
  CalendarCheck,
  ArrowUpRight,
  Package,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, PageHeader, StatCard, Avatar, Badge } from '@/components/ui/primitives'
import { formatUZS } from '@/lib/utils'

const financeData = [
  { month: 'Yan', daromad: 42, xarajat: 18 },
  { month: 'Fev', daromad: 38, xarajat: 16 },
  { month: 'Mar', daromad: 45, xarajat: 21 },
  { month: 'Apr', daromad: 40, xarajat: 17 },
  { month: 'May', daromad: 48, xarajat: 19 },
  { month: 'Iyn', daromad: 44, xarajat: 20 },
  { month: 'Iyl', daromad: 52, xarajat: 22 },
  { month: 'Avg', daromad: 49, xarajat: 18 },
]

const recentPayments = [
  { name: 'Karimov Aziz', time: 'Bugun, 09:12', amount: 320000, method: 'Payme' },
  { name: 'Nazarova Laylo', time: 'Bugun, 08:40', amount: 1200000, method: 'Naqd' },
  { name: 'Sharipov Davron', time: 'Kecha, 17:05', amount: 550000, method: "O'tkazma" },
  { name: 'Ismoilova Sabina', time: 'Kecha, 15:22', amount: 450000, method: 'Payme' },
]

const lowStock = [
  { name: 'Tuxum', level: 12 },
  { name: 'Suyuq sovun 5L', level: 45 },
  { name: 'A4 qog\'oz', level: 30 },
]

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Premium Bog'cha — umumiy ko'rsatkichlar, 27-Iyul 2026"
      />

      {/* KPI cards — bosilganda batafsil ma'lumot ochiladi */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Faol bolalar"
          value="124 nafar"
          icon={Users}
          iconTone="info"
          delta="+6"
          deltaTone="success"
          hint="O'tgan oyga nisbatan"
          detail={{
            description:
              "Hozirda bog'chada 124 nafar faol bola tarbiyalanmoqda. Shu oyda 6 nafar yangi bola qabul qilindi, 1 nafar boshqa bog'chaga o'tkazildi.",
            breakdown: [
              { label: 'Kamalak guruhi', value: '32 nafar' },
              { label: 'Yulduzcha guruhi', value: '28 nafar' },
              { label: 'Bilimdon guruhi', value: '34 nafar' },
              { label: "Qaldirg'och guruhi", value: '30 nafar' },
            ],
            linkTo: '/children',
            linkLabel: 'Bolalar ro\'yxati',
          }}
        />
        <StatCard
          label="Oylik tushum"
          value={formatUZS(185000000)}
          icon={Wallet}
          iconTone="success"
          delta="+12%"
          deltaTone="success"
          hint="Iyul oyi bo'yicha"
          detail={{
            description:
              "Iyul oyida jami 185 000 000 UZS tushum yig'ildi — o'tgan oyga nisbatan 12% ko'p. Oylik reja 84% bajarildi.",
            breakdown: [
              { label: 'Plastik karta (Payme/Click)', value: '111 000 000', tone: 'success' },
              { label: 'Naqd pul', value: '46 000 000', tone: 'success' },
              { label: "Bank o'tkazmasi", value: '28 000 000', tone: 'success' },
            ],
            linkTo: '/payments',
            linkLabel: "To'lovlar bo'limi",
          }}
        />
        <StatCard
          label="Umumiy qarzdorlik"
          value={formatUZS(23400000)}
          icon={AlertTriangle}
          iconTone="danger"
          delta="34 nafar"
          deltaTone="danger"
          hint="Qarzdor bolalar"
          detail={{
            description:
              '34 nafar bola bo\'yicha jami 23 400 000 UZS qarzdorlik mavjud. Ulardan 8 tasi 30 kundan ortiq kechikkan — ustuvor e\'tibor talab qiladi.',
            breakdown: [
              { label: 'Kechikish 1–15 kun', value: '12 000 000', tone: 'neutral' },
              { label: 'Kechikish 15–30 kun', value: '6 400 000', tone: 'danger' },
              { label: 'Kechikish 30+ kun', value: '5 000 000', tone: 'danger' },
            ],
            linkTo: '/debtors',
            linkLabel: 'Qarzdorlar bo\'limi',
          }}
        />
        <StatCard
          label="Bugungi davomat"
          value="91.5%"
          icon={CalendarCheck}
          iconTone="teal"
          delta="+2.1%"
          deltaTone="success"
          hint="113 / 124 bola"
          detail={{
            description:
              'Bugun 124 boladan 113 tasi bog\'chaga keldi (91.5%). 11 tasi kelmadi — shundan 4 tasi sababli (hujjatli).',
            breakdown: [
              { label: 'Kelganlar', value: '113 nafar', tone: 'success' },
              { label: 'Kelmaganlar', value: '7 nafar', tone: 'danger' },
              { label: 'Sababli (hujjatli)', value: '4 nafar', tone: 'neutral' },
            ],
            linkTo: '/attendance',
            linkLabel: 'Davomat bo\'limi',
          }}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Finance chart */}
        <Card className="lg:col-span-2 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Moliya dinamikasi</h2>
              <p className="text-sm text-slate-500">Tushum va xarajatlar (mln UZS)</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-slate-500">
                <span className="w-2.5 h-2.5 rounded-sm bg-brand-600" /> Daromad
              </span>
              <span className="flex items-center gap-1.5 text-slate-500">
                <span className="w-2.5 h-2.5 rounded-sm bg-rose-300" /> Xarajat
              </span>
            </div>
          </div>
          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={financeData} barGap={6}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef2f7" />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip
                  cursor={{ fill: '#f8fafc' }}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                />
                <Bar dataKey="daromad" fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={22} />
                <Bar dataKey="xarajat" fill="#fda4af" radius={[6, 6, 0, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Recent payments */}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">So'nggi to'lovlar</h2>
            <button
              data-toast="Barcha to'lovlar (demo)"
              data-toast-tone="info"
              className="text-xs font-semibold text-brand-600 hover:underline active:scale-95"
            >
              Hammasi
            </button>
          </div>
          <div className="mt-4 space-y-1">
            {recentPayments.map((p) => (
              <div
                key={p.name}
                className="flex items-center gap-3 rounded-xl px-2 py-2.5 hover:bg-slate-50"
              >
                <Avatar name={p.name} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-800">{p.name}</p>
                  <p className="text-xs text-slate-400">{p.time}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-slate-900">
                    {p.amount.toLocaleString('en-US')}
                  </p>
                  <Badge tone="info" className="mt-0.5">
                    {p.method}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Bottom row */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 flex flex-col justify-between gap-4 bg-slate-900 p-6 text-white sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2 text-brand-200">
              <ArrowUpRight className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wide">Oylik reja</span>
            </div>
            <p className="mt-2 text-3xl font-bold">84% bajarildi</p>
            <p className="mt-1 text-sm text-slate-300">
              Iyul oyi to'lov rejasi 155 mln UZS dan 130 mln UZS yig'ildi.
            </p>
          </div>
          <div className="grid place-items-center w-24 h-24 rounded-full border-8 border-brand-500/30">
            <span className="text-xl font-bold">84%</span>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-2">
            <div className="grid place-items-center w-9 h-9 rounded-xl bg-amber-50 text-amber-600">
              <Package className="w-5 h-5" />
            </div>
            <h2 className="text-base font-bold text-slate-900">Kam qolgan mahsulotlar</h2>
          </div>
          <div className="mt-4 space-y-3">
            {lowStock.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-sm">
                <span className="text-slate-600">{s.name}</span>
                <Badge tone={s.level < 20 ? 'danger' : 'warning'}>{s.level}%</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
