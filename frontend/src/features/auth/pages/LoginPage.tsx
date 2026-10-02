/**
 * Kirish sahifasi — ikki bosqichli (docs/04 §5).
 *
 * Email tashkilot ichida unikal, shuning uchun bitta email bir nechta
 * bog'chaga mos kelishi mumkin. Bunday holda backend pending token va
 * tashkilotlar ro'yxatini qaytaradi va foydalanuvchi tanlaydi.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogIn, MailCheck } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { OrgMark } from '@/components/brand/OrgMark'
import { PasswordInput } from '@/components/ui/PasswordInput'
import { useAuth } from '@/app/providers/AuthProvider'
import { authApi } from '@/features/auth/api'
import { ApiError, isPendingChoice, type OrganizationSummary } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { LanguageSwitch } from '@/components/layout/LanguageSwitch'
import { t } from '@/lib/i18n'

type Stage =
  | { kind: 'credentials' }
  | { kind: 'choose-organization'; pendingToken: string; organizations: OrganizationSummary[] }
  | { kind: 'forgot' }

export default function LoginPage() {
  const navigate = useNavigate()
  const { applySession } = useAuth()

  const [stage, setStage] = useState<Stage>({ kind: 'credentials' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const handleError = (err: unknown) => {
    setError(
      err instanceof ApiError ? err.message : t('Kutilmagan xatolik. Qaytadan urinib koʻring.'),
    )
  }

  const submitCredentials = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result = await authApi.login(email, password)
      if (isPendingChoice(result)) {
        setStage({
          kind: 'choose-organization',
          pendingToken: result.pending_token,
          organizations: result.organizations,
        })
      } else {
        applySession(result)
        navigate('/home', { replace: true })
      }
    } catch (err) {
      handleError(err)
    } finally {
      setBusy(false)
    }
  }

  const chooseOrganization = async (organizationId: string) => {
    if (stage.kind !== 'choose-organization') return
    setError(null)
    setBusy(true)
    try {
      const session = await authApi.selectOrganization(stage.pendingToken, organizationId)
      applySession(session)
      navigate('/home', { replace: true })
    } catch (err) {
      handleError(err)
      // Pending token 5 daqiqada tugaydi — muddati o'tsa boshidan boshlaymiz.
      setStage({ kind: 'credentials' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          {/* Mijozga ko'rinadigan yuza — ommaviy brend. Ichki nomlar
              (repo, Docker, DB rollari) ataylab `kg-crm` bo'lib qoladi.
              Sarlavha matni yo'q: logotipning o'zida yozuv bor va uni
              takrorlash brendbuk qoidasiga zid. */}
          <Logo height={40} />
          <p className="mt-3 text-sm text-tosh-500">{t('Bogʻcha boshqaruv tizimi')}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          {error && (
            <div role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {stage.kind === 'forgot' ? (
            <ForgotPasswordForm onBack={() => setStage({ kind: 'credentials' })} />
          ) : stage.kind === 'credentials' ? (
            <form onSubmit={submitCredentials} className="space-y-4">
              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
                  {t('Email')}
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
                  {t('Parol')}
                </label>
                <PasswordInput
                  id="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setStage({ kind: 'forgot' })}
                  className="mt-1.5 text-xs text-tosh-500 underline-offset-2 hover:text-nihol-700 hover:underline"
                >
                  {t('Parolni unutdingizmi?')}
                </button>
              </div>

              <button
                type="submit"
                disabled={busy}
                className={cn(
                  'flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition',
                  busy ? 'opacity-60' : 'hover:bg-brand-700',
                )}
              >
                <LogIn className="h-4 w-4" />
                {busy ? t('Tekshirilmoqda…') : t('Kirish')}
              </button>
            </form>
          ) : (
            <div className="space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">{t('Tashkilotni tanlang')}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {t('Bu email bir nechta bogʻchada roʻyxatdan oʻtgan.')}
                </p>
              </div>

              {stage.organizations.map((org) => (
                <button
                  key={org.id}
                  type="button"
                  disabled={busy}
                  onClick={() => void chooseOrganization(org.id)}
                  className="flex w-full items-center gap-3 rounded-lg border border-slate-200 px-3 py-3 text-left transition hover:border-brand-300 hover:bg-brand-50 disabled:opacity-60"
                >
                  {/* Bogʻchaning belgisi (PLAN 4.6): ikki bogʻchada
                      ishlaydigan xodim ularni nomidan ham tezroq
                      logotipi bilan ajratadi. */}
                  <OrgMark name={org.name} logoUrl={org.logo_url} size={28} />
                  <span className="text-sm font-medium text-slate-800">{org.name}</span>
                </button>
              ))}

              <button
                type="button"
                onClick={() => setStage({ kind: 'credentials' })}
                className="w-full pt-1 text-center text-sm text-slate-500 hover:text-slate-700"
              >
                {t('Orqaga')}
              </button>
            </div>
          )}
        </div>

        {/* Akkauntni faqat vendor ochadi (ADR-10) — "sinovni boshlang"
            havolasi endi hech qayerga olib bormasdi. O'rniga aloqa yo'li:
            bu sahifaga adashib tushgan odam nima qilishini bilsin. */}
        <p className="mt-6 text-center text-xs text-slate-400">
          {t('Hisobingiz yoʻqmi? Bogʻchangiz uchun akkaunt ochish uchun biz bilan bogʻlaning.')}
        </p>
        <div className="mt-4 flex justify-center">
          <LanguageSwitch size="md" />
        </div>
      </div>
    </div>
  )
}

