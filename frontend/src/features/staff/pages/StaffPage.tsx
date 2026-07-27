import { useMemo, useState } from 'react'
import { Plus, Users, UserCheck, Plane, Phone, Trash2, UserPlus } from 'lucide-react'
import {
  Card,
  PageHeader,
  StatCard,
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
import { formatMoney } from '@/lib/utils'

type Status = 'Faol' | "Ta'tilda" | 'Ishdan ketgan'

const statusTone: Record<Status, BadgeTone> = {
  Faol: 'success',
  "Ta'tilda": 'warning',
  'Ishdan ketgan': 'neutral',
}

interface Staff {
  name: string
  id: string
  position: string
  department: string
  phone: string
  hired: string
  salary: number
  status: Status
}

const departments = ['Tarbiya', "Ta'lim", 'Oshxona', 'Xizmat', 'Tibbiyot']

const seed: Staff[] = [
  { name: 'Ziloa Karimbekova', id: '#0342', position: 'Katta tarbiyachi', department: 'Tarbiya', phone: '+998 90 111 22 33', hired: '01.09.2021', salary: 6500000, status: 'Faol' },
  { name: 'Jasur Mirzayev', id: '#0392', position: 'Ingliz tili ustozi', department: "Ta'lim", phone: '+998 91 222 33 44', hired: '15.08.2022', salary: 8000000, status: 'Faol' },
  { name: 'Nigora Axmedova', id: '#0356', position: 'Logoped', department: "Ta'lim", phone: '+998 93 333 44 55', hired: '10.01.2022', salary: 7200000, status: "Ta'tilda" },
  { name: 'Mastura opa', id: '#0301', position: 'Bosh oshpaz', department: 'Oshxona', phone: '+998 94 444 55 66', hired: '05.03.2020', salary: 4500000, status: 'Faol' },
  { name: 'Dilnoza Rasulova', id: '#0377', position: 'Tarbiyachi yordamchisi', department: 'Tarbiya', phone: '+998 97 555 66 77', hired: '20.09.2023', salary: 3800000, status: 'Faol' },
  { name: 'Sardor Aliyev', id: '#0388', position: 'Xavfsizlik xodimi', department: 'Xizmat', phone: '+998 99 666 77 88', hired: '12.06.2023', salary: 4000000, status: 'Faol' },
  { name: 'Gulnora Yusupova', id: '#0333', position: 'Hamshira', department: 'Tibbiyot', phone: '+998 90 777 88 99', hired: '03.11.2021', salary: 5000000, status: "Ta'tilda" },
]

const emptyForm = { name: '', position: '', department: 'Tarbiya', phone: '', salary: '4000000' }

export default function StaffPage() {
  const { toast } = useToast()
  const [staff, setStaff] = useState<Staff[]>(seed)
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('all')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return staff.filter((s) => {
      const matchSearch =
        !q || s.name.toLowerCase().includes(q) || s.position.toLowerCase().includes(q)
      const matchDept = deptFilter === 'all' || s.department === deptFilter
      return matchSearch && matchDept
    })
  }, [staff, search, deptFilter])

  const active = staff.filter((s) => s.status === 'Faol').length
  const onLeave = staff.filter((s) => s.status === "Ta'tilda").length

  const addStaff = () => {
    if (!form.name.trim() || !form.position.trim()) {
      toast('Ism va lavozimni kiriting', 'error')
      return
    }
    const item: Staff = {
      name: form.name.trim(),
      id: `#0${400 + staff.length}`,
      position: form.position.trim(),
      department: form.department,
      phone: form.phone.trim() || '—',
      hired: new Date().toLocaleDateString('ru-RU'),
      salary: Number(form.salary) || 0,
      status: 'Faol',
    }
    setStaff((s) => [item, ...s])
    toast(`${item.name} xodimlar ro'yxatiga qo'shildi ✓`, 'success')
    setForm(emptyForm)
    setOpen(false)
  }

  const removeStaff = (id: string, name: string) => {
    setStaff((s) => s.filter((x) => x.id !== id))
    toast(`${name} o'chirildi`, 'info')
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Xodimlar" subtitle="Bog'cha xodimlari va ularning ma'lumotlari">
        <Button icon={Plus} data-sound="success" onClick={() => setOpen(true)}>
          Yangi xodim
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Jami xodimlar" value={`${staff.length} nafar`} icon={Users} iconTone="info" />
        <StatCard label="Faol" value={`${active} nafar`} icon={UserCheck} iconTone="success" />
        <StatCard label="Ta'tilda" value={`${onLeave} nafar`} icon={Plane} iconTone="warning" />
      </div>

      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Qidiruv</p>
            <SearchInput value={search} onChange={setSearch} placeholder="Ism yoki lavozim..." />
          </div>
          <Select
            label="Bo'lim"
            className="sm:w-56"
            value={deptFilter}
            onChange={setDeptFilter}
            options={[
              { label: 'Barcha bo\'limlar', value: 'all' },
              ...departments.map((d) => ({ label: d, value: d })),
            ]}
          />
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[960px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">Xodim</th>
                <th className="px-6 py-3">Lavozim</th>
                <th className="px-6 py-3">Telefon</th>
                <th className="px-6 py-3">Ishga kirgan</th>
                <th className="px-6 py-3">Oylik</th>
                <th className="px-6 py-3">Holat</th>
                <th className="px-6 py-3 text-right">Amal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50/60">
                  <td className="px-6 py-3.5">
                    <div className="flex items-center gap-3">
                      <Avatar name={s.name} />
                      <div>
                        <p className="font-medium text-slate-800">{s.name}</p>
                        <p className="text-xs text-slate-400">ID: {s.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3.5">
                    <p className="text-slate-700">{s.position}</p>
                    <p className="text-xs text-slate-400">{s.department}</p>
                  </td>
                  <td className="px-6 py-3.5">
                    <span className="inline-flex items-center gap-1.5 text-slate-600">
                      <Phone className="w-3.5 h-3.5 text-slate-400" />
                      {s.phone}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-slate-500">{s.hired}</td>
                  <td className="px-6 py-3.5 text-slate-700">{formatMoney(s.salary)} UZS</td>
                  <td className="px-6 py-3.5">
                    <Badge tone={statusTone[s.status]} dot>
                      {s.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    <button
                      onClick={() => removeStaff(s.id, s.name)}
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
                  <td colSpan={7} className="px-6 py-14 text-center text-sm text-slate-400">
                    Xodim topilmadi.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-6 pb-4">
          <Pagination label={`Jami ${filtered.length} ta ko'rsatilmoqda`} pages={1} current={1} />
        </div>
      </Card>

      <Modal open={open} onClose={() => setOpen(false)}>
        <div className="p-6">
          <div className="flex items-center gap-3 pr-8">
            <div className="grid place-items-center w-11 h-11 rounded-xl bg-brand-50 text-brand-600">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Yangi xodim qo'shish</h2>
              <p className="text-sm text-slate-500">Xodim ma'lumotlarini kiriting.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Field label="F.I.O" className="sm:col-span-2">
              <TextInput value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Karimbekova Ziloa" />
            </Field>
            <Field label="Lavozim">
              <TextInput value={form.position} onChange={(e) => set('position', e.target.value)} placeholder="Tarbiyachi" />
            </Field>
            <Field label="Bo'lim">
              <Select
                value={form.department}
                onChange={(v) => set('department', v)}
                options={departments.map((d) => ({ label: d, value: d }))}
              />
            </Field>
            <Field label="Telefon">
              <TextInput value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+998 90 111 22 33" />
            </Field>
            <Field label="Oylik (UZS)">
              <TextInput
                value={form.salary}
                onChange={(e) => set('salary', e.target.value.replace(/\D/g, ''))}
                inputMode="numeric"
              />
            </Field>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Bekor qilish
            </Button>
            <Button icon={Plus} data-sound="success" onClick={addStaff}>
              Qo'shish
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
