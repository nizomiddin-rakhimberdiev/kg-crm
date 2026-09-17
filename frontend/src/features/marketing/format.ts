/**
 * Public saytdagi pul formati — bitta joyda.
 *
 * CRM ichidagi `formatUZS()` bu yerga mos emas: u vergul bilan ajratadi
 * va "UZS" qo'shadi ("400,000 UZS") — bu ichki boshqaruv panelining
 * formati. Public sahifadagi matn (content.ts) esa bo'sh joy bilan
 * ajratadi va "so'm"/"сум" so'zini ishlatadi ("400 000 so'm"). Hero,
 * kalkulyator va FAQ bir xil ko'rinishda bo'lishi shart.
 */

import type { Locale } from './content'

const CURRENCY_WORD: Record<Locale, string> = { uz: 'so‘m', ru: 'сум' }

export const groupThousands = (value: number) =>
  Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

export const formatAmount = (value: string | number | undefined, locale: Locale) =>
  value === undefined || value === '' ? '—' : `${groupThousands(Number(value))} ${CURRENCY_WORD[locale]}`
