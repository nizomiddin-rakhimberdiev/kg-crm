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
17. [Internationalization (uz / ru / en)](#17-internationalization-uz--ru--en)
18. [Brand System (Radix Brendbuk 1.1)](#18-brand-system-radix-brendbuk-11)

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

### 4.0 Every kindergarten has its own address

Customer routes live under `/t/<slug>` — `https://kg-crm.uz/t/quyosh/dashboard`. The prefix is applied as the router's `basename`, computed once at page load in `src/lib/tenantAddress.ts`; route definitions stay unprefixed (`/dashboard`, `/children`), so nothing in the feature code knows about it.

Three things follow, and they are the reason for this shape:

- **The address is not the tenant mechanism.** The organization comes from the JWT and is enforced by Postgres RLS ([04 §1](./04_Backend_API_Specification.md)). Opening `/t/beta/dashboard` with an alpha token shows nothing of beta's — the app simply redirects the user to their own address. The slug is branding and an entry point, never permission.
- **`/platform` sits outside the prefix.** The vendor console is reached at the bare root, so it can never fall under a kindergarten's `basename`; the two planes are separated at the URL level too (ADR-10).
- **The refresh token key is namespaced by slug** (`kg_crm_refresh:<slug>`). All kindergartens share one origin, therefore one `localStorage`. With a single key, a bookkeeper serving two kindergartens would be logged out of the first the moment they signed into the second.

**Why a path and not a subdomain.** A subdomain needs wildcard DNS *and* a wildcard TLS certificate; Let's Encrypt issues those only through the DNS-01 challenge, which means a standing dependency on the DNS provider's API — and a renewal that fails silently 90 days later. A path needs one nginx block, one certificate and one CORS origin. The move to `<slug>.kg-crm.uz` remains open and is deliberately cheap: `TENANT_URL_STYLE` in the backend (`apps/core/tenant_address.py`) and `basenameFor()` here, plus a 301 from the old paths. Because the address carries no authority, that migration cannot affect isolation.

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
| `PermissionRoute permission="x.read"` | Session valid but permission missing → redirect to the first section the role **may** open. |
| `PublicOnlyRoute` | Already authenticated → same computed landing path (used on `/login`). |
| `HomeRedirect` | Renders at `/` and `/home` and at any unknown path: resolves the landing path and redirects. |

**The landing path is computed, never hard-coded.** `landingPathFor(allows)` (`config/navigation.ts`) walks `navItems` in order and returns the first one the person may open, falling back to `/profile`, which needs no permission. Every guard, the index route, the catch-all and the post-login navigation use it.

Why it matters: the safe destination used to be a literal `/dashboard` in six places. That worked only because every *system* role has `dashboard.read`. The first customer created a custom "Tarbiyachi" role (children, groups, attendance) and the account landed on `/dashboard`, which the API refused — an error box on an otherwise empty screen, on a role that had three perfectly good sections available.

**Post-login goes to `/home`, not `/`.** On the SaaS deployment the marketing site owns the root (`routes.test.ts` pins this), so navigating to `/` after login would show the product website instead of the app. `/home` sits inside the protected tree in both deployment modes and renders `HomeRedirect`.

---

## 5. Layouts

| Layout | Used by | Contains |
|--------|---------|----------|
| **PublicLayout** | login, forgot-password | Centered card, branding, no nav. |
| **AppLayout** | all authenticated pages | Persistent **Sidebar** (nav filtered by permissions), **Topbar** (user menu, **branch selector** — Org Owner sees all their branches, notifications bell, theme toggle), a **trial/read-only banner** when the subscription requires one, and `<Outlet/>` content area. |

Navigation items come from `config/navigation.ts`, each tagged with the permission required to show it — the sidebar renders only what the user can access (driven by `useCan`). An item may list several permissions; any one of them shows it (e.g. *Xodimlar* needs `payroll.read` **or** `users.read`).

**Responsive rule.** The shell is phone-first below `lg` (1024px): the sidebar becomes a **drawer** opened from a hamburger in the Topbar (`MobileSidebar` — same `SidebarContent` as the desktop aside, so a new nav item can never be missing on mobile), the branch selector moves into the drawer, and the layout height is `dvh` so iOS Safari's address bar never hides the bottom of a page. Pages follow three rules: the body never scrolls horizontally; every `<table>` lives in an `overflow-x-auto` container with a `min-w`; and the two lists people work in all day (children, employees) render **cards below `md`** and a table above it — a horizontally scrolled six-column table is not usable with a thumb.

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
| `/staff` | StaffPage — tabs: *Xodimlar* (HR employees, `payroll.read`), *Tizim hisoblari* (login accounts, `users.read`), *Rollar* (`users.read`); tab in `?tab=` | any of `payroll.read`, `users.read` |
| `/inventory/products` | ProductsPage | `inventory.read` |
| `/inventory/movements` | StockMovementsPage | `inventory.read` |
| `/inventory/suppliers` | SuppliersPage | `inventory.read` |
| `/expenses` | ExpensesPage | `expenses.read` |
| `/reports` | ReportsPage — period picker (day / week / month / quarter / year / custom, with ◀ ▶), grouping derived one step finer than the preset (`features/reports/period.ts`) | `reports.read` |
| `/notifications` | NotificationsPage | `notifications.read` |
| `/settings` | SettingsPage | `settings.read` |
| `/users`, `/users/roles` | folded into `/staff` tabs (above) | — |
| `/audit` | AuditLogPage | `audit.read` |
| `/not-authorized` | NotAuthorizedPage | Protected |
| `*` | NotFoundPage | — |

---

## 7. Authentication in the UI

Follows the JWT flow in [02 §10](./02_Software_Architecture.md).

- **Access token** kept in memory (module variable), never in `localStorage` (XSS safety). **Refresh token** in an httpOnly Secure cookie (preferred) or secure storage.
- On app boot: if a session may exist, call `GET /auth/me` → hydrate `AuthProvider` with `{ user, role, permissions, branch }`. This drives routing and UI gating.
- On login: store tokens, hydrate auth context, redirect to the intended URL or `/home` (which resolves to the first section the role may open).
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
- **Tailwind** utility-first; design tokens (colours, fonts, radius) are defined **once** in `tailwind.config.js`, with the few JS-side values in `lib/brand.ts` — see [§18](#18-brand-system-radix-brendbuk-11). No dark mode: the product is used in daylight offices and a second theme would double the surface the brand has to hold.
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
| **Debounced search** | Search inputs debounce before hitting the API (`hooks/useDebouncedValue`). |
| **Server pagination** | Lists request `page`/`page_size` and render `components/ui` `Pagination` from `meta.pagination`; the page number is *derived* from the filter key (`hooks/usePageState`) so a filter change resets to page 1 in the same render — no stale "page 3 of a 5-row search" request. `placeholderData: keepPreviousData` keeps the old rows on screen while the next page loads. |
| **Memoization** | `useMemo`/`React.memo` on heavy renders. |
| **Lazy images / charts** | Photos and report charts load on demand. |
| **Production build** | Vite tree-shaking + minification; Nginx gzip/brotli + static caching. |
| **Prerendered public pages** | The product website (`features/landing`, `/uz`, `/ru`, `/en`, legal pages — three locales, `x-default` = uz; every sample-screen label lives in `content.ts` under `ui` so the key-parity test proves no locale falls back to Uzbek) is rendered to static HTML at build time — `npm run build` runs `vite build --ssr src/prerender/entry.tsx` and `scripts/prerender.mjs`, writing `dist/uz/index.html` etc. with the full text, per-page meta, hreflang and FAQ JSON-LD **inside the response**. Nginx `try_files $uri $uri/ /index.html` serves them; every other route still gets the SPA shell. Reason: a bare SPA shell (1.8 KB, 42 words) is what Google — slowly — and ChatGPT, Telegram/WhatsApp previews, Yandex — never — render; the same defect had been found on another site's audit. On the client the app still mounts with `createRoot().render`; `router.tsx` gives `lazy()` a synchronous thenable when `main.tsx` has preloaded the landing chunk, so the prerendered content is never replaced by a Suspense fallback (verified with a MutationObserver: the root is never emptied, "Yuklanmoqda…" never appears). The pure meta builders (`buildPageMeta`, `headHtml`, `landingMeta`, `landingJsonLd`) feed both the prerender and the in-browser `applyPageMeta`, so bot and browser see one source. Standalone builds (`VITE_DEPLOYMENT_MODE=standalone`) skip the step — there is no public site there. |

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
| Formatting | **One home: `lib/format.ts`** — `money`, `som`, `number`, `signed`, `compact`, `quantity`, `percent`, and every date helper. Never `new Intl.NumberFormat(…)` in a component, never a local `money()`; `lib/utils.ts` keeps the old names as re-exports for existing call sites. |
| Dates in forms | `components/ui/DateInput` (`dd.mm.yyyy`), never a bare `input[type=date]`. The value in and out is ISO `yyyy-mm-dd`. |
| Save feedback | `useToast()` from `app/providers/ToastProvider` — a save that changes data says so. |
| Tokens | `lib/auth/tokenStorage` holds the **access token in memory only**. The refresh token is an `httpOnly` cookie the browser manages — the module deliberately has no `getRefresh`/`setRefresh`, because offering them would bring the old compromise back. |
| Strings | Uzbek source text wrapped in `t('…')` from `lib/i18n` (§17); no bare UI text, no dynamic `t(variable)`. |
| Env | Access only through `config/env.ts` (typed). |
| Linting | ESLint + Prettier enforced in CI ([06](./06_Development_Roadmap.md)). |

---

## 17. Internationalization (uz / ru / en)

The CRM shell is trilingual ([02 ADR-16](./02_Software_Architecture.md)). The mechanism is deliberately small:

| Piece | Where | Rule |
|-------|-------|------|
| `t(source, vars?)` | `lib/i18n/index.ts` | Pure lookup: `catalog[source] ?? source`, `{name}` placeholders filled from `vars`. Usable anywhere — module constants, hooks, JSX — because the locale is fixed for the life of the page. |
| Locale | `localStorage` `kg-crm.locale` (`uz` default) | Read once in `main.tsx` → `initI18n()` **before** `App` is imported (dynamic import), so module-level `t()` calls already see the catalog. `setLocale()` writes and reloads. |
| Catalogs | `lib/i18n/messages/{ru,en}.ts` | `Record<sourceString, translation>`, sorted by key. `uz` has no catalog. Only the active one is loaded. |
| Switcher | `components/layout/LanguageSwitch` | Topbar (`sm+`), mobile drawer footer, login page. |
| Backend | `Accept-Language: <locale>` on every request (`lib/api/client.ts`) | Error messages, validation and choice labels come back translated (Django `gettext`). |
| Dates | `lib/format.ts` `MONTHS`, `formatDateLong`; `features/reports/period.ts` | Month names per locale; numeric dates (`14.09.2026`) are identical in all three (Q12). |
| Apostrophes | `lib/i18n/__tests__/apostrophes.test.ts` | Uzbek source text uses **U+02BB (ʻ)** for `oʻ`/`gʻ` and **U+02BC (ʼ)** for the glottal stop (Q11). ASCII `'` in a `t()` source or a catalog key is a build failure: the difference is invisible on screen but makes it a *different string*, so the lookup silently misses and the Russian app shows Uzbek. User data is never touched, and SMS bodies go the other way (`sms_safe` swaps them back to ASCII — `ʻ` is not in GSM-7 and doubles the price). |
| Intelligence | `features/intelligence/content.ts` `getCopy()` | Its own uz/ru/en copy objects, selected by the app locale (key-parity test). |
| Guarantee | `lib/i18n/__tests__/catalog.test.ts` | Extracts every `t('…')` literal from `src/` and fails when a source is missing from `ru`/`en`, when a catalog has stale keys, or when placeholders differ. |

**Out of scope on purpose:** the public site (`features/landing`, own content layer + prerender per locale), the vendor console (`features/platform`, Uzbek only), and tenant data (role names, categories, message templates — the customer's own words). When adding UI text: write it in Uzbek, wrap it in `t()`, run the tests, add the `ru`/`en` lines the failing test lists.

---

## 17.1 Numbers, money and dates (Q12)

| Rule | Detail |
|------|--------|
| Grouping | uz/ru use a **non-breaking space** (`1 500 000`), en uses a comma (`1,500,000`). Done by hand, not by `Intl`: the engine's output differs between browsers and Node versions, and a figure that renders one way on the server and another on screen produces "I copied it and it came out different". |
| Currency | `CURRENCY`: uz `soʻm`, ru `сум`, en `UZS`. |
| Dates | `dd.mm.yyyy` in **all three** languages. |
| Missing value | An em dash, never `0` — in a report "0" and "no data" are different facts, and mixing them shows up in the worst place. |
| Money type | Display only. Arithmetic stays on the backend in `Decimal` ([CLAUDE.md invariant 3](../CLAUDE.md)). |

> **Why a dedicated `DateInput`.** A native `input[type=date]` renders the date in the *browser's* locale: one member of staff sees `02.10.2026`, another `10/02/2026` — and the second reads October 2nd as February 10th. On a financial document that is not a cheap mistake: an overdue invoice looks like one that is not due yet. So the display is ours and the calendar stays native (rewriting it breaks keyboard and screen-reader support, and the browser does it well). An impossible date (`31.02.2026`) is refused rather than silently rolled forward, which is what `new Date()` does.

---

## 17.2 Accessibility floor (PLAN 4.8)

These four are guarded by `src/__tests__/a11y.test.ts`, because none of them breaks a feature — they just quietly make the product worse for some people, and they come back if nothing watches.

| Rule | Why |
|------|-----|
| **No text below 12px** | A kindergarten director is often 40+ and looks at the screen at arm's length. The public site's miniature mock screens are exempt: there the small type is part of an *illustration*, not text to read. |
| **An icon button carries `aria-label`** (as well as `title`) | `title` is a mouse tooltip; the reliable accessible name is `aria-label`. |
| **A `placeholder` is not a label** | It disappears as soon as someone types, so a filled-in form stops saying what its fields are. Fields therefore have a `<label>` or an `aria-label`. |
| **Visible focus** | `outline-none` appears in ~99 places and removes the browser's focus ring; a `focus:border-…` colour change is not enough for someone working by keyboard. A global `:focus-visible` ring (not `:focus` — no ring on mouse clicks) answers "where am I now?" in an eight-field form. |

The payment modal is keyboard-operable end to end: **Enter** accepts, **Esc** closes. A cashier works at the keyboard all day, and reaching for the mouse costs a few seconds on every payment, hundreds of times a day. Every other button inside it is `type="button"` — otherwise picking a payment method would submit the payment.

---

## 18. Brand System (Radix Brendbuk 1.1)

The visual identity is **not** re-decided per screen. Everything comes from the brand book (September 2026) through two files:

| File | Holds | Used by |
|------|-------|---------|
| `tailwind.config.js` | The whole palette, the three typefaces, the radius scale, the shadows | Every class in the app |
| `lib/brand.ts` | The same colours as hex, plus a chart sequence | Recharts, inline `style`, canvas — places Tailwind cannot reach |
| `components/brand/Logo.tsx` | The logo itself (`Logo`, `RadixMark`) | Sidebar, login, public nav/footer, platform console, demo mock-ups |

### The palette

| Name | Hex | Role |
|------|-----|------|
| Ildiz | `#12352F` | Mark, headings, dark surfaces (`ildiz-900`) |
| Nihol | `#2E9E6B` | Buttons, links, "paid" (`nihol-500`; `nihol-600` is the button fill — see below) |
| O'rik | `#F29B55` | Seed dot, small accent (`orik-400`) |
| Sut | `#F6F7F4` | The page ground (`bg-sut`, also `tosh-50`) |
| Tosh | `#1B2421` | Text, pictograms (`tosh-900`) |
| — | `#B45F1E` | Debt warning (`orik-700`). **Not a brand colour** — system use only. |

Per page: Sut 60 · Ildiz 25 · Nihol 10 · Tosh 4 · O'rik 1.

**Blue and purple are forbidden** — the brand book's reasoning is that nearly every competing CRM is blue. Two layers enforce it:

1. `tailwind.config.js` **re-points** Tailwind's `blue`, `sky`, `indigo`, `cyan`, `violet`, `purple` and `fuchsia` scales at the brand ramps. Even a screen nobody has reviewed cannot render blue.
2. `src/__tests__/brand.test.ts` fails the build on any `-sky-500`-style class or hardcoded `#rrggbb` outside the two brand files, and tells the author which brand name to use instead.

`slate`, `emerald`, `teal`, `amber` and `red` are re-pointed the same way, so the screens written before the rebrand inherit the brand without being edited one by one.

### Status colours

The status chips of a finance screen must be distinguishable at a glance, and after the rebrand "paid" and "issued" would both have been green. So an in-progress state is **outlined**, not just differently coloured — form carries the difference, not hue alone:

| State | Class | Example |
|-------|-------|---------|
| Done / paid | `bg-nihol-50 text-nihol-700` | `paid`, `ready`, `approved` (absence claim) |
| In progress / recorded | `border border-ildiz-300 bg-ildiz-50 text-ildiz-800` | `issued`, `finalized`, `running`, `applied` |
| Waiting / attention | `bg-orik-50 text-orik-700` | `pending`, overdue amounts |
| Neutral / draft | `bg-tosh-100 text-tosh-600` | `draft`, `queued`, `cancelled` |
| Error / destructive | `bg-red-50 text-red-700` | `failed`, `rejected` |

On the dark vendor console the outline becomes `border border-tosh-500/40 text-tosh-200` — a dark-green outline would disappear there.

### Typography

Headings **Onest** 600/700, body **Golos Text** 400/500, numbers **JetBrains Mono** — all three loaded once in `index.html`. `index.css` puts Onest on `h1`–`h4` globally, so a new page gets it without anyone remembering.

`.num` (`index.css`) is the number style. It goes on **indicator** figures — KPI values, cash balances, payment totals — and **not** on table cells: monospace widens columns and 30-plus screens would start wrapping. It also never goes on a value that contains a word (`42 nafar` in mono reads as code), which is why `Tile` takes a `mono` prop.

### The logo

`components/brand/Logo.tsx` carries the brand book's rules so callers do not have to:

- Mark left, lowercase wordmark right, **always together**. There is no wordmark-only export.
- Below 96 px wide the full logo would break the brand book's minimum, so `Logo` drops the wordmark and renders the mark alone.
- `variant="light"` is the A variant (Ildiz plate, Tosh wordmark) for white and Sut grounds; `variant="dark"` is B (Nihol plate, white wordmark) for Ildiz grounds. **The colours are never overridden in CSS** — the public nav passes a variant instead.
- `safeArea` adds the required 2x clearance (x = the apricot dot's diameter).

Assets live in `public/brand/`; the favicon, the PWA manifest icons and the share images all come from the same mark.

### Share images

`public/og-{uz,ru,en}.png` are generated, not drawn: `node scripts/og.mjs` renders the Ildiz cover from the site's own copy (`features/landing/content.ts`) and screenshots it headless. Re-run it whenever the hero copy or the brand changes — the previous set was hand-made and survived a rebrand looking wrong.

---

## Cross-References
- What the UI is for: [01_Project_Vision](./01_Project_Vision.md); commercial model the `billing` feature surfaces: [01 §4](./01_Project_Vision.md).
- System-level frontend decisions: [02_Software_Architecture](./02_Software_Architecture.md) §14–15; the two access planes: [02 §11.0](./02_Software_Architecture.md).
- Endpoints, permissions, and payloads consumed here: [04_Backend_API_Specification](./04_Backend_API_Specification.md).
- Build order: [06_Development_Roadmap](./06_Development_Roadmap.md).

*End of Frontend Architecture v1.5 — formatting in one home (§17.1), `DateInput`, Uzbek apostrophes (Q11), accessibility floor (§17.2), sectioned navigation, kindergarten logo.*

*Previously v1.4 — organization-scoped query cache, read-only mode, `billing`/`branches`/`onboarding` features; responsive shell (mobile drawer), server pagination, `/staff` tabs, report period picker; trilingual shell (§17) and public site (`/uz` `/ru` `/en`); Radix brand system (§18).*
