"""
Konkurentlik testlari — qulflar HAQIQATAN ushlab turadimi (P1-009).

Nega alohida fayl va nega `TransactionTestCase`: pytest-django'ning
odatiy `db` fixture'i har bir testni bitta tranzaksiyaga o'raydi va
oxirida qaytaradi. Bu tez, lekin u yerda ikkinchi ULANISH birinchisining
commit qilinmagan ma'lumotini KO'RMAYDI — ya'ni poyga holatini umuman
qayta tiklab bo'lmaydi. `TransactionTestCase` esa haqiqiy commit
qiladi, shuning uchun bu yerdagi testlar sekinroq va ATAYLAB shunday.

Bu testlar nimani qo'riqlaydi: loyihada to'rt joyda `SELECT ... FOR
UPDATE` bor, lekin ularning ishlashini hech narsa isbotlamasdi. Qulf
tasodifan olib tashlansa, qolgan 618 testning birortasi ham qizarmasdi.
"""

from __future__ import annotations

import threading
import uuid
from datetime import date
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase

from apps.accounts.services import register_organization
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Invoice, InvoiceStatus, Payment, TariffPlan
from apps.inventory import services as inventory
from apps.inventory.models import Product, Warehouse
from apps.subscriptions.models import SubscriptionPlan


def _run_together(target, count: int = 2) -> list:
    """
    `count` ta ipni bir vaqtda ishga tushiradi va natijalarni qaytaradi.

    Har bir ip O'Z baza ulanishini yopadi — Django ulanishlarni ip
    bo'yicha saqlaydi va yopilmasa test bazasini tozalab bo'lmaydi.
    """
    results: list = [None] * count
    barrier = threading.Barrier(count)

    def worker(index: int) -> None:
        try:
            # Barcha iplar AYNAN bir paytda boshlasin — aks holda
            # birinchisi ikkinchisi boshlangunicha tugab ketardi va
            # poyga umuman yuz bermasdi.
            barrier.wait(timeout=10)
            results[index] = target()
        except Exception as exc:  # noqa: BLE001 — natija sifatida qaytaramiz
            results[index] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


