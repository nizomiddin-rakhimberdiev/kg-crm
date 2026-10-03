/**
 * Settings → Contract templates (PLAN 6.5).
 *
 * The text is the kindergarten's own and is not translated (ADR-16). The
 * placeholder buttons insert the exact names the server accepts — the
 * same list it checks on save, so a typo never reaches a printed contract.
 * Editing a template does not touch contracts already made from it.
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileSignature } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { contractTemplatesApi, type ContractTemplate } from '@/features/contracts/api'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'

type Draft = Pick<ContractTemplate, 'name' | 'language' | 'body'> & { id?: string }

const EMPTY: Draft = { name: '', language: 'uz', body: '' }

export function ContractTemplatesSettings() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { can } = useCan()
  const editable = can('settings.update')
  const key = ['org', organizationId, 'contract-templates']

  const listQuery = useQuery({ queryKey: key, queryFn: contractTemplatesApi.list })
  const namesQuery = useQuery({
    queryKey: ['contract-placeholders'],
    queryFn: contractTemplatesApi.placeholders,
    staleTime: Infinity,
    enabled: editable,
  })

  const [draft, setDraft] = useState<Draft | null>(null)
  const [error, setError] = useState<string | null>(null)
  const bodyRef = useRef<HTMLTextAreaElement>(null)

  const save = useMutation({
    mutationFn: (value: Draft) => {
      const body = { name: value.name.trim(), language: value.language, body: value.body }
      return value.id
        ? contractTemplatesApi.update(value.id, body)
        : contractTemplatesApi.create(body)
    },
    onSuccess: () => {
      setDraft(null)
      setError(null)
      toast(t('Saqlandi'))
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
  })

  const remove = useMutation({
    mutationFn: (id: string) => contractTemplatesApi.remove(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: key }),
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const insert = (name: string) => {
    if (!draft) return
    const token = `{{${name}}}`
    const area = bodyRef.current
    const start = area?.selectionStart ?? draft.body.length
    const end = area?.selectionEnd ?? draft.body.length
    const body = draft.body.slice(0, start) + token + draft.body.slice(end)
    setDraft({ ...draft, body })
    requestAnimationFrame(() => {
      area?.focus()
      area?.setSelectionRange(start + token.length, start + token.length)
    })
  }

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <h2 className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-900">
        <FileSignature className="h-4 w-4 text-slate-500" />
        {t('Shartnoma shablonlari')}
      </h2>

      <div className="divide-y divide-slate-100">
        {(listQuery.data ?? []).map((template) => (
          <div key={template.id} className="flex items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-900">{template.name}</p>
              <p className="text-xs text-slate-500">
                {template.language.toUpperCase()} · {t('versiya {v}', { v: template.version })}
              </p>
            </div>
            {editable && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setDraft({ ...template })}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  {t('Tahrirlash')}
                </button>
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(t('Shablonni oʻchirasizmi? Tuzilgan shartnomalar qoladi.')))
                      remove.mutate(template.id)
                  }}
                  className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-red-50 hover:text-red-600"
                >
                  {t('Oʻchirish')}
                </button>
              </div>
            )}
          </div>
        ))}
        {(listQuery.data ?? []).length === 0 && !listQuery.isPending && (
          <p className="px-4 py-3 text-sm text-slate-500">{t('Shablon hali yoʻq.')}</p>
        )}
      </div>

      {editable && !draft && (
        <div className="border-t border-slate-100 px-4 py-3">
          <button
            type="button"
            onClick={() => setDraft({ ...EMPTY })}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('Yangi shablon')}
          </button>
        </div>
      )}

      {editable && draft && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate(draft)
          }}
          className="space-y-3 border-t border-slate-100 bg-slate-50 px-4 py-4"
        >
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <div>
              <label htmlFor="tpl-name" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Nomi')}
              </label>
              <input
                id="tpl-name"
                required
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label htmlFor="tpl-lang" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Til')}
              </label>
              <select
                id="tpl-lang"
                value={draft.language}
                onChange={(event) =>
                  setDraft({ ...draft, language: event.target.value as Draft['language'] })
                }
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
              >
                <option value="uz">{t('Oʻzbekcha')}</option>
                <option value="ru">{t('Ruscha')}</option>
                <option value="en">{t('Inglizcha')}</option>
              </select>
            </div>
          </div>

          <div>
            <p className="mb-1 text-xs font-medium text-slate-600">
              {t('Maydon qoʻshish (kursor turgan joyga):')}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(namesQuery.data ?? []).map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => insert(name)}
                  className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-mono text-xs text-slate-700 hover:border-brand-300"
                >
                  {name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="tpl-body" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Matn')}
            </label>
            <textarea
              id="tpl-body"
              ref={bodyRef}
              required
              rows={14}
              value={draft.body}
              onChange={(event) => setDraft({ ...draft, body: event.target.value })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setDraft(null)
                setError(null)
              }}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={save.isPending}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
