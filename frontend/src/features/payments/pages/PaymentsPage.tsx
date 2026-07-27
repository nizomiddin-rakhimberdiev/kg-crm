import { useMemo, useState } from 'react'
import {
  Wallet,
  ArrowLeftRight,
  Clock,
  CreditCard,
  Banknote,
  Building2,
  CheckCircle2,
  Download,
  type LucideIcon,
} from 'lucide-react'
import {
  Card,
  PageHeader,
  StatCard,
  Button,
  Badge,
  Avatar,
  Select,
  type BadgeTone,
} from '@/components/ui/primitives'
import { useToast } from '@/app/providers/ToastProvider'
import { formatMoney, formatUZS, cn } from '@/lib/utils'

interface Method {
  key: string
  label: string
  icon: LucideIcon
  badge: string
  tone: BadgeTone
}

const methods: Method[] = [
  { key: 'payme', label: 'Payme / Click', icon: CreditCard, badge: 'PAYME', tone: 'sky' },
  { key: 'cash', label: 'Naqd pul', icon: Banknote, badge: 'NAQD PUL', tone: 'success' },
  { key: 'transfer', label: "O'tkazma", icon: Building2, badge: "O'TKAZMA", tone: 'violet' },
]

interface Kid {
  name: string
  group: string
  id: string
  debt: number
}
const kids: Kid[] = [
  { name: 'Abdurahmonov Umar', group: 'Kamalak · 4 yosh', id: '#B-3049', debt: 450000 },
  { name: 'Karimova Laylo', group: 'Yulduzcha · 5 yosh', id: '#B-3055', debt: 1500000 },
  { name: 'Yusupov Bekzod', group: 'Bilimdon · 4 yosh', id: '#B-3061', debt: 900000 },
  { name: 'Salimova Nilufar', group: "Qaldirg'och · 5 yosh", id: '#B-3070', debt: 300000 },
]

interface Payment {
  id: number
  name: string
  time: string
  amount: number
  badge: string
  tone: BadgeTone
}
const recentSeed: Payment[] = [
  { id: 1, name: 'Karimov Aziz', time: '10-Okt, 14:20', amount: 320000, badge: 'KARTA', tone: 'info' },
  { id: 2, name: 'Nazarova Laylo', time: '10-Okt, 12:05', amount: 1200000, badge: 'NAQD PUL', tone: 'success' },
  { id: 3, name: 'Sharipov Davron', time: '09-Okt, 16:40', amount: 550000, badge: "O'TKAZMA", tone: 'violet' },
  { id: 4, name: 'Ismoilova Sabina', time: '09-Okt, 11:15', amount: 450000, badge: 'PAYME', tone: 'sky' },
]

const BASE_TOTAL = 4250000

