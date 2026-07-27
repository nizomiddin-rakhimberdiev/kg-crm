# 01 — Project Vision & Requirements

| | |
|---|---|
| **Project** | Kindergarten Management System (KG-CRM) |
| **Document** | Project Vision, Scope & Requirements v1.0 |
| **Status** | Baseline — governs all downstream design |
| **Audience** | Product, Backend, Frontend, QA, Stakeholders |
| **Related** | [00_INDEX](./00_INDEX.md) · [02_Software_Architecture](./02_Software_Architecture.md) · [03_Database_Design](./03_Database_Design.md) · [04_Backend_API_Specification](./04_Backend_API_Specification.md) · [05_Frontend_Architecture](./05_Frontend_Architecture.md) · [06_Development_Roadmap](./06_Development_Roadmap.md) |

> This is the **"why" and "what"** of the system. Every architectural and technical decision downstream must trace back to a requirement here. When a requirement changes, this document changes first, then the affected design docs.

---

## 1. Vision Statement

> **A single platform that lets a kindergarten run its entire operation — enrollments, money, staff, kitchen, and communication — from one place, replacing paper ledgers, spreadsheets, and disconnected chat apps.**

The system unifies three enterprise domains:

- **CRM** — the relationship side: children, guardians, enrollment, communication.
- **ERP** — the operations side: payments, debts, payroll, expenses, kitchen & warehouse.
- **LMS** — the future learning side: homework, meal planning, teacher & parent portals.

We deliver an **administrative back-office MVP** first (staff-facing), then grow into parent/teacher-facing and multi-branch capabilities **without re-architecting** (see [06_Development_Roadmap](./06_Development_Roadmap.md)).

---

## 2. Problem Statement

Kindergartens today typically operate with:

| Pain point | Current reality | Cost |
|-----------|-----------------|------|
| Fragmented data | Paper registers, Excel files, phone notes | Lost/duplicated records, no single truth |
| Manual billing | Hand-calculated monthly fees | Errors, missed debts, revenue leakage |
| Debt tracking | "Who owes what?" answered from memory | Uncollected payments, disputes |
| Payroll | Manual salary math | Slow, error-prone, no history |
| Inventory | No kitchen/warehouse tracking | Waste, stock-outs, no cost visibility |
| Communication | Ad-hoc calls / group chats | Missed reminders, no delivery record |
| Reporting | Assembled by hand each month | No real-time visibility for the director |

**The system's job** is to make each of these a fast, accurate, auditable, single-source operation.

---

## 3. Goals & Non-Goals

### 3.1 Goals (MVP)
1. One system of record for **children & guardians**.
2. Accurate **monthly billing**, **payment intake**, and **automatic debtor tracking**.
3. Daily **attendance** with history.
4. **Payroll** for staff with per-period runs and payslips.
5. **Kitchen & warehouse** stock tracking (in/out, low-stock alerts).
6. **Expense** tracking with approval and P&L visibility.
7. **Dashboard** and **reports** giving the director real-time operational and financial visibility.
8. **SMS notifications** (payment receipts, debt reminders).
9. **Role-based access** so each staff member sees only what they should.
10. Full **audit trail** for money and administrative actions.

### 3.2 Non-Goals (explicitly out of MVP scope)
- Parent-facing or teacher-facing portals (designed for, not built yet).
- Online/card payment gateway integration.
- Medical records, meal planning, homework/LMS features.
- Native mobile app.
- Multi-branch operation *enabled* (the data model supports it; the MVP runs single-branch).

> Non-goals are **designed for** at the architecture/data layer (see [02](./02_Software_Architecture.md) §22, [03](./03_Database_Design.md) §6) so they become additive later, never a rewrite.

---

## 4. Target Users (Personas & Roles)

The MVP is **internal / staff-facing**. Five roles (full permission matrix in [02_Software_Architecture](./02_Software_Architecture.md) §11):