/**
 * "Parolni unutdingizmi?" (PLAN 5.2).
 *
 * Javob HAR DOIM bir xil — email tizimda bor-yoʻqligi tashqaridan
 * koʻrinmaydi: "bunday email yoʻq" degan matn begona odamga mijozlar
 * roʻyxatini tekshirish imkonini berardi (bir bogʻcha direktori
 * raqobatchisining xodimi tizimda borligini bilib olardi).
 */
function ForgotPasswordForm({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await authApi.requestPasswordReset(email)
      setSent(true)
    } catch (err) {
      // Faqat TEXNIK xato koʻrsatiladi (tarmoq, 429). Hisobning
      // bor-yoʻqligi haqidagi ma'lumot serverdan ham kelmaydi.
      setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
    } finally {
      setBusy(false)
    }
  }

  if (sent) {
    return (
      <div className="space-y-3 text-center">
        <MailCheck className="mx-auto h-8 w-8 text-nihol-600" />
        <p className="text-sm text-tosh-700">
          {t('Agar bu email tizimda boʻlsa, tiklash havolasi yuborildi. Pochtangizni tekshiring.')}
        </p>
        <p className="text-xs text-tosh-500">{t('Havola 30 daqiqa ishlaydi.')}</p>
        <button
          type="button"
          onClick={onBack}
          className="w-full pt-1 text-center text-sm text-tosh-500 hover:text-tosh-700"
        >
          {t('Kirishga qaytish')}
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-tosh-900">{t('Parolni tiklash')}</h2>
        <p className="mt-1 text-sm text-tosh-500">
          {t('Email manzilingizni yozing — tiklash havolasini yuboramiz.')}
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="forgot-email" className="mb-1 block text-sm font-medium text-tosh-700">
          {t('Email')}
        </label>
        <input
          id="forgot-email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-lg border border-tosh-200 px-3 py-2 text-sm outline-none focus:border-nihol-500"
        />
      </div>

      <button
        type="submit"
        disabled={busy}
        className={cn(
          'w-full rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white transition',
          busy ? 'opacity-60' : 'hover:bg-nihol-700',
        )}
      >
        {busy ? t('Yuborilmoqda…') : t('Havolani yuborish')}
      </button>

      <button
        type="button"
        onClick={onBack}
        className="w-full text-center text-sm text-tosh-500 hover:text-tosh-700"
      >
        {t('Orqaga')}
      </button>
    </form>
  )
}
