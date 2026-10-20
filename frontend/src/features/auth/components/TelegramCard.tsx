/**
 * Oʻz Telegram'ini botga ulash (Bosqich 13.3c): chiqimni bot orqali
 * kiritish — summa, chek rasmi va bitta tugma — va (13.4) egaga
 * darhol xabarlar. Havola bir martalik; faqat oʻz hisobi.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Send } from 'lucide-react'
import { api } from '@/lib/api/client'
import { formatDate } from '@/lib/format'
import { t } from '@/lib/i18n'

interface Status {
  linked: boolean
  linked_at: string | null
}

export function TelegramCard() {
  const queryClient = useQueryClient()
  const key = ['me', 'telegram']
  const status = useQuery({ queryKey: key, queryFn: () => api.get<Status>('/auth/telegram') })
  const link = useMutation({
    mutationFn: () => api.post<{ link: string }>('/auth/telegram'),
    onSuccess: (data) => {
      window.open(data.link, '_blank', 'noopener')
      void queryClient.invalidateQueries({ queryKey: key })
    },
  })
  const unlink = useMutation({
    mutationFn: () => api.delete('/auth/telegram'),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: key }),
  })
  const data = status.data

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2">
        <Send className="h-4 w-4 text-slate-500" />
        <h2 className="text-sm font-semibold text-slate-900">{t('Telegram')}</h2>
      </div>
      <p className="mt-1 text-sm text-slate-600">
        {t(
          'Botga ulansangiz, chiqimni u yerdan kiritasiz (summa va chek rasmi) va savol berasiz: «bugungi tushum», «bu oy foyda», «faol bolalar». Roʻyxat — /help.',
        )}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {data?.linked ? (
          <>
            <span className="text-sm font-medium text-emerald-700">
              {t('Ulangan')}
              {data.linked_at && ` · ${formatDate(data.linked_at)}`}
            </span>
            <button
              type="button"
              onClick={() => unlink.mutate()}
              disabled={unlink.isPending}
              className="text-sm text-slate-600 hover:underline"
            >
              {t('Uzish')}
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => link.mutate()}
            disabled={link.isPending}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {t('Telegram botga ulash')}
          </button>
        )}
      </div>
    </div>
  )
}
