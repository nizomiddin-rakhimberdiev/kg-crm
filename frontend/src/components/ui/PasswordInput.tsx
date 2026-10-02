/**
 * Parol maydoni — koʻrsatish/yashirish tugmasi bilan (PLAN 5.2).
 *
 * Nega kerak: kuchli parol uzun va aralash belgili, mobil
 * klaviaturada esa uni xato terish oson. Koʻrinmas maydonda odam
 * xatoni faqat "parol notoʻgʻri" javobidan keyin biladi — va yangi
 * parol oʻrnatayotganda bu xato PAROLNING OʻZIGA yoziladi, yaʼni
 * hisobga kirish imkonini yoʻqotadi.
 *
 * Sukut holat — YASHIRIN: yonida turgan odam parolni koʻrmasligi
 * kerak. Koʻrsatish — ongli bosish.
 */

import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

type Props = Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'>

export function PasswordInput({ className, ...props }: Props) {
  const [shown, setShown] = useState(false)

  return (
    <div className="relative">
      <input
        {...props}
        type={shown ? 'text' : 'password'}
        className={cn(
          'w-full rounded-lg border border-tosh-200 px-3 py-2 pr-10 text-sm outline-none focus:border-nihol-500',
          className,
        )}
      />
      <button
        type="button"
        onClick={() => setShown((value) => !value)}
        // `tabIndex={-1}`: tugma parol bilan keyingi maydon orasiga
        // tushib, klaviatura bilan toʻldirishni sekinlashtirmasligi
        // kerak. Skrinrider uni nomidan topadi.
        tabIndex={-1}
        aria-label={shown ? t('Parolni yashirish') : t('Parolni koʻrsatish')}
        title={shown ? t('Parolni yashirish') : t('Parolni koʻrsatish')}
        className="absolute right-1 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-tosh-400 hover:bg-tosh-50 hover:text-tosh-700"
      >
        {shown ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  )
}
