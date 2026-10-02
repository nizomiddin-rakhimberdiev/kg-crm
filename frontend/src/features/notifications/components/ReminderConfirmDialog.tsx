/**
 * Ommaviy eslatmadan oldingi tasdiq (PLAN 3.5).
 *
 * "Qarzdorlarga eslatma" tugmasi 200 ta SMS yuborishi mumkin va uni
 * qaytarib bo'lmaydi: yuborilgan xabar ota-onaning telefonida qoladi.
 * Shuning uchun tasdiqdan oldin ANIQ son ko'rsatiladi — nechtasiga
 * ketadi, nechtasi telefonsiz, nechtasi bugun allaqachon olgan va
 * taxminan qanchaga tushadi.
 *
 * Sonlar SERVERDAN keladi va yuborish AYNI filtr bilan ketadi: ikkita
 * alohida hisob bo'lsa, "48 ta" deb ko'rsatib 51 tasiga yuborish
 * holati paydo bo'lardi.
 */

import { useQuery } from '@tanstack/react-query'
import { BellRing } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { notificationsApi, type ReminderFilters } from '@/features/notifications/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'

const money = som

interface Props {
  open: boolean
  filters: ReminderFilters
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ReminderConfirmDialog({ open, filters, busy, onConfirm, onCancel }: Props) {
  const organizationId = useOrganizationId()
  const preview = useQuery({
    queryKey: queryKeys.reminderPreview(organizationId, filters as Record<string, unknown>),
    queryFn: () => notificationsApi.reminderPreview(filters),
    enabled: open,
  })

  const data = preview.data
  return (
    <ConfirmDialog
      open={open}
      title={t('Eslatma yuborilsinmi?')}
      confirmLabel={t('Ha, yuborilsin')}
      busy={busy || preview.isPending}
      onConfirm={onConfirm}
      onCancel={onCancel}
      body={
        preview.isPending ? (
          <p className="text-sm text-tosh-500">{t('Hisoblanmoqda…')}</p>
        ) : data ? (
          <div className="space-y-2 text-sm">
            <p className="flex items-center gap-2 font-semibold text-tosh-900">
              <BellRing className="h-4 w-4 text-nihol-600" />
              {t('{count} ta ota-onaga SMS ketadi', { count: data.eligible })}
            </p>
            <ul className="space-y-1 text-tosh-600">
              {data.skipped_no_phone > 0 && (
                <li>
                  {t('{count} tasining telefon raqami yo‘q — ularga yuborilmaydi', {
                    count: data.skipped_no_phone,
                  })}
                </li>
              )}
              {data.skipped_already_sent > 0 && (
                <li>
                  {t('{count} tasi bugun allaqachon eslatma olgan', {
                    count: data.skipped_already_sent,
                  })}
                </li>
              )}
              <li>{t('{count} ta SMS bo‘lagi', { count: data.parts })}</li>
              {data.estimated_cost && (
                <li>{t('Taxminiy xarajat: {cost}', { cost: money(data.estimated_cost) })}</li>
              )}
            </ul>
          </div>
        ) : null
      }
    />
  )
}
