import { useMemo, useState } from 'react'
import {
  Receipt,
  Utensils,
  Zap,
  Home,
  FileText,
  Landmark,
  Filter,
  CalendarDays,
  FileCheck2,
  TrendingUp,
  TrendingDown,
  Plus,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  Card,
  PageHeader,
  StatCard,
  Button,
  Badge,
  Select,
  Pagination,
  type BadgeTone,
} from '@/components/ui/primitives'
import { Modal } from '@/components/ui/Modal'
import { Field, TextInput } from '@/components/ui/form'
import { useToast } from '@/app/providers/ToastProvider'
import { formatMoney, formatUZS } from '@/lib/utils'

const daily = [
  { day: '01', v: 1.2 }, { day: '03', v: 0.9 }, { day: '05', v: 1.6 }, { day: '07', v: 1.1 },
  { day: '09', v: 2.1 }, { day: '11', v: 1.4 }, { day: '13', v: 1.9 }, { day: '15', v: 1.2 },
  { day: '17', v: 2.4 }, { day: '19', v: 1.7 }, { day: '21', v: 1.3 }, { day: '23', v: 2.0 },
  { day: '25', v: 1.5 }, { day: '28', v: 1.8 },
]

interface CatMeta {
  name: string
  icon: LucideIcon
  tone: BadgeTone
}
const categoryMeta: CatMeta[] = [
  { name: 'Oziq-ovqat', icon: Utensils, tone: 'teal' },
  { name: 'Kommunal', icon: Zap, tone: 'sky' },
  { name: 'Ijara', icon: Home, tone: 'amber' },
  { name: 'Kantselyariya', icon: FileText, tone: 'neutral' },
  { name: "Xo'jalik", icon: Receipt, tone: 'violet' },
  { name: 'Soliqlar', icon: Landmark, tone: 'danger' },
]
const catTone = (name: string): BadgeTone =>
  categoryMeta.find((c) => c.name === name)?.tone ?? 'neutral'

interface Expense {
  id: number
  name: string
  category: string
  amount: number
  date: string
}

const seed: Expense[] = [
  { id: 1, name: "Go'sht va sut mahsulotlari", category: 'Oziq-ovqat', amount: 3250000, date: '14 Mart, 2024' },
  { id: 2, name: 'Suv va kanalizatsiya', category: 'Kommunal', amount: 840000, date: '12 Mart, 2024' },
  { id: 3, name: "A4 qog'ozlar va papkalar", category: 'Kantselyariya', amount: 450000, date: '10 Mart, 2024' },
  { id: 4, name: 'Gigiyena vositalari', category: "Xo'jalik", amount: 1100000, date: '08 Mart, 2024' },
]

const categoriesSummary = [
  { name: 'Oziq-ovqat', amount: '19.2 mln', icon: Utensils, tone: 'teal' as BadgeTone },
  { name: 'Kommunal', amount: '4.5 mln', icon: Zap, tone: 'sky' as BadgeTone },
  { name: 'Ijara', amount: '12.0 mln', icon: Home, tone: 'amber' as BadgeTone },
  { name: 'Kantselyariya', amount: '2.8 mln', icon: FileText, tone: 'neutral' as BadgeTone },
  { name: 'Soliqlar', amount: '3.4 mln', icon: Landmark, tone: 'danger' as BadgeTone },
]

const emptyForm = { name: '', category: 'Oziq-ovqat', amount: '' }

