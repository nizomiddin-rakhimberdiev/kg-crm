/**
 * Imzolangan shartnomaning elektron nusxasi (mijoz so'rovi, 2026-10-21).
 *
 * Bogʻcha qogʻozda imzolangan shartnomani PDF, DOC yoki DOCX qilib bolaga
 * biriktiradi; majburiy emas. Shablondan tuziladigan shartnomadan
 * (Shartnomalar kartasi) alohida — bu bogʻchaning oʻz hujjati. Fayl turi
 * va hajmi shu yerda ham tekshiriladi (tez javob uchun), lekin oxirgi soʻz
 * serverda: u fayl ICHINI ham koʻradi.
 */

import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileText, Paperclip, Trash2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { childrenApi, type ChildDocument } from '@/features/children/api'
import { documentProblem } from '@/features/children/documents'
import { ApiError } from '@/lib/api/types'
import { formatDate } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'

function size(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function ChildDocumentsCard({ childId }: { childId: string }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const editable = can('children.update')
  const input = useRef<HTMLInputElement>(null)
  const key = ['org', organizationId, 'children', childId, 'documents']
  const query = useQuery({ queryKey: key, queryFn: () => childrenApi.documents(childId) })
  const [error, setError] = useState<string | null>(null)
  const [removing, setRemoving] = useState<ChildDocument | null>(null)

  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
  const upload = useMutation({
    mutationFn: (file: File) => childrenApi.uploadDocument(childId, file),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: (document: ChildDocument) => childrenApi.removeDocument(childId, document.id),
    onSuccess: () => {
      setRemoving(null)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: fail,
  })

  const choose = (file: File | undefined) => {
    if (!file) return
    const problem = documentProblem(file)
    if (problem) {
      setError(problem)
      return
    }
    upload.mutate(file)
  }

  const rows = query.data ?? []
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{t('Shartnoma fayli')}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Imzolangan shartnomaning elektron nusxasi — PDF, DOC yoki DOCX, 10 MB gacha.')}
          </p>
        </div>
        {editable && (
          <>
            <input
              ref={input}
              type="file"
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              aria-label={t('Shartnoma faylini tanlash')}
              onChange={(event) => {
                choose(event.target.files?.[0])
                event.target.value = ''
              }}
            />
            <button
              type="button"
              disabled={upload.isPending}
              onClick={() => input.current?.click()}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <Paperclip className="h-4 w-4" aria-hidden />
              {upload.isPending ? t('Yuklanmoqda…') : t('Fayl biriktirish')}
            </button>
          </>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{t('Fayl biriktirilmagan.')}</p>
      ) : (
        <ul className="mt-3 divide-y divide-slate-100">
          {rows.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center gap-3 py-2.5">
              <FileText className="h-5 w-5 shrink-0 text-slate-500" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-900" title={row.name}>
                  {row.name}
                </p>
                <p className="text-xs text-slate-500">
                  {size(row.size)} · {formatDate(row.created_at)}
                  {row.uploaded_by && ` · ${row.uploaded_by}`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void childrenApi.downloadDocument(childId, row).catch(fail)}
                aria-label={t('{name} — yuklab olish', { name: row.name })}
                className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
              >
                <Download className="h-4 w-4" aria-hidden />
              </button>
              {editable && (
                <button
                  type="button"
                  onClick={() => setRemoving(row)}
                  aria-label={t('{name} — oʻchirish', { name: row.name })}
                  className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={removing !== null}
        title={t('Faylni oʻchirasizmi?')}
        body={removing?.name ?? ''}
        confirmLabel={t('Oʻchirish')}
        tone="danger"
        busy={remove.isPending}
        onConfirm={() => removing && remove.mutate(removing)}
        onCancel={() => setRemoving(null)}
      />
    </section>
  )
}
