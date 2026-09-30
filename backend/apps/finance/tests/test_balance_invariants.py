"""
Balans invariantlari — PLAN 1.1.

Bitta bolaning qarzi qaysi ekranda ko'rilsa ham BITTA raqam bo'lishi
kerak. 2026-09-30 auditida shunday emas edi: To'lovlar doskasi
1 500 000, Qarzdorlar 130 000 ko'rsatdi. Sabab — ikkita mustaqil
formula (`docs/big-update/PLAN.md` §2).

Bu fayl tekshiradigan narsa "funksiya to'g'ri ishlaydimi" emas, balki
**ikki funksiya bir-biriga zid javob beryaptimi**. Shuning uchun
testlar bitta amalni emas, REAL KETMA-KETLIKNI o'ynaydi: bir necha oy,
qisman to'lovlar, avans, qaytarish — va har qadamdan keyin barcha
o'quvchilarni solishtiradi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import balance, selectors, services
from apps.finance.models import Invoice, InvoiceStatus, Payment, PaymentAllocation, TariffPlan

pytestmark = pytest.mark.django_db

TARIFF = Decimal("1500000.00")


@pytest.fixture
def tariff(tenant_a) -> TariffPlan:
    with organization_context(tenant_a.organization.id):
        return TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="To'liq kun",
            amount=TARIFF,
        )


@pytest.fixture
def children(tenant_a, tariff) -> list[Child]:
    with organization_context(tenant_a.organization.id):
        return [
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name=name,
                last_name="Testov",
                date_of_birth=date(2021, 3, 14),
                gender="female",
                tariff=tariff,
            )
            for name in ("Robiya", "Malika", "Sevara")
        ]


def _assert_child_invariants(child: Child, year: int, month: int) -> None:
    """Bitta bola: hamma o'quvchi bir xil raqamni bermoqda."""
    detail = balance.child_balance(child)

    # 1. Balans ledger'dan chiqadi: Σ debet − Σ kredit.
    assert detail.balance == detail.charged - detail.credited

    # 2. Bola kartasidagi kesh ledger bilan bir xil.
    child.refresh_from_db()
    assert child.balance == detail.balance, "`child.balance` keshi ledger'dan ajralgan"

    # 3. To'lovlar doskasi.
    row = selectors.board_row(
        next(
            r
            for r in selectors.month_board_queryset(
                organization_id=child.organization_id, period_year=year, period_month=month
            )
            if r.id == child.id
        )
    )
    assert Decimal(row["balance"]) == detail.balance, "doska boshqa balans ko'rsatyapti"
    assert Decimal(row["advance"]) == max(detail.advance, Decimal("0"))

    # 4. Qarzdorlar ro'yxati (faqat musbat balansli bolalar).
    debtor = next(
        (r for r in selectors.debtor_rows() if r["child"]["id"] == str(child.id)),
        None,
    )
    if detail.balance > 0:
        assert debtor is not None, "qarzdor ro'yxatdan tushib qolgan"
        assert Decimal(debtor["balance"]) == detail.balance
    else:
        assert debtor is None, "qarzi yo'q bola qarzdorlar ro'yxatida"

    # 5. Avans = to'langan − taqsimlangan.
    assert detail.advance == detail.paid - detail.allocated


def _assert_ledger_invariants(organization_id) -> None:
    """Tenant darajasidagi invariantlar."""
    # Har bir hisob-fakturaning keshi taqsimotdan kelib chiqadi.
    for invoice in Invoice.objects.all():
        allocated = sum(
            (a.amount for a in invoice.allocations.filter(released_at__isnull=True)),
            Decimal("0"),
        )
        assert invoice.amount_paid == allocated, f"{invoice.number}: kesh taqsimotdan ajralgan"
        assert invoice.amount_paid <= invoice.amount_due, f"{invoice.number}: ortiqcha to'langan"

    # Hech bir to'lov o'zidan ko'proq taqsimlanmagan.
    for payment in Payment.objects.all():
        allocated = sum(
            (a.amount for a in payment.allocations.filter(released_at__isnull=True)),
            Decimal("0"),
        )
        assert allocated <= payment.amount, "to'lov o'zidan ko'proq taqsimlangan"
        if payment.is_reversed:
            assert allocated == 0, "qaytarilgan to'lov hali ham hujjat yopib turibdi"

    # Qarzdorlar yig'indisi = musbat balanslar yig'indisi.
    rows = selectors.debtor_rows()
    listed = sum((Decimal(r["balance"]) for r in rows), Decimal("0"))
    computed = sum(
        (
            b
            for b in (
                balance.child_balance(c).balance for c in Child.objects.filter(is_active=True)
            )
            if b > 0
        ),
        Decimal("0"),
    )
    assert listed == computed, "Qarzdorlardagi 'Jami qarz' bolalar yig'indisiga teng emas"


