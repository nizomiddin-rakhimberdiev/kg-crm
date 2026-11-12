/**
 * «Toʻlangan» — pul QAYSI qopdan chiqishini soʻraydigan oyna (ADR-29).
 *
 * Nega kerak boʻldi. Jonli bogʻchada mudira 12 000 000 soʻmlik oylikni
 * "toʻlangan" deb belgiladi. Tizim hech narsa soʻramay naqd kassa va
 * bank hisobidan pulni yechdi — kassada esa 6 mln ham yoʻq edi, va
 * boshqaruv panelida qoldiq −6 752 500 boʻlib chiqdi. Ikkita xato
 * bitta tugmada edi: foydalanuvchi QOPNI tanlamadi va qopda pul
 * yetishi TEKSHIRILMADI.
 *
 * Shuning uchun bu oyna uchta narsani koʻrsatadi: har bir xodimning
 * qaysi qopdan qancha olishi, har bir qopdan jami qancha chiqishi va
 * oʻsha qopda hozir qancha pul borligi. Yetmasa — tasdiqlash katagi;
 * yozuv baribir mumkin, lekin koʻrib turib.
 */

import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Lock } from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { Modal } from '@/components/ui/Modal'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { cashApi } from '@/features/cash/api'
import { payrollApi, type PayoutLine, type PlannedPayout } from '@/features/payroll/api'
import { money, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Select } from '@/components/ui/Select'

const PART_LABEL: Record<string, string> = {
  official: t('rasmiy'),
  cash: t('naqd'),
}

