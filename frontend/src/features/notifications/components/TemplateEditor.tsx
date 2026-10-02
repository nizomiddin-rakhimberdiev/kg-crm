/**
 * SMS shablon muharriri (PLAN 3.4).
 *
 * Uchta narsa auditda yo'q edi va har biri pul yoki obro' turadi:
 *
 * 1. **O'zgaruvchi tugmalari.** Mudira `${guardian}` ni yodlab
 *    yozishi kerak emas; o'zi o'ylab topgan `${ota}` esa hech narsaga
 *    almashmaydi va shu ko'rinishda ota-onaga ketadi.
 * 2. **Belgi va bo'lak hisoblagichi.** Narx bo'laklar bo'yicha; kirill
 *    matni 70 belgidan keyin ikkinchi bo'lakka o'tadi. Hisoblagichsiz
 *    bu faqat oy oxirida ko'rinadi.
 * 3. **Ko'rib chiqish.** O'rinbosarlar to'ldirilgan holda matn qanday
 *    ko'rinishini yuborishdan OLDIN ko'rish kerak.
 */

import { useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Eye, Languages, Plus } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { templatesApi } from '@/features/notifications/api'
import { insertVariable, measureSms, smsSafe } from '@/features/notifications/sms'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import type { NotificationTemplate } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const LANGUAGES: Array<[NotificationTemplate['language'], string]> = [
  ['uz', t("O'zbekcha")],
  ['ru', t('Ruscha')],
]

/**
 * Kanal ko'rinishlari (PLAN 3.7).
 *
 * Matnlar ataylab bir xil emas: SMS'da har belgi pul turadi, Telegram
 * esa bepul va uzunlik bilan cheklanmagan — shuning uchun ularni
 * alohida tahrirlash kerak.
 */
const CHANNELS: Array<[NotificationTemplate['channel'], string]> = [
  ['telegram', t('Telegram')],
  ['sms', t('SMS')],
]

const CODE_LABEL: Record<string, string> = {
  payment_received: t("To'lov qabul qilindi"),
  debt_reminder: t('Qarzdorlik eslatmasi'),
  absence_notice: t('Kelmagani haqida'),
  custom: t('Erkin xabar'),
}

/** Ko'rib chiqishda ishlatiladigan namuna qiymatlar. */
const SAMPLE: Record<string, string> = {
  guardian: 'Nodira Karimova',
  child: 'Ali Karimov',
  amount: '1 500 000',
  days: '15',
  organization: 'Oriental Kinderland',
}

