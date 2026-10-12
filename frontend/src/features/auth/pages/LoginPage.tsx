/**
 * Kirish sahifasi — ikki bosqichli (docs/04 §5).
 *
 * Email tashkilot ichida unikal, shuning uchun bitta email bir nechta
 * bog'chaga mos kelishi mumkin. Bunday holda backend pending token va
 * tashkilotlar ro'yxatini qaytaradi va foydalanuvchi tanlaydi.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Building2, Eye, EyeOff, Loader2 } from 'lucide-react'
import { AuthShell } from '@/components/auth/AuthShell'
import { useAuth } from '@/app/providers/AuthProvider'
import { authApi } from '@/features/auth/api'
import { ApiError, isPendingChoice, type OrganizationSummary } from '@/lib/api/types'
import { t } from '@/lib/i18n'

type Stage =
  | { kind: 'credentials' }
  | { kind: 'choose-organization'; pendingToken: string; organizations: OrganizationSummary[] }

const swap = {
  initial: { opacity: 0, x: 16 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const } },
  exit: { opacity: 0, x: -16, transition: { duration: 0.2 } },
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { applySession } = useAuth()

  const [stage, setStage] = useState<Stage>({ kind: 'credentials' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const handleError = (err: unknown) => {
    setError(
      err instanceof ApiError ? err.message : t("Kutilmagan xatolik. Qaytadan urinib ko'ring."),
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
    <AuthShell
      title={stage.kind === 'credentials' ? t('Xush kelibsiz') : t('Tashkilotni tanlang')}
      subtitle={
        stage.kind === 'credentials'
          ? t('Hisobingizga kiring va bog‘changizni boshqaring.')
          : t("Bu email bir nechta bog'chada ro'yxatdan o'tgan.")
      }
      footer={
        <>
          {t("Hisobingiz yo'qmi?")}{' '}
          <Link
            to="/signup"
            className="font-semibold text-nihol-700 underline-offset-4 transition hover:text-nihol-800 hover:underline"
          >
            {t('Sinov uchun ariza qoldiring')}
          </Link>
        </>
      }
    >
      <AnimatePresence mode="wait" initial={false}>
        {error && (
          <motion.div
            key="error"
            role="alert"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mb-5 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait" initial={false}>
        {stage.kind === 'credentials' ? (
          <motion.form key="credentials" {...swap} onSubmit={submitCredentials} className="space-y-5">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-semibold text-tosh-700">
                {t('Email')}
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="username"
                placeholder="name@kindergarten.uz"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="field"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-semibold text-tosh-700">
                {t('Parol')}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? t('Parolni yashirish') : t("Parolni ko'rsatish")}
                  className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-lg text-tosh-400 transition hover:bg-tosh-100 hover:text-tosh-700"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={busy} className="btn-primary group">
              {busy ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('Tekshirilmoqda…')}
                </>
              ) : (
                <>
                  {t('Kirish')}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </motion.form>
        ) : (
          <motion.div key="choose" {...swap} className="space-y-3">
            {stage.organizations.map((org, index) => (
              <motion.button
                key={org.id}
                type="button"
                disabled={busy}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0, transition: { delay: index * 0.05 } }}
                whileHover={{ y: -1 }}
                onClick={() => void chooseOrganization(org.id)}
                className="flex w-full items-center gap-3 rounded-xl border border-tosh-200 bg-white px-4 py-3.5 text-left shadow-card transition hover:border-nihol-300 hover:bg-nihol-50 disabled:opacity-60"
              >
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-nihol-50 text-nihol-700">
                  <Building2 className="h-4 w-4" />
                </span>
                <span className="text-sm font-semibold text-tosh-800">{org.name}</span>
              </motion.button>
            ))}

            <button
              type="button"
              onClick={() => setStage({ kind: 'credentials' })}
              className="w-full pt-1 text-center text-sm text-tosh-500 transition hover:text-tosh-800"
            >
              {t('Orqaga')}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthShell>
  )
}
