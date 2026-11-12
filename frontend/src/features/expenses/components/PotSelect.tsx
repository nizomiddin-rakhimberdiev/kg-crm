/**
 * "Qaysi puldan" — qop tanlash, har birining qoldigʻi bilan (mijoz soʻrovi, 2026-10-14).
 *
 * Sukut YOʻQ, ataylab. Ilgari birinchi qator "Naqd kassa (sukut)" edi va
 * bankdan toʻlangan chiqim jimgina kassadan yozilardi — adashish hech
 * qayerda koʻrinmasdi. Endi tanlanmaguncha forma yuborilmaydi; backend ham
 * yaratishda qopni talab qiladi.
 *
 * Qoldiq tanlov yonida turadi (ADR-29): odam "bankda pul yoʻq" degan
 * xabarni yuborgandan keyin emas, tanlayotgan paytda koʻradi.
 */

import type { Pot } from '@/features/expenses/pots'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

export function PotSelect({
  id,
  pots,
  value,
  onChange,
}: {
  id: string
  pots: Pot[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <Select
      id={id}
      required
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full"
    >
      <option value="" disabled>
        {t('Tanlang…')}
      </option>
      {pots.map((pot) => (
        <option key={pot.id} value={pot.id}>
          {pot.balance === null ? pot.name : `${pot.name} — ${som(pot.balance)}`}
          {/* Qoldiqning qancha qismi hali yo'lda — bankka tushmagan (audit F3). */}
          {pot.balance !== null && pot.inTransit > 0
            ? ` · ${t('yoʻlda {sum}', { sum: som(pot.inTransit) })}`
            : ''}
        </option>
      ))}
    </Select>
  )
}

/** Qopda pul yetmasa — ogohlantirish va ongli "baribir yozilsin" (ADR-29). */
export function ShortfallNotice({
  pot,
  short,
  checked,
  onChange,
}: {
  pot: Pot | undefined
  short: number
  checked: boolean
  onChange: (value: boolean) => void
}) {
  if (!pot || short <= 0) return null
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
      <p>
        {t('«{pot}» da {balance} bor — {short} yetmaydi.', {
          pot: pot.name,
          balance: som(pot.balance ?? 0),
          short: som(short),
        })}
      </p>
      <label className="mt-1.5 flex items-center gap-2 font-medium">
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="h-4 w-4 rounded border-amber-300 focus-visible:ring-2 focus-visible:ring-amber-500"
        />
        {t('Baribir yozilsin — qoldiq manfiy boʻladi')}
      </label>
    </div>
  )
}
