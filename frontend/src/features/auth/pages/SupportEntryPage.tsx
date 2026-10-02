/**
 * Vendor xodimining bog'chaga kirish nuqtasi (ADR-10).
 *
 * Konsol tokenni `localStorage` ga qo'yadi va shu sahifani yangi tabda
 * ochadi; bu sahifa uni darhol o'qib O'CHIRADI va sessiyani xotirada
 * ochadi. Token manzilga hech qachon yozilmaydi.
 */

import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { supportHandoff } from '@/lib/auth/supportSession'
import { t } from '@/lib/i18n'

export default function SupportEntryPage() {
  const { applySupportSession, isAuthenticated } = useAuth()
  const [error, setError] = useState<string | null>(null)
  // StrictMode effektni ikki marta ishga tushiradi; token bir martalik
  // bo'lgani uchun ikkinchi urinish uni topa olmasdi.
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true

    const token = supportHandoff.take()
    if (!token) {
      setError(t('Kirish tokeni topilmadi. Konsoldan qayta urinib koʻring.'))
      return
    }
    applySupportSession(token).catch(() =>
      setError(t('Sessiya ochilmadi — ruxsat muddati tugagan boʻlishi mumkin.')),
    )
  }, [applySupportSession])

  if (isAuthenticated) return <Navigate to="/home" replace />

  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-4">
      <div className="w-full max-w-sm text-center">
        <ShieldCheck className="mx-auto h-8 w-8 text-brand-600" />
        <p className="mt-4 text-sm text-slate-600">
          {error ?? t('Qoʻllab-quvvatlash sessiyasi ochilmoqda…')}
        </p>
      </div>
    </div>
  )
}
