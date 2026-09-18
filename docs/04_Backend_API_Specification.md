# 04 — Backend API Specification

| | |
|---|---|
| **Project** | Kindergarten Management System (KG-CRM) |
| **Document** | REST API Contract v1.0 |
| **Base URL** | `/api/v1` |
| **Auth** | JWT Bearer (access + refresh) |
| **Related** | [01_Project_Vision](./01_Project_Vision.md) · [02_Software_Architecture](./02_Software_Architecture.md) · [03_Database_Design](./03_Database_Design.md) · [05_Frontend_Architecture](./05_Frontend_Architecture.md) |

> This is the **contract** between backend and frontend (and future mobile). It defines conventions, endpoints, permissions, and request/response shapes. It does **not** contain implementation (no serializers/views). Entities referenced here are defined in [03_Database_Design](./03_Database_Design.md); conventions are established in [02_Software_Architecture](./02_Software_Architecture.md) §13.

---

## Table of Contents
1. [Global Conventions](#1-global-conventions)
2. [Response & Error Envelope](#2-response--error-envelope)
3. [Pagination, Filtering, Searching, Sorting](#3-pagination-filtering-searching-sorting)
4. [Permission Mapping](#4-permission-mapping)
5. [Auth Endpoints](#5-auth-endpoints)
6. [Users & Roles](#6-users--roles)
7. [Children (Children, Guardians, Groups, Enrollment)](#7-children)
8. [Attendance](#8-attendance)
9. [Finance (Tariffs, Invoices, Payments, Discounts)](#9-finance)
10. [Debtors](#10-debtors)
11. [HR & Payroll](#11-hr--payroll)
12. [Inventory (Kitchen & Warehouse)](#12-inventory)
13. [Expenses](#13-expenses)
14. [Reports & Dashboard](#14-reports--dashboard)
15. [Notifications](#15-notifications)
16. [Settings & Branches](#16-settings--branches)
17. [Audit Log](#17-audit-log)
18. [Billing & Subscription (customer-facing)](#18-billing--subscription-customer-facing)
19. [Platform Console (vendor-only)](#19-platform-console-vendor-only)
20. [HTTP Status Codes](#20-http-status-codes)

---

## 1. Global Conventions

| Aspect | Convention |
|--------|-----------|
| **Base path** | All endpoints under `/api/v1/`. Breaking changes ship as `/api/v2/`. |
| **Format** | JSON only. `Content-Type: application/json`, `Accept: application/json`. |
| **Auth header** | `Authorization: Bearer <access_token>` on every non-public request. |
| **Resource naming** | Plural nouns, lowercase: `/children`, `/payments`. |
| **IDs** | UUID strings. |
| **Verbs** | `GET` (read), `POST` (create), `PATCH` (partial update), `PUT` (full replace — rarely used), `DELETE` (soft delete). |
| **Actions** | Non-CRUD operations as sub-resources: `POST /invoices/{id}/payments`, `POST /payroll/runs/{id}/finalize`. |
| **Timestamps** | ISO 8601 UTC (`2026-07-24T09:30:00Z`). |
| **Money** | Decimal strings (e.g. `"1500000.00"`) to avoid float rounding. |
| **Tenant scope** | Applied automatically from the JWT's `organization_id`. Clients **never** send it and **cannot** override it. A request referencing another organization's resource returns `404`, never `403` (P10, [02 §11.3](./02_Software_Architecture.md)). |
| **Branch scope** | Applied automatically from the JWT. Org Owner may pass `branch_id` to filter across their own organization's branches; other roles are bound to their branch and the parameter is ignored. |
| **Idempotency** | Mutating money endpoints accept optional `Idempotency-Key` header to safely retry. |
| **Subscription gate** | If the caller's organization is `suspended`, all write verbs return `402 SUBSCRIPTION_INACTIVE`; reads continue to work ([03 §20.6](./03_Database_Design.md)). |

---

## 2. Response & Error Envelope

**Every** response uses one envelope so the frontend has a single handler.

### Success — single resource
```json
{
  "success": true,
  "data": { "id": "…", "…": "…" },
  "meta": null,
  "message": null
}
```

### Success — list (paginated)
```json
{
  "success": true,
  "data": [ { "…": "…" }, { "…": "…" } ],
  "meta": {
    "pagination": {
      "count": 128,
      "page": 2,
      "page_size": 25,
      "total_pages": 6,
      "next": "/api/v1/children?page=3",
      "previous": "/api/v1/children?page=1"
    }
  },
  "message": null
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted data is invalid.",
    "details": {
      "amount": ["This field must be greater than 0."],
      "child": ["This child does not exist."]
    }
  }
}
```

### Error code taxonomy
| HTTP | `error.code` | Meaning |
|------|--------------|---------|
| 400 | `VALIDATION_ERROR` | Field validation failed (`details` per field) |
| 401 | `AUTHENTICATION_REQUIRED` | Missing/expired/invalid token |
| 403 | `PERMISSION_DENIED` | RBAC or branch scope denies |
| 404 | `NOT_FOUND` | Resource missing, outside branch scope, **or in another organization** |
| 402 | `SUBSCRIPTION_INACTIVE` | Organization is suspended — writes blocked, reads allowed ([03 §20.6](./03_Database_Design.md)) |
| 409 | `CONFLICT` | Duplicate / state conflict (e.g. duplicate invoice period) |
| 422 | `BUSINESS_RULE_VIOLATION` | Valid input, violates a domain rule (e.g. insufficient stock) |
| 429 | `RATE_LIMITED` | Throttled |
| 500 | `INTERNAL_ERROR` | Unhandled (no internals leaked) |

> **Why cross-tenant access is `404` and not `403`:** a `403` confirms the resource exists, which leaks the fact that another customer holds that id. Tenant boundary violations must be indistinguishable from "no such thing". This is the one place where a deliberately less-informative error is the correct design.

---

## 3. Pagination, Filtering, Searching, Sorting

| Concern | Param | Example |
|---------|-------|---------|
| Pagination | `page`, `page_size` (default 25, max 100) | `?page=2&page_size=50` |
| Search | `search` (across configured text fields) | `?search=aziz` |
| Ordering | `ordering` (`-` = desc, comma = multi) | `?ordering=-created_at` |
| Field filter | `<field>=<value>` | `?status=active&group=<uuid>` |
| Date range | `<field>_after`, `<field>_before` | `?paid_at_after=2026-07-01` |

All list endpoints support these unless stated otherwise.

---

## 4. Permission Mapping

Every endpoint requires a permission `"<module>.<action>"` checked against the caller's role (matrix in [02 §11](./02_Software_Architecture.md)). Notation below: **Auth** column lists the required permission. `—` in the role matrix of [02](./02_Software_Architecture.md) means the endpoint returns `403 PERMISSION_DENIED`.

Actions: `read`, `create`, `update`, `delete`, `approve`, `export`.

---

## 5. Auth Endpoints

Public (no token) except `/me`, `/logout`, `/password/change`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | public | Exchange credentials for tokens |
| POST | `/auth/select-organization` | pending token | Choose organization when the email belongs to several |
| POST | `/auth/refresh` | public (valid refresh) | Rotate access (+refresh) token |
| POST | `/auth/logout` | authenticated | Blacklist refresh token |
| GET | `/auth/me` | authenticated | Current user profile + role + permissions + org/subscription state |
| PATCH | `/auth/me` | authenticated | **Edit own profile** — `full_name`, `phone` only |
| POST | `/auth/me/photo` | authenticated | Upload own profile photo (multipart, ≤2 MB, jpg/png/webp) |
| DELETE | `/auth/me/photo` | authenticated | Remove own profile photo |
| POST | `/auth/password/change` | authenticated | Change own password |

> **There is no public signup.** `POST /auth/signup` was removed. Accounts are opened by vendor staff through the platform console — `POST /platform/organizations/create` (§19) — because every signup creates a real tenant (RLS policies, a subscription, seeded roles) and tenant data is never deleted (ADR-11). A door open to the internet meant strangers leaving permanent rows in the database. It also matched the commercial model badly: customers are legal entities who pay by bank transfer, so the tenant should exist *after* the sales conversation, not before it.

**`POST /auth/login` — request**
```json
{ "email": "cashier@kg.uz", "password": "••••••••" }
```
**Response `200`**
```json
{
  "success": true,
  "data": {
    "access": "<jwt>",
    "refresh": "<jwt>",
    "user": {
      "id": "…", "full_name": "Dilnoza K.", "email": "cashier@kg.uz",
      "role": { "code": "cashier", "name": "Cashier" },
      "organization": { "id": "…", "name": "Premium Bog'cha", "slug": "premium" },
      "branch": { "id": "…", "name": "Main Branch" },
      "permissions": ["payments.read","payments.create","debtors.read","children.read","notifications.create"]
    },
    "subscription": { "status": "active", "trial_ends_at": null, "read_only": false }
  }
}
```

**Multi-organization login.** Email is unique *per organization* ([03 §10.6](./03_Database_Design.md)), so one address may exist in several. When it does, `/auth/login` returns `200` with a short-lived **pending token** and the list of organizations; the client then calls `/auth/select-organization` to obtain real tokens.

> The pending-token step must **never** reveal organizations whose credentials didn't match — it lists only those the supplied password authenticated against. Otherwise login becomes an oracle for "which kindergartens use this email".

**Errors:** `401 AUTHENTICATION_REQUIRED` (bad credentials — generic message), `429 RATE_LIMITED` (login is throttled to defend against brute force).

**`GET /auth/me`** returns the same `user` object plus the live `subscription` block — the frontend calls this on boot to hydrate auth state, drive role-based routing, and switch the whole app into read-only mode when the subscription is suspended ([05](./05_Frontend_Architecture.md)).

---

## 6. Users & Roles

Module: `users` (backed by `accounts`). Managed by **Org Owner** (Director read-only within branch). New users are always created inside the caller's organization — `organization_id` is never accepted from the client.

> **User accounts are unlimited on every plan.** Charging per seat would push staff to share one login and destroy the audit trail that money handling depends on ([01 §4.5](./01_Project_Vision.md)).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users` | `users.read` | List users |
| POST | `/users` | `users.create` | Create user (assign role, branch) |
| GET | `/users/{id}` | `users.read` | User detail |
| PATCH | `/users/{id}` | `users.update` | Update user |
| DELETE | `/users/{id}` | `users.delete` | Deactivate (soft) |
| POST | `/users/{id}/reset-password` | `users.update` | Admin password reset |
| GET | `/roles` | `users.read` | List roles |
| POST | `/roles` | `users.create` | Create role |
| PATCH | `/roles/{id}` | `users.update` | Update role (not system roles) |
| GET | `/roles/{id}/permissions` | `users.read` | Role's permissions |
| PUT | `/roles/{id}/permissions` | `users.update` | Replace role's permission set |
| GET | `/permissions` | `users.read` | List all permissions (reference) |

**`POST /users` — request**
```json
{
  "full_name": "Bekzod A.",
  "email": "manager@kg.uz",
  "password": "••••••••",
  "role_id": "<uuid>",
  "branch_id": "<uuid>",
  "phone": "+998901234567"
}
```
**Errors:** `409 CONFLICT` (email exists), `422 BUSINESS_RULE_VIOLATION` (non-super-admin without branch).

---

## 7. Children

Module: `children`. Sub-domains: children, guardians, groups, enrollment.

### 7.1 Children
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/children` | `children.read` | List (filters: `group`, `enrollment_status`, `tariff`; `search` by name); `?ids=a,b,c` (≤ 100) returns exactly those rows — used by the insight "Why?" panel to resolve labels live by id ([07 §6](./07_Radix_Intelligence.md)) |
| POST | `/children` | `children.create` | Create child |
| GET | `/children/{id}` | `children.read` | Detail (includes guardians, current group, balance) |
| PATCH | `/children/{id}` | `children.update` | Update |
| DELETE | `/children/{id}` | `children.delete` | Soft delete |
| POST | `/children/{id}/photo` | `children.update` | Upload photo (multipart) |
| GET | `/children/{id}/statement` | `children.read` + `payments.read` | Ledger statement (charges/payments/balance) |
| GET | `/children/{id}/guardians` | `children.read` | Guardians of a child |
| POST | `/children/{id}/guardians` | `children.update` | Link a guardian (relation, is_primary, can_pickup) |
| DELETE | `/children/{id}/guardians/{guardianId}` | `children.update` | Unlink guardian |

**`POST /children` — request**
```json
{
  "first_name": "Ali",
  "last_name": "Karimov",
  "date_of_birth": "2021-05-14",
  "gender": "male",
  "tariff_id": "<uuid>",
  "group_id": "<uuid>",
  "guardians": [
    { "guardian_id": "<uuid>", "relation": "mother", "is_primary": true, "can_pickup": true }
  ]
}
```
**Response `201`** — the created child with `balance: "0.00"`, `enrollment_status: "active"`.
**Errors:** `422` (dob not in past), `409` (child already has an open enrollment for that group), `400` (validation).

### 7.2 Guardians
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/guardians` | `children.read` | List/search guardians |
| POST | `/guardians` | `children.create` | Create guardian |
| GET | `/guardians/{id}` | `children.read` | Detail (+ linked children) |
| PATCH | `/guardians/{id}` | `children.update` | Update |
| DELETE | `/guardians/{id}` | `children.delete` | Soft delete (blocked if linked & active) |

### 7.3 Groups
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/groups` | `children.read` | List groups (+ `enrolled_count`, `capacity`) |
| POST | `/groups` | `children.create` | Create group |
| GET | `/groups/{id}` | `children.read` | Detail |
| PATCH | `/groups/{id}` | `children.update` | Update |
| DELETE | `/groups/{id}` | `children.delete` | Soft delete |
| GET | `/groups/{id}/children` | `children.read` | Children currently enrolled, with `capacity` and `free_seats` |

### 7.4 Enrollment
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/enrollments` | `children.read` | List (filters: `child`, `group`, `status`) |
| POST | `/enrollments` | `children.update` | Enroll child into group (closes prior open enrollment) |
| PATCH | `/enrollments/{id}` | `children.update` | End/transfer enrollment |

**Errors:** `409 CONFLICT` (group at capacity → `422 BUSINESS_RULE_VIOLATION`; existing open enrollment).

---

## 8. Attendance

Module: `attendance`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/attendance` | `attendance.read` | List records (filters: `child`, `group`, `attendance_date`, date range, `status`) |
| POST | `/attendance` | `attendance.create` | Create one record |
| POST | `/attendance/bulk` | `attendance.create` | Mark a whole group for a day in one call |
| GET | `/attendance/{id}` | `attendance.read` | Detail |
| PATCH | `/attendance/{id}` | `attendance.update` | Correct a same-day record |
| GET | `/attendance/daily` | `attendance.read` | Register for a group on a date (`?group=&date=`) |
| GET | `/attendance/summary` | `attendance.read` | Monthly summary per child (`?group=&month=`) |

**`POST /attendance/bulk` — request**
```json
{
  "group_id": "<uuid>",
  "attendance_date": "2026-07-24",
  "records": [
    { "child_id": "<uuid>", "status": "present", "check_in_at": "2026-07-24T08:05:00Z" },
    { "child_id": "<uuid>", "status": "absent", "reason": "sick" },
    { "child_id": "<uuid>", "status": "excused", "reason": "family" }
  ]
}
```
**Behavior:** upserts one record per child per day (unique constraint `child_id + attendance_date`). Re-posting the same day updates statuses.
**Errors:** `422` (future date), `400` (invalid status).

---

## 9. Finance

Module: `finance` (Payments module UI). The **ledger** is the source of truth ([03 §13](./03_Database_Design.md)).

### 9.1 Tariffs
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tariffs` | `payments.read` | List tariff plans |
| POST | `/tariffs` | `payments.create` | Create tariff |
| PATCH | `/tariffs/{id}` | `payments.update` | Update |
| DELETE | `/tariffs/{id}` | `payments.delete` | Soft delete |

### 9.2 Invoices
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/invoices` | `payments.read` | List (filters: `child`, `status`, `period_year`, `period_month`, `due_date` range) |
| POST | `/invoices` | `payments.create` | Create a one-off invoice (with lines) |
| GET | `/invoices/{id}` | `payments.read` | Detail (+ lines, payments, balance) |
| PATCH | `/invoices/{id}` | `payments.update` | Update draft invoice |
| POST | `/invoices/{id}/cancel` | `payments.update` | Cancel invoice (status → cancelled) |
| POST | `/invoices/generate` | `payments.create` | **Bulk-generate** monthly invoices for all active children |
| POST | `/invoices/{id}/payments` | `payments.create` | Record a payment against this invoice |
| GET | `/invoices/{id}/receipt` | `payments.read` | Download/generate receipt PDF |

**`POST /invoices/generate` — request**
```json
{ "period_year": 2026, "period_month": 8 }
```
**Behavior:** async (Celery); idempotent — the unique `(child, period)` constraint prevents duplicates, so re-running skips already-invoiced children ([03 §13.3](./03_Database_Design.md)). Returns a job handle:
```json
{ "success": true, "data": { "job_id": "<uuid>", "status": "queued" }, "message": "Invoice generation started." }
```

### 9.3 Payments
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/payments` | `payments.read` | List (filters: `child`, `invoice`, `method`, `paid_at` range) |
| POST | `/payments` | `payments.create` | Record a payment (optionally linked to invoice) |
| GET | `/payments/{id}` | `payments.read` | Detail |
| POST | `/payments/{id}/reverse` | `payments.update` | Reverse a payment (creates counter-entry; never deletes) |
| GET | `/payments/{id}/receipt` | `payments.read` | Receipt PDF |
| GET | `/payments/daily-summary` | `payments.read` | Cashier daily totals (`?date=`) by method |

**`POST /invoices/{id}/payments` — request** (`Idempotency-Key` header recommended)
```json
{ "amount": "1500000.00", "method": "cash", "reference": null }
```
**Response `201`** — payment + updated invoice `status` (`partially_paid`/`paid`) and child `balance`. In one transaction the server: inserts the payment, writes a **credit** ledger entry, updates invoice `amount_paid`/`status`, updates child balance, and (async) fires an SMS receipt.
**Errors:** `422 BUSINESS_RULE_VIOLATION` (overpayment beyond `amount_due`), `409 CONFLICT` (duplicate idempotency key), `404` (invoice not in caller's branch).

### 9.4 Discounts
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/discounts` | `payments.read` | List (filter: `child`) |
| POST | `/discounts` | `payments.create` | Grant a child discount |
| PATCH | `/discounts/{id}` | `payments.update` | Update |
| DELETE | `/discounts/{id}` | `payments.delete` | Soft delete |

---

## 10. Debtors

Module: `debtors` — **derived view over the finance ledger** ([03 §13.7](./03_Database_Design.md)). Read-only + reminder action.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/debtors` | `debtors.read` | List children with outstanding balance (filters: `overdue=true`, `group`, `min_amount`; `ordering=-balance`) |
| GET | `/debtors/{childId}` | `debtors.read` | Debtor detail + ledger statement |
| POST | `/debtors/{childId}/remind` | `debtors.update` + `notifications.create` | Send an SMS debt reminder to the primary guardian |
| POST | `/debtors/remind-all` | `debtors.update` + `notifications.create` | Queue reminders to all current debtors (async) |

> `?overdue_days=N` is a **frontend** deep-link parameter ([07 §8](./07_Radix_Intelligence.md)): the page turns on `overdue=true` and narrows the list to `oldest_overdue_date < today − N` client-side. The API itself does not know it.

**`GET /debtors` — response item**
```json
{
  "child": { "id": "…", "full_name": "Ali Karimov", "group": "Sunflowers" },
  "balance": "3000000.00",
  "oldest_overdue_date": "2026-06-05",
  "primary_guardian": { "full_name": "Nodira K.", "phone": "+998901234567" }
}
```

---

## 11. HR & Payroll

Modules: `hr` (employees, positions) and `payroll`.

### 11.1 Employees & Positions
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/employees` | `payroll.read` | List employees |
| POST | `/employees` | `payroll.create` | Create employee |
| GET | `/employees/{id}` | `payroll.read` | Detail |
| PATCH | `/employees/{id}` | `payroll.update` | Update (incl. base_salary, status) |
| DELETE | `/employees/{id}` | `payroll.delete` | Soft delete (terminate) |
| GET | `/positions` | `payroll.read` | List positions |
| POST | `/positions` | `payroll.create` | Create position |

### 11.2 Payroll Runs
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/payroll/runs` | `payroll.read` | List runs (filter: period, status) |
| POST | `/payroll/runs` | `payroll.create` | Create a draft run for a period (auto-populates items from employees) |
| GET | `/payroll/runs/{id}` | `payroll.read` | Detail (+ items, totals) |
| GET | `/payroll/runs/{id}/items` | `payroll.read` | Line items |
| PATCH | `/payroll/runs/{id}/items/{itemId}` | `payroll.update` | Edit bonus/deduction on a draft item |
| POST | `/payroll/runs/{id}/finalize` | `payroll.update` | Lock the run (immutable) |
| POST | `/payroll/runs/{id}/mark-paid` | `payroll.update` | Mark finalized run as paid |
| GET | `/payroll/runs/{id}/payslips/{employeeId}` | `payroll.read` | Payslip PDF |

**`POST /payroll/runs` — request**
```json
{ "period_year": 2026, "period_month": 7 }
```
**Errors:** `409 CONFLICT` (run already exists for period — unique `(branch, period)`), `422` (finalize/mark-paid out of allowed state order).

---

## 12. Inventory

Module: `inventory` (Kitchen & Warehouse). **Stock levels derived from movements** ([03 §15](./03_Database_Design.md)).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/products` | `inventory.read` | List (filters: `category`, `low_stock=true`; search) |
| POST | `/products` | `inventory.create` | Create product |
| GET | `/products/{id}` | `inventory.read` | Detail (+ current_stock) |
| PATCH | `/products/{id}` | `inventory.update` | Update (name, min_stock, unit) |
| DELETE | `/products/{id}` | `inventory.delete` | Soft delete |
| GET | `/product-categories` | `inventory.read` | List categories |
| POST | `/product-categories` | `inventory.create` | Create category |
| GET | `/suppliers` | `inventory.read` | List suppliers |
| POST | `/suppliers` | `inventory.create` | Create supplier |
| GET | `/warehouses` | `inventory.read` | List warehouses |
| GET | `/stock-movements` | `inventory.read` | List movements (filters: `product`, `warehouse`, `direction`, `movement_type`, date range) |
| POST | `/stock-movements` | `inventory.create` | Record a stock movement (in/out) |
| GET | `/inventory/low-stock` | `inventory.read` | Products below `min_stock` |

**`POST /stock-movements` — request**
```json
{
  "product_id": "<uuid>",
  "warehouse_id": "<uuid>",
  "direction": "out",
  "movement_type": "consumption",
  "quantity": "5.500",
  "occurred_at": "2026-07-24T07:30:00Z",
  "note": "Breakfast prep"
}
```
**Behavior:** for `out`, the server locks the product row, verifies sufficient stock, records the movement, and updates cached `current_stock` — all in one transaction.
**Errors:** `422 BUSINESS_RULE_VIOLATION` (insufficient stock — would go negative), `400` (invalid unit/quantity).

---

## 13. Expenses

Module: `expenses`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/expenses` | `expenses.read` | List (filters: `category`, `status`, `expense_date` range) |
| POST | `/expenses` | `expenses.create` | Create expense (status `pending`) |
| GET | `/expenses/{id}` | `expenses.read` | Detail |
| PATCH | `/expenses/{id}` | `expenses.update` | Update pending expense |
| POST | `/expenses/{id}/approve` | `expenses.approve` | Approve (Director) |
| POST | `/expenses/{id}/reject` | `expenses.approve` | Reject |
| POST | `/expenses/{id}/receipt` | `expenses.update` | Upload receipt (multipart) |
| GET | `/expense-categories` | `expenses.read` | List categories |
| POST | `/expense-categories` | `expenses.create` | Create category |

**Errors:** `422` (future date; approving a non-pending expense).

---

## 14. Reports & Dashboard

Modules: `reports` + Dashboard (aggregation). **Read-only.** Exports are async.

### 14.1 Dashboard
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard` | `dashboard.read` | KPI bundle (cached): active children, month revenue, outstanding debt, today's attendance %, recent payments, low-stock count |

**Response**
```json
{
  "success": true,
  "data": {
    "active_children": 142,
    "month_revenue": "185000000.00",
    "outstanding_debt": "23400000.00",
    "attendance_today_pct": 91.5,
    "recent_payments": [ { "child": "Ali K.", "amount": "1500000.00", "paid_at": "2026-07-24T08:12:00Z" } ],
    "low_stock_count": 3
  }
}
```

### 14.2 Reports
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/reports/revenue` | `reports.read` | Revenue by period (`?from=&to=&group_by=`) |
| GET | `/reports/debtors` | `reports.read` | Outstanding debt snapshot |
| GET | `/reports/attendance` | `reports.read` | Attendance stats (`?group=&month=`) |
| GET | `/reports/payroll` | `reports.read` | Payroll totals by month for a year (`?year=`) |
| GET | `/reports/expenses` | `reports.read` | Expenses by category/period (`?from=&to=&group_by=`) |
| GET | `/reports/profit-loss` | `reports.read` | P&L: revenue − expenses − payroll (`?from=&to=&group_by=`) |

**Period grouping (`group_by`)** — `day` · `week` · `month` (default) · `quarter` · `year`. Applies to `revenue`, `expenses` and `profit-loss`:

- The response echoes `group_by` and returns `by_period: [{ period, … }]`, where `period` is the ISO date of the bucket **start** (`2026-09-01`, week buckets start on Monday, matching Postgres `date_trunc`). The series is **gap-free**: an empty week is returned as zeros, never dropped — a missing bucket would make a dip look like growth.
- Range totals (`total`, `revenue`, `expenses`, `payroll`, `net`) do **not** depend on `group_by`; only the row split does.
- A range that would produce more than 400 buckets (e.g. six years by day) is rejected with `422` — pick a coarser grouping.
- **Payroll is a monthly figure.** In `month`/`quarter`/`year` grouping it lands in the bucket of its period month (`payroll_in_periods: true`). In `day`/`week` grouping it is **not** spread into rows (`payroll_in_periods: false`, row `payroll` = `0.00`, row `net` = revenue − expenses) — dividing one month's salaries across 30 days would be an invented number. The range totals still include it, and the UI says so on screen.
- Exports (`POST /reports/{type}/export`) accept the same `group_by` in `params`, so the CSV matches what was on screen (header column `period`).
| POST | `/reports/{type}/export` | `reports.export` | Queue an Excel/PDF export → returns `job_id` |
| GET | `/reports/exports/{jobId}` | `reports.read` | Poll export status / download link |

> Report reads may route to a replica; heavy aggregations are served from materialized views ([03 §25](./03_Database_Design.md)).

### 14.3 Radix Intelligence — insights & daily briefing (ADR-14)

Module: `intelligence`. Permission module is **`dashboard`** — no new permission codes: reading uses `dashboard.read`, changing a row's status uses `dashboard.update`. Full design in [07](./07_Radix_Intelligence.md).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/insights` | `dashboard.read` | Open insights by default (`status` = `open`, the default · `all` · a single status); filters `type`, `severity`; ordering `severity_rank` (critical first), `generated_at` |
| GET | `/insights/{id}` | `dashboard.read` | One row, open **or closed** |
| GET | `/insights/briefing` | `dashboard.read` | Open insights (max 20) + **live checks** for today: `working_day`, child-level attendance completeness — per branch for an owner without `?branch=` |
| POST | `/insights/{id}/seen` | `dashboard.update` | First open; idempotent |
| POST | `/insights/{id}/resolve` | `dashboard.update` | Closes the row; audit `insight.resolve`; **no suppression** — if the data disagrees tomorrow, a new row appears |
| POST | `/insights/{id}/dismiss` | `dashboard.update` | Closes the row and suppresses the same condition for **7 days**; audit `insight.dismiss` |

Closing an already-closed row → `422 BUSINESS_RULE_VIOLATION`. Another organization's id → `404` on every route.

**The API returns keys and evidence, never sentences.** `type` + `evidence` + `recommendation_key` are rendered by the frontend content layer (`features/intelligence/content.ts`), so a wording change never touches the database. `deep_link` is a path relative to the tenant basename.

**`GET /insights/briefing` — response**
```json
{
  "success": true,
  "data": {
    "date": "2026-09-17",
    "open_count": 1,
    "insights": [
      {
        "id": "…", "type": "payment_delay", "severity": "critical", "status": "new", "is_open": true,
        "subject_type": "branch", "subject_id": "…",
        "evidence": { "as_of": "2026-09-17", "overdue_days_threshold": 15, "children_count": 24, "active_children": 105,
                      "critical_days_threshold": 45, "critical_children_threshold": 10,
                      "total_overdue": "21758500.00", "average_days_overdue": 76, "max_days_overdue": 160,
                      "children": [ { "child_id": "…", "group_id": "…", "overdue_amount": "418000.00", "days_overdue": 160, "invoices": 1 } ] },
        "evidence_version": 1,
        "recommendation_key": "payment_delay.review_debtors",
        "deep_link": "/debtors?overdue_days=15",
        "generated_at": "2026-09-17T03:30:00Z", "refreshed_at": null,
        "seen_at": null, "resolved_at": null, "dismissed_at": null, "dismissed_until": null, "auto_resolved_at": null
      }
    ],
    "checks": {
      "working_day": true,
      "attendance_by_branch": { "<branch_id>": { "expected": 105, "recorded": 88, "percent": 84, "complete": false } }
    }
  }
}
```

`checks.attendance` (a branch user, or `?branch=`) or `checks.attendance_by_branch` (owner) is `null` on a non-working day or when the branch has no enrolled children — the check is hidden, not shown as 0/0.

---

## 15. Notifications

Module: `notifications`. Channel-agnostic (SMS now; Telegram/Email later).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications` | `notifications.read` | Delivery log (filters: `channel`, `status`, date range) |
| GET | `/notifications/{id}` | `notifications.read` | Detail (status, retries, error) |
| POST | `/notifications/send` | `notifications.create` | Send an ad-hoc message (template + recipients) |
| POST | `/notifications/{id}/retry` | `notifications.create` | Retry a failed message |
| GET | `/notification-templates` | `notifications.read` | List templates |
| POST | `/notification-templates` | `notifications.create` | Create template |
| PATCH | `/notification-templates/{id}` | `notifications.update` | Edit template body/variables |

**`POST /notifications/send` — request**
```json
{
  "template_code": "debt_reminder",
  "channel": "sms",
  "guardian_ids": ["<uuid>", "<uuid>"],
  "variables": { "amount": "3000000.00", "due_date": "2026-07-30" }
}
```
**Behavior:** always async (Celery `notifications` queue); each dispatch produces a `notification` row with status lifecycle `queued → sent → delivered/failed`.

---

## 16. Settings & Branches

Module: `settings_app` + `branches`. Managed by Org Owner (Director read-only).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/organization` | `settings.read` | The caller's own organization profile |
| PATCH | `/organization` | `settings.update` | Edit name, legal name, tax id, contact details |
| GET | `/settings` | `settings.read` | List effective settings (branch overrides organization) |
| GET | `/settings/{key}` | `settings.read` | Single setting |
| PUT | `/settings/{key}` | `settings.update` | Set a value (JSONB) |
| GET | `/branches` | `branches.read` | List the organization's branches |
| POST | `/branches` | `branches.create` | Create branch |
| PATCH | `/branches/{id}` | `branches.update` | Update branch (currency, timezone) |
| DELETE | `/branches/{id}` | `branches.delete` | Soft-delete (blocked if it holds children/employees) |

> **`/organization` is a singleton — it takes no id.** The organization is read from the caller's token, never from the URL, so there is no id to tamper with and no cross-tenant path to test for. `slug`, `onboarded_at` and `created_at` are read-only: the slug is the organization's global identifier, and the onboarding timestamp is what the trial period is counted from ([01 §4.4](./01_Project_Vision.md)) — editing it would move a billing date.

> **`PATCH /auth/me` exists so that self-service does not require admin rights.** Editing a user through `/users/{id}` needs `users.update`, which a cashier does not have — they could not correct their own phone number. This endpoint accepts **only** `full_name` and `phone`. `role`, `branch`, `email`, `is_active` and `organization` are silently ignored: each is a privilege boundary, and a self-edit path that touches one is a privilege-escalation path. Those stay on `/users/{id}`, where every change is audit-logged against an administrator.

> **`POST /branches` is never rate-limited by plan and never returns a quota error.** Branch count is not billed ([01 §4.5](./01_Project_Vision.md)); adding a location is exactly the growth we want, and it raises the bill only through the children it brings.

---

## 17. Audit Log

Module: `audit`. **Read-only** (insert-only at DB level). Org Owner + Director.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/audit-logs` | `audit.read` | List (filters: `actor`, `entity_type`, `entity_id`, `action`, date range) |
| GET | `/audit-logs/{id}` | `audit.read` | Detail (before/after diff) |
| GET | `/audit-logs/platform-access` | `audit.read` | **Vendor access to this organization** — every support grant and platform read ([02 §20.3](./02_Software_Architecture.md)) |

> The last endpoint exists so vendor access is *visible to the customer*, not merely logged for the vendor. A tenant can always see when we looked at their data.

---

## 18. Billing & Subscription (customer-facing)

Module: `subscriptions`. **Org Owner only** ([02 §11.2](./02_Software_Architecture.md)). All paths are implicitly scoped to the caller's organization — there is no way to address another organization's billing.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/billing/subscription` | `billing.read` | Current plan, status, term, discount, period dates, trial end |
| GET | `/billing/usage` | `billing.read` | Current billable child count + **projected** charge for the open period |
| GET | `/billing/usage/history` | `billing.read` | Past `usage_snapshot` rows — the evidence behind each invoice |
| GET | `/billing/invoices` | `billing.read` | Subscription invoices (filters: `status`, date range) |
| GET | `/billing/invoices/{id}` | `billing.read` | Detail with base/overage/discount breakdown |
| GET | `/billing/invoices/{id}/document` | `billing.read` | Download invoice / act (PDF) |
| POST | `/billing/accept-trial` | `billing.update` | Convert the trial → issues the first invoice, enters `pending_payment` |
| POST | `/billing/payment-term` | `billing.update` | Request a term change (monthly / semiannual / annual) |
| POST | `/billing/export` | `billing.update` | Request a full data export (async job) |

**`GET /billing/usage` — response**
```json
{
  "success": true,
  "data": {
    "period": { "year": 2026, "month": 7 },
    "billable_children": 73,
    "peak_children": 73,
    "included_children": 50,
    "overage_steps": 3,
    "projected": {
      "base_amount": "500000.00",
      "overage_amount": "240000.00",
      "discount_amount": "0.00",
      "total_amount": "740000.00",
      "currency": "UZS"
    },
    "is_projection": true
  }
}
```

> `is_projection: true` is not decoration — it marks the number as *not yet charged*. The billed amount always comes from a closed `usage_snapshot` ([03 §20.3](./03_Database_Design.md)). Exposing this endpoint at all is a retention decision: a customer who can see the count moving never receives a surprise invoice.

**`POST /billing/export`** must work in **every** subscription status, including `cancelled`. A customer's own operational data is never held hostage to a billing dispute.

---

## 18a. Idempotency

`POST /payments` accepts an **`Idempotency-Key`** header. The key identifies a *user action*, not a request: a retried submission carries the same key, and the server returns the payment already recorded instead of creating a second one. The response is `201` either way — the caller cannot tell, and does not need to.

Locking the invoice already prevented *over*payment; it did nothing about *duplicate* payment, and an advance payment (no invoice) had no guard at all — a double-click doubled a child's credit. The key is enforced by a partial unique index on `(organization, idempotency_key)`, so two simultaneous requests are resolved by the database rather than by a check-then-act race in the application. Uniqueness is **per organization**: a global key space would let one kindergarten's key block another's payment.

Omitting the header keeps the old behaviour. That is deliberate — making it mandatory would break existing integrations in a single deploy — but a caller without a key is not protected.

---

## 19. Platform Console (vendor-only)

Module: `platform`. **Not part of the customer API surface** — separate auth path, mandatory 2FA, every call audited (ADR-10, [02 §11.0](./02_Software_Architecture.md)).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/platform/organizations/create` | **Open a new customer** — organization + first branch + Org Owner + trial. Admin only. Replaces the removed public signup. |
| GET | `/platform/organizations` | List all organizations — **metadata only** (name, plan, status, child count, MRR) |
| GET | `/platform/organizations/{id}` | Organization detail + subscription + usage history |
| POST | `/platform/organizations/{id}/suspend` | Move to `suspended` (read-only for the customer) |
| POST | `/platform/organizations/{id}/reactivate` | Restore access |
| POST | `/platform/organizations/{id}/extend-trial` | Extend the trial (reason required) |
| POST | `/platform/organizations/{id}/support-grant` | Request time-boxed operational access (reason required, customer-visible) |
| POST | `/platform/organizations/{id}/support-session` | Enter the customer's app under an active grant — **read-only**, short-lived, no refresh token |

> **Support access is two steps, deliberately.** `support-grant` records *why* and *until when*; `support-session` is the act of entering, and it may happen several times inside one grant — each entry writes its own row to the **customer's** audit log, so a kindergarten sees not only that permission was taken but that it was used.
>
> The session is an ordinary customer access token issued for the organization's owner account, so the vendor reads through the same viewsets, permissions and RLS policies the customer uses — there is no second data path to drift out of sync. Three limits apply, all enforced in `TenantJWTAuthentication` (one place, impossible to forget on a new endpoint):
>
> - **Read-only.** Any unsafe method is `403`. Writing would change a customer's data without their knowledge, and — because the session runs through the owner's account — the audit log would attribute it to the kindergarten's own owner. Permitting writes would make the audit log lie.
> - **The grant is re-checked on every request**, not just at issuance. Revoking a grant closes the session immediately; otherwise the revoke button would offer false comfort for up to 30 minutes.
> - **No refresh token, 30-minute ceiling**, capped further by whatever remains of the grant.
>
> This closes a gap rather than adding a feature: the grant model existed since Sprint 11 but `active_grant()` was never called from production code, so a grant granted nothing. The only practical way to support a customer was to know their password — which puts every kindergarten's key on one laptop and signs the vendor's actions with the customer's name.

> **`POST /platform/organizations/create` — the address is chosen here.** An optional `slug` sets where the kindergarten lives: `https://<base>/t/<slug>`. It is validated once, at creation, against a reserved list (`www`, `api`, `admin`, …) and global uniqueness — because the slug ends up in links, invoices and SMS text, so changing it later breaks what customers already have. The response returns `login_url`, `owner_email` and the organization; the initial password is set by the vendor and handed to the customer. The 15-day trial starts at creation, so the account should be opened when the customer is ready to begin. The creation is written to the **customer's** audit log — a kindergarten can see who opened its account and when.
| GET | `/platform/subscriptions/expiring` | Trials ending, invoices overdue — the daily work list |
| GET | `/platform/invoices` | All subscription invoices across organizations |
| POST | `/platform/invoices/{id}/payments` | Record a received bank transfer |
| GET | `/platform/plans` | Plan versions |
| POST | `/platform/plans` | Create a **new plan version** (never edits an existing one) |

**Hard constraints on this surface:**

- No endpoint here returns children, guardians, payments, payroll, or attendance rows. Aggregate counts only.
- Reading a tenant's operational data requires an approved `support-grant` and happens through the **normal customer API** under that grant — not through a privileged bypass. There is no second code path to audit.
- Every call writes a platform audit row, and grant-related rows surface to the customer via `/audit-logs/platform-access`.

> **Why no cross-tenant data endpoints at all:** the moment one exists, it becomes the thing an attacker targets and the thing a bug misuses. Keeping the vendor console to metadata means the blast radius of a compromised platform account is "knows who our customers are", not "reads every child's record in the country".

---

## 20. HTTP Status Codes

| Code | Used for |
|------|----------|
| 200 | Successful GET / PATCH / action |
| 201 | Successful POST create |
| 202 | Accepted — async job queued (invoice generation, exports, bulk notifications) |
| 204 | Successful DELETE (soft) with no body |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Authenticated but not permitted (RBAC/branch) |
| 404 | Not found / outside branch scope |
| 409 | Conflict (duplicate) |
| 422 | Business-rule violation |
| 429 | Rate limited |
| 500 | Internal error |

---

## Cross-References
- Conventions & security: [02_Software_Architecture](./02_Software_Architecture.md) §13, §20.
- Tenant scoping and the two access planes: [02_Software_Architecture](./02_Software_Architecture.md) §11.
- Entities, constraints, transactional rules behind these endpoints: [03_Database_Design](./03_Database_Design.md).
- Subscription lifecycle and metering: [03_Database_Design](./03_Database_Design.md) §20; commercial terms: [01_Project_Vision](./01_Project_Vision.md) §4.
- How the frontend consumes these (query keys, interceptors, forms): [05_Frontend_Architecture](./05_Frontend_Architecture.md).

*End of Backend API Specification v1.1 — signup/tenant scoping, billing (§18) and platform console (§19) added. Contract only — no implementation.*
