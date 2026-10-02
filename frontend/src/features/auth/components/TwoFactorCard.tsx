/**
 * Ikki bosqichli tasdiqlash — oʻz hisobi uchun (PLAN 5.4, ADR-24).
 *
 * Mijoz tomonida 2FA **ixtiyoriy**, va bu ataylab: bogʻchada smenada
 * ishlaydigan xodimda shaxsiy smartfon boʻlmasligi mumkin, majburiy
 * kod esa jamoani bitta umumiy telefonga oʻtishga majburlardi — yaʼni
 * audit izi "kim kirdi" degan savolga javob bermay qolardi. Ega uchun
 * esa u aynan kerak: uning hisobi butun bogʻchaning moliyasini
 * koʻradi.
 *
 * Yoqish **ikki qadam**: sir olinadi, keyin ilovadagi haqiqiy kod
 * bilan tasdiqlanadi. Bir qadamda qilinsa, QR'ni koʻrib ilovaga
 * qoʻshmagan odam keyingi kirishda oʻz hisobidan chiqib qolardi.
 *
 * QR rasm YOʻQ: uning uchun kutubxona kerak boʻlardi, holbuki
 * `otpauth://` havolasi telefonda bosilganda Authenticator ilovasini
 * oʻzi ochadi, kompyuterda esa kalitni qoʻlda kiritish mumkin.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Check, Copy, ShieldCheck, ShieldOff } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { PasswordInput } from '@/components/ui/PasswordInput'
import { authApi } from '@/features/auth/api'
import { ApiError } from '@/lib/api/types'
import { t } from '@/lib/i18n'

const FIELD =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

/** Zaxira kodlari — faqat bir marta koʻrinadi, shuning uchun nusxalash tugmasi bilan. */
function BackupCodes({ codes }: { codes: string[] }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
      <p className="text-xs font-medium text-amber-900">
        {t('Zaxira kodlari — har biri BIR MARTA ishlaydi. Ularni hozir saqlab oling.')}
      </p>
      <ul className="mt-2 grid grid-cols-2 gap-1 font-mono text-sm text-amber-950">
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => {
          void navigator.clipboard.writeText(codes.join('\n')).then(() => {
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
          })
        }}
        className="mt-3 flex items-center gap-1.5 text-xs font-medium text-amber-900 hover:text-amber-700"
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        {copied ? t('Nusxalandi') : t('Hammasini nusxalash')}
      </button>
      <p className="mt-2 text-xs text-amber-800">
        {/* Kodlar sir bilan BIR JOYDA saqlanmasligi kerak: aks holda
            ikkinchi omil omil boʻlmay qoladi. */}
        {t('Telefoningizdan boshqa joyda saqlang — qogʻozda yoki parol menejerida.')}
      </p>
    </div>
  )
}

export function TwoFactorCard() {
  const { user, refreshUser } = useAuth()
  const enabled = user?.two_factor ?? false

  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [codes, setCodes] = useState<string[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const start = useMutation({
    mutationFn: () => authApi.twoFactorSetup(),
    onSuccess: (result) => {
      setError(null)
      setCodes(null)
      setSetup(result)
    },
    onError: fail,
  })

  const confirm = useMutation({
    mutationFn: () => authApi.twoFactorConfirm(code.trim()),
    onSuccess: async (result) => {
      setError(null)
      setSetup(null)
      setCode('')
      setCodes(result.backup_codes)
      await refreshUser()
    },
    onError: fail,
  })

  const renew = useMutation({
    mutationFn: () => authApi.twoFactorBackupCodes(password),
    onSuccess: async (result) => {
      setError(null)
      setPassword('')
      setCodes(result.backup_codes)
      await refreshUser()
    },
    onError: fail,
  })

  const turnOff = useMutation({
    mutationFn: () => authApi.twoFactorDisable(password),
    onSuccess: async () => {
      setError(null)
      setPassword('')
      setCodes(null)
      setSetup(null)
      await refreshUser()
    },
    onError: fail,
  })

  const busy = start.isPending || confirm.isPending || renew.isPending || turnOff.isPending

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2">
        {enabled ? (
          <ShieldCheck className="h-4 w-4 text-nihol-600" />
        ) : (
          <ShieldOff className="h-4 w-4 text-slate-400" />
        )}
        <h2 className="text-sm font-semibold text-slate-900">{t('Ikki bosqichli tasdiqlash')}</h2>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {enabled
          ? t('Yoqilgan. Kirishda Authenticator kodi soʻraladi.')
          : t('Parol oʻgʻirlansa ham hisob yopiq qoladi: kirishda telefondagi kod soʻraladi.')}
      </p>

      {error && (
        <div role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {codes && (
        <div className="mt-3">
          <BackupCodes codes={codes} />
        </div>
      )}

      {!enabled && !setup && (
        <button
          type="button"
          disabled={busy}
          onClick={() => start.mutate()}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          {start.isPending ? t('Tayyorlanmoqda…') : t('Yoqish')}
        </button>
      )}

      {!enabled && setup && (
        <form
          className="mt-4 space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            confirm.mutate()
          }}
        >
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-600">
            <li>{t('Authenticator ilovasini oching (Google Authenticator, Authy, 1Password).')}</li>
            <li>
              {t('Quyidagi kalitni qoʻshing yoki havolani telefonda bosing:')}
              <div className="mt-1.5 rounded-lg bg-slate-50 p-2">
                <code className="block break-all font-mono text-xs text-slate-800">
                  {setup.secret}
                </code>
                <a
                  href={setup.otpauth_uri}
                  className="mt-1 inline-block text-xs text-nihol-700 underline-offset-2 hover:underline"
                >
                  {t('Ilovada ochish')}
                </a>
              </div>
            </li>
            <li>{t('Ilovada chiqqan olti xonali kodni kiriting:')}</li>
          </ol>

          <div>
            <label htmlFor="totp-confirm" className="mb-1 block text-sm font-medium text-slate-700">
              {t('Authenticator kodi')}
            </label>
            <input
              id="totp-confirm"
              required
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              className={FIELD}
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || code.trim().length < 6}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {confirm.isPending ? t('Tekshirilmoqda…') : t('Tasdiqlash')}
            </button>
            <button
              type="button"
              onClick={() => {
                setSetup(null)
                setCode('')
                setError(null)
              }}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
          </div>
        </form>
      )}

      {enabled && (
        <div className="mt-4 space-y-3">
          <p className="text-xs text-slate-500">
            {t('Qolgan zaxira kodlari: {count}', { count: user?.backup_codes_left ?? 0 })}
          </p>

          <div>
            <label
              htmlFor="totp-password"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              {t('Parolingiz')}
            </label>
            <PasswordInput
              id="totp-password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {/* Parol soʻraladi: oʻgʻirlangan sessiya (XSS, ochiq
                qolgan noutbuk) himoyani olib tashlamasligi kerak. */}
            <p className="mt-1 text-xs text-slate-400">
              {t('Oʻchirish va kodlarni yangilash uchun parol kerak.')}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || !password}
              onClick={() => renew.mutate()}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
            >
              {renew.isPending ? t('Saqlanmoqda…') : t('Yangi zaxira kodlari')}
            </button>
            <button
              type="button"
              disabled={busy || !password}
              onClick={() => turnOff.mutate()}
              className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:opacity-50"
            >
              {turnOff.isPending ? t('Oʻchirilmoqda…') : t('Oʻchirish')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
