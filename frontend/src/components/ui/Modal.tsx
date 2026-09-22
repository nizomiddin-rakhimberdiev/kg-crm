import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

interface ModalProps {
  open: boolean
  onClose: () => void
  children: ReactNode
  className?: string
}

/**
 * Reusable dialog with a blurred backdrop and a soft spring-in animation.
 * Rendered through a portal to <body> so it's never clipped/mis-positioned by
 * the page-transition transform.
 */
export function Modal({ open, onClose, children, className }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[95] flex items-center justify-center p-4">
          {/* Backdrop — blurred + dimmed */}
          <motion.div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          {/* Panel */}
          <motion.div
            role="dialog"
            aria-modal="true"
            className={cn(
              'relative z-10 max-h-[85vh] w-full max-w-lg overflow-y-auto scrollbar-thin rounded-2xl border border-slate-200 bg-white shadow-2xl',
              className,
            )}
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <button
              onClick={onClose}
              aria-label={t('Yopish')}
              className="absolute top-4 right-4 grid place-items-center w-8 h-8 rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 active:scale-90"
            >
              <X className="w-4 h-4" />
            </button>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
