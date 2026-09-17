/**
 * Yangi bog'cha ochish — ochiq ro'yxatdan o'tishning o'rnini bosadi.
 *
 * Muvaffaqiyatdan keyin forma YOPILMAYDI, natija ekranini ko'rsatadi.
 * Sabab amaliy: parolni siz belgilaysiz va uni mijozga topshirishingiz
 * kerak. Modal darhol yopilsa, parol ko'z oldidan g'oyib bo'lardi va uni
 * qayta tiklashning yagona yo'li — parolni almashtirish bo'lardi.
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Plus } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { ApiError } from '@/lib/api/types'
import { platform, type NewOrgResult } from '../api'

const FIELD =
  'w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-brand-500'

const EMPTY = {
  organization_name: '',
  contact_email: '',
  contact_phone: '',
  full_name: '',
  password: '',
  slug: '',
  branch_name: '',
}

/** Backenddagi `slugify` ning yengil ko'rinishi — faqat oldindan ko'rsatish uchun. */
const previewSlug = (value: string): string =>
  value
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 50)

function CopyRow({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2">
      <div className="min-w-0">
        <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
        <p className="truncate font-mono text-sm text-slate-100">{value}</p>
      </div>
      <button
        type="button"
        onClick={() => {
          void navigator.clipboard.writeText(value).then(() => {
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
          })
        }}
        className="flex-none rounded-md p-2 text-slate-400 hover:bg-slate-700 hover:text-slate-100"
        aria-label={`${label} — nusxalash`}
      >
        {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
      </button>
    </div>
  )
}

export function NewOrganizationDialog() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<NewOrgResult | null>(null)

  const set = (key: keyof typeof EMPTY) => (event: { target: { value: string } }) =>
    setForm((previous) => ({ ...previous, [key]: event.target.value }))

  const create = useMutation({
    mutationFn: () =>
      platform.createOrganization({
        ...form,
        slug: form.slug || undefined,
        branch_name: form.branch_name || undefined,
        contact_phone: form.contact_phone || undefined,
      }),
    onSuccess: (result) => {
      setError(null)
      setCreated(result)
      void queryClient.invalidateQueries({ queryKey: ['platform'] })
    },
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : 'Tashkilot ochilmadi.'),
  })

  const close = () => {
    setOpen(false)
    setForm(EMPTY)
    setCreated(null)
    setError(null)
  }

  const slugPreview = previewSlug(form.slug || form.organization_name)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-500"
      >
        <Plus className="h-4 w-4" />
        Yangi bog'cha
      </button>

      <Modal open={open} onClose={close} className="max-w-lg">
        {created ? (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">{created.name} ochildi</h2>
              <p className="mt-1 text-sm text-slate-400">
                Quyidagilarni mijozga topshiring. Parol boshqa ko'rsatilmaydi — uni hozir
                nusxalab oling.
              </p>
            </div>

            <div className="space-y-2">
              <CopyRow label="Kirish havolasi" value={created.login_url} />
              <CopyRow label="Login (email)" value={created.owner_email} />
              <CopyRow label="Parol" value={form.password} />
            </div>

            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              15 kunlik sinov <strong>shu paytdan</strong> boshlandi.
            </p>

            <button
              type="button"
              onClick={close}
              className="w-full rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white"
            >
              Yopish
            </button>
          </div>
        ) : (
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              create.mutate()
            }}
          >
            <div>
              <h2 className="text-lg font-semibold">Yangi bog'cha ochish</h2>
              <p className="mt-1 text-sm text-slate-400">
                Mijoz o'zini o'zi ro'yxatdan o'tkaza olmaydi — akkauntni siz ochasiz.
              </p>
            </div>

            <div className="space-y-3">
              <label className="block">
                <span className="mb-1 block text-xs text-slate-400">Bog'cha nomi</span>
                <input
                  required
                  value={form.organization_name}
                  onChange={set('organization_name')}
                  className={FIELD}
                  placeholder="Quyosh bog'chasi"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs text-slate-400">
                  Kirish havolasi (URL) — ixtiyoriy, bo'sh qoldirilsa nomdan olinadi
                </span>
                <div className="flex items-center overflow-hidden rounded-lg border border-slate-700 bg-slate-800 focus-within:border-brand-500">
                  <span className="pl-3 font-mono text-sm text-slate-500">/t/</span>
                  <input
                    value={form.slug}
                    onChange={set('slug')}
                    className="w-full bg-transparent px-1 py-2 text-sm outline-none"
                    placeholder="quyosh"
                  />
                </div>
                <span className="mt-1 block text-xs text-slate-500">
                  Bu — bog'cha jamoasi kiradigan sahifaning veb-havolasi, bog'chaning jismoniy
                  manzili emas. Masalan: <span className="font-mono">/t/{slugPreview || 'quyosh'}</span>
                </span>
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-400">Egasining ismi</span>
                  <input
                    required
                    value={form.full_name}
                    onChange={set('full_name')}
                    className={FIELD}
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-400">Telefon</span>
                  <input
                    value={form.contact_phone}
                    onChange={set('contact_phone')}
                    className={FIELD}
                    placeholder="+998901234567"
                  />
                </label>
              </div>

              <label className="block">
                <span className="mb-1 block text-xs text-slate-400">Email (login)</span>
                <input
                  required
                  type="email"
                  value={form.contact_email}
                  onChange={set('contact_email')}
                  className={FIELD}
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs text-slate-400">Boshlang'ich parol</span>
                <input
                  required
                  value={form.password}
                  onChange={set('password')}
                  className={FIELD}
                  placeholder="Kamida 8 belgi"
                />
              </label>
            </div>

            {error && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </p>
            )}

            <div className="flex gap-2">
              <button
                type="button"
                onClick={close}
                className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                disabled={create.isPending}
                className="flex-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50"
              >
                {create.isPending ? 'Ochilmoqda…' : 'Ochish'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </>
  )
}
