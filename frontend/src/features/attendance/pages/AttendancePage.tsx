import { useMemo, useState } from 'react'
import {
  Users,
  UserCheck,
  UserX,
  FileText,
  CalendarDays,
  Send,
  Printer,
  ArrowUpDown,
  Check,
  X,
  Plus,
} from 'lucide-react'
import { Card, Badge, Avatar, Button, StatCard } from '@/components/ui/primitives'
import { SearchInput } from '@/components/ui/form'
import { cn } from '@/lib/utils'

type Status = 'present' | 'absent' | 'excused' | 'unset'

interface Pupil {
  name: string
  id: string
  age: number
  status: Status
}

const groups = ['Kamalak', 'Yulduzcha', 'Bilimdon', "Qaldirg'och"]

const initialPupils: Pupil[] = [
  { name: 'Abdurashidov Jasurbek', id: '00452', age: 5, status: 'present' },
  { name: 'Olimova Madina', id: '00481', age: 4, status: 'absent' },
  { name: 'Xabibullayev Sardor', id: '00429', age: 5, status: 'unset' },
  { name: 'Karimova Shaxlo', id: '00502', age: 4, status: 'present' },
  { name: 'Rahimov Doniyor', id: '00511', age: 5, status: 'present' },
  { name: 'Nazarova Sevara', id: '00523', age: 4, status: 'excused' },
  { name: 'Toshpulatov Elyor', id: '00530', age: 5, status: 'present' },
  { name: 'Yoqubova Malika', id: '00544', age: 4, status: 'present' },
  { name: 'Sobirov Islom', id: '00551', age: 5, status: 'absent' },
  { name: 'Aliyeva Nafisa', id: '00560', age: 4, status: 'present' },
  { name: 'Umarov Diyorbek', id: '00572', age: 5, status: 'present' },
  { name: 'Xolova Zulfiya', id: '00588', age: 4, status: 'present' },
]

