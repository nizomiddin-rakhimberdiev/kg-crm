/**
 * Contracts on the child's card (PLAN 6.5).
 *
 * A contract is made from a template in one click and keeps the values of
 * that moment — the card says so, because the first question after a
 * tariff change is "will the contract change too?". Signing and ending
 * are status changes with a date; the text itself is never edited.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileSignature, Printer } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { Modal } from '@/components/ui/Modal'
import {
  contractsApi,
  contractTemplatesApi,
  printContract,
  type Contract,
  type ContractStatus,
} from '@/features/contracts/api'
import { formatDate, today as todayIso } from '@/lib/format'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const STATUS: Record<ContractStatus, [string, string]> = {
  draft: [t('Qoralama'), 'bg-slate-100 text-slate-600'],
  signed: [t('Imzolangan'), 'bg-emerald-50 text-emerald-700'],
  terminated: [t('Bekor qilingan'), 'bg-red-50 text-red-700'],
}

export function ContractsCard({ childId }: { childId: string }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const key = ['org', organizationId, 'contracts', childId]

  const contractsQuery = useQuery({ queryKey: key, queryFn: () => contractsApi.forChild(childId) })
  const templatesQuery = useQuery({
    queryKey: ['org', organizationId, 'contract-templates'],
    queryFn: contractTemplatesApi.list,
    enabled: can('children.create'),
  })

  const [templateId, setTemplateId] = useState('')
  const [open, setOpen] = useState<Contract | null>(null)
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () => contractsApi.create(childId, templateId),
    onSuccess: (contract) => {
      setError(null)
      setOpen(contract)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const templates = templatesQuery.data ?? []
  const contracts = contractsQuery.data ?? []

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <FileSignature className="h-4 w-4 text-slate-500" />
        <h2 className="text-sm font-semibold text-slate-900">{t('Shartnomalar')}</h2>
      </div>

      {contracts.length === 0 && !contractsQuery.isPending && (
        <p className="text-sm text-slate-500">{t('Shartnoma hali tuzilmagan.')}</p>
      )}
      <ul className="divide-y divide-slate-100">
        {contracts.map((contract) => {
          const [label, tone] = STATUS[contract.status]
          return (
            <li key={contract.id}>
              <button
                type="button"
                onClick={() => setOpen(contract)}
                className="flex w-full items-center gap-3 py-2 text-left hover:bg-slate-50"
              >
                <span className="min-w-0 flex-1">
                  <span className="block font-mono text-sm text-slate-900">{contract.number}</span>
                  <span className="block truncate text-xs text-slate-500">
                    {contract.template_name} · {formatDate(contract.created_at)}
                  </span>
                </span>
                <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                  {label}
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      {can('children.create') && (
        <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
          {templates.length === 0 ? (
            <p className="text-xs text-slate-500">
              {t('Avval Sozlamalarda shartnoma shablonini yarating.')}
            </p>
          ) : (
            <>
              <div className="min-w-0 flex-1">
                <label
                  htmlFor="contract-template"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Shablon')}
                </label>
                <select
                  id="contract-template"
                  value={templateId}
                  onChange={(event) => setTemplateId(event.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">{t('Tanlang')}</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                disabled={!templateId || create.isPending}
                onClick={() => create.mutate()}
                className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                {create.isPending ? t('Saqlanmoqda…') : t('Shartnoma tuzish')}
              </button>
            </>
          )}
          {error && (
            <p role="alert" className="w-full text-sm text-red-700">
              {error}
            </p>
          )}
        </div>
      )}

      {open && (
        <ContractDialog
          contract={open}
          onClose={() => setOpen(null)}
          onChanged={(next) => {
            setOpen(next)
            void queryClient.invalidateQueries({ queryKey: key })
          }}
        />
      )}
    </section>
  )
}

function ContractDialog({
  contract,
  onClose,
  onChanged,
}: {
  contract: Contract
  onClose: () => void
  onChanged: (contract: Contract) => void
}) {
  const { can } = useCan()
  const today = todayIso()
  const [date, setDate] = useState(today)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const sign = useMutation({
    mutationFn: () => contractsApi.sign(contract.id, date),
    onSuccess: onChanged,
    onError: fail,
  })
  const terminate = useMutation({
    mutationFn: () => contractsApi.terminate(contract.id, date, reason),
    onSuccess: onChanged,
    onError: fail,
  })
  const [label, tone] = STATUS[contract.status]

  return (
    <Modal open onClose={onClose} className="max-w-2xl">
      <div className="space-y-4 p-6">
        <div className="flex flex-wrap items-center gap-2 pr-10">
          <h2 className="font-mono text-lg font-bold text-slate-900">{contract.number}</h2>
          <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>{label}</span>
          {contract.signed_on && (
            <span className="text-xs text-slate-500">
              {t('Imzolangan: {date}', { date: formatDate(contract.signed_on) })}
            </span>
          )}
          {contract.terminated_on && (
            <span className="text-xs text-slate-500">
              {t('Bekor qilingan: {date}', { date: formatDate(contract.terminated_on) })}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">
          {t(
            'Matn tuzilgan paytdagi qiymatlar bilan saqlanadi: tarif keyin oʻzgarsa ham shartnoma oʻzgarmaydi.',
          )}
        </p>
        <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 font-sans text-sm leading-6 text-slate-800">
          {contract.rendered_text}
        </pre>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-end gap-2">
          <button
            type="button"
            onClick={() => printContract(contract)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Printer className="h-4 w-4" />
            {t('Chop etish')}
          </button>

          {can('children.update') && contract.status !== 'terminated' && (
            <>
              <div className="ml-auto">
                <label htmlFor="contract-date" className="mb-1 block text-xs text-slate-600">
                  {t('Sana')}
                </label>
                <DateInput id="contract-date" value={date} onChange={setDate} max={today} />
              </div>
              {contract.status === 'draft' && (
                <button
                  type="button"
                  disabled={sign.isPending || !date}
                  onClick={() => sign.mutate()}
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
                >
                  {t('Imzolandi')}
                </button>
              )}
              <div>
                <label htmlFor="contract-reason" className="mb-1 block text-xs text-slate-600">
                  {t('Bekor qilish sababi')}
                </label>
                <input
                  id="contract-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <button
                type="button"
                disabled={terminate.isPending || !date}
                onClick={() => terminate.mutate()}
                className="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
              >
                {t('Bekor qilish')}
              </button>
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}
