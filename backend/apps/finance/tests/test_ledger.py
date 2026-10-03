"""
Ledger va hisob-faktura testlari — loyihadagi eng yuqori bar (docs/06 §8).

Noto'g'ri hisoblangan balans mijozning ishonchini yo'qotadi va uni qayta
qozonish qiyin. Shuning uchun bu yerda "ishlaydi" yetarli emas: har bir
invariant alohida qotiriladi.
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
from apps.finance import services
from apps.finance.models import (
    ChildLedgerEntry,
    Direction,
    Discount,
    EntryType,
    Invoice,
    InvoiceStatus,
    SourceType,
    TariffPlan,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def tariff(tenant_a) -> TariffPlan:
    with organization_context(tenant_a.organization.id):
        return TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000.00"),
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


class TestLedgerContract:
    def test_balance_is_debits_minus_credits(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.post_ledger_entry(
                child=child,
                entry_type=EntryType.CHARGE,
                direction=Direction.DEBIT,
                amount=Decimal("1000000"),
                source_type=SourceType.MANUAL,
            )
            services.post_ledger_entry(
                child=child,
                entry_type=EntryType.PAYMENT,
                direction=Direction.CREDIT,
                amount=Decimal("400000"),
                source_type=SourceType.MANUAL,
            )
            assert services.child_balance(child.id) == Decimal("600000.00")

    def test_amount_must_be_positive(self, tenant_a, child):
        """Ishora `direction` dan keladi, summadan emas."""
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation),
        ):
            services.post_ledger_entry(
                child=child,
                entry_type=EntryType.CHARGE,
                direction=Direction.DEBIT,
                amount=Decimal("-500"),
                source_type=SourceType.MANUAL,
            )

    def test_database_rejects_negative_amount(self, tenant_a, child):
        """Servis chetlab oʻtilsa ham baza toʻsadi (D1)."""
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            ChildLedgerEntry.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                entry_type=EntryType.CHARGE,
                direction=Direction.DEBIT,
                amount=Decimal("-100"),
                source_type=SourceType.MANUAL,
                # `date.today()` EMAS: u `DateTimeField` ga yarim tundagi naive
                # vaqt bo'lib tushadi va D7 ("har doim timestamptz") buziladi.
                occurred_at=timezone.now(),
            )

    def test_cached_balance_is_never_the_source_of_truth(self, tenant_a, child):
        """
        Keshni ataylab buzib, ledger'dan tiklanishini tekshiramiz.

        Agar biror kod keshga ishonib qolsa, bu test uni ushlaydi.
        """
        with organization_context(tenant_a.organization.id):
            services.post_ledger_entry(
                child=child,
                entry_type=EntryType.CHARGE,
                direction=Direction.DEBIT,
                amount=Decimal("750000"),
                source_type=SourceType.MANUAL,
            )
            Child.objects.filter(pk=child.pk).update(balance=Decimal("999999"))

            assert services.child_balance(child.id) == Decimal("750000.00")
            assert services.recompute_child_balance(child) == Decimal("750000.00")
            child.refresh_from_db()
            assert child.balance == Decimal("750000.00")


class TestInvoiceIssuing:
    def test_issuing_posts_a_debit_to_the_ledger(self, tenant_a, child, tariff):
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)

            entries = ChildLedgerEntry.objects.filter(
                source_type=SourceType.INVOICE, source_id=invoice.id
            )
            assert entries.count() == 1
            entry = entries.first()
            assert entry.direction == Direction.DEBIT
            assert entry.amount == tariff.amount
            assert services.child_balance(child.id) == tariff.amount

    def test_issuing_twice_is_idempotent(self, tenant_a, child):
        """
        Bir bola — bir davr — bitta hisob-faktura.

        Bu ikki marta hisoblashdan himoya qiladi: oylik vazifa qayta
        ishga tushsa (retry, qo'lda takror) balans ikkilanmaydi.
        """
        with organization_context(tenant_a.organization.id):
            first = services.issue_invoice(child=child, period_year=2026, period_month=7)
            second = services.issue_invoice(child=child, period_year=2026, period_month=7)

            assert first.id == second.id
            assert Invoice.objects.filter(child=child).count() == 1
            assert ChildLedgerEntry.objects.filter(child=child).count() == 1

    def test_database_blocks_duplicate_period(self, tenant_a, child):
        """Servis chetlab oʻtilsa ham qisman unikal indeks toʻsadi."""
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=7)
            with pytest.raises(IntegrityError), transaction.atomic():
                Invoice.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    number="QOLBAKI-1",
                    child=child,
                    period_year=2026,
                    period_month=7,
                    amount_due=Decimal("1"),
                    issued_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                )

    def test_child_without_tariff_is_rejected(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            orphan = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Tarifsiz",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="female",
            )
            with pytest.raises(BusinessRuleViolation, match="tarif"):
                services.issue_invoice(child=orphan, period_year=2026, period_month=7)

    def test_invoice_number_is_sequential_per_branch(self, tenant_a, tariff):
        with organization_context(tenant_a.organization.id):
            numbers = []
            for index in range(3):
                kid = Child.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    first_name=f"Bola{index}",
                    last_name="Testov",
                    date_of_birth=date(2021, 1, 1),
                    gender="male",
                    tariff=tariff,
                )
                numbers.append(
                    services.issue_invoice(child=kid, period_year=2026, period_month=7).number
                )
        assert numbers == ["MAIN-202607-0001", "MAIN-202607-0002", "MAIN-202607-0003"]


class TestDiscounts:
    def test_percent_discount_reduces_the_invoice(self, tenant_a, child, tariff):
        with organization_context(tenant_a.organization.id):
            Discount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                discount_type="percent",
                value=Decimal("20"),
                valid_from=date(2026, 1, 1),
                reason="Aka-uka",
            )
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
            # Satrlarni KONTEKST ICHIDA sanaymiz: `invoice_line` ham RLS
            # ostida (ota `invoice` orqali), ya'ni tashqarida so'rov
            # bo'sh qaytadi.
            line_count = invoice.lines.count()

        assert invoice.amount_due == Decimal("1200000.00")
        assert line_count == 2  # tarif + chegirma satri

    def test_fixed_discount_reduces_the_invoice(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            Discount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                discount_type="fixed",
                value=Decimal("500000"),
                valid_from=date(2026, 1, 1),
            )
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
        assert invoice.amount_due == Decimal("1000000.00")

    def test_discount_cannot_make_the_invoice_negative(self, tenant_a, child):
        """
        Tarifdan katta chegirma hisob-fakturani manfiy qilmasligi kerak —
        aks holda bog'cha bolaga qarzdor bo'lib qolardi.
        """
        with organization_context(tenant_a.organization.id):
            Discount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                discount_type="fixed",
                value=Decimal("99000000"),
                valid_from=date(2026, 1, 1),
            )
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
        assert invoice.amount_due == Decimal("0.00")

    def test_expired_discount_is_ignored(self, tenant_a, child, tariff):
        with organization_context(tenant_a.organization.id):
            Discount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                discount_type="percent",
                value=Decimal("50"),
                valid_from=date(2025, 1, 1),
                valid_to=date(2025, 12, 31),
            )
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
        assert invoice.amount_due == tariff.amount


class TestCancellation:
    def test_cancel_posts_a_counter_entry_not_a_delete(self, tenant_a, child, tariff):
        """
        Bekor qilish ledger'dan qator O'CHIRMAYDI — teng kredit qo'shadi.

        Shunda "nima boʻldi?" degan savolga jurnal javob beradi.
        """
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
            services.cancel_invoice(invoice=invoice, reason="Xato chiqarilgan")

            entries = ChildLedgerEntry.objects.filter(child=child).order_by("created_at")
            assert entries.count() == 2
            assert entries[0].direction == Direction.DEBIT
            assert entries[1].direction == Direction.CREDIT
            assert entries[1].entry_type == EntryType.ADJUSTMENT
            assert services.child_balance(child.id) == Decimal("0.00")

            invoice.refresh_from_db()
            assert invoice.status == InvoiceStatus.CANCELLED

    def test_cancelled_period_can_be_reissued(self, tenant_a, child):
        """Bekor qilingandan keyin oʻsha davrga yangisini chiqarish mumkin."""
        with organization_context(tenant_a.organization.id):
            first = services.issue_invoice(child=child, period_year=2026, period_month=7)
            services.cancel_invoice(invoice=first)
            second = services.issue_invoice(child=child, period_year=2026, period_month=7)

        assert second.id != first.id
        assert second.status == InvoiceStatus.ISSUED

    def test_paid_invoice_cannot_be_cancelled(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
            Invoice.objects.filter(pk=invoice.pk).update(amount_paid=Decimal("100000"))
            invoice.refresh_from_db()
            with pytest.raises(BusinessRuleViolation, match="qaytaring"):
                services.cancel_invoice(invoice=invoice)


class TestMonthlyRun:
    @pytest.fixture
    def three_children(self, tenant_a, tariff):
        with organization_context(tenant_a.organization.id):
            return [
                Child.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    first_name=f"Bola{index}",
                    last_name="Testov",
                    date_of_birth=date(2021, 1, 1),
                    gender="male",
                    tariff=tariff,
                )
                for index in range(3)
            ]

    def test_generates_for_every_active_child(self, tenant_a, three_children, tariff):
        with organization_context(tenant_a.organization.id):
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=7
            )
        assert result.created == 3
        assert result.total_amount == tariff.amount * 3

    def test_rerunning_creates_nothing(self, tenant_a, three_children):
        """
        Oylik vazifa ikki marta ishga tushsa (retry yoki qo'lda takror)
        ikkinchi marta hisoblanmasligi SHART.
        """
        with organization_context(tenant_a.organization.id):
            services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=7
            )
            second = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=7
            )
            total = services.child_balance(three_children[0].id)

        assert second.created == 0
        assert second.skipped_existing == 3
        assert total == Decimal("1500000.00")  # ikkilanmagan

    def test_child_without_tariff_is_reported_not_fatal(self, tenant_a, three_children):
        """
        Bitta bolaning nosozligi butun ishni to'xtatmaydi.

        200 bolali bog'chada bitta tarifsiz bola oyni bloklab qo'ymasligi
        kerak — u hisobotga tushadi va qolganlari o'z hisob-fakturasini oladi.
        """
        with organization_context(tenant_a.organization.id):
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Tarifsiz",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="female",
            )
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=7
            )
        assert result.created == 3
        assert result.skipped_no_tariff == ["Bola Tarifsiz"]

    def test_inactive_children_are_skipped(self, tenant_a, three_children):
        with organization_context(tenant_a.organization.id):
            Child.objects.filter(pk=three_children[0].pk).update(is_active=False)
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=7
            )
        assert result.created == 2

    @pytest.mark.tenancy
    def test_run_never_touches_another_tenant(self, tenant_a, tenant_b, three_children):
        with organization_context(tenant_b.organization.id):
            other_tariff = TariffPlan.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                name="Beta tarif",
                amount=Decimal("900000"),
            )
            Child.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Beta",
                last_name="Bolasi",
                date_of_birth=date(2021, 1, 1),
                gender="male",
                tariff=other_tariff,
            )

        with organization_context(tenant_a.organization.id):
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=7
            )
        assert result.created == 3  # tenant_b ning bolasi tegilmagan

        with organization_context(tenant_b.organization.id):
            assert Invoice.objects.count() == 0


class TestOverdue:
    def test_marks_only_past_due_unpaid_invoices(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(
                child=child,
                period_year=2026,
                period_month=7,
                issued_date=date.today() - timedelta(days=30),
                due_date=date.today() - timedelta(days=20),
            )
            count = services.mark_overdue_invoices(organization_id=tenant_a.organization.id)
            invoice.refresh_from_db()

        assert count == 1
        assert invoice.status == InvoiceStatus.OVERDUE


class TestEndpoints:
    def test_generate_endpoint_is_idempotent(self, tenant_a, child):
        client = tenant_a.client()
        url = reverse("v1:invoice-generate")
        body = {"period_year": 2026, "period_month": 7}

        first = client.post(url, body, format="json")
        second = client.post(url, body, format="json")

        assert first.status_code == 200
        assert first.json()["data"]["created"] == 1
        assert second.json()["data"]["created"] == 0
        assert second.json()["data"]["skipped_existing"] == 1

    def test_invoices_are_read_only(self, tenant_a, child):
        """
        Hisob-faktura API orqali tahrirlanmaydi — u ledger yozuvini
        yaratgan hujjat (D3).
        """
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)

        client = tenant_a.client()
        url = reverse("v1:invoice-detail", args=[invoice.id])
        assert client.patch(url, {"amount_due": "1"}, format="json").status_code == 405
        assert client.delete(url).status_code == 405

    def test_ledger_has_no_write_endpoint(self, tenant_a, child):
        """Ledgerʼga API orqali qoʻlda yozuv qoʻshib boʻlmaydi."""
        client = tenant_a.client()
        response = client.post(
            reverse("v1:ledger-list"),
            {"child": str(child.id), "amount": "1000", "direction": "credit"},
            format="json",
        )
        assert response.status_code == 405

    def test_balance_endpoint_reads_the_ledger(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=7)
            Child.objects.filter(pk=child.pk).update(balance=Decimal("0"))  # keshni buzamiz

        response = tenant_a.client().get(reverse("v1:ledger-balance"), {"child": str(child.id)})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["balance"] == "1500000.00"  # ledger'dan
        assert data["cached_balance"] == "0.00"  # buzilgan kesh

    @pytest.mark.tenancy
    def test_balance_endpoint_rejects_another_tenants_child(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            foreign = Child.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Begona",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="male",
            )
        response = tenant_a.client().get(reverse("v1:ledger-balance"), {"child": str(foreign.id)})
        # 404 — 422 emas (CLAUDE.md, invariant 2): begona qator "mavjud emas".
        assert response.status_code == 404
        assert "topilmadi" in response.json()["error"]["message"]

    def test_cashier_can_generate_invoices(self, tenant_a, child):
        """Kassirda `payments` toʻliq (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Kassir",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = client.post(
            reverse("v1:invoice-generate"),
            {"period_year": 2026, "period_month": 7},
            format="json",
        )
        assert response.status_code == 200