export default function AttendancePage() {
  const [activeGroup, setActiveGroup] = useState('Kamalak')
  const [pupils, setPupils] = useState<Pupil[]>(initialPupils)
  const [search, setSearch] = useState('')

  const setStatus = (id: string, status: Status) =>
    setPupils((prev) => prev.map((p) => (p.id === id ? { ...p, status } : p)))

  const shown = useMemo(() => {
    const q = search.trim().toLowerCase()
    return pupils.filter((p) => !q || p.name.toLowerCase().includes(q) || p.id.includes(q))
  }, [pupils, search])

  const stats = useMemo(() => {
    const total = pupils.length
    const present = pupils.filter((p) => p.status === 'present').length
    const absent = pupils.filter((p) => p.status === 'absent').length
    const excused = pupils.filter((p) => p.status === 'excused').length
    const pct = (n: number) => (total ? Math.round((n / total) * 100) : 0)
    return { total, present, absent, excused, pct }
  }, [pupils])

  return (
    <div className="space-y-6">
      {/* Header row: group tabs + date, and report banner */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-1.5">
              {groups.map((g) => (
                <button
                  key={g}
                  onClick={() => setActiveGroup(g)}
                  className={cn(
                    'rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors',
                    activeGroup === g
                      ? 'bg-brand-600 text-white'
                      : 'text-slate-500 hover:bg-slate-100',
                  )}
                >
                  {g}
                </button>
              ))}
            </div>
            <button className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
              <CalendarDays className="w-4 h-4 text-slate-400" />
              24 May, 2024
            </button>
          </div>
        </Card>

        <Card className="flex items-center justify-between gap-3 bg-slate-900 p-4 text-white">
          <div>
            <p className="text-sm font-semibold">Bugun uchun hisobot</p>
            <p className="mt-0.5 text-xs text-slate-300">
              Davomat kiritilgach tasdiqlab, ota-onalarga yuboring.
            </p>
          </div>
          <Button
            variant="primary"
            icon={Send}
            className="shrink-0"
            data-sound="success"
            data-toast="Davomat tasdiqlandi va ota-onalarga yuborildi ✓"
          >
            Tasdiqlash
          </Button>
        </Card>
      </div>

      {/* KPI */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Jami bolalar"
          value={`${stats.total} nafar`}
          icon={Users}
          iconTone="info"
          detail={{
            description: `${activeGroup} guruhida jami ${stats.total} nafar bola ro'yxatga olingan.`,
            breakdown: [
              { label: 'Kelganlar', value: `${stats.present} nafar`, tone: 'success' },
              { label: 'Kelmaganlar', value: `${stats.absent} nafar`, tone: 'danger' },
              { label: 'Sababli', value: `${stats.excused} nafar` },
            ],
          }}
        />
        <StatCard
          label="Kelganlar"
          value={`${stats.present}`}
          icon={UserCheck}
          iconTone="success"
          delta={`${stats.pct(stats.present)}%`}
          deltaTone="success"
          detail={{
            description: `Bugun ${activeGroup} guruhidan ${stats.present} nafar bola keldi (${stats.pct(stats.present)}%). Har bir bolani "Keldi / Sababli / Kelmagan" tugmalari orqali belgilashingiz mumkin.`,
          }}
        />
        <StatCard
          label="Kelmaganlar"
          value={`${stats.absent}`}
          icon={UserX}
          iconTone="danger"
          delta={`${stats.pct(stats.absent)}%`}
          deltaTone="danger"
          detail={{
            description: `Bugun ${stats.absent} nafar bola sababsiz kelmadi (${stats.pct(stats.absent)}%). Ota-onalarga avtomatik xabar yuborish uchun "Tasdiqlash" tugmasidan foydalaning.`,
          }}
        />
        <StatCard
          label="Sababli"
          value={`${stats.excused}`}
          icon={FileText}
          iconTone="warning"
          hint="Hujjatli"
          detail={{
            description: `${stats.excused} nafar bola sababli (hujjatli) kelmadi — masalan kasallik yoki oilaviy sabab bilan.`,
          }}
        />
      </div>

      {/* List */}
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">{activeGroup} guruhi ro'yxati</h2>
            <p className="text-sm text-slate-500">Bugungi sana: Juma, 24-May</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SearchInput value={search} onChange={setSearch} placeholder="Bola ismi..." className="w-48" />
            <Button variant="outline" icon={ArrowUpDown} data-toast="Ro'yxat saralandi">
              Saralash
            </Button>
            <Button variant="outline" icon={Printer} data-toast="Chop etishga yuborildi">
              Chop etish
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">Bolaning ismi va ID</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3 text-right">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {shown.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/60">
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-3">
                      <Avatar name={p.name} />
                      <div>
                        <p className="font-medium text-slate-800">{p.name}</p>
                        <p className="text-xs text-slate-400">
                          ID: {p.id} · {p.age} yosh
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3.5">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-6 py-3.5">
                    <div className="flex items-center justify-end gap-2">
                      <ToggleButton
                        active={p.status === 'present'}
                        tone="present"
                        icon={Check}
                        label="Keldi"
                        onClick={() => setStatus(p.id, 'present')}
                      />
                      <ToggleButton
                        active={p.status === 'excused'}
                        tone="excused"
                        icon={FileText}
                        label="Sababli"
                        onClick={() => setStatus(p.id, 'excused')}
                      />
                      <ToggleButton
                        active={p.status === 'absent'}
                        tone="absent"
                        icon={X}
                        label="Kelmagan"
                        onClick={() => setStatus(p.id, 'absent')}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between p-4">
          <p className="text-sm text-slate-400">
            Jami {stats.total} boladan {shown.length} tasi ko'rsatilmoqda
          </p>
          <button
            data-toast="Yangi bola qo'shish (demo)"
            data-toast-tone="info"
            className="grid place-items-center w-10 h-10 rounded-full bg-brand-600 text-white shadow-lg shadow-brand-600/30 transition-all hover:bg-brand-700 active:scale-90"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </Card>
    </div>
  )
}

/* ------- helpers ------- */

function StatusBadge({ status }: { status: Status }) {
  if (status === 'present') return <Badge tone="success" dot>Keldi</Badge>
  if (status === 'absent') return <Badge tone="danger" dot>Kelmagan</Badge>
  if (status === 'excused') return <Badge tone="warning" dot>Sababli</Badge>
  return <Badge tone="neutral" dot>Belgilanmagan</Badge>
}

interface ToggleButtonProps {
  active: boolean
  tone: 'present' | 'absent' | 'excused'
  icon: typeof Check
  label: string
  onClick: () => void
}

function ToggleButton({ active, tone, icon: Icon, label, onClick }: ToggleButtonProps) {
  const activeCls = {
    present: 'bg-emerald-600 text-white border-emerald-600',
    absent: 'bg-red-600 text-white border-red-600',
    excused: 'bg-amber-500 text-white border-amber-500',
  }[tone]
  const idleCls = {
    present: 'text-emerald-700 border-slate-200 hover:border-emerald-300 hover:bg-emerald-50',
    absent: 'text-red-600 border-slate-200 hover:border-red-300 hover:bg-red-50',
    excused: 'text-amber-600 border-slate-200 hover:border-amber-300 hover:bg-amber-50',
  }[tone]
  const sound = tone === 'present' ? 'success' : tone === 'absent' ? 'error' : 'toggle'
  return (
    <button
      onClick={onClick}
      data-sound={sound}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all duration-150 active:scale-95',
        active ? activeCls : idleCls,
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
    </button>
  )
}