export default function ExpensesPage() {
  const { toast } = useToast()
  const [expenses, setExpenses] = useState<Expense[]>(seed)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const total = useMemo(() => expenses.reduce((s, e) => s + e.amount, 0), [expenses])

  const addExpense = () => {
    if (!form.name.trim() || !form.amount) {
      toast('Nomi va summani kiriting', 'error')
      return
    }
    const item: Expense = {
      id: Date.now(),
      name: form.name.trim(),
      category: form.category,
      amount: Number(form.amount) || 0,
      date: new Date().toLocaleDateString('ru-RU'),
    }
    setExpenses((e) => [item, ...e])
    toast(`Xarajat qo'shildi: ${formatMoney(item.amount)} UZS ✓`, 'success')
    setForm(emptyForm)
    setOpen(false)
  }

  const removeExpense = (id: number) => {
    setExpenses((e) => e.filter((x) => x.id !== id))
    toast("Xarajat o'chirildi", 'info')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Chiqimlar tahlili"
        subtitle="Bog'cha xarajatlarini real vaqt rejimida kuzating"
      >
        <button
          data-toast="Oy tanlash (demo)"
          data-toast-tone="info"
          className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition-all hover:bg-slate-50 active:scale-95"
        >
          <CalendarDays className="w-4 h-4 text-slate-400" />
          Mart, 2024
        </button>
        <Button variant="outline" icon={Filter} data-toast="Filtr qo'llandi ✓">
          Filtr
        </Button>
        <Button icon={Plus} data-sound="success" onClick={() => setOpen(true)}>
          Yangi xarajat
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Umumiy xarajat (jami)"
          value={formatUZS(total)}
          icon={Receipt}
          iconTone="danger"
          delta="+12%"
          deltaTone="danger"
          detail={{
            description: `Joriy ro'yxatdagi barcha xarajatlar yig'indisi ${formatUZS(total)}.`,
            breakdown: expenses.slice(0, 4).map((e) => ({ label: e.name, value: formatMoney(e.amount), tone: 'danger' as const })),
          }}
        />
        <StatCard
          label="Asosiy kategoriya"
          value="Oziq-ovqat"
          icon={Utensils}
          iconTone="teal"
          hint="Umumiy xarajatning 45% qismi"
          detail={{ description: 'Eng katta xarajat — oziq-ovqat (45%).' }}
        />
        <StatCard
          label="Yozuvlar soni"
          value={`${expenses.length} ta`}
          icon={TrendingDown}
          iconTone="success"
          hint="Joriy ro'yxatda"
          detail={{ description: `Hozirda ${expenses.length} ta xarajat yozuvi mavjud.` }}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Kunlik xarajatlar dinamikasi</h2>
              <p className="text-sm text-slate-500">Mart 2024 (mln UZS)</p>
            </div>
            <span className="flex items-center gap-1.5 text-xs text-brand-600">
              <TrendingUp className="w-4 h-4" /> Mart 2024
            </span>
          </div>
          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={daily}>
                <defs>
                  <linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef2f7" />
                <XAxis
                  dataKey="day"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#94a3b8' }}
                  tickFormatter={(d) => `${d} Mart`}
                  interval={2}
                />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                  formatter={(v: number) => [`${v} mln`, 'Xarajat']}
                />
                <Area type="monotone" dataKey="v" stroke="#2563eb" strokeWidth={2.5} fill="url(#expenseFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-base font-bold text-slate-900">Kategoriyalar</h2>
          <div className="mt-4 space-y-2">
            {categoriesSummary.map((c) => (
              <div key={c.name} className="flex items-center gap-3 rounded-xl px-2 py-2.5 hover:bg-slate-50">
                <div
                  className={
                    'grid place-items-center w-9 h-9 rounded-lg ' +
                    {
                      teal: 'bg-teal-50 text-teal-600',
                      sky: 'bg-sky-50 text-sky-600',
                      amber: 'bg-amber-50 text-amber-600',
                      neutral: 'bg-slate-100 text-slate-500',
                      danger: 'bg-red-50 text-red-500',
                    }[c.tone as 'teal' | 'sky' | 'amber' | 'neutral' | 'danger']
                  }
                >
                  <c.icon className="w-4 h-4" />
                </div>
                <span className="flex-1 text-sm text-slate-600">{c.name}</span>
                <span className="text-sm font-semibold text-slate-900">{c.amount}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 p-4">
          <h2 className="text-base font-bold text-slate-900">So'nggi xarajatlar</h2>
          <Button variant="outline" icon={Plus} className="px-3 py-1.5 text-xs" onClick={() => setOpen(true)}>
            Qo'shish
          </Button>
        </div>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">Nomi</th>
                <th className="px-6 py-3">Kategoriya</th>
                <th className="px-6 py-3">Miqdor (UZS)</th>
                <th className="px-6 py-3">Sana</th>
                <th className="px-6 py-3 text-right">Amal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {expenses.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/60">
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="grid place-items-center w-9 h-9 rounded-lg bg-slate-100 text-slate-500">
                        <Receipt className="w-4 h-4" />
                      </div>
                      <span className="font-medium text-slate-800">{r.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3.5">
                    <Badge tone={catTone(r.category)}>{r.category}</Badge>
                  </td>
                  <td className="px-6 py-3.5 font-semibold text-slate-900">{formatMoney(r.amount)}</td>
                  <td className="px-6 py-3.5 text-slate-500">{r.date}</td>
                  <td className="px-6 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        data-toast={`${r.name} — cheki ochildi`}
                        data-toast-tone="info"
                        className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-slate-100 hover:text-brand-600 active:scale-90"
                      >
                        <FileCheck2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => removeExpense(r.id)}
                        className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-red-50 hover:text-red-500 active:scale-90"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-14 text-center text-sm text-slate-400">
                    Xarajat yo'q. "Yangi xarajat" tugmasi orqali qo'shing.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-6 pb-4">
          <Pagination label={`Jami ${expenses.length} ta ko'rsatilmoqda`} pages={1} current={1} />
        </div>
      </Card>

      {/* Add expense modal */}
      <Modal open={open} onClose={() => setOpen(false)}>
        <div className="p-6">
          <div className="flex items-center gap-3 pr-8">
            <div className="grid place-items-center w-11 h-11 rounded-xl bg-red-50 text-red-500">
              <Receipt className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Yangi xarajat</h2>
              <p className="text-sm text-slate-500">Xarajat ma'lumotlarini kiriting.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            <Field label="Xarajat nomi">
              <TextInput value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Masalan: Elektr energiyasi" />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Kategoriya">
                <Select
                  value={form.category}
                  onChange={(v) => set('category', v)}
                  options={categoryMeta.map((c) => ({ label: c.name, value: c.name }))}
                />
              </Field>
              <Field label="Miqdor (UZS)">
                <TextInput
                  value={form.amount}
                  onChange={(e) => set('amount', e.target.value.replace(/\D/g, ''))}
                  inputMode="numeric"
                  placeholder="1 000 000"
                />
              </Field>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Bekor qilish
            </Button>
            <Button icon={Plus} data-sound="success" onClick={addExpense}>
              Qo'shish
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