export function PayoutModal({
  runId,
  period,
  periodStart,
  saving,
  onClose,
  onConfirm,
}: {
  runId: string
  period: string
  /** Davr boshi `yyyy-mm-dd` — undan oldin toʻlov boʻlishi mumkin emas. */
  periodStart: string
  saving: boolean
  onClose: () => void
  onConfirm: (payload: {
    payouts: PayoutLine[]
    allow_negative: boolean
    /** Pul QAYSI kuni chiqqani (audit, 2026-10-30). */
    paid_on: string
  }) => void
}) {
  const organizationId = useOrganizationId()
  const [rows, setRows] = useState<PlannedPayout[]>([])
  const [confirmed, setConfirmed] = useState(false)
  // Toʻlov sanasi — tugma bosilgan kun EMAS (audit, 2026-10-30).
  // Sentabr oyligi 5-oktabrda berilgan boʻlsa, pul oʻsha kuni
  // chiqqan: kassa usulidagi hisobot buni shunday koʻrsatishi kerak.
  const [paidOn, setPaidOn] = useState(today())

  const planned = useQuery({
    queryKey: ['org', organizationId, 'payroll', 'planned-payouts', runId],
    queryFn: () => payrollApi.plannedPayouts(runId),
  })
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash-accounts'],
    queryFn: () => cashApi.accounts(),
  })
  const balances = useQuery({
    queryKey: ['org', organizationId, 'cash-balances'],
    queryFn: () => cashApi.balances(),
  })

  useEffect(() => {
    if (planned.data) setRows(planned.data)
  }, [planned.data])

  /** Qop → shu qopdan chiqadigan jami va undagi qoldiq. */
  const perAccount = useMemo(() => {
    const out = new Map<string, { name: string; outgoing: number; balance: number }>()
    for (const row of rows) {
      const current = out.get(row.cash_account_id)
      const name =
        accounts.data?.items.find((a) => a.id === row.cash_account_id)?.name ??
        row.cash_account_name
      const balance = Number(
        balances.data?.find((b) => b.id === row.cash_account_id)?.balance ?? '0',
      )
      out.set(row.cash_account_id, {
        name,
        balance,
        outgoing: (current?.outgoing ?? 0) + Number(row.amount),
      })
    }
    return [...out.values()]
  }, [rows, accounts.data, balances.data])

  const short = perAccount.filter((a) => a.outgoing > a.balance)
  const total = rows.reduce((sum, row) => sum + Number(row.amount), 0)
  const blocked = short.length > 0 && !confirmed

  return (
    <Modal open onClose={onClose} className="max-w-2xl">
      <div className="p-5 sm:p-6">
        <div className="pr-8">
          <h2 className="text-base font-semibold text-slate-900">
            {t('{period} — toʻlash', { period })}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Pul qaysi qopdan chiqishini tekshiring — yozuv shundan keyin qaytmaydi.')}
          </p>
        </div>

        {planned.isPending && (
          <p className="py-8 text-center text-sm text-slate-500">{t('Yuklanmoqda…')}</p>
        )}

        {rows.length > 0 && (
          <>
            <ul className="mt-4 divide-y divide-slate-100 rounded-xl border border-slate-200">
              {rows.map((row, index) => (
                <li
                  key={`${row.payroll_item_id}-${row.part}`}
                  className="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{row.employee}</p>
                    <p className="text-xs text-slate-500">
                      {PART_LABEL[row.part] ?? row.part}
                      <span className="num ml-1.5 font-semibold text-slate-700">
                        {money(row.amount)}
                      </span>
                    </p>
                  </div>
                  <label className="sm:w-56">
                    <span className="sr-only">{t('Qaysi hisobdan')}</span>
                    <Select
                      value={row.cash_account_id}
                      onChange={(event) =>
                        setRows((prev) =>
                          prev.map((item, i) =>
                            i === index ? { ...item, cash_account_id: event.target.value } : item,
                          ),
                        )
                      }
                      className="w-full"
                    >
                      {accounts.data?.items.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name}
                        </option>
                      ))}
                    </Select>
                  </label>
                </li>
              ))}
            </ul>

            {/* Qoplar kesimi: qancha chiqadi va qancha bor. */}
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              {perAccount.map((account) => {
                const enough = account.outgoing <= account.balance
                return (
                  <li
                    key={account.name}
                    className={cn(
                      'rounded-xl border px-3 py-2 text-sm',
                      enough ? 'border-slate-200' : 'border-orik-300 bg-orik-50',
                    )}
                  >
                    <p className="font-medium text-slate-800">{account.name}</p>
                    <p className="num text-xs text-slate-600">
                      {t('chiqadi {out} · qoldiq {left}', {
                        out: money(account.outgoing),
                        left: money(account.balance),
                      })}
                    </p>
                    {/* Qancha yetmaydi — "manfiyga tushadi" o'rniga raqam (H2). */}
                    {!enough && (
                      <p className="num text-xs font-semibold text-orik-900">
                        {t('yetmaydi {sum}', {
                          sum: money(account.outgoing - account.balance),
                        })}
                      </p>
                    )}
                  </li>
                )
              })}
            </ul>

            <p className="num mt-3 text-sm font-semibold text-slate-900">
              {t('Jami: {money} soʻm', { money: money(total) })}
            </p>

            {short.length > 0 && (
              <div className="mt-3 rounded-xl border border-orik-300 bg-orik-50 px-3 py-2.5">
                <p className="flex items-start gap-2 text-sm font-medium text-orik-900">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  {t('Hisobda pul yetmaydi — qoldiq manfiyga tushadi.')}
                </p>
                <p className="mt-1 text-xs text-orik-900">
                  {t(
                    'Kassaga tushmagan pul boʻlsa, avval «Kassa» boʻlimida oʻsha qoldiqni kiriting.',
                  )}
                </p>
                <label className="mt-2 flex items-start gap-2 text-sm text-orik-900">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(event) => setConfirmed(event.target.checked)}
                    className="mt-0.5 h-5 w-5 shrink-0 accent-orik-600"
                  />
                  <span>{t('Bilaman, baribir yozilsin')}</span>
                </label>
              </div>
            )}
          </>
        )}

        <div className="mt-4 max-w-xs">
          <label htmlFor="payout-date" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Qaysi kuni toʻlandi')} <span className="text-red-500">*</span>
          </label>
          <DateInput
            id="payout-date"
            required
            min={periodStart}
            max={today()}
            value={paidOn}
            onChange={setPaidOn}
          />
          <p className="mt-1 text-xs text-slate-500">{t('Pul shu sana bilan kassadan chiqadi.')}</p>
        </div>

        <div className="sticky bottom-0 -mx-5 -mb-5 mt-5 flex flex-col-reverse gap-2 border-t border-slate-100 bg-white px-5 py-3 sm:-mx-6 sm:-mb-6 sm:flex-row sm:justify-end sm:px-6">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="button"
            disabled={saving || blocked || rows.length === 0}
            onClick={() =>
              onConfirm({
                payouts: rows.map((row) => ({
                  payroll_item_id: row.payroll_item_id,
                  part: row.part,
                  amount: row.amount,
                  cash_account_id: row.cash_account_id,
                })),
                allow_negative: confirmed,
                paid_on: paidOn,
              })
            }
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-nihol-600 px-4 py-2 text-sm font-semibold text-white hover:bg-nihol-700 disabled:opacity-60"
          >
            <Lock className="h-4 w-4" />
            {saving ? t('Saqlanmoqda…') : t('Toʻlangan deb belgilash')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
