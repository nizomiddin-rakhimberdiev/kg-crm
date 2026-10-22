/**
 * Ota-onani Telegram botga ulash (PLAN 3.7, ADR-23).
 *
 * Asosiy kanal — Telegram, ya'ni **ulanmagan ota-ona hech qanday
 * xabar olmaydi**. Shuning uchun bu holat bola kartasida ko'rinib
 * turishi kerak, sozlamalar ichida yashirinib qolmasligi: "nega
 * hech kim to'lamadi?" degan savolning javobi ko'pincha shu yerda.
 *
 * `chat_id` ni biz bera olmaymiz — u faqat ota-onaning o'zi botni
 * ishga tushirganda paydo bo'ladi. Ya'ni bu tugma xabar yubormaydi,
 * balki **havola beradi**: mudira uni WhatsApp orqali yuboradi yoki
 * QR qilib chop etadi.
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Link2, Send, Unlink } from 'lucide-react'
import { guardiansApi } from '@/features/children/api'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

interface Props {
  guardianId: string
  linked: boolean
  /** Ulanish/uzilishdan keyin bola kartasini yangilash. */
  onChange: () => void
}

export function TelegramLinkButton({ guardianId, linked, onChange }: Props) {
  const { can } = useCan()
  const queryClient = useQueryClient()
  const [url, setUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const issue = useMutation({
    mutationFn: (rotate: boolean) => guardiansApi.telegramLink(guardianId, rotate),
    onSuccess: (result) => {
      setError(null)
      setCopied(false)
      setUrl(result.url)
      if (!result.url) {
        setError(t('Telegram bot sozlanmagan — administratorga murojaat qiling.'))
      }
    },
    onError: fail,
  })

  const unlink = useMutation({
    mutationFn: () => guardiansApi.telegramUnlink(guardianId),
    onSuccess: () => {
      setError(null)
      setUrl(null)
      onChange()
      void queryClient.invalidateQueries({ queryKey: ['org'] })
    },
    onError: fail,
  })

  const copy = async () => {
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
    } catch {
      // Brauzer ruxsat bermasa havola baribir ekranda ko'rinadi —
      // uni qo'lda belgilab olish mumkin.
      setCopied(false)
    }
  }

  if (!can('children.update')) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 text-xs',
          linked ? 'text-nihol-700' : 'text-tosh-500',
        )}
      >
        <Send className="h-3 w-3" />
        {linked ? t('Telegram ulangan') : t('Telegram ulanmagan')}
      </span>
    )
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        {linked ? (
          <>
            <span className="inline-flex items-center gap-1 rounded-full bg-nihol-50 px-2 py-0.5 text-xs font-medium text-nihol-700">
              <Check className="h-3 w-3" />
              {t('Telegram ulangan')}
            </span>
            <button
              type="button"
              onClick={() => unlink.mutate()}
              disabled={unlink.isPending}
              className="inline-flex items-center gap-1 text-xs text-tosh-500 underline-offset-2 hover:text-orik-800 hover:underline"
            >
              <Unlink className="h-3 w-3" />
              {t('Uzish')}
            </button>
          </>
        ) : (
          <>
            <span className="inline-flex items-center gap-1 rounded-full bg-orik-50 px-2 py-0.5 text-xs font-medium text-orik-800">
              <Send className="h-3 w-3" />
              {t('Telegram ulanmagan')}
            </span>
            <button
              type="button"
              onClick={() => issue.mutate(false)}
              disabled={issue.isPending}
              className="inline-flex items-center gap-1 rounded-lg border border-tosh-200 px-2 py-1 text-xs font-medium text-tosh-700 hover:bg-tosh-50 disabled:opacity-50"
            >
              <Link2 className="h-3 w-3" />
              {issue.isPending ? t('Tayyorlanmoqda…') : t('Ulash havolasi')}
            </button>
          </>
        )}
      </div>

      {url && (
        <div className="space-y-1 rounded-lg bg-tosh-50 p-2">
          <p className="text-xs text-tosh-600">
            {t(
              'Shu havolani ota-onaga yuboring — u botni ochib, xabarlarga ulanadi. Botni ochish — roziligi: manzilni biz bera olmaymiz, u faqat ota-ona oʻzi boshlaganda paydo boʻladi.',
            )}
          </p>
          <div className="flex items-center gap-1.5">
            <code className="min-w-0 flex-1 truncate rounded bg-white px-2 py-1 text-xs text-tosh-700">
              {url}
            </code>
            <button
              type="button"
              onClick={() => void copy()}
              className="inline-flex items-center gap-1 rounded-lg border border-tosh-200 bg-white px-2 py-1 text-xs font-medium text-tosh-700 hover:bg-tosh-50"
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? t('Nusxalandi') : t('Nusxalash')}
            </button>
          </div>
          <button
            type="button"
            onClick={() => issue.mutate(true)}
            className="text-xs text-tosh-500 underline-offset-2 hover:underline"
          >
            {t('Yangi havola — eskisi ishlamay qoladi')}
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="text-xs text-orik-800">
          {error}
        </p>
      )}
    </div>
  )
}
