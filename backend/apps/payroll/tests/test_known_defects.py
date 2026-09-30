"""
Oylik hisoblash kamchiliklari — 2026-09-30 auditi (PLAN 1.10, Q10).

Auditda uchta holat:
  * Abdullayeva Maftuna (Tarbiyachi, ishga kirgan 10.05.2026) birorta
    oylik hisobida yo'q;
  * "ushlab qolindi 0" — ushlanma ko'rinmaydi;
  * ishga kirgan oyi to'liq hisoblanadi, proporsional emas.

`create_run()` xodimlarni hisob YARATILGAN paytda suratga oladi. Shu
sababli keyinroq qo'shilgan xodim eski hisobga tushmaydi — va hisob
yakunlangan bo'lsa, `recalculate_run()` ham unga tegolmaydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.core.tenancy import organization_context
from apps.hr.models import Employee, Position
from apps.payroll import services
from apps.payroll.models import PayrollItem

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

SALARY = Decimal("7500000.00")


@pytest.fixture
def position(tenant_a) -> Position:
    with organization_context(tenant_a.organization.id):
        return Position.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, title="Tarbiyachi"
        )


def _hire(tenant_a, position, *, first: str, last: str, hire_date: date) -> Employee:
    with organization_context(tenant_a.organization.id):
        return Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name=first,
            last_name=last,
            position=position,
            hire_date=hire_date,
            base_salary=SALARY,
        )


class TestEmployeeReachesPayroll:
    def test_a_missing_employee_is_detectable(self, tenant_a, position):
        """
        Maftuna holati: hisob YARATILGANDA u hali tizimda yo'q edi.

        `create_run()` xodimlarni o'sha ondagi ro'yxatdan suratga oladi.
        Keyin qo'shilgan xodim qoralamaga `recalculate_run()` bilan
        tushadi — lekin hisob YAKUNLANGAN bo'lsa, uni ochmasdan biror
        narsa qilib bo'lmaydi va, eng yomoni, **tushib qolgani hech
        qayerda ko'rinmaydi**. Auditda aynan shu bo'lgan: xodim bor,
        oyligi yo'q, xato yo'q.

        Kerak: yakunlangan hisobda kim yo'qligini AYTADIGAN funksiya.
        """
        # Hisob bo'sh bo'lsa yakunlab bo'lmaydi — bitta hamkasb bor.
        _hire(tenant_a, position, first="Dilnoza", last="Ergasheva", hire_date=date(2024, 1, 1))

        with organization_context(tenant_a.organization.id):
            june = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=6,
            )
            services.finalize_run(run=june)

        # Hisob yakunlangandan KEYIN xodim tizimga kiritildi.
        maftuna = _hire(
            tenant_a, position, first="Maftuna", last="Abdullayeva", hire_date=date(2026, 5, 10)
        )

        with organization_context(tenant_a.organization.id):
            assert not PayrollItem.objects.filter(payroll_run=june, employee=maftuna).exists()
            # Tizim buni o'zi aytishi kerak — buxgalter 40 satrni ko'z bilan
            # solishtirmasligi uchun.
            missing = services.missing_employees(run=june)  # type: ignore[attr-defined]

        assert maftuna in missing

    def test_employee_is_absent_from_runs_before_the_hire_date(self, tenant_a, position):
        maftuna = _hire(
            tenant_a, position, first="Maftuna", last="Abdullayeva", hire_date=date(2026, 5, 10)
        )
        with organization_context(tenant_a.organization.id):
            april = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=4,
            )
            # Aprelda u hali ishlamagan — satr bo'lmasligi kerak.
            assert not PayrollItem.objects.filter(payroll_run=april, employee=maftuna).exists()


class TestHireMonthIsProrated:
    def test_hire_month_is_prorated_by_working_days(self, tenant_a, position):
        # 2026-05: 21 ish kuni; 10-may yakshanba → 11-maydan 15 ish kuni qoladi.
        maftuna = _hire(
            tenant_a, position, first="Maftuna", last="Abdullayeva", hire_date=date(2026, 5, 10)
        )
        with organization_context(tenant_a.organization.id):
            may = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=5,
            )
            item = PayrollItem.objects.get(payroll_run=may, employee=maftuna)

        assert item.base_amount < SALARY, "ishga kirgan oyi to'liq emas"


class TestWithholding:
    def test_withholding_is_off_by_default(self, tenant_a, position):
        """
        Q10: sukut — 0 (o'chirilgan).

        Hozir `payroll.income_tax_rate` default 12 % — ya'ni sozlamaga
        tegmagan bog'cha ham xodimdan pul ushlab qoladi.
        """
        from apps.settings_app.services import get_setting

        with organization_context(tenant_a.organization.id):
            assert Decimal(str(get_setting(key="payroll.income_tax_rate"))) == Decimal("0")

    def test_employer_social_tax_setting_exists(self, tenant_a):
        """Q10 ikkita stavka talab qiladi: xodimdan ushlanadi va ish beruvchi xarajati."""
        from apps.settings_app.services import DEFAULTS

        assert "payroll.social_tax_rate" in DEFAULTS
        assert Decimal(str(DEFAULTS["payroll.social_tax_rate"])) == Decimal("0")


class TestHireMonthNumbers:
    """Proporsiya raqamlari — PLAN 1.10."""

    def test_the_share_matches_the_calendar(self, tenant_a, position):
        # 2026-05: 21 ish kuni. 10-may — yakshanba, ya'ni 11-maydan 15 kun.
        maftuna = _hire(
            tenant_a, position, first="Maftuna", last="Abdullayeva", hire_date=date(2026, 5, 10)
        )
        with organization_context(tenant_a.organization.id):
            assert services.period_share(employee=maftuna, period_year=2026, period_month=5) == (
                15,
                21,
            )
            may = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=5,
            )
            item = PayrollItem.objects.get(payroll_run=may, employee=maftuna)

        # 7 500 000 ÷ 21 × 15 = 5 357 142,86
        assert item.base_amount == Decimal("5357142.86")

    def test_a_full_month_is_not_prorated(self, tenant_a, position):
        maftuna = _hire(
            tenant_a, position, first="Maftuna", last="Abdullayeva", hire_date=date(2026, 5, 10)
        )
        with organization_context(tenant_a.organization.id):
            june = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=6,
            )
            item = PayrollItem.objects.get(payroll_run=june, employee=maftuna)

        assert item.base_amount == SALARY

    def test_holidays_shrink_the_month_for_everyone(self, tenant_a, position):
        """Bayram maxrajni ham, suratni ham kamaytiradi — nisbat adolatli qoladi."""
        from apps.attendance.models_absence import Holiday

        maftuna = _hire(
            tenant_a, position, first="Maftuna", last="Abdullayeva", hire_date=date(2026, 5, 18)
        )
        with organization_context(tenant_a.organization.id):
            Holiday.objects.create(
                organization=tenant_a.organization,
                holiday_date=date(2026, 5, 20),
                name="Sinov bayrami",
            )
            worked, total = services.period_share(
                employee=maftuna, period_year=2026, period_month=5
            )

        assert total == 20, "bayram oyning ish kunini kamaytiradi"
        assert worked == 9, "bayram xodimning kunini ham kamaytiradi"


class TestEmployerSocialTax:
    """Q10: ish beruvchi solig'i xodimga tegmaydi, xarajatni oshiradi."""

    def test_social_tax_does_not_touch_the_employee(self, tenant_a, position):
        from apps.settings_app.services import set_setting

        employee = _hire(
            tenant_a, position, first="Nilufar", last="Sodiqova", hire_date=date(2024, 1, 1)
        )
        employee.official_salary = Decimal("3000000")
        with organization_context(tenant_a.organization.id):
            employee.save(update_fields=["official_salary"])
            set_setting(organization=tenant_a.organization, key="payroll.social_tax_rate", value=12)
            run = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=6,
            )
            item = PayrollItem.objects.get(payroll_run=run, employee=employee)
            run.refresh_from_db()

        # 3 000 000 × 12 % = 360 000 — bog'cha ustiga to'laydi.
        assert item.tax_social == Decimal("360000.00")
        # Xodim qo'liga tegadigan summa o'zgarmaydi.
        assert item.net == SALARY
        assert run.total_social_tax == Decimal("360000.00")

    def test_social_tax_is_off_by_default(self, tenant_a, position):
        employee = _hire(
            tenant_a, position, first="Nilufar", last="Sodiqova", hire_date=date(2024, 1, 1)
        )
        with organization_context(tenant_a.organization.id):
            run = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=6,
            )
            item = PayrollItem.objects.get(payroll_run=run, employee=employee)

        assert item.tax_social == Decimal("0.00")
