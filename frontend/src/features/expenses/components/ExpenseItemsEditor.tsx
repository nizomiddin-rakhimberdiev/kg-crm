/**
 * Chiqim qatorlari (PLAN 7.5).
 *
 * Mijozning so'zi: "bozorlik — 600 000" yetarli emas. Nima olingani,
 * qancha va qanchadan olingani kerak: *kartoshka, 50 kg, 3 000 →
 * 150 000*. Shuning uchun summa qo'lda yozilmaydi — u qatorlardan
 * yig'iladi va pastda ko'rinib turadi.
 *
 * Jami SERVERDA ham qayta hisoblanadi: bu yerdagi raqam faqat
 * ko'rsatish uchun, kassadan chiqadigan pul esa backend hisobidan
 * (aks holda ikkalasi bir kun ajralib qolardi).
 */

import { Plus, X } from 'lucide-react'
import type { ExpenseItemInput } from '@/features/expenses/api'
import { som } from '@/lib/format'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

/** Bog'cha amalda ishlatadigan o'lchovlar. */
export const UNITS = ['kg', 'dona', 'l', 'quti', 'bogʻlam'] as const

// Miqdor sukut bo'yicha 1 (mijoz so'rovi, 2026-10-14): ko'p chiqim
// bitta narsa — "kraska", "konditsioner ta'miri" — va bo'sh miqdor
// qatorni nol so'mlik qilib, "Qo'shish" ni o'chirib qo'yardi.
export const EMPTY_ITEM: ExpenseItemInput = {
  name: '',
  quantity: '1',
  unit: 'kg',
  unit_price: '',
  note: '',
}

/** Bitta qator summasi; to'ldirilmagan qator nolga teng. */
export function lineTotal(item: ExpenseItemInput): number {
  const quantity = Number(item.quantity.replace(',', '.')) || 0
  const price = Number(item.unit_price.replace(',', '.')) || 0
  return quantity * price
}

export function itemsTotal(items: ExpenseItemInput[]): number {
  return items.reduce((sum, item) => sum + lineTotal(item), 0)
}

/** Serverga yuboriladigan qatorlar — to'ldirilmaganlari tashlanadi. */
export function usableItems(items: ExpenseItemInput[]): ExpenseItemInput[] {
  return items.filter((item) => item.name.trim() && lineTotal(item) > 0)
}

const field =
  'w-full rounded-lg border border-slate-200 px-2.5 py-2 text-sm outline-none focus:border-brand-500'

export function ExpenseItemsEditor({
  items,
  onChange,
}: {
  items: ExpenseItemInput[]
  onChange: (items: ExpenseItemInput[]) => void
}) {
  const patch = (index: number, change: Partial<ExpenseItemInput>) =>
    onChange(items.map((item, i) => (i === index ? { ...item, ...change } : item)))

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-slate-600">{t('Nima olindi')}</p>

      {items.map((item, index) => (
        <div key={index} className="grid gap-2 sm:grid-cols-[1.4fr_0.7fr_0.6fr_1fr_1.2fr_auto]">
          <input
            aria-label={t('Nomi')}
            placeholder={t('Masalan: kartoshka')}
            value={item.name}
            onChange={(e) => patch(index, { name: e.target.value })}
            className={field}
          />
          <input
            aria-label={t('Miqdori')}
            inputMode="decimal"
            placeholder="50"
            value={item.quantity}
            onChange={(e) => patch(index, { quantity: e.target.value.replace(/[^\d.,]/g, '') })}
            className={cn(field, 'text-right')}
          />
          <Select
            aria-label={t('Oʻlchov')}
            value={item.unit}
            onChange={(e) => patch(index, { unit: e.target.value })}
            className="mt-1"
          >
            {UNITS.map((unit) => (
              <option key={unit} value={unit}>
                {unit}
              </option>
            ))}
          </Select>
          <input
            aria-label={t('Birlik narxi')}
            inputMode="decimal"
            placeholder="3000"
            value={item.unit_price}
            onChange={(e) => patch(index, { unit_price: e.target.value.replace(/[^\d.,]/g, '') })}
            className={cn(field, 'text-right')}
          />
          <input
            aria-label={t('Izoh')}
            placeholder={t('Izoh (ixtiyoriy)')}
            value={item.note ?? ''}
            onChange={(e) => patch(index, { note: e.target.value })}
            className={field}
          />
          <div className="flex items-center justify-between gap-2 sm:justify-end">
            {/* Qator summasi yonida turadi: "50 × 3000 qancha bo'ladi?"
                degan savol hisob-kitobsiz javob topsin. */}
            <span className="num text-sm font-semibold text-slate-700">
              {lineTotal(item) > 0 ? som(lineTotal(item)) : '—'}
            </span>
            {items.length > 1 && (
              <button
                type="button"
                aria-label={t('Qatorni oʻchirish')}
                title={t('Qatorni oʻchirish')}
                onClick={() => onChange(items.filter((_, i) => i !== index))}
                className="rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      ))}

      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={() => onChange([...items, { ...EMPTY_ITEM }])}
          className="flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline"
        >
          <Plus className="h-4 w-4" />
          {t('Yana qoʻshish')}
        </button>
        <p className="text-sm text-slate-600">
          {t('Jami')}{' '}
          <span className="num text-base font-bold text-slate-900">{som(itemsTotal(items))}</span>
        </p>
      </div>
    </div>
  )
}
