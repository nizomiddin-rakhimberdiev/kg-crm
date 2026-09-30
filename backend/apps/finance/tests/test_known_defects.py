"""
Ma'lum moliyaviy kamchiliklar — 2026-09-30 production auditi.

Har bir test KUTILAYOTGAN xatti-harakatni yozadi va hozir yiqiladi:
u xatoni takrorlaydi, tuzatmaydi. Tuzatish 1-bosqichda
(`docs/big-update/PLAN.md` §3).

`xfail(strict=True)` ataylab:
  * hozir — CI yashil qoladi, lekin xato hujjatlashtirilgan;
  * tuzatilgach — test XPASS bo'ladi, `strict` uni XATO deb belgilaydi
    va marker'ni olib tashlashga majbur qiladi. Ya'ni "tuzatdim, lekin
    testni yoqishni unutdim" holati mumkin emas.

Audit holatlari shu yerda qayta tiklangan:
  * Ibragimov Robiya — avans to'lovlar, lekin faktura "To'lanmagan"
  * TEST Sinov Claude — yaratilgan kuniyoq 20 kun kechikkan faktura
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import selectors, services
from apps.finance.models import Invoice, InvoiceStatus, TariffPlan

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

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


def _child(tenant_a, tariff, *, first: str, last: str, enrolled_on: date | None = None) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name=first,
            last_name=last,
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
            enrolled_on=enrolled_on,
        )


def _board_row(tenant_a, child, year: int, month: int) -> dict:
    """Bolaning To'lovlar doskasidagi qatori."""
    queryset = selectors.month_board_queryset(
        organization_id=tenant_a.organization.id, period_year=year, period_month=month
    )
    row = next(r for r in queryset if r.id == child.id)
    return selectors.board_row(row)


def _debtor_row(tenant_a, child) -> dict | None:
    """Bolaning Qarzdorlar ro'yxatidagi qatori (bo'lmasa None)."""
    return next(
        (r for r in selectors.debtor_rows() if r["child"]["id"] == str(child.id)),
        None,
    )


class TestBalanceIsOneNumber:
    """
    PLAN 1.1 — bitta bola, bitta qarz.

    Tizimda ikkita mustaqil hisob bor: ledger (`Σ debet − Σ kredit`) va
    faktura keshi (`amount_due − amount_paid`). Avans faqat birinchisiga
    tushadi, shuning uchun ikki ekran ikki xil raqam ko'rsatadi.
    """

    def test_advance_payments_show_the_same_debt_on_every_screen(self, tenant_a, tariff):
        # Ibragimov Robiya: 1 500 000 faktura, 830 000 + 540 000 avans.
        child = _child(tenant_a, tariff, first="Robiya", last="Ibragimova")
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            # Avans = hisob-fakturaga bog'lanmagan to'lov (kassir shunday kiritgan).
            services.record_payment(child=child, amount=Decimal("830000"), method="cash")
            services.record_payment(child=child, amount=Decimal("540000"), method="cash")

            board = _board_row(tenant_a, child, 2026, 9)
            debtor = _debtor_row(tenant_a, child)

        # Ledger to'g'ri hisoblaydi: 1 500 000 − 1 370 000 = 130 000.
        assert debtor is not None
        assert Decimal(debtor["balance"]) == Decimal("130000.00")
        # Doska esa 1 500 000 ko'rsatadi — bir ekranda ikki haqiqat.
        assert Decimal(board["outstanding"]) == Decimal("130000.00")

    def test_month_summary_counts_advances(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, first="Robiya", last="Ibragimova")
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            services.record_payment(child=child, amount=Decimal("1370000"), method="cash")

            summary = selectors.month_board_summary(
                organization_id=tenant_a.organization.id, period_year=2026, period_month=9
            )

        assert Decimal(summary["paid"]) == Decimal("1370000.00")
        assert Decimal(summary["outstanding"]) == Decimal("130000.00")


