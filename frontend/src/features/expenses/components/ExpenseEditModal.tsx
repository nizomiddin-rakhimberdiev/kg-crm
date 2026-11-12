/**
 * Chiqimni tahrirlash (mijoz soʻrovi, 2026-10-14).
 *
 * Chiqim yaratilishi bilan tasdiqlanadi va pul qopdan chiqadi, shuning
 * uchun bu oyna faqat hujjatni emas, pul izini ham oʻzgartiradi: summa,
 * sana yoki qop oʻzgarsa backend eski chiqimga qarshi yozuv va yangisiga
 * chiqim yozadi. Yetmaslik hisobi ham shunga mos — eski summa avval shu
 * qopga qaytadi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { REASON_MIN } from '@/components/ui/ConfirmDialog'
import { Modal } from '@/components/ui/Modal'
import { expensesApi, type ExpenseItemInput } from '@/features/expenses/api'
import {
  EMPTY_ITEM,
  ExpenseItemsEditor,
  itemsTotal,
  usableItems,
} from '@/features/expenses/components/ExpenseItemsEditor'
import { PotSelect, ShortfallNotice } from '@/features/expenses/components/PotSelect'
import { shortfall, usePots } from '@/features/expenses/pots'
import { invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Expense } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { groupCategories } from '@/features/expenses/categoryGroups'
import { Select } from '@/components/ui/Select'

export function ExpenseEditModal({ expense, onClose }: { expense: Expense; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { pots } = usePots()
  const categories = useQuery({
    queryKey: queryKeys.expenseCategories(organizationId),
    queryFn: expensesApi.categories,
  })

  // Qatorsiz eski chiqim — bitta summa; qatorlilari — qatorlar.
  const lined = expense.items.length > 0
  const [items, setItems] = useState<ExpenseItemInput[]>(
    lined
      ? expense.items.map((item) => ({
          name: item.name,
          quantity: item.quantity,
          unit: item.unit,
          unit_price: item.unit_price,
          note: item.note,
        }))
      : [{ ...EMPTY_ITEM }],
  )
  const [amount, setAmount] = useState(expense.amount)
  const [form, setForm] = useState({
    category_id: expense.category,
    expense_date: expense.expense_date,
    description: expense.description,
    cash_account_id: expense.cash_account ?? '',
  })
  const [allowNegative, setAllowNegative] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const total = lined ? itemsTotal(items) : Number(amount || 0)
  // Shu qopdan toʻlangan eski summa avval qaytadi.
  const credit = form.cash_account_id === expense.cash_account ? Number(expense.amount) : 0
  const short = shortfall(pots, form.cash_account_id, total, credit)
  const pot = pots.find((p) => p.id === form.cash_account_id)
  // Pul qayta yoziladigan tahrir — sabab majburiy (backend ham tekshiradi).
  const moneyChanged =
    total !== Number(expense.amount) ||
    form.expense_date !== expense.expense_date ||
    form.cash_account_id !== (expense.cash_account ?? '')
  const reasonMissing = moneyChanged && reason.trim().length < REASON_MIN

  const save = useMutation({
    mutationFn: () =>
      expensesApi.update(expense.id, {
        ...form,
        ...(lined ? { items: usableItems(items) } : { amount: String(amount) }),
        ...(short > 0 ? { allow_negative: allowNegative } : {}),
        ...(moneyChanged ? { reason: reason.trim() } : {}),
      }),
    onSuccess: () => {
      invalidateMoney(queryClient, organizationId)
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
  })

  const field =
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

  return (
    <Modal open onClose={onClose} className="max-w-3xl">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
        className="space-y-4 p-5"
      >
        <h2 className="text-lg font-semibold text-slate-900">{t('Chiqimni tahrirlash')}</h2>

        {error && (
          <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="xcat" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Kategoriya')}
            </label>
            <Select
              id="xcat"
              required
              value={form.category_id}
              onChange={(e) => setForm((p) => ({ ...p, category_id: e.target.value }))}
              className="mt-1"
            >
              {groupCategories(categories.data?.items ?? []).map((group) => (
                <optgroup key={group.label || 'flat'} label={group.label || t('Boshqa')}>
                  {group.items.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </Select>
          </div>
          <div>
            <label htmlFor="xdate" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Sana')}
            </label>
            <DateInput
              id="xdate"
              required
              value={form.expense_date}
              onChange={(iso) => setForm((p) => ({ ...p, expense_date: iso }))}
            />
          </div>
        </div>

        {lined ? (
          <ExpenseItemsEditor items={items} onChange={setItems} />
        ) : (
          <div>
            <label htmlFor="xamt" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Summa')}
            </label>
            <input
              id="xamt"
              type="number"
              min="1"
              step="any"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={field}
            />
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="xdesc" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Tavsif')}
            </label>
            <input
              id="xdesc"
              maxLength={255}
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="xpot" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Qaysi puldan')}
            </label>
            <PotSelect
              id="xpot"
              pots={pots}
              value={form.cash_account_id}
              onChange={(value) => setForm((p) => ({ ...p, cash_account_id: value }))}
            />
          </div>
        </div>

        <ShortfallNotice
          pot={pot}
          short={short}
          checked={allowNegative}
          onChange={setAllowNegative}
        />

        {moneyChanged && (
          <div>
            <label htmlFor="xreason" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Tuzatish sababi')}
            </label>
            <input
              id="xreason"
              maxLength={255}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className={field}
            />
            <p className="mt-1 text-xs text-slate-500">
              {t('Summa, sana yoki hisob oʻzgardi — pul qayta yoziladi. Kamida {n} ta belgi.', {
                n: REASON_MIN,
              })}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={
              save.isPending || total <= 0 || (short > 0 && !allowNegative) || reasonMissing
            }
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
