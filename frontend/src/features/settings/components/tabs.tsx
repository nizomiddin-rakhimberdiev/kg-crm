import { useState } from 'react'
import {
  Camera,
  Check,
  CreditCard,
  Banknote,
  Building2,
  Smartphone,
  Monitor,
  Volume2,
  Bell,
  Mail,
  ShieldCheck,
  KeyRound,
  Laptop,
  LogOut,
  Wallet,
} from 'lucide-react'
import { Button, Select, Switch, Avatar, Badge } from '@/components/ui/primitives'
import { useToast } from '@/app/providers/ToastProvider'
import { useSound } from '@/app/providers/SoundProvider'
import { cn } from '@/lib/utils'
import { SectionTitle, Field, TextInput, TextArea, SettingRow, Segmented } from './controls'

/* ============================================================ 1. Muassasa */

export function OrgTab() {
  const [form, setForm] = useState({
    name: 'Premium Bog\'cha',
    stir: '123 456 789',
    phone: '+998 71 200 00 00',
    address: 'Toshkent sh., Mirzo Ulug\'bek tumani, 12-uy',
    currency: 'UZS',
    tz: 'Asia/Tashkent',
  })
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="max-w-2xl">
      <SectionTitle
        title="Muassasa Ma'lumotlari"
        description="Bog'cha haqidagi asosiy ma'lumotlarni bu yerda boshqaring."
      />

      <div className="flex items-center gap-4">
        <div className="grid place-items-center w-20 h-20 rounded-2xl border-2 border-dashed border-slate-200 text-slate-400">
          <Camera className="w-6 h-6" />
        </div>
        <div>
          <button
            data-toast="Logotip yuklandi (demo)"
            data-toast-tone="info"
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition-all hover:bg-slate-50 active:scale-95"
          >
            Logotip yuklash
          </button>
          <p className="mt-2 text-xs text-slate-400">PNG, JPG yoki SVG. Maksimal 2MB.</p>
        </div>
      </div>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        <Field label="Muassasa nomi">
          <TextInput value={form.name} onChange={(e) => set('name', e.target.value)} />
        </Field>
        <Field label="STIR (INN)">
          <TextInput value={form.stir} onChange={(e) => set('stir', e.target.value)} />
        </Field>
        <Field label="Telefon">
          <TextInput value={form.phone} onChange={(e) => set('phone', e.target.value)} />
        </Field>
        <Field label="Valyuta">
          <Select
            value={form.currency}
            onChange={(v) => set('currency', v)}
            options={[
              { label: "UZS — O'zbek so'mi", value: 'UZS' },
              { label: 'USD — AQSH dollari', value: 'USD' },
            ]}
          />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Manzil">
            <TextArea rows={3} value={form.address} onChange={(e) => set('address', e.target.value)} />
          </Field>
        </div>
        <Field label="Vaqt mintaqasi">
          <Select
            value={form.tz}
            onChange={(v) => set('tz', v)}
            options={[
              { label: 'Asia/Tashkent (GMT+5)', value: 'Asia/Tashkent' },
              { label: 'Asia/Samarkand (GMT+5)', value: 'Asia/Samarkand' },
            ]}
          />
        </Field>
      </div>
    </div>
  )
}

/* ====================================================== 2. Rollar / Huquqlar */

const roles = [
  { code: 'super_admin', name: 'Super Admin', desc: 'Barcha imkoniyatlar', locked: true },
  { code: 'director', name: 'Direktor', desc: "Filialning to'liq boshqaruvi" },
  { code: 'manager', name: 'Menejer', desc: 'Kundalik operatsiyalar' },
  { code: 'cashier', name: 'Kassir', desc: "To'lovlar va qarzdorlik" },
  { code: 'attendance', name: 'Davomat menejeri', desc: 'Kunlik davomat' },
]
const rbacModules = [
  'Bolalar',
  "To'lovlar",
  'Qarzdorlar',
  'Davomat',
  'Xodimlar',
  'Oylik',
  'Ombor',
  'Chiqimlar',
  'Hisobotlar',
  'Sozlamalar',
]
const rbacActions = ["Ko'rish", "Qo'shish", 'Tahrirlash', "O'chirish"]

