import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, Info, AlertTriangle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

type ToastTone = 'success' | 'info' | 'error'

interface ToastItem {
  id: number
  message: string
  tone: ToastTone
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export function useToast(): ToastContextValue {
  return useContext(ToastContext)
}

const toneStyles: Record<ToastTone, { icon: typeof Info; ring: string; iconColor: string }> = {
  success: { icon: CheckCircle2, ring: 'border-emerald-100', iconColor: 'text-emerald-600' },
  info: { icon: Info, ring: 'border-brand-100', iconColor: 'text-brand-600' },
  error: { icon: AlertTriangle, ring: 'border-red-100', iconColor: 'text-red-500' },
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const toast = useCallback((message: string, tone: ToastTone = 'success') => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, message, tone }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 2800)
  }, [])

  // Global handler: any element with data-toast="..." shows a toast when clicked.
  // Lets us give feedback to every button by just adding an attribute.
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null
      const el = target?.closest?.('[data-toast]') as HTMLElement | null
      if (!el) return
      const message = el.getAttribute('data-toast')
      if (!message) return
      const tone = (el.getAttribute('data-toast-tone') as ToastTone) || 'success'
      toast(message, tone)
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [toast])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed top-4 right-4 z-[100] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => {
            const s = toneStyles[t.tone]
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, x: 40, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, scale: 0.95 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                className={cn(
                  'pointer-events-auto flex items-center gap-3 rounded-xl border bg-white px-4 py-3 shadow-lg',
                  s.ring,
                )}
              >
                <s.icon className={cn('w-5 h-5 shrink-0', s.iconColor)} />
                <p className="flex-1 text-sm font-medium text-slate-700">{t.message}</p>
                <button
                  type="button"
                  title="Yopish"
                  aria-label="Yopish"
                  onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
                  className="grid place-items-center w-6 h-6 rounded-md text-slate-300 hover:bg-slate-100 hover:text-slate-500"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
