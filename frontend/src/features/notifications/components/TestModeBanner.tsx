/**
 * Kanal holati banneri (PLAN 3.2, 3.7).
 *
 * Auditda topilgan eng jimgina xato: jurnal "Yuborildi" deb turardi,
 * ota-ona esa hech narsa olmagan edi — chunki haqiqiy provayder
 * ulanmagan. Ekran buni ochiq aytmaguncha, bog'cha xabarlar
 * ishlayapti deb o'ylab turadi va bir oydan keyin "nega hech kim
 * to'lamadi?" degan savol beradi.
 *
 * Asosiy kanal — Telegram (ADR-23), va u yerda ikkita boshqa savol
 * ham bor: **bot sozlanganmi** va **ota-onalar ulanganmi**. Ikkinchisi
 * muhimroq: bot ishlab turgani bilan hech kim ulanmagan bo'lsa,
 * natija bir xil — xabar hech kimga bormaydi.
 *
 * Banner **yopilmaydi**: u bezovta qiluvchi eslatma emas, tizim
 * holati.
 */

import { AlertTriangle, Send } from 'lucide-react'
import { useSmsStatus } from '@/features/notifications/useSmsStatus'
import { t } from '@/lib/i18n'

function Warning({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      role="status"
      className="flex items-start gap-2 rounded-xl border border-orik-200 bg-orik-50 px-3 py-2 text-sm text-orik-900"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orik-600" />
      <div>
        <p className="font-semibold">{title}</p>
        <p className="mt-0.5 text-orik-800">{children}</p>
      </div>
    </div>
  )
}

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
        <p>{t('Xabar yuborish oʻchirilgan — Sozlamalarda yoqishingiz mumkin.')}</p>
      </div>
    )
  }

  // 1. Kanalning o'zi ulanmagan — eng muhim holat.
  if (data.test_mode) {
    return data.default_channel === 'telegram' ? (
      <Warning title={t('Telegram bot ulanmagan')}>
        {t(
          'Xabarlar jurnalga yoziladi, lekin ota-onalarga YUBORILMAYDI. Botni ulash uchun administratorga murojaat qiling.',
        )}
      </Warning>
    ) : (
      <Warning title={t('SMS test rejimida')}>
        {t(
          'Xabarlar jurnalga yoziladi, lekin ota-onalarga YUBORILMAYDI. Haqiqiy yuborish uchun SMS provayderi ulanishi kerak.',
        )}
      </Warning>
    )
  }

  // 2. Kanal ishlaydi, lekin ota-onalar ulanmagan — natija bir xil.
  const reach = data.channels.telegram.reach
  if (data.default_channel === 'telegram' && reach.total > 0 && reach.linked < reach.total) {
    const missing = reach.total - reach.linked
    return (
      <div
        role="status"
        className="flex items-start gap-2 rounded-xl border border-tosh-200 bg-white px-3 py-2 text-sm text-tosh-700"
      >
        <Send className="mt-0.5 h-4 w-4 shrink-0 text-nihol-600" />
        <p>
          {t(
            '{linked} ota-onadan {total} tasi Telegramga ulangan. Qolgan {missing} tasi xabar olmaydi — bola kartasidan ulash havolasini yuboring.',
            { linked: reach.linked, total: reach.total, missing },
          )}
        </p>
      </div>
    )
  }

  return null
}