class ConcurrencyCase(TransactionTestCase):
    """Har bir test uchun haqiqiy, commit qilingan maʼlumot."""

    def setUp(self) -> None:
        # `TransactionTestCase` har bir testdan keyin JADVALLARNI
        # TOZALAYDI — shu jumladan migratsiya bilan seed qilingan
        # `subscription_plan` ni. Plansiz `register_organization`
        # sinov obunasini ocholmaydi va setUp yiqiladi. Shuning uchun
        # plan shu yerda ta'minlanadi: test o'z sharoitini o'zi quradi.
        SubscriptionPlan.objects.get_or_create(
            code="standard",
            valid_from=date(2026, 1, 1),
            defaults={
                "name": "Standart",
                "currency": "UZS",
                "base_price": Decimal("500000.00"),
                "included_children": 50,
                "overage_step_children": 10,
                "overage_step_price": Decimal("80000.00"),
            },
        )

        self.tenant = register_organization(
            organization_name="Poyga Bogʻchasi",
            contact_email="owner@poyga.uz",
            full_name="Egasi",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106 — test ma'lumoti
        )
        self.org = self.tenant.organization
        with organization_context(self.org.id):
            self.tariff = TariffPlan.objects.create(
                organization=self.org,
                branch=self.tenant.branch,
                name="Toʻliq kun",
                amount=Decimal("1000000"),
            )
            self.child = Child.objects.create(
                organization=self.org,
                branch=self.tenant.branch,
                first_name="Aziza",
                last_name="Testova",
                date_of_birth=date(2021, 3, 14),
                gender="female",
                tariff=self.tariff,
            )

    # --- To'lov: hisob-faktura qulfi ---

    def test_two_cashiers_cannot_overpay_one_invoice(self) -> None:
        """
        Ikki kassir bir vaqtda to'liq summani kiritsa, hisob-faktura
        ORTIQCHA TO'LANMAYDI — lekin ikkala pul ham yo'qolmaydi.

        Ilgari ikkinchi to'lov rad etilardi. Endi (Q1) u qabul qilinadi
        va ortig'i avansga aylanadi: kassaga haqiqatan ikki marta pul
        kelgan bo'lsa, tizim buni inkor eta olmaydi — inkor qilish
        kassani kamomadga solardi.

        Qulf esa o'z ishini qilishda davom etadi: taqsimot paytida
        hujjat qatori `SELECT ... FOR UPDATE` bilan qulflanadi, shuning
        uchun `amount_paid` hech qachon `amount_due` dan oshmaydi.
        `CHECK` buni ushlay olmaydi — u boshqa tranzaksiyani ko'rmaydi.
        """
        with organization_context(self.org.id):
            invoice = finance.issue_invoice(child=self.child, period_year=2026, period_month=3)
            due = invoice.amount_due

        def pay():
            with organization_context(self.org.id):
                return finance.record_payment(
                    child=Child.objects.get(pk=self.child.pk),
                    amount=due,
                    method="cash",
                    invoice=Invoice.objects.get(pk=invoice.pk),
                )

        results = _run_together(pay, count=2)
        succeeded = [r for r in results if isinstance(r, Payment)]
        failed = [r for r in results if isinstance(r, Exception)]

        assert not failed, f"kutilmagan xato: {failed}"
        assert len(succeeded) == 2

        with organization_context(self.org.id):
            invoice.refresh_from_db()
            # Asosiy invariant: hujjat ortiqcha to'lanmaydi.
            assert invoice.amount_paid == due, "hisob-faktura ortiqcha toʻlangan"
            assert invoice.status == InvoiceStatus.PAID
            # Ikkinchi to'lov yo'qolmaydi — u avans bo'lib turadi.
            assert finance.child_advance(Child.objects.get(pk=self.child.pk)) == due

    # --- To'lov: idempotentlik kaliti ---

    def test_the_same_idempotency_key_creates_one_payment(self) -> None:
        """
        Ikki marta bosish — bitta to'lov (P1-003).

        Bu hisob-fakturasiz AVANS to'lov: u yerda qulflanadigan qator
        yo'q, ya'ni yagona himoya — idempotentlik kaliti.
        """
        key = str(uuid.uuid4())

        def pay():
            with organization_context(self.org.id):
                return finance.record_payment(
                    child=Child.objects.get(pk=self.child.pk),
                    amount=Decimal("500000"),
                    method="cash",
                    idempotency_key=key,
                )

        results = _run_together(pay, count=4)
        payments = [r for r in results if isinstance(r, Payment)]
        assert len(payments) == 4, f"hammasi javob qaytarishi kerak edi: {results}"
        assert len({p.id for p in payments}) == 1, "har xil toʻlovlar yaratildi"

        with organization_context(self.org.id):
            assert Payment.objects.filter(child=self.child).count() == 1
            assert finance.child_balance(self.child.id) == Decimal("-500000.00")

    def test_different_keys_create_different_payments(self) -> None:
        """Himoya haqiqiy ikkinchi toʻlovni toʻsib qoʻymasin."""
        with organization_context(self.org.id):
            for _ in range(2):
                finance.record_payment(
                    child=self.child,
                    amount=Decimal("100000"),
                    method="cash",
                    idempotency_key=str(uuid.uuid4()),
                )
            assert Payment.objects.filter(child=self.child).count() == 2

    # --- Ombor: qoldiq qulfi ---

    def test_stock_cannot_go_negative_under_concurrent_issue(self) -> None:
        """
        Ikki chiqim bir vaqtda: qoldiq manfiy bo'lib ketmasligi kerak.
        """
        with organization_context(self.org.id):
            warehouse = Warehouse.objects.create(
                organization=self.org, branch=self.tenant.branch, name="Ombor"
            )
            product = Product.objects.create(
                organization=self.org, branch=self.tenant.branch, name="Guruch", unit="kg"
            )
            inventory.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=Decimal("10"),
            )

        def issue():
            with organization_context(self.org.id):
                return inventory.record_movement(
                    product=Product.objects.get(pk=product.pk),
                    warehouse=Warehouse.objects.get(pk=warehouse.pk),
                    movement_type="consumption",
                    quantity=Decimal("8"),
                )

        results = _run_together(issue, count=2)
        succeeded = [r for r in results if not isinstance(r, Exception)]

        assert len(succeeded) == 1, "ikkala chiqim ham oʻtdi — qoldiq manfiy boʻlardi"
        with organization_context(self.org.id):
            product.refresh_from_db()
            assert product.current_stock == Decimal("2.000")
            assert product.current_stock >= 0

    # --- Oylik generatsiya ---

    def test_a_duplicate_does_not_abort_the_whole_run(self) -> None:
        """
        Bitta to'qnashuv 200 bolani hisob-fakturasiz qoldirmasin (P2-005).

        Avval `IntegrityError` tutilmasdi va butun ishni yiqitardi.
        `acks_late` bilan bu ehtimol ORTDI: qayta yetkazilgan vazifa
        aynan shu holatga tushadi.
        """
        with organization_context(self.org.id):
            others = [
                Child.objects.create(
                    organization=self.org,
                    branch=self.tenant.branch,
                    first_name=f"Bola{index}",
                    last_name="Testov",
                    date_of_birth=date(2021, 3, 14),
                    gender="male",
                    tariff=self.tariff,
                )
                for index in range(3)
            ]
            # Bitta bolada hisob-faktura ALLAQACHON bor.
            finance.issue_invoice(child=others[1], period_year=2026, period_month=7)

            result = finance.generate_monthly_invoices(
                organization=self.org, period_year=2026, period_month=7
            )

            # `self.child` + uchtasi = 4 bola; bittasida allaqachon bor.
            assert result.skipped_existing >= 1
            assert result.created == len(others) + 1 - 1
            for child in [self.child, *others]:
                assert Invoice.objects.filter(
                    child=child, period_year=2026, period_month=7
                ).exists(), f"{child.first_name} hisob-fakturasiz qoldi"

    # --- Hisob-faktura: bir bola, bir davr ---

    def test_one_child_one_period_gets_one_invoice(self) -> None:
        """
        `uq_invoice_child_period` qisman indeksi — oylik generatsiya ikki
        marta ishga tushsa ham ikkinchi hisob-faktura yozilmaydi.
        """

        def issue():
            with organization_context(self.org.id):
                return finance.issue_invoice(
                    child=Child.objects.get(pk=self.child.pk),
                    period_year=2026,
                    period_month=5,
                )

        results = _run_together(issue, count=2)
        invoices = [r for r in results if isinstance(r, Invoice)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(invoices) + len(errors) == 2
        with organization_context(self.org.id):
            count = (
                Invoice.objects.filter(child=self.child, period_year=2026, period_month=5)
                .exclude(status=InvoiceStatus.CANCELLED)
                .count()
            )
            assert count == 1, f"{count} ta hisob-faktura yozildi"