export default function PaymentsPage() {
  const { toast } = useToast()
  const [method, setMethod] = useState('payme')
  const [kidIdx, setKidIdx] = useState(0)
  const [amount, setAmount] = useState(String(kids[0].debt))
  const [recent, setRecent] = useState<Payment[]>(recentSeed)

  const kid = kids[kidIdx]
  const addedTotal = useMemo(
    () => recent.filter((p) => p.id > 1000).reduce((s, p) => s + p.amount, 0),
    [recent],
  )
  const todayTotal = BASE_TOTAL + addedTotal
  const txCount = 28 + recent.filter((p) => p.id > 1000).length

  const selectKid = (v: string) => {
    const i = Number(v)
    setKidIdx(i)
    setAmount(String(kids[i].debt))
  }

  const confirm = () => {
    const amt = Number(amount) || 0
    if (amt <= 0) {
      toast('To\'lov summasini kiriting', 'error')
      return
    }
    const m = methods.find((x) => x.key === method)!
    const payment: Payment = {
      id: Date.now(),
      name: kid.name,
      time: 'Hozir',
      amount: amt,
      badge: m.badge,
      tone: m.tone,
    }
    setRecent((r) => [payment, ...r])
    toast(`${kid.name} — ${formatMoney(amt)} UZS qabul qilindi ✓`, 'success')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="To'lovlar va Kassa"
        subtitle="Bugungi kassa holati va yangi to'lov shakllantirish"
      >
        <div className="text-right">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Sana</p>
          <p className="text-sm font-semibold text-slate-700">14-Oktyabr, 2023</p>
        </div>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Bugungi tushum"
          value={formatUZS(todayTotal)}
          icon={Wallet}
          iconTone="success"
          delta="+12%"
          deltaTone="success"
          hint="Kechagiga nisbatan"
          detail={{
            description: `Bugun kassaga jami ${formatUZS(todayTotal)} tushdi (${txCount} ta tranzaksiya).`,
          }}
        />
        <StatCard
          label="Tranzaksiyalar"
          value={`${txCount} ta`}
          icon={ArrowLeftRight}
          iconTone="info"
          hint="Bugun"
          detail={{ description: `Bugun jami ${txCount} ta to'lov qayd etildi.` }}
        />
        <StatCard
          label="Kutilayotgan to'lovlar"
          value={formatUZS(1800000)}
          icon={Clock}
          iconTone="danger"
          hint="12 bola qarzdor"
          detail={{ description: '12 nafar bola bo\'yicha kutilayotgan to\'lovlar 1 800 000 UZS.' }}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left — payment form */}
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-base font-bold text-slate-900">Bola tanlash</h2>
            <div className="mt-3">
              <Select
                value={String(kidIdx)}
                onChange={selectKid}
                options={kids.map((k, i) => ({
                  label: `${k.name} — qarz: ${formatMoney(k.debt)}`,
                  value: String(i),
                }))}
              />
            </div>

            <div className="mt-4 flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="flex items-center gap-3">
                <Avatar name={kid.name} size="lg" />
                <div>
                  <p className="font-semibold text-slate-900">{kid.name}</p>
                  <p className="text-xs text-slate-500">Guruh: {kid.group}</p>
                  <p className="text-xs text-slate-400">ID: {kid.id}</p>
                </div>
              </div>
              <div className="rounded-xl bg-red-50 px-4 py-2 text-right">
                <p className="text-[11px] font-semibold uppercase text-red-400">Qarzdorlik</p>
                <p className="text-lg font-bold text-red-600">{formatUZS(kid.debt)}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-base font-bold text-slate-900">To'lov shakllantirish</h2>

            <label className="mt-4 block text-sm font-medium text-slate-600">To'lov summasi</label>
            <div className="relative mt-1.5">
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value.replace(/\D/g, ''))}
                inputMode="numeric"
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-lg font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm font-medium text-slate-400">
                UZS
              </span>
            </div>

            <p className="mt-4 text-sm font-medium text-slate-600">To'lov usuli</p>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {methods.map((m) => {
                const active = method === m.key
                return (
                  <button
                    key={m.key}
                    onClick={() => setMethod(m.key)}
                    className={cn(
                      'flex flex-col items-center gap-2 rounded-xl border-2 px-2 py-3 text-xs font-medium transition-all active:scale-95',
                      active
                        ? 'border-brand-500 bg-brand-50 text-brand-700'
                        : 'border-slate-200 text-slate-500 hover:border-slate-300',
                    )}
                  >
                    <m.icon className="w-5 h-5" />
                    {m.label}
                    <span
                      className={cn(
                        'grid place-items-center w-4 h-4 rounded-full border',
                        active ? 'border-brand-500' : 'border-slate-300',
                      )}
                    >
                      {active && <span className="w-2 h-2 rounded-full bg-brand-500" />}
                    </span>
                  </button>
                )
              })}
            </div>

            <Button
              icon={CheckCircle2}
              data-sound="success"
              onClick={confirm}
              className="mt-5 w-full py-3"
            >
              To'lovni tasdiqlash
            </Button>
            <p className="mt-3 text-center text-xs text-slate-400">
              Tasdiqlangandan so'ng ota-onaga chek avtomatik SMS orqali yuboriladi.
            </p>
          </Card>
        </div>

        {/* Right — recent + plan */}
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">So'nggi to'lovlar</h2>
              <button
                data-toast="Barcha to'lovlar ro'yxati (demo)"
                data-toast-tone="info"
                className="text-xs font-semibold text-brand-600 hover:underline active:scale-95"
              >
                Hammasini ko'rish
              </button>
            </div>
            <div className="mt-4 divide-y divide-slate-50">
              {recent.map((p) => (
                <div key={p.id} className="flex items-center gap-3 py-3">
                  <Avatar name={p.name} size="sm" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{p.name}</p>
                    <p className="text-xs text-slate-400">{p.time}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-900">{formatMoney(p.amount)}</p>
                    <Badge tone={p.tone} className="mt-0.5">
                      {p.badge}
                    </Badge>
                  </div>
                  <button
                    data-toast={`${p.name} — cheki yuklab olindi`}
                    className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-slate-100 active:scale-90"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </Card>

          <Card className="bg-slate-900 p-6 text-white">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-200">Oylik reja</p>
            <div className="mt-2 flex items-end justify-between">
              <p className="text-3xl font-bold">84% Bajarildi</p>
            </div>
            <div className="mt-4 h-2.5 w-full overflow-hidden rounded-full bg-white/15">
              <div className="h-full rounded-full bg-brand-400" style={{ width: '84%' }} />
            </div>
            <p className="mt-3 text-sm text-slate-300">
              Tizim orqali amalga oshirilgan barcha to'lovlar avtomatik hisobga olinadi.
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}
