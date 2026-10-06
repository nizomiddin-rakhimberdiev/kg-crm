/**
 * Dashboarddagi pul qoplarini IKKITA guruhga yig'adi (PLAN 7.3).
 *
 * Mijozning so'rovi: "o'tkazma, terminal va Payme/Click bitta «Bank
 * hisobi» bo'lsin". Sababi oddiy — bu uchalasi ham bankdagi pul, va
 * bog'cha egasi uchun savol bitta: naqd qancha, bankda qancha.
 *
 * Bu FAQAT ko'rsatish qarori. `cash_account` jadvalida qoplar
 * avvalgidek to'rtta bo'lib qoladi va har bir harakat o'z qopiga
 * yoziladi (ADR-17) — aks holda kassa jurnali "pul qayerda" degan
 * savolga javob bera olmay qolardi.
 */

import type { CashAccountBalance } from '@/lib/api/types'

export interface CashGroup {
  key: 'cash' | 'bank'
  /** Guruhga kirgan qoplar — izoh sifatida ko'rsatish uchun. */
  parts: string[]
  balance: number
}

/** Naqddan boshqa hamma qop "Bank hisobi" ga yig'iladi. */
export function groupAccounts(accounts: CashAccountBalance[] | undefined): CashGroup[] {
  const groups: Record<'cash' | 'bank', CashGroup> = {
    cash: { key: 'cash', parts: [], balance: 0 },
    bank: { key: 'bank', parts: [], balance: 0 },
  }
  for (const account of accounts ?? []) {
    const key = account.kind === 'cash' ? 'cash' : 'bank'
    groups[key].parts.push(account.name)
    groups[key].balance += Number(account.balance) || 0
  }
  // Qopi yo'q guruh ko'rsatilmaydi: bo'sh "0 so'm" kartochka savol
  // tug'diradi, javob bermaydi.
  return [groups.cash, groups.bank].filter((group) => group.parts.length > 0)
}
