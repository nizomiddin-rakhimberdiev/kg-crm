import { useMemo, useState } from 'react'
import {
  Package,
  AlertTriangle,
  History,
  Truck,
  ShoppingCart,
  Download,
  Printer,
  Trash2,
  Zap,
  QrCode,
  PackagePlus,
} from 'lucide-react'
import {
  Card,
  PageHeader,
  StatCard,
  Button,
  Badge,
  Select,
  Switch,
  ProgressBar,
  Pagination,
  type BadgeTone,
} from '@/components/ui/primitives'
import { Modal } from '@/components/ui/Modal'
import { Field, TextInput, SearchInput } from '@/components/ui/form'
import { useToast } from '@/app/providers/ToastProvider'

interface Product {
  name: string
  category: string
  level: number
  max: number
  unit: string
  supplier: string
}

const categoryTone: Record<string, BadgeTone> = {
  'Oziq-ovqat': 'amber',
  "O'quv qurollari": 'sky',
  'Tozalik mahsulotlari': 'teal',
}
const categories = ['Oziq-ovqat', "O'quv qurollari", 'Tozalik mahsulotlari']
const units = ['dona', 'quti', 'litr', 'kg', "to'plam"]

const seed: Product[] = [
  { name: 'Tuxum (Sara)', category: 'Oziq-ovqat', level: 12, max: 100, unit: 'dona', supplier: 'Global Agro MCHJ' },
  { name: "Oq qog'oz A4", category: "O'quv qurollari", level: 85, max: 100, unit: 'quti', supplier: 'Kantsler Service' },
  { name: 'Suyuq sovun 5L', category: 'Tozalik mahsulotlari', level: 45, max: 100, unit: 'litr', supplier: 'EcoClean Uz' },
  { name: "Sariyog'", category: 'Oziq-ovqat', level: 92, max: 100, unit: 'kg', supplier: 'Sutli Dunyo' },
  { name: 'Guruch', category: 'Oziq-ovqat', level: 60, max: 100, unit: 'kg', supplier: 'Global Agro MCHJ' },
  { name: "Qalam to'plami", category: "O'quv qurollari", level: 18, max: 100, unit: "to'plam", supplier: 'Kantsler Service' },
]

function stockMeta(level: number): { tone: 'success' | 'warning' | 'danger'; label: string } {
  if (level < 20) return { tone: 'danger', label: 'Kam qolgan' }
  if (level < 60) return { tone: 'warning', label: 'Yarim zaxira' }
  return { tone: 'success', label: "Me'yorida" }
}

const emptyForm = { name: '', category: 'Oziq-ovqat', unit: 'kg', level: '80', supplier: '' }

