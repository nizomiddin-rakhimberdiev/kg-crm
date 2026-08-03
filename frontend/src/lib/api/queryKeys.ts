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
  child: (orgId: string, id: string) => ['org', orgId, 'children', 'detail', id] as const,
  groups: (orgId: string) => ['org', orgId, 'groups'] as const,

  tariffs: (orgId: string) => ['org', orgId, 'tariffs'] as const,
  invoices: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'invoices', params ?? {}] as const,

  payments: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'payments', params ?? {}] as const,
  debtors: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'debtors', params ?? {}] as const,
  statement: (orgId: string, childId: string) =>
    ['org', orgId, 'debtors', 'statement', childId] as const,
  dailyCash: (orgId: string, date: string) =>
    ['org', orgId, 'payments', 'daily', date] as const,

  attendanceDaily: (orgId: string, groupId: string, date: string) =>
    ['org', orgId, 'attendance', 'daily', groupId, date] as const,
  attendanceSummary: (orgId: string, month: string, groupId: string | null) =>
    ['org', orgId, 'attendance', 'summary', month, groupId ?? 'all'] as const,
} as const
