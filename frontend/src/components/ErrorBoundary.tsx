/**
 * Render xatosini ushlaydi (P1-006).
 *
 * Usiz React 18 ushlanmagan xatoda BUTUN daraxtni yechadi va
 * foydalanuvchi oq ekran ko'radi: xabar yo'q, tugma yo'q, nima
 * bo'lganini bilish imkoni yo'q. Bog'cha xodimi uchun bu "tizim
 * buzildi" degani va keyingi qadami — qo'ng'iroq qilish.
 *
 * Chegara ikkita narsa beradi: odam o'qiydigan xabar va `X-Request-ID`.
 * Ikkinchisi qo'llab-quvvatlash uchun: mijoz kodni aytadi, siz uni
 * log'dan bir urinishda topasiz (backendda `apps/core/logging.py`).
 *
 * Sinf komponenti ATAYLAB: `componentDidCatch` ning hook varianti
 * React'da hozircha yo'q.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'
import { lastRequestId } from '@/lib/api/client'
import { t } from '@/lib/i18n'

interface Props {
  children: ReactNode
  /** Qaysi qism yiqilgani log'da ko'rinsin. */
  area?: string
}

interface State {
  error: Error | null
  requestId: string | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, requestId: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error, requestId: lastRequestId() }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Konsolga yozamiz — bugun xato kuzatuvi (Sentry va h.k.) yo'q,
    // shuning uchun brauzer konsoli yagona manba. Kuzatuv ulanganda
    // aynan shu joyga qo'shiladi.
    console.error(`[${this.props.area ?? 'app'}] render xatosi`, error, info.componentStack)
  }

  render() {
    const { error, requestId } = this.state
    if (!error) return this.props.children

    return (
      <div className="grid min-h-[60vh] place-items-center px-4">
        <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />

          <h2 className="mt-4 text-lg font-semibold text-slate-900">{t('Sahifa ochilmadi')}</h2>
          <p className="mt-2 text-sm text-slate-600">
            {t(
              'Kutilmagan xatolik yuz berdi. Maʼlumotlaringiz joyida — bu faqat shu ekranga tegishli.',
            )}
          </p>

          <div className="mt-5 flex gap-2">
            <button
              type="button"
              onClick={() => this.setState({ error: null, requestId: null })}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <RotateCcw className="h-4 w-4" />
              {t('Qayta urinish')}
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="flex-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500"
            >
              {t('Sahifani yangilash')}
            </button>
          </div>

          {requestId && (
            <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
              {t('Qoʻllab-quvvatlashga ayting:')} <span className="font-mono">{requestId}</span>
            </p>
          )}
        </div>
      </div>
    )
  }
}
