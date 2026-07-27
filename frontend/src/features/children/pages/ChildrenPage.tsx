import { useMemo, useState } from 'react'
import { Plus, RotateCcw, Trash2, UserPlus } from 'lucide-react'
import {
  Card,
  PageHeader,
  Button,
  Badge,
  Avatar,
  Select,
  Pagination,
  type BadgeTone,
} from '@/components/ui/primitives'
import { Modal } from '@/components/ui/Modal'
import { Field, TextInput, SearchInput } from '@/components/ui/form'
import { useToast } from '@/app/providers/ToastProvider'
import { formatMoney, formatSigned, cn } from '@/lib/utils'

type Status = 'Faol' | 'Qarzdor' | 'Muzlatilgan'

interface Child {
  name: string
  id: string
  group: string
  parent: string
  phone: string
  fee: number
  balance: number
  date: string
  status: Status
}

const groupTone: Record<string, BadgeTone> = {
  Kamalak: 'rose',
  Yulduzcha: 'amber',
  Bilimdon: 'sky',
  "Qaldirg'och": 'violet',
}

const statusTone: Record<Status, BadgeTone> = {
  Faol: 'success',
  Qarzdor: 'danger',
  Muzlatilgan: 'neutral',
}

const seed: Child[] = [
  { name: 'Abdurahmonov Aziz', id: '#00241', group: 'Kamalak', parent: 'Abdurahmonov F.', phone: '+998 90 123 45 67', fee: 1800000, balance: 250000, date: '12.08.2023', status: 'Faol' },
  { name: 'Karimov Laylo', id: '#00242', group: 'Yulduzcha', parent: 'Karimov Sh.', phone: '+998 91 456 78 90', fee: 1500000, balance: -450000, date: '05.09.2023', status: 'Qarzdor' },
  { name: 'Tohirova Madina', id: '#00243', group: 'Bilimdon', parent: 'Tohirov M.', phone: '+998 94 987 65 43', fee: 2000000, balance: 0, date: '10.10.2023', status: 'Muzlatilgan' },
  { name: 'Yusupov Bekzod', id: '#00244', group: 'Kamalak', parent: 'Yusupov A.', phone: '+998 93 111 22 33', fee: 1800000, balance: 120000, date: '14.10.2023', status: 'Faol' },
  { name: 'Salimova Nilufar', id: '#00245', group: "Qaldirg'och", parent: 'Salimov D.', phone: '+998 97 555 44 33', fee: 1600000, balance: -300000, date: '20.10.2023', status: 'Qarzdor' },
  { name: 'Rasulov Jasur', id: '#00246', group: 'Bilimdon', parent: 'Rasulova M.', phone: '+998 90 777 88 99', fee: 2000000, balance: 500000, date: '22.10.2023', status: 'Faol' },
  { name: 'Ahmedova Zarina', id: '#00247', group: 'Yulduzcha', parent: 'Ahmedov B.', phone: '+998 99 222 33 44', fee: 1500000, balance: 0, date: '25.10.2023', status: 'Faol' },
  { name: "G'aniev Sardor", id: '#00248', group: 'Kamalak', parent: "G'aniev T.", phone: '+998 91 888 77 66', fee: 1800000, balance: -900000, date: '01.11.2023', status: 'Qarzdor' },
]

const groupOptions = ['Kamalak', 'Yulduzcha', 'Bilimdon', "Qaldirg'och"]

const emptyForm = {
  first: '',
  last: '',
  group: 'Kamalak',
  fee: '1500000',
  parent: '',
  phone: '',
}

