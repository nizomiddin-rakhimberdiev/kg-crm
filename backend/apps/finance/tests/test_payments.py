"""
To'lov va qarzdorlar testlari — pul yadrosining yakuni.

Bu yerdagi asosiy savol: "balans qachondir notoʻgʻri boʻlib qola oladimi?"
Har bir test shu savolning bitta ehtimolli javobini yopadi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import selectors, services
from apps.finance.models import (
    ChildLedgerEntry,
    Direction,
    EntryType,
    Invoice,
    InvoiceStatus,
    Payment,
    TariffPlan,
)

pytestmark = pytest.mark.django_db

AMOUNT = Decimal("1500000.00")


@pytest.fixture
def tariff(tenant_a) -> TariffPlan:
    with organization_context(tenant_a.organization.id):
        return TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=AMOUNT,
        )


@pytest.fixture
def child(tenant_a, tariff) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
        )


@pytest.fixture
def invoice(tenant_a, child) -> Invoice:
    with organization_context(tenant_a.organization.id):
        return services.issue_invoice(child=child, period_year=2026, period_month=7)


class TestRecordPayment:
    def test_full_payment_settles_the_invoice(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=AMOUNT, method="cash", invoice=invoice)
            invoice.refresh_from_db()
            assert invoice.status == InvoiceStatus.PAID
            assert invoice.amount_paid == AMOUNT
            assert services.child_balance(child.id) == Decimal("0.00")

    def test_partial_payment_marks_partially_paid(self, tenant_a, child):
        """Muddati kelmagan hisob-faktura qisman toʻlanganda `partially_paid`."""
        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            current = services.issue_invoice(
                child=child,
                period_year=today.year,
                period_month=today.month,
                issued_date=today,
                due_date=today + timedelta(days=10),
            )
            services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=current
            )
            current.refresh_from_db()
            assert current.status == InvoiceStatus.PARTIALLY_PAID
            assert services.child_balance(child.id) == Decimal("1000000.00")

    def test_past_due_partial_payment_becomes_overdue(self, tenant_a, child, invoice):
        """
        Muddati o'tgan va to'liq to'lanmagan hisob-faktura `overdue` bo'ladi.

        `partially_paid` bo'lib qolsa, u qarzdorlar ekranida "muddati
        o'tgan" filtriga tushmasdi va kassir uni ko'rmasdan qolardi.
        """
        with organization_context(tenant_a.organization.id):
            services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=invoice
            )
            invoice.refresh_from_db()
        assert invoice.due_date < timezone.localdate()
        assert invoice.status == InvoiceStatus.OVERDUE

    def test_payment_writes_a_credit_to_the_ledger(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(
                child=child, amount=AMOUNT, method="terminal", invoice=invoice
            )
            entry = ChildLedgerEntry.objects.get(source_id=payment.id)
        assert entry.direction == Direction.CREDIT
        assert entry.entry_type == EntryType.PAYMENT
        assert entry.amount == AMOUNT

    def test_overpayment_becomes_an_advance(self, tenant_a, child, invoice):
        """
        Ortiqcha to'lov RAD ETILMAYDI — ortig'i avans bo'lib qoladi (Q1).

        Ilgari bu `BusinessRuleViolation` edi. Sabab tushunarli:
        `amount_paid <= amount_due` invariantini saqlash kerak edi. Lekin
        natijada ota-ona ikki oylik pulni bir marta keltirganda kassir
        summani qo'lda bo'lib, ikki marta kiritishga majbur bo'lardi —
        va bu xatoga eng qulay joy.

        Endi invariantni TAQSIMOT saqlaydi: hujjatga faqat qoldig'icha
        biriktiriladi, ortig'i esa hech qaysi hujjatga tegishli bo'lmagan
        pul — ya'ni avans — bo'lib turadi.
        """
        with organization_context(tenant_a.organization.id):
            services.record_payment(
                child=child, amount=AMOUNT + Decimal("200000"), method="cash", invoice=invoice
            )
            invoice.refresh_from_db()

            assert invoice.amount_paid == AMOUNT, "hisob-faktura ortiqcha toʻlanmaydi"
            assert invoice.status == InvoiceStatus.PAID
            assert services.child_advance(child) == Decimal("200000.00")
            # Balans manfiy — bog'cha oilaga qarzdor.
            assert services.child_balance(child.id) == Decimal("-200000.00")

    def test_unlinked_advance_payment_creates_credit_balance(self, tenant_a, child):
        """Hisob-fakturasiz toʻlov — avans, balans manfiy boʻladi."""
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=Decimal("300000"), method="cash")
            assert services.child_balance(child.id) == Decimal("-300000.00")

    def test_payment_to_cancelled_invoice_is_rejected(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            services.cancel_invoice(invoice=invoice)
            invoice.refresh_from_db()
            with pytest.raises(BusinessRuleViolation, match="Bekor qilingan"):
                services.record_payment(
                    child=child, amount=Decimal("100"), method="cash", invoice=invoice
                )

    def test_payment_for_another_childs_invoice_is_rejected(self, tenant_a, child, invoice, tariff):
        with organization_context(tenant_a.organization.id):
            other = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Boshqa",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="female",
                tariff=tariff,
            )
            with pytest.raises(BusinessRuleViolation, match="boshqa bolaga"):
                services.record_payment(
                    child=other, amount=Decimal("100"), method="cash", invoice=invoice
                )

    def test_database_rejects_non_positive_amount(self, tenant_a, child):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            Payment.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                amount=Decimal("0"),
                method="cash",
                paid_at=timezone.now(),
            )


class TestInvoiceStateIsRecomputed:
    def test_amount_paid_is_recomputed_not_incremented(self, tenant_a, child, invoice):
        """
        `amount_paid` qo'shish bilan emas, QAYTA HISOBLASH bilan yangilanadi.

        Keshni ataylab buzib, keyingi to'lovda to'g'rilanishini tekshiramiz —
        inkremental yangilash bunday holatda siljigan qiymatni saqlab qolardi.
        """
        with organization_context(tenant_a.organization.id):
            services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=invoice
            )
            Invoice.objects.filter(pk=invoice.pk).update(amount_paid=Decimal("999"))

            services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=invoice
            )
            invoice.refresh_from_db()

        assert invoice.amount_paid == Decimal("1000000.00")


class TestReversal:
    def test_reversal_posts_a_debit_and_keeps_the_original(self, tenant_a, child, invoice):
        """
        Qaytarish o'chirmaydi — teng debet qo'shadi.

        Kassa jurnali "qabul qilindi, keyin qaytarildi" deb ko'rsatishi
        kerak, "hech narsa boʻlmagan" emas.
        """
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(
                child=child, amount=AMOUNT, method="cash", invoice=invoice
            )
            services.reverse_payment(payment=payment, reason="Xato summa")

            entries = list(ChildLedgerEntry.objects.filter(child=child).order_by("created_at"))
            payment.refresh_from_db()
            invoice.refresh_from_db()
            still_exists = Payment.objects.filter(pk=payment.pk).exists()
            balance = services.child_balance(child.id)

        assert still_exists, "Qaytarilgan toʻlov qatori oʻchirilmasligi kerak"
        assert payment.is_reversed
        assert [e.direction for e in entries] == [
            Direction.DEBIT,  # hisob-faktura
            Direction.CREDIT,  # to'lov
            Direction.DEBIT,  # qaytarish
        ]
        assert balance == AMOUNT
        # Muddati o'tgan bo'lgani uchun `overdue`; muhimi — to'lanmagan holatga
        # qaytgani.
        assert invoice.status in (InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE)
        assert invoice.amount_paid == Decimal("0.00")

    def test_double_reversal_is_rejected(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(
                child=child, amount=AMOUNT, method="cash", invoice=invoice
            )
            services.reverse_payment(payment=payment, reason="Kassir xato kiritdi")
            with pytest.raises(BusinessRuleViolation, match="allaqachon"):
                services.reverse_payment(payment=payment, reason="Kassir xato kiritdi")

    def test_reversed_payment_is_excluded_from_daily_summary(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            good = services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=invoice
            )
            bad = services.record_payment(
                child=child, amount=Decimal("300000"), method="cash", invoice=invoice
            )
            services.reverse_payment(payment=bad, reason="Kassir xato kiritdi")

            summary = services.daily_cash_summary(
                organization_id=tenant_a.organization.id, on_date=timezone.localdate()
            )
        assert summary["total"] == "500000.00"
        assert summary["reversed_total"] == "300000.00"
        del good


class TestDebtorsAreDerived:
    def test_no_debtor_table_exists(self):
        """
        `debtor` jadvali BO'LMASLIGI kerak (ADR-7).

        Agar kimdir uni qo'shsa, ro'yxat ertami kechmi ledger bilan mos
        kelmay qoladi va "qaysi biri toʻgʻri?" degan javobsiz savol
        paydo bo'ladi.
        """
        from django.apps import apps as django_apps

        tables = {model._meta.db_table for model in django_apps.get_models()}
        assert "debtor" not in tables

    def test_debtor_list_comes_from_the_ledger(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            rows = selectors.debtor_rows()
        assert len(rows) == 1
        assert rows[0]["child"]["full_name"] == "Valiyev Ali"
        assert rows[0]["balance"] == "1500000.00"

    def test_paying_removes_the_child_from_the_list(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=AMOUNT, method="cash", invoice=invoice)
            assert selectors.debtor_rows() == []

    def test_list_ignores_the_cached_balance(self, tenant_a, child, invoice):
        """
        Kesh siljigan bo'lsa ham ro'yxat to'g'ri qoladi.

        Bu eng muhim: noto'g'ri qarzdorlar ro'yxati eng yomon joyda —
        ota-onadan pul talab qilishda — chiqardi.
        """
        with organization_context(tenant_a.organization.id):
            Child.objects.filter(pk=child.pk).update(balance=Decimal("0"))
            rows = selectors.debtor_rows()
        assert len(rows) == 1
        assert rows[0]["balance"] == "1500000.00"

    def test_advance_payment_is_not_a_debtor(self, tenant_a, child):
        """Manfiy balans (avans) — qarzdor emas."""
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=Decimal("200000"), method="cash")
            assert selectors.debtor_rows() == []

    def test_overdue_filter(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(
                child=child,
                period_year=2026,
                period_month=6,
                issued_date=date.today() - timedelta(days=40),
                due_date=date.today() - timedelta(days=30),
            )
            assert len(selectors.debtor_rows(overdue_only=True)) == 1
            assert len(selectors.debtor_rows(min_amount=Decimal("99999999"))) == 0

    @pytest.mark.tenancy
    def test_debtors_never_cross_tenants(self, tenant_a, tenant_b, child, invoice):
        with organization_context(tenant_b.organization.id):
            assert selectors.debtor_rows() == []


class TestStatement:
    def test_running_balance_is_cumulative(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=invoice
            )
            statement = selectors.child_statement(child=child)

        running = [line["running_balance"] for line in statement["entries"]]
        assert running == ["1500000.00", "1000000.00"]
        assert statement["balance"] == "1000000.00"


class TestEndpoints:
    def test_record_payment_endpoint(self, tenant_a, child, invoice):
        response = tenant_a.client().post(
            reverse("v1:payment-list"),
            {
                "child_id": str(child.id),
                "invoice_id": str(invoice.id),
                "amount": "1500000.00",
                "method": "cash",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["amount"] == "1500000.00"

    def test_payments_cannot_be_edited_or_deleted(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(
                child=child, amount=AMOUNT, method="cash", invoice=invoice
            )
        client = tenant_a.client()
        url = reverse("v1:payment-detail", args=[payment.id])
        assert client.patch(url, {"amount": "1"}, format="json").status_code == 405
        assert client.delete(url).status_code == 405

    def test_reverse_endpoint(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(
                child=child, amount=AMOUNT, method="cash", invoice=invoice
            )
        response = tenant_a.client().post(
            reverse("v1:payment-reverse", args=[payment.id]),
            {"reason": "Xato summa"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_reversed"] is True

    def test_debtors_endpoint(self, tenant_a, child, invoice):
        response = tenant_a.client().get(reverse("v1:debtor-list"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 1
        assert data["total_debt"] == "1500000.00"

    def test_debtor_detail_returns_statement(self, tenant_a, child, invoice):
        response = tenant_a.client().get(reverse("v1:debtor-detail", args=[child.id]))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["balance"] == "1500000.00"
        assert len(data["entries"]) == 1
        assert len(data["open_invoices"]) == 1

    @pytest.mark.tenancy
    def test_debtor_detail_rejects_another_tenants_child(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            foreign = Child.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Begona",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="male",
            )
        # `404`, `422` emas: begona tashkilotning qatori uchun javob
        # qolgan HAMMA endpoint bilan bir xil bo'lishi kerak (docs/04 §2).
        # Avval bu yerda `422` qaytardi va shu farqning o'zi bitta
        # endpointning boshqacha ishlashini oshkor qilardi.
        response = tenant_a.client().get(reverse("v1:debtor-detail", args=[foreign.id]))
        assert response.status_code == 404

    def test_daily_summary_endpoint(self, tenant_a, child, invoice):
        with organization_context(tenant_a.organization.id):
            services.record_payment(
                child=child, amount=Decimal("500000"), method="cash", invoice=invoice
            )
        response = tenant_a.client().get(reverse("v1:payment-daily-summary"))
        assert response.status_code == 200
        assert response.json()["data"]["total"] == "500000.00"

    def test_attendance_manager_cannot_touch_payments(self, tenant_a, child):
        """Davomat menejerida `payments` yoʻq (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            monitor = User.objects.create_user(
                email="dav@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Davomat",
                organization=tenant_a.organization,
                role=tenant_a.role("attendance_manager"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(monitor)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:payment-list")).status_code == 403


class TestIdempotencyOverTheApi:
    """
    `Idempotency-Key` sarlavhasi (P1-003).

    Servis darajasidagi poyga testi `test_concurrency.py` da; bu yerda
    esa API SIMI tekshiriladi — sarlavha o'qiladimi va u servisga
    yetib boradimi.
    """

    def _payload(self, child):
        return {"child_id": str(child.id), "amount": "100000", "method": "cash"}

    def test_the_same_key_records_one_payment(self, tenant_a, child):
        client = tenant_a.client()
        key = "форма-1"

        first = client.post(
            reverse("v1:payment-list"),
            self._payload(child),
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        second = client.post(
            reverse("v1:payment-list"),
            self._payload(child),
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

        assert first.status_code == 201
        assert second.status_code == 201
        # Ikkala javob ham AYNAN bir xil to'lovni ko'rsatadi.
        assert first.json()["data"]["id"] == second.json()["data"]["id"]

        with organization_context(tenant_a.organization.id):
            assert Payment.objects.filter(child=child).count() == 1

    def test_without_a_key_nothing_changes(self, tenant_a, child):
        """
        Kalitsiz so'rov avvalgidek ishlaydi.

        Eski mijozlar va skriptlar buzilmasin — lekin ular
        takrorlanishdan himoyalanmagan va bu ataylab shunday: majburiy
        kalit mavjud integratsiyalarni bir kechada sindirardi.
        """
        client = tenant_a.client()
        for _ in range(2):
            assert (
                client.post(
                    reverse("v1:payment-list"), self._payload(child), format="json"
                ).status_code
                == 201
            )

        with organization_context(tenant_a.organization.id):
            assert Payment.objects.filter(child=child).count() == 2

    def test_one_tenants_key_does_not_collide_with_another(self, tenant_a, tenant_b):
        """
        Kalit tashkilot ICHIDA unikal.

        Global unikal bo'lsa, bir bog'chaning kaliti boshqasining
        to'lovini bloklardi — va bu chalkash, takrorlanmaydigan
        nosozlik bo'lardi.
        """
        from apps.children.models import Child

        key = "bir-xil-kalit"
        for tenant in (tenant_a, tenant_b):
            with organization_context(tenant.organization.id):
                kid = Child.objects.create(
                    organization=tenant.organization,
                    branch=tenant.branch,
                    first_name="Bola",
                    last_name="Testov",
                    date_of_birth=date(2021, 3, 14),
                    gender="male",
                )
            response = tenant.client().post(
                reverse("v1:payment-list"),
                {"child_id": str(kid.id), "amount": "50000", "method": "cash"},
                format="json",
                HTTP_IDEMPOTENCY_KEY=key,
            )
            assert response.status_code == 201, response.content
