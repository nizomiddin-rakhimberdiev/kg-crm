"""
2026-09-30 dagi sinov yozuvlarini tozalash (PLAN 5.11).

Audit paytida Oriental Kinderland'da ishlaydigan tizimda bir nechta
sinov yozuvi qoldirilgan. Bu buyruq FAQAT ularni tozalaydi:

* "TEST Sinov Claude" bolasi va "TEST-Vasiy Sinov" vasiysi;
* bolaning 200 000 to'lovi va sentabr hisob-fakturasi;
* "nimadir" guruhidagi uning davomati;
* "TEST Guruch" mahsuloti va harakati;
* "TEST Oziq-ovqat" kategoriyasi va uning 300 000 chiqimi.

**Sukut bo'yicha dry-run.** Yozish uchun `--apply` kerak — buyruqni
ishga tushirish egasining qarori (brief, 2-qoida 5).

**Hech narsa jimgina o'chirilmaydi** — har bir qadam tizimning o'z
tuzatish yo'li bilan va audit yozuvi bilan:

* to'lov — QAYTARILADI (qarshi yozuv; kassa ham qarshi harakat);
* hisob-faktura — BEKOR qilinadi (qarshi yozuv);
* bola — ARXIVLANADI (moliyaviy izi bor, Q6 bo'yicha o'chirilmaydi);
* vasiy, mahsulot, kategoriya — faolsizlantiriladi;
* ombor qoldig'i — qarshi `adjustment` harakati bilan nolga;
* chiqim — kassadan qarshi harakat, keyin faolsizlantiriladi;
* davomat — o'chiriladi (ledger emas), yozuvlar audit'ga ko'chiriladi.

Uch ledger (pul, kassa, ombor) append-only qoladi: asl qatorlar
joyida, ustiga qarshi yozuv. Jurnal "kiritildi, keyin tuzatildi" deb
ko'rsatadi — "hech narsa bo'lmagan" emas.

Moslik QAT'IY: aynan shu sana (Toshkent vaqti) va aynan shu nomlar.
Biror yozuv ikki marta mos kelsa — buyruq to'xtaydi, taxmin qilmaydi.

Ishlatish::

    python manage.py cleanup_test_records --slug <oriental-slug>          # dry-run
    python manage.py cleanup_test_records --slug <oriental-slug> --apply  # bajarish
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context

#: Sinov yozuvlari yaratilgan kun (Asia/Tashkent).
TEST_DAY = date(2026, 9, 30)
ACTOR = "system:cleanup_test_records"
REASON = "PLAN 5.11: 2026-09-30 dagi sinov yozuvi"

CHILD_TOKENS = ("TEST", "Sinov", "Claude")
GUARDIAN_TOKENS = ("TEST-Vasiy", "Sinov")
PAYMENT_AMOUNT = Decimal("200000")
GROUP_NAME = "nimadir"
PRODUCT_NAME = "TEST Guruch"
CATEGORY_NAME = "TEST Oziq-ovqat"
EXPENSE_AMOUNT = Decimal("300000")


def _has_tokens(text: str, tokens: tuple[str, ...]) -> bool:
    words = text.split()
    return all(token in words for token in tokens)


@dataclass
class Plan:
    child: Any = None
    guardian: Any = None
    payments: list[Any] = field(default_factory=list)
    invoices: list[Any] = field(default_factory=list)
    attendance: list[Any] = field(default_factory=list)
    product: Any = None
    stock: list[tuple[Any, Decimal]] = field(default_factory=list)
    category: Any = None
    expenses: list[Any] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class Command(BaseCommand):
    help = "2026-09-30 dagi sinov yozuvlarini tozalaydi (sukut — dry-run)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", required=True, help="Tashkilot slug'i (Oriental Kinderland)")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan bajarish")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.organizations.models import Organization

        with platform_context():
            organization = Organization.objects.filter(slug=options["slug"]).first()
        if organization is None:
            raise CommandError(f"'{options['slug']}' topilmadi.")

        self.stdout.write(f"Tashkilot: {organization.name} ({organization.slug})")
        with organization_context(organization.id):
            plan = self._find(organization)
            self._show(plan)
            if not options["apply"]:
                self.stdout.write(
                    self.style.WARNING("\n[dry-run] Hech narsa o'zgarmadi. Bajarish: --apply")
                )
                return
            with transaction.atomic():
                self._apply(organization, plan)
            self.stdout.write(self.style.SUCCESS("\nTozalandi. Har bir qadam audit jurnalida."))

    # --- Topish ---

    def _one(self, rows: list[Any], label: str, plan: Plan) -> Any:
        if not rows:
            plan.missing.append(label)
            return None
        if len(rows) > 1:
            raise CommandError(
                f"{label}: {len(rows)} ta mos yozuv — taxmin qilinmaydi. Qo'lda tekshiring: "
                + ", ".join(str(r.pk) for r in rows)
            )
        return rows[0]

    def _find(self, organization: Any) -> Plan:
        from apps.attendance.models import AttendanceRecord
        from apps.children.models import Child, Guardian
        from apps.expenses.models import Expense, ExpenseCategory
        from apps.finance.models import Invoice, Payment
        from apps.inventory.models import Product, StockMovement

        plan = Plan()

        children = [
            c
            for c in Child.all_objects.filter(created_at__date=TEST_DAY)
            if _has_tokens(f"{c.last_name} {c.first_name} {c.middle_name}", CHILD_TOKENS)
        ]
        plan.child = self._one(children, "Bola 'TEST Sinov Claude'", plan)

        guardians = [
            g
            for g in Guardian.all_objects.filter(created_at__date=TEST_DAY)
            if _has_tokens(f"{g.last_name} {g.first_name}", GUARDIAN_TOKENS)
        ]
        plan.guardian = self._one(guardians, "Vasiy 'TEST-Vasiy Sinov'", plan)

        if plan.child is not None:
            plan.payments = list(
                Payment.objects.filter(
                    child=plan.child, amount=PAYMENT_AMOUNT, reversed_at__isnull=True
                )
            )
            plan.invoices = list(
                Invoice.objects.filter(child=plan.child, period_year=2026, period_month=9)
            )
            plan.attendance = list(
                AttendanceRecord.objects.filter(child=plan.child, group__name=GROUP_NAME)
            )

        products = list(Product.all_objects.filter(name=PRODUCT_NAME, created_at__date=TEST_DAY))
        plan.product = self._one(products, f"Mahsulot '{PRODUCT_NAME}'", plan)
        if plan.product is not None:
            by_warehouse: dict[Any, Decimal] = {}
            for movement in StockMovement.objects.filter(product=plan.product):
                by_warehouse[movement.warehouse] = (
                    by_warehouse.get(movement.warehouse, Decimal("0")) + movement.signed_quantity
                )
            plan.stock = [(w, q) for w, q in by_warehouse.items() if q != 0]

        categories = list(
            ExpenseCategory.all_objects.filter(name=CATEGORY_NAME, created_at__date=TEST_DAY)
        )
        plan.category = self._one(categories, f"Kategoriya '{CATEGORY_NAME}'", plan)
        if plan.category is not None:
            plan.expenses = list(
                Expense.all_objects.filter(
                    category=plan.category, amount=EXPENSE_AMOUNT, is_active=True
                )
            )
        return plan

    def _show(self, plan: Plan) -> None:
        line = self.stdout.write
        line("\nTopildi:")
        line(f"  bola:        {plan.child or '—'}")
        line(f"  vasiy:       {plan.guardian or '—'}")
        line(f"  to'lovlar:   {len(plan.payments)} → qaytariladi")
        line(f"  fakturalar:  {[i.number for i in plan.invoices]} → bekor qilinadi")
        line(f"  davomat:     {len(plan.attendance)} yozuv → o'chiriladi (audit'ga ko'chadi)")
        line(f"  mahsulot:    {plan.product or '—'}; qoldiq: {[str(q) for _, q in plan.stock]}")
        line(f"  kategoriya:  {plan.category or '—'}")
        line(f"  chiqimlar:   {len(plan.expenses)} → kassadan qaytariladi, faolsizlanadi")
        if plan.missing:
            line(self.style.WARNING(f"  topilmadi:   {', '.join(plan.missing)}"))

    # --- Bajarish ---

    def _audit(
        self, organization: Any, action: str, entity: str, entity_id: Any, **changes: Any
    ) -> None:
        from apps.audit import services as audit

        audit.record(
            action=action,
            organization=organization,
            actor_email=ACTOR,
            entity_type=entity,
            entity_id=entity_id,
            changes={"reason": REASON, **changes},
        )

    def _apply(self, organization: Any, plan: Plan) -> None:
        from apps.cash import services as cash
        from apps.cash.models import MovementSource
        from apps.children.services import archive_child
        from apps.finance.services import cancel_invoice, reverse_payment
        from apps.inventory.services import record_movement

        # Tartib muhim: avval to'lov (taqsimot bo'shaydi), keyin faktura
        # — to'langan fakturani bekor qilib bo'lmaydi.
        for payment in plan.payments:
            reverse_payment(payment=payment, reason=REASON)
            self._audit(organization, "update", "payment", payment.id, reversed=str(payment.amount))

        for invoice in plan.invoices:
            invoice.refresh_from_db()
            cancel_invoice(invoice=invoice, reason=REASON)
            self._audit(organization, "update", "invoice", invoice.id, cancelled=invoice.number)

        for record in plan.attendance:
            snapshot = {
                "child_id": str(record.child_id),
                "date": record.attendance_date.isoformat(),
                "status": record.status,
            }
            record.delete()
            self._audit(organization, "delete", "attendance_record", record.pk, record=snapshot)

        if plan.child is not None:
            archive_child(child=plan.child, reason=REASON)
            self._audit(organization, "update", "child", plan.child.id, archived=True)

        if plan.guardian is not None:
            plan.guardian.is_active = False
            plan.guardian.save(update_fields=["is_active", "updated_at"])
            self._audit(organization, "update", "guardian", plan.guardian.id, is_active=False)

        if plan.product is not None:
            for warehouse, quantity in plan.stock:
                record_movement(
                    product=plan.product,
                    warehouse=warehouse,
                    movement_type="adjustment",
                    quantity=abs(quantity),
                    direction="out" if quantity > 0 else "in",
                    note=REASON,
                    create_expense=False,
                )
            plan.product.is_active = False
            plan.product.save(update_fields=["is_active", "updated_at"])
            self._audit(
                organization, "update", "product", plan.product.id,
                is_active=False, stock_zeroed=[str(q) for _, q in plan.stock],
            )  # fmt: skip

        for expense in plan.expenses:
            cash.reverse_movements_for(
                source_type=MovementSource.EXPENSE, source_id=expense.id, description=REASON
            )
            expense.is_active = False
            expense.save(update_fields=["is_active", "updated_at"])
            self._audit(organization, "update", "expense", expense.id, is_active=False)

        if plan.category is not None:
            plan.category.is_active = False
            plan.category.save(update_fields=["is_active", "updated_at"])
            self._audit(
                organization, "update", "expense_category", plan.category.id, is_active=False
            )
