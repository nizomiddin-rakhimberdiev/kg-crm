import { useState } from 'react'
import { Wallet, CheckCircle2, Clock, Download, Send, SlidersHorizontal } from 'lucide-react'
import { useToast } from '@/app/providers/ToastProvider'
import {
  Card,
  PageHeader,
  StatCard,
  Button,
  Badge,
  Avatar,
  Pagination,
  type BadgeTone,
} from '@/components/ui/primitives'
import { formatMoney, formatUZS, cn } from '@/lib/utils'

type Status = "To'langan" | 'Kutilmoqda' | 'Kechikkan'

interface Row {
  name: string
  id: string
  position: string
  base: number
  bonus: number
  penalty: number
  advance: number
  total: number
  status: Status
}

const statusTone: Record<Status, BadgeTone> = {
  "To'langan": 'success',
  Kutilmoqda: 'warning',
  Kechikkan: 'danger',
}

const seed: Row[] = [
  { name: 'Ziloa Karimbekova', id: '#0342', position: 'Katta tarbiyachi', base: 6500000, bonus: 500000, penalty: 0, advance: 1000000, total: 6000000, status: "To'langan" },
  { name: 'Jasur Mirzayev', id: '#0392', position: 'Ingliz tili ustozi', base: 8000000, bonus: 1200000, penalty: 250000, advance: 0, total: 8950000, status: 'Kutilmoqda' },
  { name: 'Nigora Axmedova', id: '#0356', position: 'Logoped', base: 7200000, bonus: 0, penalty: 150000, advance: 500000, total: 6550000, status: 'Kechikkan' },
  { name: 'Mastura opa', id: '#0301', position: 'Bosh oshpaz', base: 4500000, bonus: 300000, penalty: 0, advance: 0, total: 4800000, status: "To'langan" },
  { name: 'Dilnoza Rasulova', id: '#0377', position: 'Tarbiyachi yordamchisi', base: 3800000, bonus: 200000, penalty: 0, advance: 500000, total: 3500000, status: "To'langan" },
  { name: 'Sardor Aliyev', id: '#0388', position: 'Xavfsizlik xodimi', base: 4000000, bonus: 0, penalty: 100000, advance: 0, total: 3900000, status: 'Kutilmoqda' },
]

const tabs = ['Barchasi', "To'lanmagan", "To'langan"]

export default function PayrollPage() {
  const { toast } = useToast()
  const [tab, setTab] = useState('Barchasi')
  const [rows, setRows] = useState<Row[]>(seed)

  const filtered = rows.filter((r) =>
    tab === 'Barchasi'
      ? true
      : tab === "To'langan"
        ? r.status === "To'langan"
        : r.status !== "To'langan",
  )

  const markPaid = (id: string, name: string) => {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, status: "To'langan" } : r)))
    toast(`${name}ga maosh to'landi ✓`, 'success')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Oylik Maoshlar"
        subtitle="2023-yil, Dekabr oyi uchun hisoblangan ish haqi ko'rsatkichlari"
      >
        <Button variant="outline" icon={Download} data-toast="Hisobot Excel'ga eksport qilindi">
          Eksport
        </Button>
        <Button icon={Send} data-sound="success" data-toast="Barcha xodimlarga maosh to'landi ✓">
          Ommaviy to'lash
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Jami to'lanadigan"
          value={formatUZS(450200000)}
          icon={Wallet}
          iconTone="info"
          delta="+4%"
          deltaTone="success"
          hint="O'tgan oyga nisbatan"
          detail={{
            description:
              'Dekabr oyi uchun 48 nafar xodimga jami 450 200 000 UZS ish haqi hisoblangan (mukofot va jarimalar bilan).',
            breakdown: [
              { label: 'Asosiy oyliklar', value: '398 000 000' },
              { label: 'Mukofotlar', value: '+62 200 000', tone: 'success' },
              { label: 'Jarima va avanslar', value: '-10 000 000', tone: 'danger' },
            ],
          }}
        />
        <StatCard
          label="To'lab berilgan"
          value={formatUZS(320500000)}
          icon={CheckCircle2}
          iconTone="success"
          delta="71%"
          deltaTone="success"
          hint="Umumiy hajmi to'landi"
          detail={{
            description:
              "48 xodimdan 34 tasiga to'liq ish haqi to'lab berildi — umumiy hajmning 71% i.",
            breakdown: [
              { label: "To'liq to'langan", value: '34 nafar', tone: 'success' },
              { label: 'Qisman to\'langan', value: '0 nafar' },
            ],
          }}
        />
        <StatCard
          label="Qolgan summa"
          value={formatUZS(129700000)}
          icon={Clock}
          iconTone="warning"
          hint="14 nafar xodimga to'lanmagan"
          detail={{
            description:
              "14 nafar xodimga hali 129 700 000 UZS to'lanmagan. Ularning bir qismi kechikkan holatda.",
            breakdown: [
              { label: 'Kutilmoqda', value: '9 nafar' },
              { label: 'Kechikkan', value: '5 nafar', tone: 'danger' },
            ],
          }}
        />
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
          <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-1">
            {tabs.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                  tab === t ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700',
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <Button variant="outline" icon={SlidersHorizontal} data-toast="Filtrlar qo'llandi ✓">
            Filtrlar
          </Button>
        </div>

        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[980px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">Xodim</th>
                <th className="px-6 py-3">Lavozim</th>
                <th className="px-6 py-3">Asosiy oylik</th>
                <th className="px-6 py-3">Mukofot</th>
                <th className="px-6 py-3">Jarima</th>
                <th className="px-6 py-3">Avans</th>
                <th className="px-6 py-3">Hisoblangan</th>
                <th className="px-6 py-3">Holat</th>
                <th className="px-6 py-3 text-right">Amal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/60">
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-3">
                      <Avatar name={r.name} />
                      <div>
                        <p className="font-medium text-slate-800">{r.name}</p>
                        <p className="text-xs text-slate-400">ID: {r.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3.5 text-slate-600">{r.position}</td>
                  <td className="px-6 py-3.5 text-slate-700">{formatMoney(r.base)}</td>
                  <td className="px-6 py-3.5 font-medium text-emerald-600">
                    {r.bonus ? `+${formatMoney(r.bonus)}` : '—'}
                  </td>
                  <td className="px-6 py-3.5 font-medium text-red-500">
                    {r.penalty ? `-${formatMoney(r.penalty)}` : '—'}
                  </td>
                  <td className="px-6 py-3.5 font-medium text-slate-500">
                    {r.advance ? `-${formatMoney(r.advance)}` : '—'}
                  </td>
                  <td className="px-6 py-3.5 font-bold text-slate-900">{formatMoney(r.total)}</td>
                  <td className="px-6 py-3.5">
                    <Badge tone={statusTone[r.status]} dot>
                      {r.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    {r.status === "To'langan" ? (
                      <span className="text-xs text-slate-400">Bajarildi</span>
                    ) : (
                      <Button
                        variant="outline"
                        className="px-3 py-1.5 text-xs"
                        data-sound="success"
                        onClick={() => markPaid(r.id, r.name)}
                      >
                        To'lash
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-6 pb-4">
          <Pagination label="Jami 48 tadan 1-10 tasi ko'rsatilmoqda" pages={3} current={1} />
        </div>
      </Card>
    </div>
  )
}
