"""
Birinchi oy: proporsiya va muddat — PLAN 1.3 (Q2, Q3).

Auditda "TEST Sinov Claude" 30-sentabrda qabul qilindi va unga to'liq
oylik 1 500 000, muddati 10-sentabr bo'lgan hisob-faktura yozildi —
ya'ni bola yaratilgan kuniyoq 20 kun kechikkan qarzdor bo'lib chiqdi.

Bu yerdagi testlar uchta savolni yopadi:
  * qancha? (ish kunlari bo'yicha, bayramlar chiqarib tashlanadi)
  * qachongacha? (to'lov kuni yoki qabul + imtiyoz — qaysi kechroq)
  * qachon proporsiya QO'LLANMAYDI? (ikkinchi oy, sozlama boshqacha)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.attendance.models_absence import Holiday
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services
from apps.finance.models import TariffPlan
from apps.settings_app.services import set_setting

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


def _child(tenant_a, tariff, enrolled_on: date | None) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Sinov",
            last_name="Bolasi",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
            enrolled_on=enrolled_on,
        )


class TestProration:
    @pytest.mark.parametrize(
        ("enrolled_day", "attended_days", "expected"),
        [
            # 2026-09: 22 ish kuni (Du–Ju, bayramsiz).
            (30, 1, Decimal("68182.00")),  # chorshanba, oxirgi ish kuni
            (17, 10, Decimal("681818.00")),  # payshanba
            (1, 22, TARIFF),  # oyning boshi — to'liq oy
        ],
    )
    def test_amount_follows_the_working_days(
        self, tenant_a, tariff, enrolled_day, attended_days, expected
    ):
        child = _child(tenant_a, tariff, date(2026, 9, enrolled_day))
        with organization_context(tenant_a.organization.id):
            share = services.first_month_share(child=child, period_year=2026, period_month=9)
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert share == (attended_days, 22)
        assert invoice.amount_due == expected

    def test_holidays_are_not_charged(self, tenant_a, tariff):
        """
        Bayram kuni ish kuni sanalmaydi — na maxrajda, na suratda.

        Bo'lmasa bog'cha ishlamagan kun uchun pul olgan bo'lardi.
        """
        child = _child(tenant_a, tariff, date(2026, 9, 28))  # dushanba
        with organization_context(tenant_a.organization.id):
            # 29-sentabr (seshanba) yopiq — qolgan 28 va 30 ish kuni.
            Holiday.objects.create(
                organization=tenant_a.organization,
                holiday_date=date(2026, 9, 29),
                name="Sinov bayrami",
            )
            share = services.first_month_share(child=child, period_year=2026, period_month=9)
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        # Oyda 21 ish kuni qoldi, boladan 2 kun.
        assert share == (2, 21)
        assert invoice.amount_due == Decimal("142857.00")

    def test_only_the_first_month_is_prorated(self, tenant_a, tariff):
        """Ikkinchi oy — to'liq tarif, garchi qabul oy o'rtasida bo'lsa ham."""
        child = _child(tenant_a, tariff, date(2026, 9, 17))
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            october = services.issue_invoice(child=child, period_year=2026, period_month=10)

        assert october.amount_due == TARIFF

    def test_a_child_without_an_enrolment_date_pays_the_full_month(self, tenant_a, tariff):
        """Import qilingan eski bolada qabul sanasi bo'lmasligi mumkin."""
        child = _child(tenant_a, tariff, None)
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert invoice.amount_due == TARIFF

    def test_the_invoice_line_says_why(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, date(2026, 9, 30))
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
            line = invoice.lines.first()

        assert line is not None
        assert "22" in line.description and "1" in line.description
        assert line.line_total == invoice.amount_due


class TestFirstMonthMode:
    def test_full_mode_charges_the_whole_month(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, date(2026, 9, 30))
        with organization_context(tenant_a.organization.id):
            set_setting(
                organization=tenant_a.organization, key="finance.first_month_mode", value="full"
            )
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert invoice.amount_due == TARIFF

    def test_next_month_mode_refuses_to_issue(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, date(2026, 9, 30))
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="keyingi oydan"),
        ):
            set_setting(
                organization=tenant_a.organization,
                key="finance.first_month_mode",
                value="next_month",
            )
            services.issue_invoice(child=child, period_year=2026, period_month=9)


