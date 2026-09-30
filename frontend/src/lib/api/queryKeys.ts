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
  groupChildren: (orgId: string, groupId: string) =>
    ['org', orgId, 'groups', groupId, 'children'] as const,

  tariffs: (orgId: string) => ['org', orgId, 'tariffs'] as const,
  invoices: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'invoices', params ?? {}] as const,

  payments: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'payments', params ?? {}] as const,
  debtors: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'debtors', params ?? {}] as const,
  statement: (orgId: string, childId: string) =>
    ['org', orgId, 'debtors', 'statement', childId] as const,
  absenceClaims: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'absence-claims', params ?? {}] as const,
  holidays: (orgId: string) => ['org', orgId, 'holidays'] as const,
  cashAccounts: (orgId: string) => ['org', orgId, 'cash', 'accounts'] as const,
  dailyCash: (orgId: string, date: string) => ['org', orgId, 'payments', 'daily', date] as const,

  employees: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'employees', params ?? {}] as const,
  positions: (orgId: string) => ['org', orgId, 'positions'] as const,
  payrollRuns: (orgId: string) => ['org', orgId, 'payroll'] as const,
  // Avanslar ham `payroll` ostida: bitta `invalidate` ikkalasini yangilaydi
  // (avans yozilsa, qoralama hisoblash ham o'zgaradi).
  payrollAdvances: (orgId: string) => ['org', orgId, 'payroll', 'advances'] as const,
  payrollRun: (orgId: string, id: string) => ['org', orgId, 'payroll', id] as const,

  products: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'products', params ?? {}] as const,
  warehouses: (orgId: string) => ['org', orgId, 'warehouses'] as const,
  productCategories: (orgId: string) => ['org', orgId, 'product-categories'] as const,
  suppliers: (orgId: string) => ['org', orgId, 'suppliers'] as const,
  movements: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'movements', params ?? {}] as const,
  expenses: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'expenses', params ?? {}] as const,
  expenseCategories: (orgId: string) => ['org', orgId, 'expense-categories'] as const,

  subscription: (orgId: string) => ['org', orgId, 'billing', 'subscription'] as const,
  billingUsage: (orgId: string) => ['org', orgId, 'billing', 'usage'] as const,
  billingUsageHistory: (orgId: string) => ['org', orgId, 'billing', 'usage-history'] as const,
  billingInvoices: (orgId: string) => ['org', orgId, 'billing', 'invoices'] as const,

  dashboard: (orgId: string) => ['org', orgId, 'dashboard'] as const,
  briefing: (orgId: string) => ['org', orgId, 'insights', 'briefing'] as const,
  insights: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'insights', 'list', params ?? {}] as const,
  childLabels: (orgId: string, ids: string[]) =>
    ['org', orgId, 'children', 'labels', ids.join(',')] as const,
  reportRevenue: (orgId: string, from: string, to: string, groupBy: string) =>
    ['org', orgId, 'reports', 'revenue', from, to, groupBy] as const,
  reportProfitLoss: (orgId: string, from: string, to: string, groupBy: string) =>
    ['org', orgId, 'reports', 'profit-loss', from, to, groupBy] as const,
  reportExports: (orgId: string) => ['org', orgId, 'reports', 'exports'] as const,
  auditLogs: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'audit-logs', params ?? {}] as const,

  platformAccess: (orgId: string) => ['org', orgId, 'audit-logs', 'platform-access'] as const,

  notificationTemplates: (orgId: string) => ['org', orgId, 'notification-templates'] as const,
  notifications: (orgId: string, params?: Record<string, unknown>) =>
    ['org', orgId, 'notifications', params ?? {}] as const,
  settings: (orgId: string) => ['org', orgId, 'settings'] as const,
  organization: (orgId: string) => ['org', orgId, 'organization'] as const,

  attendanceDaily: (orgId: string, groupId: string, date: string) =>
    ['org', orgId, 'attendance', 'daily', groupId, date] as const,
  attendanceSummary: (orgId: string, month: string, groupId: string | null) =>
    ['org', orgId, 'attendance', 'summary', month, groupId ?? 'all'] as const,
} as const