class TestAdvanceAllocation:
    """PLAN 1.2 — Q1: to'lov eng eski ochiq fakturaga (FIFO), qoldiq avans."""

    def test_payment_is_allocated_to_the_oldest_open_invoice(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, first="Robiya", last="Ibragimova")
        with organization_context(tenant_a.organization.id):
            august = services.issue_invoice(child=child, period_year=2026, period_month=8)
            september = services.issue_invoice(child=child, period_year=2026, period_month=9)

            # Kassir fakturani tanlamadi — tizimning o'zi taqsimlashi kerak.
            services.record_payment(child=child, amount=TARIFF, method="cash")

            august.refresh_from_db()
            september.refresh_from_db()

        # FIFO: avval avgust yopiladi, sentabr tegilmaydi.
        assert august.status == InvoiceStatus.PAID
        assert august.amount_paid == TARIFF
        assert september.amount_paid == Decimal("0.00")

    def test_overpayment_flows_to_the_next_invoice_then_stays_as_advance(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, first="Robiya", last="Ibragimova")
        with organization_context(tenant_a.organization.id):
            august = services.issue_invoice(child=child, period_year=2026, period_month=8)
            september = services.issue_invoice(child=child, period_year=2026, period_month=9)

            # Ikki oylik + 200 000 ortiqcha.
            services.record_payment(
                child=child, amount=TARIFF * 2 + Decimal("200000"), method="cash"
            )

            august.refresh_from_db()
            september.refresh_from_db()
            balance = services.child_balance(child.id)

        assert august.status == InvoiceStatus.PAID
        assert september.status == InvoiceStatus.PAID
        # Manfiy balans = bog'cha oilaga qarzdor, ya'ni avans.
        assert balance == Decimal("-200000.00")

    def test_new_invoice_consumes_an_existing_advance(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, first="Sinov", last="Claude")
        with organization_context(tenant_a.organization.id):
            # Avval pul keldi, faktura keyin — audit ssenariysi aynan shu.
            services.record_payment(child=child, amount=Decimal("200000"), method="cash")
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
            invoice.refresh_from_db()

        assert invoice.amount_paid == Decimal("200000.00")
        assert invoice.amount_outstanding == TARIFF - Decimal("200000.00")

    def test_reversal_undoes_the_allocation(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, first="Robiya", last="Ibragimova")
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
            payment = services.record_payment(child=child, amount=TARIFF, method="cash")

            invoice.refresh_from_db()
            assert invoice.status == InvoiceStatus.PAID, "avval taqsimlanishi kerak"

            services.reverse_payment(payment=payment, reason="Kassir xato kiritdi")
            invoice.refresh_from_db()
            balance = services.child_balance(child.id)

        assert invoice.amount_paid == Decimal("0.00")
        assert invoice.status != InvoiceStatus.PAID
        assert balance == TARIFF


class TestFirstInvoice:
    """
    PLAN 1.3 — Q2 va Q3.

    `issue_invoice()` bolaning qabul sanasini umuman ko'rmaydi: davr
    boshidan hisoblaydi va muddatni oyning 10-kuniga qo'yadi. Oyning
    oxirida qabul qilingan bola shu sababli to'liq oy to'laydi va
    fakturasi yaratilgan kuniyoq kechikkan bo'ladi.
    """

    def test_first_invoice_is_prorated_from_the_enrolment_date(self, tenant_a, tariff):
        # 2026-09-30 — chorshanba, sentabrning 22 ish kunidan oxirgisi.
        child = _child(
            tenant_a, tariff, first="Sinov", last="Claude", enrolled_on=date(2026, 9, 30)
        )
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        # 1 500 000 ÷ 22 × 1 = 68 182 (butun so'mgacha).
        assert invoice.amount_due == Decimal("68182.00")

    def test_first_invoice_is_not_overdue_on_the_day_it_is_created(self, tenant_a, tariff):
        child = _child(
            tenant_a, tariff, first="Sinov", last="Claude", enrolled_on=date(2026, 9, 30)
        )
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        # Q3: muddat = max(tashkilot to'lov kuni, qabul + 5 kun).
        assert invoice.due_date >= date(2026, 10, 5)
        assert invoice.issued_date >= child.enrolled_on

    def test_due_day_setting_is_honoured(self, tenant_a, tariff):
        from apps.settings_app.services import set_setting

        child = _child(
            tenant_a, tariff, first="Oy", last="Boshlangan", enrolled_on=date(2026, 9, 1)
        )
        with organization_context(tenant_a.organization.id):
            set_setting(organization=tenant_a.organization, key="finance.due_day", value=15)
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert invoice.due_date.day == 15


class TestInvoiceRunPreview:
    """PLAN 1.4 — ommaviy generatsiyadan oldin nima bo'lishini ko'rsatish."""

    @pytest.mark.xfail(strict=True, reason="PLAN 1.4: preview funksiyasi hali yo'q")
    def test_run_can_be_previewed_before_it_is_committed(self, tenant_a, tariff):
        _child(tenant_a, tariff, first="Bir", last="Bola")
        _child(tenant_a, tariff, first="Tarifsiz", last="Bola").tariff = None

        with organization_context(tenant_a.organization.id):
            preview = services.preview_monthly_invoices(  # type: ignore[attr-defined]
                organization=tenant_a.organization, period_year=2026, period_month=10
            )
            # Preview hech narsa yozmasligi kerak.
            assert not Invoice.objects.filter(period_year=2026, period_month=10).exists()

        assert preview.will_create >= 1
        assert isinstance(preview.skipped_no_tariff, list)