function buildPerms(): Record<string, boolean> {
  const p: Record<string, boolean> = {}
  roles.forEach((r) =>
    rbacModules.forEach((_, mi) =>
      rbacActions.forEach((_, ai) => {
        p[`${r.code}|${mi}|${ai}`] = r.code === 'super_admin' ? true : ai === 0
      }),
    ),
  )
  return p
}

export function RolesTab() {
  const [active, setActive] = useState('director')
  const [perms, setPerms] = useState<Record<string, boolean>>(buildPerms)
  const current = roles.find((r) => r.code === active)!

  const toggle = (mi: number, ai: number) => {
    if (current.locked) return
    const k = `${active}|${mi}|${ai}`
    setPerms((p) => ({ ...p, [k]: !p[k] }))
  }

  return (
    <div>
      <SectionTitle
        title="Rollar va Huquqlar"
        description="Har bir rol uchun modullarga kirish huquqlarini boshqaring."
      />

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        {/* Roles list */}
        <div className="space-y-2">
          {roles.map((r) => (
            <button
              key={r.code}
              data-sound="toggle"
              onClick={() => setActive(r.code)}
              className={cn(
                'w-full rounded-xl border p-3 text-left transition-colors',
                active === r.code
                  ? 'border-brand-300 bg-brand-50'
                  : 'border-slate-200 hover:bg-slate-50',
              )}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800">{r.name}</p>
                {r.locked && <Badge tone="neutral">Tizim</Badge>}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{r.desc}</p>
            </button>
          ))}
          <button
            data-toast="Yangi rol yaratish (demo)"
            data-toast-tone="info"
            className="w-full rounded-xl border border-dashed border-slate-300 p-3 text-sm font-medium text-slate-500 transition-colors hover:bg-slate-50"
          >
            + Yangi rol
          </button>
        </div>

        {/* Permission matrix */}
        <div className="overflow-x-auto scrollbar-thin rounded-xl border border-slate-200">
          <table className="w-full min-w-[520px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Modul</th>
                {rbacActions.map((a) => (
                  <th key={a} className="px-2 py-3 text-center">
                    {a}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {rbacModules.map((m, mi) => (
                <tr key={m} className="hover:bg-slate-50/60">
                  <td className="px-4 py-2.5 font-medium text-slate-700">{m}</td>
                  {rbacActions.map((_, ai) => (
                    <td key={ai} className="px-2 py-2.5 text-center">
                      <div className="flex justify-center">
                        <Checkbox
                          checked={perms[`${active}|${mi}|${ai}`]}
                          disabled={current.locked}
                          onClick={() => toggle(mi, ai)}
                        />
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {current.locked && (
        <p className="mt-3 text-xs text-slate-400">
          Super Admin roli tizim roli — huquqlari o'zgartirilmaydi.
        </p>
      )}
    </div>
  )
}

function Checkbox({
  checked,
  disabled,
  onClick,
}: {
  checked: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      data-sound="toggle"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'grid place-items-center w-5 h-5 rounded border transition-all active:scale-90',
        checked ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 bg-white',
        disabled && 'opacity-60',
      )}
    >
      {checked && <Check className="w-3.5 h-3.5" />}
    </button>
  )
}

/* ====================================================== 3. To'lov Tizimlari */

export function PaymentsTab() {
  const [gateways, setGateways] = useState([
    { key: 'payme', name: 'Payme', desc: "Payme to'lov tizimi", icon: CreditCard, enabled: true, keys: true },
    { key: 'click', name: 'Click', desc: "Click to'lov tizimi", icon: CreditCard, enabled: true, keys: true },
    { key: 'uzum', name: 'Uzum Bank', desc: "Uzum to'lov tizimi", icon: CreditCard, enabled: false, keys: true },
    { key: 'cash', name: 'Naqd pul', desc: 'Kassada naqd qabul qilish', icon: Banknote, enabled: true, keys: false },
    { key: 'transfer', name: "Bank o'tkazmasi", desc: 'Bank hisobiga o\'tkazma', icon: Building2, enabled: true, keys: false },
  ])
  const [testMode, setTestMode] = useState(true)
  const setEnabled = (key: string, val: boolean) =>
    setGateways((g) => g.map((x) => (x.key === key ? { ...x, enabled: val } : x)))

  return (
    <div className="max-w-2xl">
      <SectionTitle
        title="To'lov Tizimlari"
        description="Qaysi to'lov usullari yoqilishini va integratsiya kalitlarini boshqaring."
      />

      <div className="mb-5 flex items-center justify-between rounded-xl border border-amber-100 bg-amber-50/60 px-4 py-3">
        <div>
          <p className="text-sm font-medium text-amber-800">Test (sandbox) rejimi</p>
          <p className="text-xs text-amber-600">Yoqilganda haqiqiy to'lovlar amalga oshmaydi.</p>
        </div>
        <Switch checked={testMode} onChange={setTestMode} />
      </div>

      <div className="space-y-3">
        {gateways.map((g) => (
          <div key={g.key} className="rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="grid place-items-center w-10 h-10 rounded-lg bg-slate-100 text-slate-600">
                  <g.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{g.name}</p>
                  <p className="text-xs text-slate-500">{g.desc}</p>
                </div>
              </div>
              <Switch checked={g.enabled} onChange={(v) => setEnabled(g.key, v)} />
            </div>
            {g.enabled && g.keys && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Field label="Merchant ID">
                  <TextInput placeholder="Masalan: 6789..." />
                </Field>
                <Field label="API kalit">
                  <TextInput type="password" placeholder="••••••••••••" />
                </Field>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ============================================================= 4. SMS */

export function SmsTab() {
  const [provider, setProvider] = useState('eskiz')
  const [events, setEvents] = useState({
    payment: true,
    debt: true,
    absence: false,
    birthday: true,
  })
  const setEvent = (k: keyof typeof events, v: boolean) => setEvents((e) => ({ ...e, [k]: v }))

  return (
    <div className="max-w-2xl">
      <SectionTitle
        title="SMS Xabarnomalar"
        description="SMS provayder va qaysi hodisalarda avtomatik SMS yuborilishini sozlang."
      />

      <div className="mb-6 flex items-center justify-between rounded-xl bg-slate-900 px-5 py-4 text-white">
        <div>
          <p className="text-xs uppercase tracking-wide text-brand-200">SMS balans</p>
          <p className="text-2xl font-bold">1,240 ta</p>
        </div>
        <Button variant="primary" data-toast="Balansni to'ldirish (demo)" data-toast-tone="info">
          To'ldirish
        </Button>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Provayder">
          <Select
            value={provider}
            onChange={setProvider}
            options={[
              { label: 'Eskiz.uz', value: 'eskiz' },
              { label: 'Play Mobile', value: 'playmobile' },
            ]}
          />
        </Field>
        <Field label="Jo'natuvchi nomi">
          <TextInput defaultValue="PREMIUM" />
        </Field>
        <div className="sm:col-span-2">
          <Field label="API token" hint="Tokeningiz maxfiy saqlanadi.">
            <TextInput type="password" placeholder="••••••••••••••••" />
          </Field>
        </div>
      </div>

      <div className="mt-6">
        <p className="mb-1 text-sm font-semibold text-slate-800">Avtomatik SMS hodisalari</p>
        <div className="rounded-xl border border-slate-200 px-4">
          <SettingRow title="To'lov qabul qilinganda" description="Ota-onaga chek va rahmat xabari">
            <Switch checked={events.payment} onChange={(v) => setEvent('payment', v)} />
          </SettingRow>
          <SettingRow title="Qarzdorlik eslatmasi" description="Har hafta qarzdorlarga eslatma">
            <Switch checked={events.debt} onChange={(v) => setEvent('debt', v)} />
          </SettingRow>
          <SettingRow title="Bola kelmaganda" description="Davomatda 'kelmagan' belgilanganda">
            <Switch checked={events.absence} onChange={(v) => setEvent('absence', v)} />
          </SettingRow>
          <SettingRow title="Tug'ilgan kun tabrigi" description="Bolaning tug'ilgan kunida">
            <Switch checked={events.birthday} onChange={(v) => setEvent('birthday', v)} />
          </SettingRow>
        </div>
      </div>
    </div>
  )
}

/* =============================================== 5. Ko'rinish / Bildirishnoma */

export function AppearanceTab() {
  const { muted, toggle } = useSound()
  const [lang, setLang] = useState<'uz' | 'ru' | 'en'>('uz')
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light')
  const [dateFmt, setDateFmt] = useState('dmy')
  const [push, setPush] = useState(true)
  const [emailDigest, setEmailDigest] = useState(false)

  return (
    <div className="max-w-2xl">
      <SectionTitle
        title="Ko'rinish va Bildirishnomalar"
        description="Interfeys tili, mavzusi va bildirishnoma sozlamalari."
      />

      <div className="space-y-6">
        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">Interfeys tili</p>
          <Segmented
            value={lang}
            onChange={setLang}
            options={[
              { label: "O'zbek", value: 'uz' },
              { label: 'Русский', value: 'ru' },
              { label: 'English', value: 'en' },
            ]}
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">Mavzu</p>
          <div className="flex flex-wrap gap-3">
            {[
              { key: 'light', label: 'Yorug\'', icon: Monitor },
              { key: 'dark', label: 'Tungi', icon: Smartphone },
              { key: 'system', label: 'Tizim', icon: Laptop },
            ].map((t) => (
              <button
                key={t.key}
                data-sound="toggle"
                onClick={() => setTheme(t.key as typeof theme)}
                className={cn(
                  'flex items-center gap-2 rounded-xl border-2 px-4 py-2.5 text-sm font-medium transition-colors',
                  theme === t.key
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-500 hover:border-slate-300',
                )}
              >
                <t.icon className="w-4 h-4" />
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <Field label="Sana formati" className="max-w-xs">
          <Select
            value={dateFmt}
            onChange={setDateFmt}
            options={[
              { label: 'KK.OO.YYYY (12.08.2026)', value: 'dmy' },
              { label: 'YYYY-OO-KK (2026-08-12)', value: 'ymd' },
            ]}
          />
        </Field>

        <div>
          <p className="mb-1 text-sm font-semibold text-slate-800">Bildirishnomalar</p>
          <div className="rounded-xl border border-slate-200 px-4">
            <SettingRow title="Interfeys ovozlari" description="Tugma bosilganda yumshoq ovoz">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-slate-400" />
                <Switch checked={!muted} onChange={() => toggle()} />
              </div>
            </SettingRow>
            <SettingRow title="Push bildirishnomalar" description="Brauzerda yangi hodisalar">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-slate-400" />
                <Switch checked={push} onChange={setPush} />
              </div>
            </SettingRow>
            <SettingRow title="Email hisobot" description="Har kuni kunlik hisobot emailga">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-slate-400" />
                <Switch checked={emailDigest} onChange={setEmailDigest} />
              </div>
            </SettingRow>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ============================================================ 6. Xavfsizlik */

export function SecurityTab() {
  const { toast } = useToast()
  const [cur, setCur] = useState('')
  const [nw, setNw] = useState('')
  const [conf, setConf] = useState('')
  const [twofa, setTwofa] = useState(false)
  const [autoLogout, setAutoLogout] = useState('30')

  const changePassword = () => {
    if (!cur || !nw || !conf) return toast("Barcha maydonlarni to'ldiring", 'error')
    if (nw.length < 6) return toast("Yangi parol kamida 6 belgidan iborat bo'lsin", 'error')
    if (nw !== conf) return toast('Parollar mos kelmadi', 'error')
    toast('Parol muvaffaqiyatli yangilandi ✓', 'success')
    setCur('')
    setNw('')
    setConf('')
  }

  const sessions = [
    { device: 'Windows · Chrome', loc: 'Toshkent', time: 'Hozir', current: true },
    { device: 'iPhone · Safari', loc: 'Toshkent', time: '2 soat oldin', current: false },
    { device: 'Windows · Edge', loc: 'Samarqand', time: 'Kecha, 18:40', current: false },
  ]

  return (
    <div className="max-w-2xl">
      <SectionTitle title="Xavfsizlik" description="Parol, ikki bosqichli himoya va faol seanslar." />

      {/* Password */}
      <div className="rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-brand-600" />
          <h3 className="text-sm font-bold text-slate-800">Parolni o'zgartirish</h3>
        </div>
        <div className="mt-4 grid gap-4">
          <Field label="Joriy parol">
            <TextInput type="password" value={cur} onChange={(e) => setCur(e.target.value)} placeholder="••••••••" />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Yangi parol">
              <TextInput type="password" value={nw} onChange={(e) => setNw(e.target.value)} placeholder="Kamida 6 belgi" />
            </Field>
            <Field label="Yangi parolni tasdiqlang">
              <TextInput type="password" value={conf} onChange={(e) => setConf(e.target.value)} placeholder="••••••••" />
            </Field>
          </div>
          <div>
            <Button onClick={changePassword}>Parolni yangilash</Button>
          </div>
        </div>
      </div>

      {/* 2FA */}
      <div className="mt-5 flex items-center justify-between rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-3">
          <div className="grid place-items-center w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Ikki bosqichli himoya (2FA)</p>
            <p className="text-xs text-slate-500">Kirishда SMS orqali tasdiqlash kodi</p>
          </div>
        </div>
        <Switch checked={twofa} onChange={setTwofa} />
      </div>

      {/* Auto logout */}
      <div className="mt-5">
        <Field label="Avtomatik chiqish (harakatsizlik)" className="max-w-xs">
          <Select
            value={autoLogout}
            onChange={setAutoLogout}
            options={[
              { label: '15 daqiqa', value: '15' },
              { label: '30 daqiqa', value: '30' },
              { label: '1 soat', value: '60' },
              { label: 'Hech qachon', value: '0' },
            ]}
          />
        </Field>
      </div>

      {/* Sessions */}
      <div className="mt-6">
        <p className="mb-2 text-sm font-semibold text-slate-800">Faol seanslar</p>
        <div className="space-y-2">
          {sessions.map((s) => (
            <div
              key={s.device}
              className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <div className="grid place-items-center w-9 h-9 rounded-lg bg-slate-100 text-slate-500">
                  <Laptop className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {s.device}
                    {s.current && (
                      <Badge tone="success" className="ml-2">
                        Joriy
                      </Badge>
                    )}
                  </p>
                  <p className="text-xs text-slate-500">
                    {s.loc} · {s.time}
                  </p>
                </div>
              </div>
              {!s.current && (
                <button
                  data-toast="Seans tugatildi"
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-red-600 transition-colors hover:bg-red-50 active:scale-95"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Chiqish
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ============================================================ 7. Profil */

export function ProfileTab() {
  const [form, setForm] = useState({
    name: 'Admin Foydalanuvchi',
    email: 'admin@premium.uz',
    phone: '+998 90 123 45 67',
    position: 'Super Administrator',
  })
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="max-w-2xl">
      <SectionTitle title="Profil Sozlamalari" description="Shaxsiy ma'lumotlaringiz va hisob sozlamalari." />

      <div className="flex items-center gap-4">
        <Avatar name={form.name} size="lg" />
        <button
          data-toast="Rasm yuklandi (demo)"
          data-toast-tone="info"
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition-all hover:bg-slate-50 active:scale-95"
        >
          Rasmni o'zgartirish
        </button>
      </div>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        <Field label="To'liq ism">
          <TextInput value={form.name} onChange={(e) => set('name', e.target.value)} />
        </Field>
        <Field label="Lavozim">
          <TextInput value={form.position} disabled className="bg-slate-50 text-slate-400" />
        </Field>
        <Field label="Email">
          <TextInput type="email" value={form.email} onChange={(e) => set('email', e.target.value)} />
        </Field>
        <Field label="Telefon">
          <TextInput value={form.phone} onChange={(e) => set('phone', e.target.value)} />
        </Field>
      </div>

      <div className="mt-6 flex items-center gap-3 rounded-xl bg-brand-50 px-4 py-3">
        <Wallet className="w-5 h-5 text-brand-600" />
        <p className="text-sm text-brand-800">
          Hisobingiz <span className="font-semibold">Super Administrator</span> huquqlariga ega.
        </p>
      </div>
    </div>
  )
}
