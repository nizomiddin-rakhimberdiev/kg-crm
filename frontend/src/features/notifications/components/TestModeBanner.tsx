/**
 * "SMS test rejimida" banneri (PLAN 3.2).
 *
 * Auditda topilgan eng jimgina xato: jurnal "Yuborildi" deb turardi,
 * ota-ona esa hech narsa olmagan edi — chunki haqiqiy provayder
 * ulanmagan. Ekran buni ochiq aytmaguncha, bog'cha SMS ishlayapti deb
 * o'ylab turadi va bir oydan keyin "nega hech kim to'lamadi?" degan
 * savol beradi.
 *
 * Shuning uchun banner **yopilmaydi**: u bezovta qiluvchi eslatma
 * emas, tizim holati.
 */

import { AlertTriangle } from 'lucide-react'
import { useSmsStatus } from '@/features/notifications/useSmsStatus'
import { t } from '@/lib/i18n'

export function TestModeBanner() {
  const { data } = useSmsStatus()
  if (!data) return null

  if (!data.sms_enabled) {
    return (
      <div
        role="status"
        className="flex items-start gap-2 rounded-xl border border-tosh-200 bg-tosh-50 px-3 py-2 text-sm text-tosh-700"
      >
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <p>{t('SMS yuborish o‘chirilgan — Sozlamalarda yoqishingiz mumkin.')}</p>
      </div>
    )
  }

  if (!data.test_mode) return null

  return (
    <div
      role="status"
      className="flex items-start gap-2 rounded-xl border border-orik-200 bg-orik-50 px-3 py-2 text-sm text-orik-900"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orik-600" />
      <div>
        <p className="font-semibold">{t('SMS test rejimida')}</p>
        <p className="mt-0.5 text-orik-800">
          {t(
            'Xabarlar jurnalga yoziladi, lekin ota-onalarga YUBORILMAYDI. Haqiqiy yuborish uchun SMS provayderi ulanishi kerak.',
          )}
        </p>
      </div>
    </div>
  )
}