function VariableButtons({
  names,
  onInsert,
}: {
  names: string[]
  onInsert: (name: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {names.map((name) => (
        <button
          key={name}
          type="button"
          onClick={() => onInsert(name)}
          className="rounded-md border border-tosh-200 bg-tosh-50 px-2 py-1 font-mono text-xs text-tosh-700 hover:border-nihol-300 hover:bg-nihol-50"
        >
          {'${' + name + '}'}
        </button>
      ))}
    </div>
  )
}

function LengthHint({ body, channel }: { body: string; channel: string }) {
  const measure = useMemo(() => measureSms(smsSafe(body)), [body])
  // Telegramda uzunlik bepul, shuning uchun bo'lak hisoblagichi
  // ma’nosiz — u faqat chalgʻitardi.
  if (channel !== 'sms') {
    return (
      <p className="text-xs text-tosh-500">
        {t('{characters} belgi', { characters: [...body].length })}
      </p>
    )
  }
  const tight = measure.parts > 1
  return (
    <p className={cn('text-xs', tight ? 'text-orik-700' : 'text-tosh-500')}>
      {t('{characters}/{limit} belgi · {parts} SMS', {
        characters: measure.characters,
        limit: measure.limit,
        parts: measure.parts,
      })}
      {measure.encoding === 'ucs2' && (
        <span className="ml-1">{t('· kirill alifbosi: bitta SMS 70 belgi')}</span>
      )}
    </p>
  )
}

function OneTemplate({
  code,
  channel,
  language,
  template,
  siblingBody,
}: {
  code: string
  channel: NotificationTemplate['channel']
  language: NotificationTemplate['language']
  template: NotificationTemplate | undefined
  siblingBody: string
}) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const area = useRef<HTMLTextAreaElement>(null)
  const [draft, setDraft] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const body = draft ?? template?.body ?? ''
  const dirty = template ? body !== template.body : body.trim().length > 0

  const refresh = () => {
    setDraft(null)
    setPreview(null)
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notificationTemplates(organizationId),
    })
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const save = useMutation({
    mutationFn: () =>
      template
        ? templatesApi.update(template.id, { body })
        : templatesApi.create({ code, channel, language, body }),
    onSuccess: () => {
      setError(null)
      refresh()
    },
    onError: fail,
  })

  const ask = useMutation({
    mutationFn: () => templatesApi.preview(body, SAMPLE),
    onSuccess: (result) => {
      setError(null)
      setPreview(result.rendered)
    },
    onError: fail,
  })

  const insert = (name: string) => {
    const cursor = area.current?.selectionStart ?? body.length
    const [next, caret] = insertVariable(body, cursor, name)
    setDraft(next)
    // Kursor qo'yilgan o'rinbosardan KEYIN turishi kerak — aks holda
    // ketma-ket ikki tugma matnni teskari tartibda yozardi.
    requestAnimationFrame(() => {
      area.current?.focus()
      area.current?.setSelectionRange(caret, caret)
    })
  }

  if (!template && draft === null) {
    return (
      <div className="rounded-lg border border-dashed border-tosh-200 p-3">
        <p className="text-xs text-tosh-500">
          {t('Bu tilda shablon yo‘q — ota-onalar boshqa tildagi matnni oladi.')}
        </p>
        <button
          type="button"
          onClick={() => setDraft(siblingBody)}
          className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-tosh-200 px-2.5 py-1.5 text-xs font-medium text-tosh-700 hover:bg-tosh-50"
        >
          <Plus className="h-3.5 w-3.5" />
          {t('Shablon qo‘shish')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <VariableButtons names={template?.variables ?? Object.keys(SAMPLE)} onInsert={insert} />
      <textarea
        ref={area}
        rows={3}
        value={body}
        aria-label={t('Xabar matni')}
        onChange={(event) => setDraft(event.target.value)}
        className="w-full rounded-lg border border-tosh-200 px-3 py-2 text-sm outline-none focus:border-nihol-500"
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <LengthHint body={body} channel={channel} />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => ask.mutate()}
            disabled={!body.trim() || ask.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg border border-tosh-200 px-2.5 py-1.5 text-xs font-medium text-tosh-700 hover:bg-tosh-50 disabled:opacity-40"
          >
            <Eye className="h-3.5 w-3.5" />
            {t('Ko‘rib chiqish')}
          </button>
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={!dirty || save.isPending}
            className="rounded-lg bg-nihol-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-nihol-700 disabled:opacity-40"
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </div>

      {preview && (
        <div className="rounded-lg bg-tosh-50 px-3 py-2">
          <p className="text-xs font-medium text-tosh-500">{t('Ota-ona shunday oladi:')}</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-tosh-900">{preview}</p>
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

export function TemplateEditor({ templates }: { templates: NotificationTemplate[] }) {
  const codes = useMemo(() => {
    const seen: string[] = []
    for (const template of templates) {
      if (!seen.includes(template.code)) seen.push(template.code)
    }
    return seen
  }, [templates])
  const [language, setLanguage] = useState<NotificationTemplate['language']>('uz')
  const [channel, setChannel] = useState<NotificationTemplate['channel']>('telegram')

  return (
    <section className="rounded-xl border border-tosh-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-tosh-900">{t('Xabar shablonlari')}</h2>
        <div
          role="tablist"
          aria-label={t('Kanal')}
          className="flex items-center gap-1 rounded-lg bg-tosh-50 p-1"
        >
          {CHANNELS.map(([code, label]) => (
            <button
              key={code}
              type="button"
              role="tab"
              aria-selected={channel === code}
              onClick={() => setChannel(code)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium',
                channel === code ? 'bg-white text-tosh-900 shadow-sm' : 'text-tosh-500',
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <div
          role="tablist"
          aria-label={t('Shablon tili')}
          className="flex items-center gap-1 rounded-lg bg-tosh-50 p-1"
        >
          <Languages className="ml-1 h-3.5 w-3.5 text-tosh-400" />
          {LANGUAGES.map(([code, label]) => (
            <button
              key={code}
              type="button"
              role="tab"
              aria-selected={language === code}
              onClick={() => setLanguage(code)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium',
                language === code ? 'bg-white text-tosh-900 shadow-sm' : 'text-tosh-500',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1 text-xs text-tosh-500">
        {t('O‘rinbosarlar yuborishda to‘ldiriladi — tugmani bosib matnga qo‘shing.')}
      </p>

      <div className="mt-4 space-y-5">
        {codes.map((code) => {
          const forCode = templates.filter((item) => item.code === code && item.channel === channel)
          const current = forCode.find((item) => item.language === language)
          const sibling = forCode.find((item) => item.language !== language)
          return (
            <div
              key={code}
              className="space-y-2 border-t border-tosh-100 pt-4 first:border-0 first:pt-0"
            >
              <p className="text-xs font-medium text-tosh-600">{CODE_LABEL[code] ?? code}</p>
              <OneTemplate
                key={`${code}-${channel}-${language}`}
                code={code}
                channel={channel}
                language={language}
                template={current}
                siblingBody={sibling?.body ?? ''}
              />
            </div>
          )
        })}
      </div>
    </section>
  )
}