class TestDueDate:
    def test_late_enrolment_gets_a_grace_period(self, tenant_a, tariff):
        """Q3: muddat = max(to'lov kuni, qabul + imtiyoz kunlari)."""
        child = _child(tenant_a, tariff, date(2026, 9, 30))
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert invoice.due_date == date(2026, 10, 5)
        assert invoice.issued_date == date(2026, 9, 30)

    def test_early_enrolment_uses_the_payment_day(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, date(2026, 9, 1))
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert invoice.due_date == date(2026, 9, 10)

    def test_payment_day_setting_is_honoured(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, date(2026, 9, 1))
        with organization_context(tenant_a.organization.id):
            set_setting(organization=tenant_a.organization, key="finance.due_day", value=25)
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)

        assert invoice.due_date == date(2026, 9, 25)

    def test_grace_does_not_apply_to_later_months(self, tenant_a, tariff):
        child = _child(tenant_a, tariff, date(2026, 9, 30))
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            october = services.issue_invoice(child=child, period_year=2026, period_month=10)

        assert october.due_date == date(2026, 10, 10)

    def test_a_short_month_clamps_the_payment_day(self, tenant_a, tariff):
        """To'lov kuni 31 bo'lsa, fevralda oyning oxirgi kuniga tushadi."""
        child = _child(tenant_a, tariff, date(2026, 2, 2))
        with organization_context(tenant_a.organization.id):
            set_setting(organization=tenant_a.organization, key="finance.due_day", value=31)
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=2)

        assert invoice.due_date == date(2026, 2, 28)


class TestBillingPreview:
    """PLAN 1.4 — tasdiqdan oldin nima bo'lishini ko'rsatish."""

    def test_preview_and_run_agree(self, tenant_a, tariff):
        """
        Preview aytgan raqam ishning natijasi bilan BIR XIL bo'lishi shart.

        Aks holda preview ishonchni oshirib, keyin sindiradi — bu
        umuman preview bo'lmaganidan yomon.
        """
        for day in (1, 17, 30):
            _child(tenant_a, tariff, date(2026, 9, day))

        with organization_context(tenant_a.organization.id):
            preview = services.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )

        assert preview.will_create == result.created == 3
        assert preview.total_amount == result.total_amount

    def test_preview_writes_nothing(self, tenant_a, tariff):
        from apps.finance.models import Invoice

        _child(tenant_a, tariff, date(2026, 9, 1))
        with organization_context(tenant_a.organization.id):
            services.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )
            assert not Invoice.objects.exists()

    def test_preview_explains_what_it_skips(self, tenant_a, tariff):
        from apps.children.models import Child

        _child(tenant_a, tariff, date(2026, 9, 1))
        with organization_context(tenant_a.organization.id):
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Tarifsiz",
                last_name="Bola",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )
            # Bir bolaga hujjat allaqachon yozilgan.
            existing = _child(tenant_a, tariff, date(2026, 8, 1))
            services.issue_invoice(child=existing, period_year=2026, period_month=9)

            preview = services.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )

        assert preview.will_create == 1
        assert preview.skipped_existing == 1
        assert preview.skipped_no_tariff == ["Bola Tarifsiz"]

    def test_preview_shows_the_prorated_reason(self, tenant_a, tariff):
        _child(tenant_a, tariff, date(2026, 9, 30))
        with organization_context(tenant_a.organization.id):
            preview = services.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )

        assert preview.rows[0].amount == Decimal("68182.00")
        assert "22" in preview.rows[0].note

    def test_preview_shows_the_advance_that_will_be_consumed(self, tenant_a, tariff):
        """Mudira avans yeyilishini TASDIQLASHDAN OLDIN ko'rishi kerak."""
        child = _child(tenant_a, tariff, date(2026, 9, 1))
        with organization_context(tenant_a.organization.id):
            services.record_payment(child=child, amount=Decimal("200000"), method="cash")
            preview = services.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )

        assert preview.rows[0].advance == Decimal("200000.00")

    def test_next_month_mode_is_listed_not_crashed(self, tenant_a, tariff):
        """Bitta bolaning qoidasi butun ishni to'xtatmasligi kerak."""
        _child(tenant_a, tariff, date(2026, 9, 30))
        with organization_context(tenant_a.organization.id):
            set_setting(
                organization=tenant_a.organization,
                key="finance.first_month_mode",
                value="next_month",
            )
            preview = services.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )

        assert preview.will_create == 0
        assert preview.skipped_next_month == ["Bolasi Sinov"]
        assert result.created == 0
        assert result.skipped_next_month == ["Bolasi Sinov"]
