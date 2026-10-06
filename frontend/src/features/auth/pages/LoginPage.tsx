/**
 * Kirish sahifasi — ikki bosqichli (docs/04 §5).
 *
 * Email tashkilot ichida unikal, shuning uchun bitta email bir nechta
 * bog'chaga mos kelishi mumkin. Bunday holda backend pending token va
 * tashkilotlar ro'yxatini qaytaradi va foydalanuvchi tanlaydi.
 *
 * **Authenticator kodi maydoni sukut bo'yicha YO'Q** (PLAN 5.4). 2FA
 * mijoz tomonida ixtiyoriy, ya'ni u kimda yoqilganini sahifa oldindan
 * bilmaydi — va bilmasligi kerak: maydonning ko'rinishi "bu hisobda
 * 2FA bor" degan ma'lumotni har qanday begonaga aytib qo'yardi.
 * Server `401 TOTP_REQUIRED` qaytargandan keyin maydon ochiladi
 * (vendor login sahifasidagi naqsh bilan bir xil).
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
import { env } from '@/config/env'

type Stage =
  | { kind: 'credentials' }
  | { kind: 'choose-organization'; pendingToken: string; organizations: OrganizationSummary[] }
  | { kind: 'forgot' }

/** `401 TOTP_REQUIRED` — xato emas, keyingi bosqich. */
const asksForCode = (err: unknown) => err instanceof ApiError && err.code === 'TOTP_REQUIRED'

const CODE_FIELD =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-center font-mono text-base tracking-[0.3em] outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

/** Kod maydoni — Authenticator kodi YOKI zaxira kodi (PLAN 5.4). */
function CodeField({
  id,
  value,
  onChange,
}: {
  id: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">
        {t('Authenticator kodi')}
      </label>
      <input
        id={id}
        required
        inputMode="text"
        autoComplete="one-time-code"
        maxLength={20}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={CODE_FIELD}
      />
      {/* Bitta maydon ikki qiymat uchun: telefonini yoʻqotgan odam
          "qaysi maydonga yozaman?" degan savolni eng yomon paytda
          bermasligi kerak. */}
      <p className="mt-1.5 text-xs text-tosh-500">
        {t('Telefoningiz yoʻqolgan boʻlsa — zaxira kodidan birini kiriting.')}
      </p>
    </div>
  )
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { applySession } = useAuth()

  const [stage, setStage] = useState<Stage>({ kind: 'credentials' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  // Kod SOʻRALGANMI — server aytgandan keyin. Tashkilot tanlash
  // bosqichida esa qaysi tashkilot uchun soʻralgani ham muhim: bir
  // bogʻchada 2FA yoqilgan, ikkinchisida yoʻq boʻlishi normal.
  const [codeAsked, setCodeAsked] = useState<string | null>(null)
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
      const result = await authApi.login(email, password, codeAsked ? code : undefined)
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
      if (asksForCode(err)) {
        // Xato emas: hisobda 2FA yoqilgan. Maydonni ochamiz,
        // foydalanuvchi kodni kiritib qayta yuboradi.
        setCodeAsked('login')
        setCode('')
        return
      }
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
      const session = await authApi.selectOrganization(
        stage.pendingToken,
        organizationId,
        codeAsked === organizationId ? code : undefined,
      )
      applySession(session)
      navigate('/home', { replace: true })
    } catch (err) {
      if (asksForCode(err)) {
        // Tanlangan bogʻchada 2FA yoqilgan. Bosqich SAQLANADI —
        // boshidan boshlash pending tokenni behuda yoʻqotardi.
        setCodeAsked(organizationId)
        setCode('')
        return
      }
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
          {/* Sahifada bitta `h1` bo'lishi kerak. Ko'rinishda logotip
              yetarli, shuning uchun sarlavha ekran o'quvchi uchun
              yashirin: brendbuk yozuvni takrorlashni taqiqlaydi. */}
          <h1 className="sr-only">Radix CRM</h1>
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
                  className="h-11 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
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
                  onClick={() => {
                    setCodeAsked(null)
                    setStage({ kind: 'forgot' })
                  }}
                  className="mt-1 inline-flex min-h-[40px] items-center text-[13px] font-medium text-nihol-700 underline-offset-2 hover:underline"
                >
                  {t('Parolni unutdingizmi?')}
                </button>
              </div>

              {codeAsked === 'login' && <CodeField id="totp" value={code} onChange={setCode} />}

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

              {/* Self-signup (PLAN 6.7): only where there is a subscription. */}
              {!env.isStandalone && (
                <p className="text-center text-sm text-tosh-600">
                  <Link
                    to="/signup"
                    className="inline-flex min-h-[40px] items-center font-semibold text-nihol-700 underline-offset-2 hover:underline"
                  >
                    {t('Bogʻchangiz hali yoʻqmi? 15 kunlik sinovni boshlang')}
                  </Link>
                </p>
              )}
            </form>
          ) : (
            <div className="space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">{t('Tashkilotni tanlang')}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {t('Bu email bir nechta bogʻchada roʻyxatdan oʻtgan.')}
                </p>
              </div>

              {stage.organizations.map((org) =>
                codeAsked === org.id ? (
                  <form
                    key={org.id}
                    className="space-y-3 rounded-lg border border-brand-200 bg-brand-50/50 p-3"
                    onSubmit={(event) => {
                      event.preventDefault()
                      void chooseOrganization(org.id)
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <OrgMark name={org.name} logoUrl={org.logo_url} size={28} />
                      <span className="text-sm font-medium text-slate-800">{org.name}</span>
                    </div>
                    <CodeField id={`totp-${org.id}`} value={code} onChange={setCode} />
                    <button
                      type="submit"
                      disabled={busy}
                      className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
                    >
                      {busy ? t('Tekshirilmoqda…') : t('Kirish')}
                    </button>
                  </form>
                ) : (
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
                ),
              )}

              <button
                type="button"
                onClick={() => {
                  setCodeAsked(null)
                  setStage({ kind: 'credentials' })
                }}
                className="w-full pt-1 text-center text-sm text-slate-500 hover:text-slate-700"
              >
                {t('Orqaga')}
              </button>
            </div>
          )}
        </div>

        {/* Eski izoh ("akkaunt ochish uchun biz bilan bog'laning")
            olib tashlandi: u yuqoridagi sinov havolasiga zid edi.
            Self-signup (PLAN 6.7) bilan odam o'zi boshlaydi. */}
        <div className="mt-6 flex justify-center">
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