export default function InventoryPage() {
  const { toast } = useToast()
  const [products, setProducts] = useState<Product[]>(seed)
  const [search, setSearch] = useState('')
  const [catFilter, setCatFilter] = useState('all')
  const [onlyLow, setOnlyLow] = useState(false)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return products.filter((p) => {
      const matchSearch = !q || p.name.toLowerCase().includes(q) || p.supplier.toLowerCase().includes(q)
      const matchCat = catFilter === 'all' || p.category === catFilter
      const matchLow = !onlyLow || p.level < 20
      return matchSearch && matchCat && matchLow
    })
  }, [products, search, catFilter, onlyLow])

  const lowCount = products.filter((p) => p.level < 20).length

  const addProduct = () => {
    if (!form.name.trim()) {
      toast('Mahsulot nomini kiriting', 'error')
      return
    }
    const item: Product = {
      name: form.name.trim(),
      category: form.category,
      level: Math.min(100, Math.max(0, Number(form.level) || 0)),
      max: 100,
      unit: form.unit,
      supplier: form.supplier.trim() || '—',
    }
    setProducts((p) => [item, ...p])
    toast(`${item.name} omborga qo'shildi ✓`, 'success')
    setForm(emptyForm)
    setOpen(false)
  }

  const removeProduct = (name: string) => {
    setProducts((p) => p.filter((x) => x.name !== name))
    toast(`${name} o'chirildi`, 'info')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ombor Boshqaruvi"
        subtitle="Barcha xom-ashyo va o'quv qurollari zaxirasini nazorat qilish"
      >
        <Button variant="outline" icon={Truck} data-toast="Yetkazib berish qo'shildi (demo)" data-toast-tone="info">
          Yetkazib berishni qo'shish
        </Button>
        <Button icon={ShoppingCart} data-sound="success" onClick={() => setOpen(true)}>
          Xarid qilish
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Jami mahsulotlar"
          value={`${products.length} tur`}
          icon={Package}
          iconTone="info"
          delta="+12%"
          deltaTone="success"
          detail={{
            description: `Omborda hozirda ${products.length} xil mahsulot ro'yxatga olingan.`,
            breakdown: categories.map((c) => ({
              label: c,
              value: `${products.filter((p) => p.category === c).length} xil`,
            })),
          }}
        />
        <StatCard
          label="Kam qolganlar"
          value={`${lowCount} turi`}
          icon={AlertTriangle}
          iconTone="danger"
          delta="Diqqat"
          deltaTone="danger"
          detail={{
            description: `${lowCount} turdagi mahsulot 20% dan kam qoldi — xarid qilish tavsiya etiladi.`,
            breakdown: products
              .filter((p) => p.level < 20)
              .map((p) => ({ label: p.name, value: `${p.level}%`, tone: 'danger' as const })),
          }}
        />
        <StatCard
          label="Oxirgi xarid"
          value="4,200,000 so'm"
          icon={History}
          iconTone="violet"
          hint="2 soat oldin"
          detail={{ description: "Eng so'nggi xarid 'Global Agro MCHJ' dan amalga oshirildi." }}
        />
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
          <div className="flex flex-1 flex-wrap items-center gap-3">
            <SearchInput value={search} onChange={setSearch} placeholder="Mahsulot yoki yetkazib beruvchi..." className="min-w-[220px] flex-1" />
            <Select
              className="w-52"
              value={catFilter}
              onChange={setCatFilter}
              options={[
                { label: 'Barcha kategoriyalar', value: 'all' },
                ...categories.map((c) => ({ label: c, value: c })),
              ]}
            />
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <Switch checked={onlyLow} onChange={setOnlyLow} />
              Faqat kam qolganlar
            </label>
          </div>
          <div className="flex items-center gap-1">
            <button
              data-toast="Ombor ro'yxati yuklab olindi"
              className="grid place-items-center w-9 h-9 rounded-lg border border-slate-200 text-slate-400 transition-all hover:bg-slate-50 active:scale-90"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              data-toast="Chop etishga yuborildi"
              className="grid place-items-center w-9 h-9 rounded-lg border border-slate-200 text-slate-400 transition-all hover:bg-slate-50 active:scale-90"
            >
              <Printer className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[940px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-6 py-3">Mahsulot</th>
                <th className="px-6 py-3">Kategoriya</th>
                <th className="px-6 py-3 w-64">Zaxira holati</th>
                <th className="px-6 py-3">O'lchov</th>
                <th className="px-6 py-3">Yetkazib beruvchi</th>
                <th className="px-6 py-3 text-right">Amal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((p) => {
                const meta = stockMeta(p.level)
                return (
                  <tr key={p.name} className="hover:bg-slate-50/60">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="grid place-items-center w-9 h-9 rounded-lg bg-slate-100 text-slate-500">
                          <Package className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">{p.name}</p>
                          <p
                            className={
                              'text-xs ' +
                              (meta.tone === 'danger'
                                ? 'text-red-500'
                                : meta.tone === 'warning'
                                  ? 'text-amber-600'
                                  : 'text-emerald-600')
                            }
                          >
                            {meta.label}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge tone={categoryTone[p.category] ?? 'neutral'}>{p.category}</Badge>
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <ProgressBar value={p.level} tone={meta.tone} className="flex-1" />
                        <span className="w-16 shrink-0 text-right text-xs font-medium text-slate-500">
                          {p.level} / {p.max}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-slate-600">{p.unit}</td>
                    <td className="px-6 py-3.5 text-slate-600">{p.supplier}</td>
                    <td className="px-6 py-3.5 text-right">
                      <button
                        onClick={() => removeProduct(p.name)}
                        title="O'chirish"
                        className="grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-all hover:bg-red-50 hover:text-red-500 active:scale-90 ml-auto"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-14 text-center text-sm text-slate-400">
                    Mahsulot topilmadi.
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

      {/* Bottom cards */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="flex items-center justify-between gap-4 bg-slate-900 p-6 text-white">
          <div>
            <div className="flex items-center gap-2 text-brand-200">
              <Zap className="w-4 h-4" />
              <span className="text-sm font-semibold">Avtomatlashtirilgan xarid</span>
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Tizim kam qolgan mahsulotlarni avtomatik aniqlaydi va yetkazib beruvchilarga so'rov yuboradi.
            </p>
            <Button variant="primary" className="mt-4" data-toast="Avtomatik xarid sozlandi (demo)" data-toast-tone="info">
              Sozlash
            </Button>
          </div>
          <div className="hidden shrink-0 sm:block">
            <div className="grid place-items-center w-16 h-16 rounded-2xl bg-white/10">
              <Zap className="w-8 h-8 text-brand-300" />
            </div>
          </div>
        </Card>

        <Card className="flex items-center justify-between gap-4 p-6">
          <div>
            <div className="flex items-center gap-2 text-slate-900">
              <QrCode className="w-4 h-4 text-brand-600" />
              <span className="text-sm font-semibold">QR-Kod orqali qabul</span>
            </div>
            <p className="mt-2 text-sm text-slate-500">
              Yetkazib berilgan tovarlarni tezroq qabul qilish uchun mobil ilovadan foydalaning.
            </p>
            <button
              data-toast="Mobil ilova havolasi yuborildi"
              className="mt-4 text-sm font-semibold text-brand-600 hover:underline active:scale-95"
            >
              Ilovani yuklash ↗
            </button>
          </div>
          <div className="grid shrink-0 place-items-center w-16 h-16 rounded-2xl bg-brand-50 text-brand-600">
            <QrCode className="w-8 h-8" />
          </div>
        </Card>
      </div>

      {/* Add product modal */}
      <Modal open={open} onClose={() => setOpen(false)}>
        <div className="p-6">
          <div className="flex items-center gap-3 pr-8">
            <div className="grid place-items-center w-11 h-11 rounded-xl bg-brand-50 text-brand-600">
              <PackagePlus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Yangi mahsulot / xarid</h2>
              <p className="text-sm text-slate-500">Omborga mahsulot qo'shing.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Field label="Mahsulot nomi" className="sm:col-span-2">
              <TextInput value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Masalan: Kartoshka" />
            </Field>
            <Field label="Kategoriya">
              <Select value={form.category} onChange={(v) => set('category', v)} options={categories.map((c) => ({ label: c, value: c }))} />
            </Field>
            <Field label="O'lchov birligi">
              <Select value={form.unit} onChange={(v) => set('unit', v)} options={units.map((u) => ({ label: u, value: u }))} />
            </Field>
            <Field label="Zaxira darajasi (%)">
              <TextInput value={form.level} onChange={(e) => set('level', e.target.value.replace(/\D/g, ''))} inputMode="numeric" />
            </Field>
            <Field label="Yetkazib beruvchi">
              <TextInput value={form.supplier} onChange={(e) => set('supplier', e.target.value)} placeholder="Global Agro MCHJ" />
            </Field>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Bekor qilish
            </Button>
            <Button icon={ShoppingCart} data-sound="success" onClick={addProduct}>
              Qo'shish
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
