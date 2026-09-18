import { useEffect, useState } from 'react'

/**
 * Qiymatni kechiktirib qaytaradi (docs/05 §15 — debounced search).
 *
 * Qidiruv maydoniga har bir harf yozilganda serverga so'rov ketmasin:
 * 300 bolali ro'yxatda "Abdullayev" so'zi 10 ta so'rov o'rniga bittasini
 * yuboradi. Kirish maydoni o'zi darhol yangilanadi — faqat so'rov kutadi.
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
