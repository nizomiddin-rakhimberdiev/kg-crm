/**
 * Markazlashgan query-key fabrikasi (docs/05 §10).
 *
 * HAR BIR kalit tashkilotdan boshlanadi. Tashkilot so'rovda uzatilmaydi —
 * uni backend tokendan oladi — lekin u keshda bo'lishi SHART: aks holda
 * tashkilot almashtirilganda (yoki umumiy kompyuterda boshqa xodim
 * kirganda) oldingi tenant'ning qatorlari xotiradan render bo'lardi.
 * Server buni hech qachon yubormagan bo'lardi — sizib chiqish butunlay
 * mijoz tomonida, lekin ko'rgan odam uchun u haqiqiy buzilishdan
 * farq qilmaydi.
 */

export const queryKeys = {
  session: ['session'] as const,

  users: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'users', params ?? {}] as const,
  user: (orgId: string, id: string) => ['org', orgId, 'users', id] as const,

  roles: (orgId: string) => ['org', orgId, 'roles'] as const,
  permissions: (orgId: string) => ['org', orgId, 'permissions'] as const,

  branches: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'branches', params ?? {}] as const,

  children: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'children', params ?? {}] as const,
  groups: (orgId: string) => ['org', orgId, 'groups'] as const,
} as const
