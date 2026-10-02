/**
 * Tanlangan filial — kichik global mijoz holati (docs/05 §10).
 *
 * Faqat **Org Owner** uchun ma'noga ega: u tashkilotning barcha filiallarini
 * ko'radi va ro'yxatlarni bittasiga toraytirishi mumkin. Qolgan rollar o'z
 * filialiga backend'da bog'langan, shuning uchun ularda tanlov ko'rsatilmaydi.
 *
 * Bu xavfsizlik emas, qulaylik: tanlov `?branch=` parametri sifatida
 * yuboriladi va backend uni allaqachon tashkilot bilan cheklangan queryset
 * ustiga qo'llaydi. Begona filial ID'si bo'sh natija beradi, xato emas.
 */

import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

interface BranchContextValue {
  /** `null` = barcha filiallar. */
  selectedBranchId: string | null
  setSelectedBranchId: (id: string | null) => void
}

const BranchContext = createContext<BranchContextValue | null>(null)

export function BranchProvider({ children }: { children: ReactNode }) {
  const [selectedBranchId, setSelectedBranchId] = useState<string | null>(null)

  const value = useMemo(() => ({ selectedBranchId, setSelectedBranchId }), [selectedBranchId])

  return <BranchContext.Provider value={value}>{children}</BranchContext.Provider>
}

export function useBranchScope(): BranchContextValue {
  const context = useContext(BranchContext)
  if (!context) throw new Error('useBranchScope() <BranchProvider> ichida chaqirilishi kerak')
  return context
}