| Role | Persona | Primary jobs |
|------|---------|--------------|
| **Super Admin** | System owner / technical admin | Manage users, roles, settings; full cross-branch access |
| **Director** | Kindergarten head | Full operational & financial oversight of the branch; reports |
| **Manager** | Operations manager | Children, attendance oversight, kitchen/warehouse, expenses |
| **Cashier** | Front-desk / accountant | Payments, invoices, debtor follow-up |
| **Attendance Manager** | Teacher/monitor | Records and manages daily attendance |

**Future personas** (roadmap): Parent, Teacher — they slot into the same data-driven RBAC without code changes.

---

## 5. Scope — Modules

### 5.1 MVP Modules (12)

| # | Module | Purpose | Backed by (Django app) |
|---|--------|---------|------------------------|
| 1 | **Dashboard** | Real-time KPIs and overview | `reports` (aggregation view) |
| 2 | **Children** | Child & guardian profiles, groups, enrollment | `children` |
| 3 | **Payments** | Invoices, payment intake, receipts | `finance` |
| 4 | **Debtors** | Who owes money and how much | `finance` (derived view) |
| 5 | **Attendance** | Daily present/absent tracking | `attendance` |
| 6 | **Payroll** | Staff salaries, payroll runs, payslips | `payroll` (+ `hr`) |
| 7 | **Kitchen & Warehouse** | Products, stock in/out, suppliers | `inventory` |
| 8 | **Expenses** | Operational spend with approval | `expenses` |
| 9 | **Reports** | Financial & operational reports, exports | `reports` |
| 10 | **Notifications** | SMS dispatch, templates, delivery log | `notifications` |
| 11 | **Settings** | System configuration, feature flags | `settings_app` |
| 12 | **Users & Roles** | User & role/permission management | `accounts` |

### 5.2 Future Modules (roadmap — architecture already supports)

Parent Portal · Teacher Portal · Online Payments · Medical Records · Meal Planning · Homework/LMS · Gallery · AI Assistant · Multiple Branches · Mobile App · Advanced Analytics.

Mapping of *how each plugs in* is in [02_Software_Architecture](./02_Software_Architecture.md) §22.

---

## 6. Functional Requirements (high level, per module)

> Detailed API contracts are in [04_Backend_API_Specification](./04_Backend_API_Specification.md). This section states **what** each module must do.

| Module | Key capabilities (MVP) |
|--------|------------------------|
| **Dashboard** | Active children count, month revenue, outstanding debt total, today's attendance %, recent payments, low-stock alerts. |
| **Children** | CRUD child; manage guardians & relationships; assign group & tariff; enrollment lifecycle; search & filter; photo upload. |
| **Payments** | Generate monthly invoices; record payments (cash/card/transfer); partial payments; generate receipts; view child statement. |
| **Debtors** | List children with outstanding balance; overdue flags; send reminders; drill into ledger. |
| **Attendance** | Mark daily status per child/group; check-in/out; absence reasons; monthly attendance view; edit same-day corrections. |
| **Payroll** | Manage employees & positions; create monthly payroll run; per-employee bonus/deduction; finalize & mark paid; payslip. |
| **Kitchen & Warehouse** | Manage products, categories, suppliers, warehouses; record stock in (purchase) and out (consumption/waste); low-stock alerts. |
| **Expenses** | Record expense with category & receipt; approval workflow (pending→approved/rejected→paid). |
| **Reports** | Monthly P&L, revenue, debtors, attendance, payroll, expense reports; export to Excel/PDF. |
| **Notifications** | Editable templates; send SMS on payment & for debt reminders; view delivery status & retries. |
| **Settings** | System-wide config (tariff defaults, reminder cadence, SMS provider), feature flags, branch settings. |
| **Users & Roles** | CRUD users; assign roles; manage role→permission mapping; deactivate users; view audit log. |

---

## 7. Non-Functional Requirements (NFRs)

