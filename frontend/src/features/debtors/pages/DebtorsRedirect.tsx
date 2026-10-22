import { Navigate, useSearchParams } from 'react-router-dom'

/**
 * `/debtors` → `/payments?tab=debtors`, soʻrov satri bilan.
 *
 * Sahifa Toʻlovlar ichiga koʻchdi, lekin eski manzil tirik: u
 * bazadagi insight yozuvlarida (`deep_link`) va xodimlarning
 * xatcho'plarida qolgan.
 */
export function DebtorsRedirect() {
  const [params] = useSearchParams()
  const query = params.toString()
  return <Navigate replace to={`/payments?tab=debtors${query ? `&${query}` : ''}`} />
}