class TestOneNumberEverywhere:
    def test_a_realistic_month_keeps_every_screen_in_step(self, tenant_a, children):
        """
        Uch bola, ikki oy, to'rt xil to'lov holati.

        Har qadamdan keyin hamma o'quvchi solishtiriladi — chunki
        auditdagi xato aynan qadamlar ORASIDA tug'ilgan edi.
        """
        robiya, malika, sevara = children
        with organization_context(tenant_a.organization.id):
            for child in children:
                services.issue_invoice(child=child, period_year=2026, period_month=8)
                services.issue_invoice(child=child, period_year=2026, period_month=9)

            # Robiya: ikki qismli to'lov, hujjat tanlanmagan (audit holati).
            services.record_payment(child=robiya, amount=Decimal("830000"), method="cash")
            services.record_payment(child=robiya, amount=Decimal("540000"), method="terminal")

            # Malika: ikki oylikdan ko'proq — ortig'i avans bo'lib qoladi.
            services.record_payment(
                child=malika, amount=TARIFF * 2 + Decimal("250000"), method="bank_transfer"
            )

            # Sevara: umuman to'lamagan.

            for child in children:
                _assert_child_invariants(child, 2026, 9)
            _assert_ledger_invariants(tenant_a.organization.id)

            # Raqamlarning o'zi ham to'g'ri bo'lsin, nafaqat bir xil.
            assert balance.child_balance(robiya).balance == TARIFF * 2 - Decimal("1370000")
            assert balance.child_balance(malika).balance == Decimal("-250000.00")
            assert balance.child_balance(malika).advance == Decimal("250000.00")
            assert balance.child_balance(sevara).balance == TARIFF * 2

    def test_reversal_puts_every_screen_back(self, tenant_a, children):
        """Qaytarishdan keyin ham hamma ekran bir xil raqamga qaytadi."""
        robiya = children[0]
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=robiya, period_year=2026, period_month=9)
            payment = services.record_payment(child=robiya, amount=TARIFF, method="cash")

            _assert_child_invariants(robiya, 2026, 9)
            assert balance.child_balance(robiya).balance == Decimal("0.00")

            services.reverse_payment(payment=payment, reason="Kassir xato kiritdi")

            _assert_child_invariants(robiya, 2026, 9)
            _assert_ledger_invariants(tenant_a.organization.id)
            assert balance.child_balance(robiya).balance == TARIFF
            assert balance.child_balance(robiya).advance == Decimal("0.00")

    def test_month_summary_equals_the_sum_of_its_rows(self, tenant_a, children):
        """
        Yuqoridagi "jami" pastdagi qatorlar yig'indisiga teng.

        Ilgari yig'indi faqat yuklangan sahifadan hisoblanardi va har
        doim kam ko'rsatardi; endi u hisob-fakturalardan olinadi — lekin
        baribir qatorlar bilan bir xil bo'lishi SHART.
        """
        with organization_context(tenant_a.organization.id):
            for child in children:
                services.issue_invoice(child=child, period_year=2026, period_month=9)
            services.record_payment(child=children[0], amount=Decimal("500000"), method="cash")

            rows = [
                selectors.board_row(r)
                for r in selectors.month_board_queryset(
                    organization_id=tenant_a.organization.id, period_year=2026, period_month=9
                )
            ]
            summary = selectors.month_board_summary(
                organization_id=tenant_a.organization.id, period_year=2026, period_month=9
            )

        assert Decimal(summary["charged"]) == sum(Decimal(r["charged"]) for r in rows)
        assert Decimal(summary["paid"]) == sum(Decimal(r["paid"]) for r in rows)
        assert Decimal(summary["outstanding"]) == sum(Decimal(r["outstanding"]) for r in rows)


class TestAdvanceIsNotDebt:
    def test_a_child_with_only_an_advance_is_not_a_debtor(self, tenant_a, children):
        """Oldindan to'lagan oila qarzdorlar ro'yxatiga tushmasligi kerak."""
        child = children[0]
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=Decimal("200000"), method="cash")

            assert balance.child_balance(child).advance == Decimal("200000.00")
            assert all(r["child"]["id"] != str(child.id) for r in selectors.debtor_rows())

    def test_advance_is_consumed_by_the_next_invoice(self, tenant_a, children):
        """Keyingi hisob-faktura avansni yeydi — kassir qayta kiritmaydi."""
        child = children[0]
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=Decimal("200000"), method="cash")
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
            invoice.refresh_from_db()

            assert invoice.amount_paid == Decimal("200000.00")
            assert balance.child_balance(child).advance == Decimal("0.00")
            assert PaymentAllocation.objects.filter(invoice=invoice).count() == 1
            _assert_child_invariants(child, 2026, 9)


class TestCancelledInvoiceReleasesMoney:
    def test_cancelling_an_unpaid_invoice_leaves_the_ledger_balanced(self, tenant_a, children):
        child = children[0]
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
            services.cancel_invoice(invoice=invoice, reason="Xato yozilgan")

            assert balance.child_balance(child).balance == Decimal("0.00")
            invoice.refresh_from_db()
            assert invoice.status == InvoiceStatus.CANCELLED
            _assert_ledger_invariants(tenant_a.organization.id)
