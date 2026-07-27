# Premium Bog'cha — Frontend

Kindergarten Management System (KG-CRM) uchun **staff back-office** frontendi. Dizayn 1:1 asosida React'da qurilgan (hozircha **mock ma'lumotlar** bilan — backend keyingi bosqichda ulanadi).

## Texnologiyalar

React · TypeScript · Vite · Tailwind CSS · React Router · Recharts · lucide-react

## Ishga tushirish

```bash
cd frontend
npm install
npm run dev
```

Brauzerda: http://localhost:5173

## Boshqa buyruqlar

```bash
npm run build     # ishlab chiqarish uchun build (tsc + vite)
npm run preview   # build'ni lokal ko'rish
```

## Tuzilma (feature-based)

```
src/
├── app/                  (router — src/router.tsx)
├── components/
│   ├── layout/           Sidebar, Topbar, AppLayout
│   └── ui/               primitives.tsx (Card, StatCard, Badge, Avatar, Button, ...)
├── config/               navigation.ts (sidebar menyusi)
├── features/             HAR bir modul alohida papka
│   ├── dashboard/        Dashboard
│   ├── children/         Bolalar
│   ├── payments/         To'lovlar va Kassa
│   ├── debtors/          Qarzdorlar
│   ├── attendance/       Davomat (to'liq interaktiv)
│   ├── staff/            Xodimlar
│   ├── payroll/          Oylik maoshlar
│   ├── inventory/        Ombor
│   ├── expenses/         Chiqimlar
│   ├── reports/          Hisobotlar va analitika
│   └── settings/         Tizim sozlamalari
└── lib/                  utils.ts (cn, pul formatlash)
```

Har bir sahifa `features/<modul>/pages/*Page.tsx` da joylashgan. Tuzilma
[docs/05_Frontend_Architecture.md](../docs/05_Frontend_Architecture.md) hujjatiga mos.

## Eslatma

- Ma'lumotlar hozircha statik (mock). Real API ulanishi [docs/04_Backend_API_Specification.md](../docs/04_Backend_API_Specification.md) bo'yicha qo'shiladi.
- **Davomat** sahifasi to'liq interaktiv: Keldi / Sababli / Kelmagan tugmalari holatni o'zgartiradi va yuqoridagi KPI'lar avtomatik qayta hisoblanadi.