export default function ChildrenPage() {
  const { toast } = useToast()
  const [children, setChildren] = useState<Child[]>(seed)
  const [search, setSearch] = useState('')
  const [groupFilter, setGroupFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return children.filter((c) => {
      const matchSearch =
        !q || c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q)
      const matchGroup = groupFilter === 'all' || c.group === groupFilter
      const matchStatus = statusFilter === 'all' || c.status === statusFilter
      return matchSearch && matchGroup && matchStatus
    })
  }, [children, search, groupFilter, statusFilter])

  const resetFilters = () => {
    setSearch('')
    setGroupFilter('all')
    setStatusFilter('all')
  }

  const addChild = () => {
    if (!form.first.trim() || !form.last.trim()) {
      toast('Ism va familiyani kiriting', 'error')
      return
    }
    const nextNum = 249 + children.length
    const child: Child = {
      name: `${form.last.trim()} ${form.first.trim()}`,
      id: `#00${nextNum}`,
      group: form.group,
      parent: form.parent.trim() || '—',
      phone: form.phone.trim() || '—',
      fee: Number(form.fee) || 0,
      balance: 0,
      date: new Date().toLocaleDateString('ru-RU'),
      status: 'Faol',
    }
    setChildren((c) => [child, ...c])
    toast(`${child.name} ro'yxatga qo'shildi ✓`, 'success')
    setForm(emptyForm)
    setOpen(false)
  }

  const removeChild = (id: string, name: string) => {
    setChildren((c) => c.filter((x) => x.id !== id))
    toast(`${name} ro'yxatdan o'chirildi`, 'info')
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Bolalar Ro'yxati" subtitle="Barcha bolalar va ularning holati">
        <Badge tone="info" className="px-3 py-1.5 text-sm">
          Jami: {children.length} nafar
        </Badge>
        <Button icon={Plus} data-sound="success" onClick={() => setOpen(true)}>
          Yangi bola
        </Button>
      </PageHeader>

      {/* Filters — live */}
      <Card className="p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <div className="flex-1">
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Qidiruv
            </p>
            <SearchInput value={search} onChange={setSearch} placeholder="Ism yoki ID bo'yicha..." />
          </div>
          <Select
            label="Guruh"
            className="lg:w-52"
            value={groupFilter}
            onChange={setGroupFilter}
            options={[
              { label: 'Barcha guruhlar', value: 'all' },
              ...groupOptions.map((g) => ({ label: g, value: g })),
            ]}
          />
          <Select
            label="Holati"
            className="lg:w-52"
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { label: 'Barcha holatlar', value: 'all' },
              { label: 'Faol', value: 'Faol' },
              { label: 'Qarzdor', value: 'Qarzdor' },
              { label: 'Muzlatilgan', value: 'Muzlatilgan' },
            ]}
          />
          <Button variant="outline" icon={RotateCcw} onClick={resetFilters}>
            Tozalash
          </Button>
        </div>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[920px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">Bola / ID</th>
                <th className="px-6 py-3">Guruh</th>
                <th className="px-6 py-3">Ota-ona</th>
                <th className="px-6 py-3">Oylik to'lov</th>
                <th className="px-6 py-3">Balans</th>
                <th className="px-6 py-3">Sana</th>
                <th className="px-6 py-3">Holat</th>
                <th className="px-6 py-3 text-right">Amal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/60">
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-3">
                      <Avatar name={c.name} />
                      <div>
                        <p className="font-medium text-slate-800">{c.name}</p>
                        <p className="text-xs text-slate-400">ID: {c.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3.5">
                    <Badge tone={groupTone[c.group] ?? 'neutral'}>{c.group}</Badge>
                  </td>
                  <td className="px-6 py-3.5">
                    <p className="text-slate-700">{c.parent}</p>
                    <p className="text-xs text-slate-400">{c.phone}</p>
                  </td>
                  <td className="px-6 py-3.5 text-slate-700">{formatMoney(c.fee)} UZS</td>
                  <td className="px-6 py-3.5">
                    <span
                      className={cn(
                        'font-semibold',
                        c.balance > 0 && 'text-emerald-600',
                        c.balance < 0 && 'text-red-500',
                        c.balance === 0 && 'text-slate-400',
                      )}
                    >
                      {c.balance === 0 ? '0.00' : formatSigned(c.balance)}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-slate-500">{c.date}</td>
                  <td className="px-6 py-3.5">
                    <Badge tone={statusTone[c.status]} dot>
                      {c.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    <button
                      onClick={() => removeChild(c.id, c.name)}
                      title="O'chirish"
                      className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-red-50 hover:text-red-500 active:scale-90 ml-auto"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-14 text-center text-sm text-slate-400">
                    Hech qanday bola topilmadi. Qidiruv yoki filtrni o'zgartiring.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-6 pb-4">
          <Pagination
            label={`${filtered.length} tadan ${filtered.length} tasi ko'rsatilmoqda`}
            pages={Math.max(1, Math.ceil(filtered.length / 10))}
            current={1}
          />
        </div>
      </Card>

      {/* Add child modal */}
      <Modal open={open} onClose={() => setOpen(false)}>
        <div className="p-6">
          <div className="flex items-center gap-3 pr-8">
            <div className="grid place-items-center w-11 h-11 rounded-xl bg-brand-50 text-brand-600">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Yangi bola qo'shish</h2>
              <p className="text-sm text-slate-500">Ma'lumotlarni to'ldiring va saqlang.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Field label="Ism">
              <TextInput value={form.first} onChange={(e) => set('first', e.target.value)} placeholder="Aziz" />
            </Field>
            <Field label="Familiya">
              <TextInput value={form.last} onChange={(e) => set('last', e.target.value)} placeholder="Abdurahmonov" />
            </Field>
            <Field label="Guruh">
              <Select
                value={form.group}
                onChange={(v) => set('group', v)}
                options={groupOptions.map((g) => ({ label: g, value: g }))}
              />
            </Field>
            <Field label="Oylik to'lov (UZS)">
              <TextInput
                value={form.fee}
                onChange={(e) => set('fee', e.target.value.replace(/\D/g, ''))}
                inputMode="numeric"
              />
            </Field>
            <Field label="Ota-ona (F.I.O)">
              <TextInput value={form.parent} onChange={(e) => set('parent', e.target.value)} placeholder="Abdurahmonov F." />
            </Field>
            <Field label="Telefon">
              <TextInput value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+998 90 123 45 67" />
            </Field>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Bekor qilish
            </Button>
            <Button icon={Plus} data-sound="success" onClick={addChild}>
              Qo'shish
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
