# 05 — Frontend Architecture

| | |
|---|---|
| **Project** | Kindergarten Management System (KG-CRM) |
| **Document** | Frontend Architecture & Build Spec v1.0 |
| **Stack** | React · TypeScript · Vite · Tailwind · Shadcn/UI · TanStack Query · React Hook Form · Zod · React Router · Axios · Recharts · Framer Motion |
| **Related** | [01_Project_Vision](./01_Project_Vision.md) · [02_Software_Architecture](./02_Software_Architecture.md) · [03_Database_Design](./03_Database_Design.md) · [04_Backend_API_Specification](./04_Backend_API_Specification.md) |

> This is the **authoritative frontend implementation reference**. It expands [02_Software_Architecture](./02_Software_Architecture.md) §7–8, §14–15 with the concrete folder layout, routing map, data-fetching patterns, and conventions every frontend developer follows. If this and §14–15 of doc 02 ever diverge, **this document wins** for frontend detail; a real architectural change is recorded in [02 §2](./02_Software_Architecture.md).

---

## Table of Contents
1. [Principles](#1-principles)
2. [Folder Structure](#2-folder-structure)
3. [Feature Anatomy](#3-feature-anatomy)
4. [Routing Architecture](#4-routing-architecture)
5. [Layouts](#5-layouts)
6. [Route Table](#6-route-table)
7. [Authentication in the UI](#7-authentication-in-the-ui)
8. [Authorization in the UI (RBAC)](#8-authorization-in-the-ui-rbac)
9. [API Layer (Axios)](#9-api-layer-axios)
10. [State Management](#10-state-management)
11. [Data Fetching with TanStack Query](#11-data-fetching-with-tanstack-query)
12. [Forms & Validation](#12-forms--validation)
13. [UI System (Tailwind + Shadcn)](#13-ui-system-tailwind--shadcn)
14. [Loading / Error / Empty States](#14-loading--error--empty-states)
15. [Performance](#15-performance)
16. [Conventions](#16-conventions)

---

## 1. Principles

| # | Principle | Consequence |
|---|-----------|-------------|
| F1 | **Feature-based, not type-based** | Code grouped by business module; adding a module = adding a folder. |
| F2 | **Server state ≠ client state** | TanStack Query owns server data; Context holds a tiny global slice; local state stays local. |
| F3 | **The API contract is typed** | Zod schemas + TS types mirror [04_Backend_API_Specification](./04_Backend_API_Specification.md); no `any`. |
| F4 | **Backend is the security authority** | The UI *hides* what the user can't do; it never *relies* on hiding for security. |
| F5 | **Consistency over novelty** | Every feature uses the same anatomy, same query-key shape, same form pattern. |
| F6 | **One HTTP entry point** | A single Axios client owns auth headers, token refresh, and error normalization. |

---

## 2. Folder Structure

```
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── App.tsx                 # Root component
│   │   ├── router.tsx              # Route tree (public / protected / role-based)
│   │   └── providers/
│   │       ├── AppProviders.tsx    # Composes all providers in order
│   │       ├── AuthProvider.tsx    # Auth context (user, permissions, branch)
│   │       ├── QueryProvider.tsx   # TanStack QueryClientProvider
│   │       └── ThemeProvider.tsx   # Light/dark, direction
│   │
│   ├── components/                 # Shared, feature-agnostic UI
│   │   ├── ui/                     # Shadcn primitives (button, dialog, input, table…)
│   │   ├── layout/                 # AppLayout, Sidebar, Topbar, PageHeader
│   │   ├── data-display/           # DataTable, StatCard, ChartCard
│   │   └── feedback/               # Spinner, EmptyState, ErrorBoundary, ConfirmDialog
│   │
│   ├── features/                   # ONE folder per module (mirrors backend apps)
│   │   ├── dashboard/
│   │   ├── children/
│   │   ├── payments/
│   │   ├── debtors/
│   │   ├── attendance/
│   │   ├── payroll/
│   │   ├── inventory/
│   │   ├── expenses/
│   │   ├── reports/
│   │   ├── notifications/
│   │   ├── settings/
│   │   ├── branches/               # Branch CRUD + switcher
│   │   ├── billing/                # Subscription, usage, projected bill, invoices
│   │   ├── onboarding/             # Signup, first-branch setup, children import wizard
│   │   └── users/
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts           # Axios instance + interceptors
│   │   │   ├── queryClient.ts      # QueryClient config (retries, staleTime)
│   │   │   └── queryKeys.ts        # Central query-key factory
│   │   ├── auth/
│   │   │   ├── tokenStorage.ts     # access (memory) / refresh handling
│   │   │   └── useAuth.ts          # Auth context hook
│   │   ├── rbac/
│   │   │   ├── permissions.ts      # Permission constants
│   │   │   └── useCan.ts           # Permission-check hook
│   │   ├── utils/                  # cn(), formatCurrency, formatDate, etc.
│   │   └── validation/             # Shared Zod helpers
│   │
│   ├── hooks/                      # Global hooks (useDebounce, useMediaQuery, usePagination)
│   ├── config/
│   │   ├── env.ts                  # Typed env access
│   │   ├── routes.ts               # Route path constants
│   │   └── navigation.ts           # Sidebar items + required permission
│   ├── types/
│   │   ├── api.ts                  # ApiResponse<T>, Paginated<T>, ApiError
│   │   └── common.ts
│   ├── styles/
│   │   └── globals.css             # Tailwind layers + design tokens
│   └── main.tsx
│
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── .env.example
└── package.json
```

Rationale for each folder is in [02_Software_Architecture](./02_Software_Architecture.md) §8.

---

## 3. Feature Anatomy

Every folder in `features/` follows the **same** internal shape. Example — `features/payments/`:

```
features/payments/
├── api/
│   ├── usePayments.ts          # useQuery list
│   ├── usePayment.ts           # useQuery detail
│   ├── useCreatePayment.ts     # useMutation
│   └── useReversePayment.ts    # useMutation
├── components/
│   ├── PaymentTable.tsx
│   ├── PaymentForm.tsx
│   ├── PaymentFilters.tsx
│   └── ReceiptButton.tsx
├── pages/
│   ├── PaymentsListPage.tsx
│   └── PaymentDetailPage.tsx
├── schemas/
│   └── payment.schema.ts       # Zod: request + response, inferred types
├── types/
│   └── payment.types.ts
├── hooks/                      # feature-local hooks (optional)
└── index.ts                    # public exports (the feature's contract)
```

**Rules:**
- Pages **orchestrate** (fetch via `api/` hooks, render components, handle mutations). No business logic in components.
- Cross-feature imports go through the target feature's `index.ts` barrel only — never deep-import internals.
- Data fetching lives **only** in `api/`; components receive data via props or call feature hooks.

---

## 4. Routing Architecture

React Router with nested layouts and three route categories.

```mermaid
graph TD
    ROOT[AppProviders<br/>Query + Auth + Theme]
    ROOT --> PUB[PublicLayout]
    ROOT --> PROT[ProtectedRoute<br/>valid session?]

    PUB --> LOGIN[/login/]
    PUB --> FORGOT[/forgot-password/]

    PROT --> APP[AppLayout<br/>Sidebar + Topbar]
    APP --> ROLE[RoleRoute<br/>has permission?]

    ROLE --> DASH[/dashboard]
    ROLE --> CH[/children/*]
    ROLE --> PAY[/payments/*]
    ROLE --> DEBT[/debtors]
    ROLE --> ATT[/attendance]
    ROLE --> PR[/payroll/*]
    ROLE --> INV[/inventory/*]
    ROLE --> EXP[/expenses]
    ROLE --> REP[/reports/*]
    ROLE --> NOT[/notifications]
    ROLE --> SET[/settings]
    ROLE --> USR[/users/*]

    APP --> NA[/not-authorized]
    ROOT --> NF[/404]
```

**Route guard components:**
| Guard | Behavior |
|-------|----------|
| `ProtectedRoute` | No valid session → redirect `/login` (remember intended URL). |
| `RoleRoute permission="x.read"` | Session valid but permission missing → redirect `/not-authorized`. |
| `PublicOnlyRoute` | Already authenticated → redirect `/dashboard` (used on `/login`). |

---

## 5. Layouts

| Layout | Used by | Contains |
|--------|---------|----------|
| **PublicLayout** | login, forgot-password | Centered card, branding, no nav. |
| **AppLayout** | all authenticated pages | Persistent **Sidebar** (nav filtered by permissions), **Topbar** (user menu, **branch selector** — Org Owner sees all their branches, notifications bell, theme toggle), a **trial/read-only banner** when the subscription requires one, and `<Outlet/>` content area. |

Navigation items come from `config/navigation.ts`, each tagged with the permission required to show it — the sidebar renders only what the user can access (driven by `useCan`).

---

## 6. Route Table

Path constants live in `config/routes.ts`. Each route maps to a feature page and a required permission (mirrors [04](./04_Backend_API_Specification.md) permissions).

| Path | Page | Guard / Permission |
|------|------|--------------------|
| `/login` | LoginPage | PublicOnly |
| `/forgot-password` | ForgotPasswordPage | PublicOnly |
| `/dashboard` | DashboardPage | `dashboard.read` |
| `/children` | ChildrenListPage | `children.read` |
| `/children/new` | ChildCreatePage | `children.create` |
| `/children/:id` | ChildDetailPage | `children.read` |
| `/children/:id/edit` | ChildEditPage | `children.update` |
| `/groups` | GroupsPage | `children.read` |
| `/payments` | PaymentsListPage | `payments.read` |
| `/payments/:id` | PaymentDetailPage | `payments.read` |
| `/invoices` | InvoicesPage | `payments.read` |
| `/invoices/:id` | InvoiceDetailPage | `payments.read` |
| `/debtors` | DebtorsPage | `debtors.read` |
| `/attendance` | AttendancePage | `attendance.read` |
| `/payroll` | PayrollRunsPage | `payroll.read` |
| `/payroll/:id` | PayrollRunDetailPage | `payroll.read` |
| `/employees` | EmployeesPage | `payroll.read` |
| `/inventory/products` | ProductsPage | `inventory.read` |
| `/inventory/movements` | StockMovementsPage | `inventory.read` |
| `/inventory/suppliers` | SuppliersPage | `inventory.read` |
| `/expenses` | ExpensesPage | `expenses.read` |
| `/reports` | ReportsPage | `reports.read` |
| `/notifications` | NotificationsPage | `notifications.read` |
| `/settings` | SettingsPage | `settings.read` |
| `/users` | UsersPage | `users.read` |
| `/users/roles` | RolesPage | `users.read` |
| `/audit` | AuditLogPage | `audit.read` |
| `/not-authorized` | NotAuthorizedPage | Protected |
| `*` | NotFoundPage | — |

---

## 7. Authentication in the UI

Follows the JWT flow in [02 §10](./02_Software_Architecture.md).

- **Access token** kept in memory (module variable), never in `localStorage` (XSS safety). **Refresh token** in an httpOnly Secure cookie (preferred) or secure storage.
- On app boot: if a session may exist, call `GET /auth/me` → hydrate `AuthProvider` with `{ user, role, permissions, branch }`. This drives routing and UI gating.
- On login: store tokens, hydrate auth context, redirect to intended URL or `/dashboard`.
- On logout: call `/auth/logout`, clear in-memory token + context, redirect `/login`.

---

## 8. Authorization in the UI (RBAC)

Permissions come from the authenticated user (`/auth/me`). Enforcement in the UI is **UX only** (F4).

- `useCan("payments.create")` → boolean; used to show/hide/disable buttons and menu items.
- `<RoleRoute permission="payments.read">` guards whole routes.
- Sidebar items in `config/navigation.ts` each declare their permission; hidden if not granted.

```
// usage sketch (illustrative, not implementation)
const canCreate = useCan("payments.create");
{canCreate && <Button>Record payment</Button>}
```

> The backend re-checks every permission on every request; the UI simply avoids showing impossible actions.

---

## 9. API Layer (Axios)

One Axios instance in `lib/api/client.ts` is the single HTTP entry point.

| Concern | Handled by |
|---------|-----------|
| Base URL & headers | Instance config (`/api/v1`, JSON). |
| Attach access token | **Request interceptor** adds `Authorization: Bearer`. |
| Token refresh | **Response interceptor**: on `401`, call `/auth/refresh` **once**, queue concurrent failures, retry after refresh; on refresh failure → force logout. |
| Error normalization | Interceptor maps the API error envelope ([04 §2](./04_Backend_API_Specification.md)) into a typed `ApiError { code, message, details }` so callers/toasts handle one shape. |
| Idempotency | Money mutations attach an `Idempotency-Key` header. |

Typed helpers return `ApiResponse<T>` / `Paginated<T>` (in `types/api.ts`).

---

## 10. State Management

Decision tree (F2) — matches [02 §15](./02_Software_Architecture.md):

| State kind | Tool | Examples |
|-----------|------|----------|
| **Server data** | **TanStack Query** (default) | children, invoices, dashboard KPIs, any API data |
| **Global client** | **React Context** (thin) | authenticated user + permissions, **current organization**, current branch, **subscription read-only flag**, theme |
| **Local UI** | `useState` / `useReducer` | modal open, selected rows, tab, filter draft |
| **Forms** | **React Hook Form + Zod** | every create/edit form |

**No Redux.** Never copy server data into Context. If a genuinely complex *client* state machine appears later (multi-step wizard), use Zustand **locally**, not globally.

### Tenancy and the query cache

The organization is **never** a request parameter — the backend derives it from the JWT ([04 §1](./04_Backend_API_Specification.md)). But it **must** be part of every query key:

```ts
// queryKeys.ts — organization first, always
children: (orgId: string, filters: Filters) => ['org', orgId, 'children', filters] as const
```

> **Why, when the client never sends it:** a user who switches organization (or logs out and another user logs in on a shared front-desk machine) would otherwise see the previous tenant's cached rows rendered from memory. The server would never have sent them — the leak is entirely client-side, and it looks exactly like a real breach to the person seeing it. Scoping the cache key makes it structurally impossible; clearing the cache on organization switch is the belt to that braces.

### Read-only mode

When `/auth/me` reports a `suspended` subscription, the app enters a global **read-only mode**: a persistent banner explains why, and all mutating controls are disabled. Writes would fail with `402` anyway ([04 §2](./04_Backend_API_Specification.md)); disabling them client-side is UX, not enforcement. Reads keep working — a customer behind on payment must still be able to see their own financial history.

---

## 11. Data Fetching with TanStack Query

**Query-key factory** (`lib/api/queryKeys.ts`) — structured, feature-prefixed keys so invalidation is precise:

```
queryKeys.payments.list(filters)   // ['payments', 'list', filters]
queryKeys.payments.detail(id)      // ['payments', 'detail', id]
queryKeys.children.list(filters)   // ['children', 'list', filters]
```

**Conventions:**
- One `useQuery` hook per read, one `useMutation` per write, all in the feature's `api/`.
- Mutations **invalidate** the relevant keys on success (e.g. recording a payment invalidates `payments.list`, `debtors.list`, `children.detail(childId)`, and `dashboard`).
- `staleTime` tuned per data volatility: reference data (tariffs, categories) long; dashboard/debtors short.
- **Optimistic updates** for fast toggles (attendance status) with rollback on error.
- Loading/error come from the query, not manual flags.

---

## 12. Forms & Validation

**React Hook Form + Zod** everywhere. The Zod schema is the single contract — it validates input **and** infers the TypeScript type, and mirrors backend validation from [04](./04_Backend_API_Specification.md).

```
// features/payments/schemas/payment.schema.ts (illustrative)
paymentCreateSchema = z.object({
  amount: z.coerce.number().positive(),
  method: z.enum(['cash','card','bank_transfer','online']),
  reference: z.string().max(100).nullable().optional(),
});
type PaymentCreateInput = z.infer<typeof paymentCreateSchema>;
```

**Conventions:**
- Field-level errors from `400 VALIDATION_ERROR.details` are mapped back onto the form fields (server truth wins).
- Submit disabled while pending; success → toast + query invalidation + navigate/close.
- Shared inputs (currency, date, select-from-API) live in `components/ui` / `components/data-display`.

---

## 13. UI System (Tailwind + Shadcn)

- **Shadcn/UI** primitives are copied into `components/ui/` — we own and theme them (no black-box dependency).
- **Tailwind** utility-first; design tokens (colors, spacing, radius) defined once in `tailwind.config.ts` + `styles/globals.css`. Light/dark via `ThemeProvider`.
- **Recharts** for dashboards/reports, wrapped in `components/data-display/ChartCard` for consistent styling. (See the `dataviz` guidance when building charts.)
- **Framer Motion** for page/section transitions and subtle interactions — never blocking or gratuitous.
- **Localization-ready:** all UI strings via a central dictionary (Uzbek/Russian), dates/currency via `lib/utils` formatters honoring branch locale ([01 §7](./01_Project_Vision.md)).

---

## 14. Loading / Error / Empty States

Enterprise polish = consistent states everywhere. Provided by `components/feedback/`:

| State | Component | Rule |
|-------|-----------|------|
| Loading | `Spinner` / skeleton rows | Every async surface shows a skeleton, not a blank screen. |
| Error | `ErrorBoundary` + inline error card | Show the API `message`; offer retry. |
| Empty | `EmptyState` | Friendly copy + primary action (e.g. "No payments yet — record one"). |
| Destructive action | `ConfirmDialog` | Reversals, deletes, finalize/mark-paid require confirmation. |

---

## 15. Performance

Matches [02 §21](./02_Software_Architecture.md):

| Technique | Where |
|-----------|-------|
| **Route-based code splitting** | `React.lazy` + Suspense per feature → small initial bundle. |
| **Query caching / background refetch** | TanStack Query removes redundant calls. |
| **List virtualization** | Large tables (children, attendance) render only visible rows. |
| **Debounced search** | Search inputs debounce before hitting the API. |
| **Memoization** | `useMemo`/`React.memo` on heavy renders. |
| **Lazy images / charts** | Photos and report charts load on demand. |
| **Production build** | Vite tree-shaking + minification; Nginx gzip/brotli + static caching. |

---

## 16. Conventions

| Area | Convention |
|------|-----------|
| Components | `PascalCase.tsx`; one component per file. |
| Hooks | `useThing.ts`, return typed values. |
| Feature imports | Only via the feature's `index.ts` barrel. |
| Query keys | Array form via `queryKeys` factory; never inline strings. **Always organization-scoped** (§10). |
| Zod schemas | `<entity>.schema.ts`; export schema + inferred type. |
| Types | No `any`; API types derive from Zod or `types/api.ts`. |
| Styling | Tailwind classes via `cn()` helper; no inline styles except dynamic values. |
| Strings | Through the i18n dictionary; no hardcoded UI text. |
| Env | Access only through `config/env.ts` (typed). |
| Linting | ESLint + Prettier enforced in CI ([06](./06_Development_Roadmap.md)). |

---

## Cross-References
- What the UI is for: [01_Project_Vision](./01_Project_Vision.md); commercial model the `billing` feature surfaces: [01 §4](./01_Project_Vision.md).
- System-level frontend decisions: [02_Software_Architecture](./02_Software_Architecture.md) §14–15; the two access planes: [02 §11.0](./02_Software_Architecture.md).
- Endpoints, permissions, and payloads consumed here: [04_Backend_API_Specification](./04_Backend_API_Specification.md).
- Build order: [06_Development_Roadmap](./06_Development_Roadmap.md).

*End of Frontend Architecture v1.1 — organization-scoped query cache, read-only mode, `billing`/`branches`/`onboarding` features added.*
