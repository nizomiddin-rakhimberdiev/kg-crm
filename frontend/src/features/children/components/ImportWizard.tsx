/**
 * Import sehrgari (docs/06 Sprint 2).
 *
 * Oqim ataylab ikki qadam: fayl → **tekshiruv natijasi** → saqlash.
 * Foydalanuvchi 200 qatorli faylni ko'r-ko'rona yuklamasligi kerak; u
 * nima yaratilishini va qaysi qatorda xato borligini oldindan ko'radi.
 */

import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, FileUp, Upload } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { childrenApi } from '@/features/children/api'
import { ApiError, type ImportReport } from '@/lib/api/types'
import { httpClient } from '@/lib/api/client'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

export function ImportWizard({ onClose }: { onClose: () => void }) {
  const organizationId = useOrganizationId()
  const { selectedBranchId } = useBranchScope()
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [report, setReport] = useState<ImportReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const runImport = useMutation({
    mutationFn: ({ target, dryRun }: { target: File; dryRun: boolean }) =>
      childrenApi.importFile(target, dryRun, selectedBranchId),
    onSuccess: (result) => {
      setReport(result)
      setError(null)
      if (!result.dry_run) {
        setDone(true)
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'children'] })
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'groups'] })
      }
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : t("Faylni yuklab bo'lmadi."))
      setReport(null)
    },
  })

  const pickFile = (selected: File | null) => {
    setFile(selected)
    setReport(null)
    setDone(false)
    setError(null)
    if (selected) runImport.mutate({ target: selected, dryRun: true })
  }

  /**
   * Shablon SERVERDAN olinadi, bu yerda yaratilmaydi.
   *
   * Ustun nomlari importer bilan aynan bir xil bo'lishi kerak. Ikki
   * joyda yozilgan ro'yxat ertami-kechmi ajralib qoladi — o'shanda
   * mijoz to'ldirgan fayl "majburiy ustun topilmadi" deb rad etilardi,
   * va sabab ko'rinmas bo'lardi.
   */
  const [templateBusy, setTemplateBusy] = useState(false)

  const downloadTemplate = async () => {
    setTemplateBusy(true)
    setError(null)
    try {
      const response = await httpClient.get('/children/import-template', {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data as Blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'bolalar-shablon.xlsx'
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      setError(t("Shablonni yuklab bo'lmadi. Qaytadan urinib ko'ring."))
    } finally {
      setTemplateBusy(false)
    }
  }

  const canSave = report !== null && report.errors.length === 0 && !done && file !== null

  return (
    <Modal open onClose={onClose} className="max-w-2xl">
      <div className="p-6">
        <div className="mb-4 pr-10">
          <h2 className="text-lg font-bold text-slate-900">{t("Ro'yxatni import qilish")}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {t("Shablonni yuklab oling, to'ldiring va shu yerga qaytaring.")}{' '}
            <strong>{t('Excel fayli')}</strong>{' '}
            {t("to'g'ridan-to'g'ri qabul qilinadi — CSV ga aylantirish shart emas.")}
          </p>
        </div>

        <button
          type="button"
          onClick={() => void downloadTemplate()}
          disabled={templateBusy}
          className="mb-4 text-sm font-medium text-brand-600 hover:underline disabled:opacity-50"
        >
          {templateBusy ? t('Tayyorlanmoqda…') : t('Excel shablonni yuklab olish')}
        </button>

        {/* 1-qadam: fayl */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault()
            pickFile(e.dataTransfer.files[0] ?? null)
          }}
          className="rounded-xl border-2 border-dashed border-slate-200 p-6 text-center"
        >
          <FileUp className="mx-auto mb-2 h-8 w-8 text-slate-300" />
          <p className="text-sm text-slate-500">
            {file ? file.name : t('Faylni shu yerga tashlang yoki tanlang')}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-3 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('Fayl tanlash')}
          </button>
        </div>

        {error && (
          <div role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {runImport.isPending && (
          <p className="mt-4 text-center text-sm text-slate-400">{t('Tekshirilmoqda…')}</p>
        )}

        {/* 2-qadam: tekshiruv natijasi */}
        {report && (
          <div className="mt-4 space-y-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                [t('Jami qator'), report.total_rows],
                [done ? t('Yaratildi') : t('Yaratiladi'), report.created],
                [t('Dublikat'), report.skipped_duplicates],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-lg font-bold text-slate-900">{value}</p>
                  <p className="text-xs text-slate-500">{label}</p>
                </div>
              ))}
            </div>

            {report.errors.length > 0 ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-900">
                  <AlertCircle className="h-4 w-4" />
                  {t('{length} ta xato — hech narsa saqlanmaydi', { length: report.errors.length })}
                </p>
                <ul className="max-h-48 space-y-1 overflow-y-auto text-sm text-amber-900">
                  {report.errors.map((rowError, index) => (
                    <li key={`${rowError.row}-${rowError.field}-${index}`}>
                      <span className="font-mono text-xs">
                        {t('{row}-qator', { row: rowError.row })}
                      </span>{' '}
                      — {rowError.message}
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-xs text-amber-800">
                  {t('Faylni tuzatib qayta yuklang. Allaqachon kiritilgan bolalar takrorlanmaydi.')}
                </p>
              </div>
            ) : done ? (
              <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                <CheckCircle2 className="h-4 w-4" />
                {t('Import yakunlandi.')}
              </div>
            ) : (
              <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                {t('Xato topilmadi. Saqlashga tayyor.')}
              </div>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            {done ? t('Yopish') : t('Bekor qilish')}
          </button>
          {canSave && (
            <button
              type="button"
              disabled={runImport.isPending}
              onClick={() => runImport.mutate({ target: file, dryRun: false })}
              className={cn(
                'flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white',
                runImport.isPending ? 'opacity-60' : 'hover:bg-brand-700',
              )}
            >
              <Upload className="h-4 w-4" />
              {t('{created} ta bolani saqlash', { created: report?.created })}
            </button>
          )}
        </div>
      </div>
    </Modal>
  )
}
