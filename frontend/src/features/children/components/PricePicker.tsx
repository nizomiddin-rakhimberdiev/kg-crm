/**
 * Bolaning oylik narxi — tarif bo'yicha YOKI individual summa.
 *
 * Xususiy bog'chada standart narx bo'lmasligi mumkin: har bir oila bilan
 * alohida kelishiladi. Narx manbai BITTA (backend `ck_child_one_price_source`),
 * shuning uchun ikki rejim — bittasini tanlash ikkinchisini tozalaydi.
 *
 * Holat ko'rinishi: `monthlyFee === null` — tarif rejimi; satr (bo'sh
 * bo'lsa ham) — individual rejim. Bo'sh satr "individual tanlandi, summa
 * hali kiritilmagan" degani; uni yuborishdan oldin `priceToPayload`
 * tekshiradi.
 */

import { cn, formatUZS } from '@/lib/utils'
import { t } from '@/lib/i18n'
import { digitsOnly, type PriceValue } from '../price'

interface TariffOption {
  id: string
  name: string
  amount: string
}

interface PricePickerProps {
  value: PriceValue
  onChange: (value: PriceValue) => void
  tariffs: TariffOption[]
  disabled?: boolean
  idPrefix?: string
}

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50'

export function PricePicker({
  value,
  onChange,
  tariffs,
  disabled,
  idPrefix = 'price',
}: PricePickerProps) {
  const individual = value.monthlyFee !== null
  const preview = individual ? Number(digitsOnly(value.monthlyFee ?? '')) : 0

  const option = (active: boolean) =>
    cn(
      'flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition',
      active ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500 hover:text-slate-800',
    )

  return (
    <div className="space-y-2">
      <div
        role="radiogroup"
        aria-label={t('Narx turi')}
        className="flex rounded-lg border border-slate-200 bg-slate-50 p-1"
      >
        <button
          type="button"
          role="radio"
          aria-checked={!individual}
          disabled={disabled}
          onClick={() => onChange({ tariffId: value.tariffId, monthlyFee: null })}
          className={option(!individual)}
        >
          {t('Tarif boʻyicha')}
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={individual}
          disabled={disabled}
          onClick={() => onChange({ tariffId: null, monthlyFee: value.monthlyFee ?? '' })}
          className={option(individual)}
        >
          {t('Individual narx')}
        </button>
      </div>

      {individual ? (
        <div>
          <div className="relative">
            <input
              id={`${idPrefix}-fee`}
              type="text"
              inputMode="numeric"
              autoComplete="off"
              disabled={disabled}
              placeholder={t('Masalan, 1 200 000')}
              aria-label={t('Oylik narx (soʻm)')}
              value={value.monthlyFee ?? ''}
              onChange={(e) => onChange({ tariffId: null, monthlyFee: digitsOnly(e.target.value) })}
              className={cn(field, 'pr-14 tabular-nums')}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
              {t('soʻm')}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {preview > 0
              ? t('Har oy {v} hisob-faktura chiqariladi.', { v: formatUZS(preview) })
              : t('Shu bola uchun kelishilgan oylik summa — tarifsiz.')}
          </p>
        </div>
      ) : (
        <div>
          <select
            id={`${idPrefix}-tariff`}
            aria-label={t('Tarif')}
            disabled={disabled}
            value={value.tariffId ?? ''}
            onChange={(e) => onChange({ tariffId: e.target.value || null, monthlyFee: null })}
            className={field}
          >
            <option value="">{t('— tarifsiz —')}</option>
            {tariffs.map((tariff) => (
              <option key={tariff.id} value={tariff.id}>
                {tariff.name} — {formatUZS(Number(tariff.amount))}
              </option>
            ))}
          </select>
          {!value.tariffId && (
            <p className="mt-1 text-xs text-amber-700">
              {tariffs.length === 0
                ? t('Tarif yoʻq — individual narxni tanlang yoki avval tarif yarating.')
                : t('Narxsiz bolaga hisob-faktura chiqarilmaydi.')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
