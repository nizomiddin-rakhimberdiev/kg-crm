import { useCallback, useState } from 'react'

/**
 * Server sahifalashi uchun sahifa raqami — filtrlarga BOG'LANGAN.
 *
 * `filterKey` (qidiruv, holat, filial, sahifa hajmi…) o'zgarsa sahifa
 * o'zi 1 ga qaytadi — `useEffect` bilan emas, hosila sifatida. Effekt
 * bir render kechikadi va o'sha oraliqda "3-sahifa + yangi filtr" so'rovi
 * ketardi: 5 natijali qidiruvning 3-sahifasi yo'q, ya'ni `404` va bo'sh
 * jadval lipillashi.
 */
export function usePageState(filterKey: string): [number, (page: number) => void] {
  const [state, setState] = useState({ key: filterKey, page: 1 })
  const page = state.key === filterKey ? state.page : 1
  const setPage = useCallback((next: number) => setState({ key: filterKey, page: next }), [filterKey])
  return [page, setPage]
}