| Category | Requirement | Where addressed |
|----------|-------------|-----------------|
| **Security** | JWT auth, deny-by-default RBAC, audit logs, rate limiting, TLS, input validation | [02](./02_Software_Architecture.md) §20 |
| **Performance** | List screens < 300 ms server time; indexed queries; heavy work async | [02](./02_Software_Architecture.md) §21, [03](./03_Database_Design.md) §22 |
| **Reliability** | No lost payments; idempotent billing; transactional money/stock ops | [03](./03_Database_Design.md) §25 |
| **Auditability** | Every financial/admin mutation logged (who/what/when) | [03](./03_Database_Design.md) §19 |
| **Scalability** | Add modules & branches without refactor; horizontal API scaling | [02](./02_Software_Architecture.md) §22, [03](./03_Database_Design.md) §26 |
| **Usability** | Clean admin UX; consistent loading/error/empty states; fast forms | [05](./05_Frontend_Architecture.md) |
| **Localization** | UI language-ready (Uzbek/Russian); `timestamptz` UTC storage, branch-timezone display; `UZS` currency default | [03](./03_Database_Design.md) §3, §6 |
| **Maintainability** | Uniform module structure; business logic in service layer; documented contracts | [02](./02_Software_Architecture.md) §5 |
| **Availability** | Single-server MVP; stateless API enables future HA | [02](./02_Software_Architecture.md) §23 |
| **Data integrity** | DB-level constraints; append-only ledgers; soft delete | [03](./03_Database_Design.md) §21 |

---

## 8. Success Criteria (MVP)

The MVP is "done" when a kindergarten can, **entirely in the system**:
1. Enroll a child with guardians, assign a group and tariff.
2. Generate that child's monthly invoice automatically.
3. Take a payment and print/send a receipt (SMS).
4. See the child appear/disappear from the **Debtors** list based on real payment state.
5. Mark daily attendance for a group.
6. Run monthly payroll for staff and produce payslips.
7. Track kitchen stock and get a low-stock alert.
8. Record and approve an expense.
9. Open the Dashboard and see accurate live numbers for all of the above.
10. Do all of this under role-appropriate access, with every money action audit-logged.

**Quality bars:** no data loss, no billing double-charge, reports reconcile to the ledger to the cent, and every endpoint enforces RBAC.

---

## 9. Constraints & Assumptions

| Type | Statement |
|------|-----------|
| Constraint | Deployment target is a single **Linux server** with Docker; no managed cloud services assumed for MVP. |
| Constraint | Notifications MVP channel is **SMS** via a third-party gateway (provider abstracted). |
| Constraint | Currency default **UZS**; timezone default **Asia/Tashkent** (branch-configurable). |
| Assumption | Staff have desktop/laptop browser access; mobile browser usable but not the primary target. |
| Assumption | Internet connectivity is generally available (SMS and app are online). |
| Assumption | Single branch operates at MVP launch; multi-branch is a later switch. |

---

## 10. Glossary

| Term | Meaning |
|------|---------|
| **Branch** | A physical kindergarten location; the tenancy boundary for all data. |
| **Guardian** | A parent/caregiver linked to a child; the SMS recipient. |
| **Group** | A kindergarten class (e.g. "Sunflowers"). |
| **Enrollment** | A dated membership of a child in a group. |
| **Tariff / Plan** | The recurring fee definition applied to a child. |
| **Invoice** | A billing document for a child for one period. |
| **Ledger** | The append-only record of all financial charges/payments per child; the source of truth for balances. |
| **Debtor** | A child whose ledger balance is positive (owes money) — a *derived* state, not a stored table. |
| **Payroll Run** | A monthly batch that computes salaries for all employees. |
| **Stock Movement** | An immutable in/out record for a product; source of truth for stock levels. |
| **RBAC** | Role-Based Access Control — permissions granted via roles. |
| **Audit Log** | Immutable record of who did what to which record. |

---

## 11. Document Governance

- This document is **upstream of all others**. A functional/scope change starts here.
- Downstream docs ([02](./02_Software_Architecture.md)–[06](./06_Development_Roadmap.md)) must remain **consistent** with this vision; conflicts are resolved in favor of an explicit decision recorded here or as an ADR in [02](./02_Software_Architecture.md) §2.
- The build sequence that realizes this scope is in [06_Development_Roadmap](./06_Development_Roadmap.md).

*End of Project Vision v1.0.*
