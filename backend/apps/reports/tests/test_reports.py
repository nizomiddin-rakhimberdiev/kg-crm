"""
Hisobot testlari (docs/04 §14).

Asosiy savol: "hisobot pulni to'g'ri ko'rsatyaptimi, va faqat O'Z
tashkilotining pulinimi?" Ikkinchi qism birinchisidan muhimroq: noto'g'ri
raqamni tuzatish mumkin, boshqa mijozning daromadini ko'rsatib qo'yishni
esa qaytarib bo'lmaydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.reports import selectors, services

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    """Dashboard keshi testlar orasida oqib o'tmasin."""
    cache.clear()
    yield
    cache.clear()


def _child(tenant, name: str = "Ali") -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _pay(tenant, child: Child, amount: str, when: date | None = None):
    with organization_context(tenant.organization.id):
        payment = finance.record_payment(child=child, amount=Decimal(amount), method="cash")
        if when is not None:
            from apps.finance.models import Payment

            Payment.objects.filter(pk=payment.pk).update(
                paid_at=timezone.make_aware(
                    timezone.datetime(when.year, when.month, when.day, 12, 0)
                )
            )
        return payment


class TestRevenue:
    def test_totals_and_monthly_split(self, tenant_a):
        child = _child(tenant_a)
        today = timezone.localdate()
        _pay(tenant_a, child, "500000", today)
        _pay(tenant_a, child, "300000", today)

        with organization_context(tenant_a.organization.id):
            report = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=today.replace(day=1),
                date_to=today,
            )

        assert report["total"] == "800000.00"
        assert report["payment_count"] == 2
        assert report["group_by"] == "month"
        assert report["by_period"][0]["period"] == today.replace(day=1).isoformat()

    def test_basis_is_stated_explicitly(self, tenant_a):
        """
        `basis` javobda bor, chunki "daromad" ikki xil ma'noga ega.

        Yozilgan hisob-faktura ham, qabul qilingan pul ham daromad deb
        ataladi va ular bir xil emas. Qaysi biri ekanini o'qiyotgan odam
        taxmin qilmasligi kerak.
        """
        with organization_context(tenant_a.organization.id):
            report = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 1, 1),
                date_to=date(2026, 12, 31),
            )
        assert report["basis"] == "cash"

    def test_unpaid_invoice_is_not_revenue(self, tenant_a):
        """Yozilgan, lekin to'lanmagan hisob-faktura daromad EMAS."""
        child = _child(tenant_a)
        with organization_context(tenant_a.organization.id):
            tariff = TariffPlan.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Tarif",
                amount=Decimal("1500000"),
            )
            Child.objects.filter(pk=child.pk).update(tariff=tariff)
            child.refresh_from_db()
            finance.issue_invoice(child=child, period_year=2026, period_month=7)

            report = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 1, 1),
                date_to=date(2026, 12, 31),
            )
        assert report["total"] == "0.00"


class TestExpensesAndPayroll:
    def test_only_approved_expenses_count(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            category = ExpenseCategory.objects.create(
                organization=tenant_a.organization, branch=tenant_a.branch, name="Kommunal"
            )
            base = {
                "organization": tenant_a.organization,
                "branch": tenant_a.branch,
                "category": category,
                "expense_date": date(2026, 7, 10),
            }
            Expense.objects.create(**base, amount=Decimal("100000"), status="pending")
            Expense.objects.create(**base, amount=Decimal("200000"), status="approved")
            Expense.objects.create(**base, amount=Decimal("300000"), status="paid")

            report = selectors.expense_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 7, 1),
                date_to=date(2026, 7, 31),
            )
        assert report["total"] == "500000.00"

    def test_draft_payroll_is_not_a_cost(self, tenant_a):
        """
        Qoralama oylik hisobotga kirmaydi.

        Uning summasi hali tahrirlanishi mumkin; uni xarajat sifatida
        ko'rsatish tasdiqlanmagan raqamni fakt qilib qo'yardi.
        """
        from apps.hr.models import Employee
        from apps.payroll import services as payroll

        with organization_context(tenant_a.organization.id):
            Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Xodim",
                last_name="Xodimov",
                hire_date=date(2025, 1, 10),
                base_salary=Decimal("4000000"),
            )
            run = payroll.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=7,
            )
            draft = selectors.payroll_report(organization_id=tenant_a.organization.id, year=2026)
            assert draft["total_gross"] == "0.00"

            payroll.finalize_run(run=run, finalized_by=tenant_a.owner)
            final = selectors.payroll_report(organization_id=tenant_a.organization.id, year=2026)
        assert final["total_gross"] == "4000000.00"


class TestProfitLoss:
    def test_net_is_revenue_minus_expenses_minus_payroll(self, tenant_a):
        child = _child(tenant_a)
        today = timezone.localdate()
        _pay(tenant_a, child, "5000000", today)

        with organization_context(tenant_a.organization.id):
            category = ExpenseCategory.objects.create(
                organization=tenant_a.organization, branch=tenant_a.branch, name="Oziq-ovqat"
            )
            Expense.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                category=category,
                amount=Decimal("1200000"),
                expense_date=today,
                status="paid",
            )
            report = selectors.profit_loss(
                organization_id=tenant_a.organization.id,
                date_from=today.replace(day=1),
                date_to=today,
            )

        assert report["revenue"] == "5000000.00"
        assert report["expenses"] == "1200000.00"
        assert report["net"] == "3800000.00"


class TestPeriodGrouping:
    """
    `group_by` — kun / hafta / oy / chorak / yil (docs/04 §14.2).

    Ikki narsa tekshiriladi: (1) jami ko'rsatkich kesimga bog'liq emas,
    (2) davrlar uzluksiz — bo'sh hafta ham qatorda turadi.
    """

    def test_totals_do_not_depend_on_group_by(self, tenant_a):
        child = _child(tenant_a)
        _pay(tenant_a, child, "100000", date(2026, 3, 2))
        _pay(tenant_a, child, "250000", date(2026, 3, 27))

        with organization_context(tenant_a.organization.id):
            totals = {
                group_by: selectors.revenue_report(
                    organization_id=tenant_a.organization.id,
                    date_from=date(2026, 3, 1),
                    date_to=date(2026, 3, 31),
                    group_by=group_by,
                )["total"]
                for group_by in selectors.GROUP_BY_CHOICES
            }
        assert set(totals.values()) == {"350000.00"}

    def test_daily_rows_are_gap_free_and_dated(self, tenant_a):
        child = _child(tenant_a)
        _pay(tenant_a, child, "100000", date(2026, 3, 2))

        with organization_context(tenant_a.organization.id):
            report = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 3, 1),
                date_to=date(2026, 3, 7),
                group_by="day",
            )
        rows = report["by_period"]
        assert [row["period"] for row in rows] == [f"2026-03-0{d}" for d in range(1, 8)]
        assert rows[1]["total"] == "100000.00"
        assert all(row["total"] == "0.00" for row in rows if row["period"] != "2026-03-02")

    def test_week_buckets_start_on_monday(self, tenant_a):
        child = _child(tenant_a)
        _pay(tenant_a, child, "100000", date(2026, 3, 4))  # chorshanba

        with organization_context(tenant_a.organization.id):
            report = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 3, 4),
                date_to=date(2026, 3, 17),
                group_by="week",
            )
        # 2026-03-02 — dushanba; davr o'rtasidan boshlansa ham hafta
        # boshi dushanba bo'lib qoladi (Postgres `date_trunc` bilan mos).
        assert [row["period"] for row in report["by_period"]] == [
            "2026-03-02",
            "2026-03-09",
            "2026-03-16",
        ]
        assert report["by_period"][0]["total"] == "100000.00"

    def test_quarter_and_year_buckets(self, tenant_a):
        child = _child(tenant_a)
        _pay(tenant_a, child, "100000", date(2026, 2, 10))
        _pay(tenant_a, child, "200000", date(2026, 8, 10))

        with organization_context(tenant_a.organization.id):
            quarters = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 1, 1),
                date_to=date(2026, 12, 31),
                group_by="quarter",
            )["by_period"]
            years = selectors.revenue_report(
                organization_id=tenant_a.organization.id,
                date_from=date(2025, 6, 1),
                date_to=date(2026, 12, 31),
                group_by="year",
            )["by_period"]

        assert [(r["period"], r["total"]) for r in quarters] == [
            ("2026-01-01", "100000.00"),
            ("2026-04-01", "0.00"),
            ("2026-07-01", "200000.00"),
            ("2026-10-01", "0.00"),
        ]
        assert [(r["period"], r["total"]) for r in years] == [
            ("2025-01-01", "0.00"),
            ("2026-01-01", "300000.00"),
        ]

    def test_payroll_is_not_spread_into_days(self, tenant_a):
        """
        Oylik maosh kun/hafta kesimida qatorlarga taqsimlanmaydi, lekin
        davr jamisida qoladi — va bu javobda ochiq aytiladi.
        """
        from apps.hr.models import Employee
        from apps.payroll import services as payroll

        with organization_context(tenant_a.organization.id):
            Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Xodim",
                last_name="Xodimov",
                hire_date=date(2025, 1, 10),
                base_salary=Decimal("3000000"),
            )
            run = payroll.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=3,
            )
            payroll.finalize_run(run=run, finalized_by=tenant_a.owner)

            daily = selectors.profit_loss(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 3, 1),
                date_to=date(2026, 3, 31),
                group_by="day",
            )
            monthly = selectors.profit_loss(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 3, 1),
                date_to=date(2026, 3, 31),
                group_by="month",
            )

        assert daily["payroll"] == monthly["payroll"] == "3000000.00"
        assert daily["net"] == monthly["net"] == "-3000000.00"
        assert daily["payroll_in_periods"] is False
        assert all(row["payroll"] == "0.00" for row in daily["by_period"])
        assert monthly["payroll_in_periods"] is True
        assert monthly["by_period"][0]["payroll"] == "3000000.00"

    def test_unknown_group_by_is_a_clear_error(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:report-revenue"), {"group_by": "decade"})
        assert response.status_code == 422
        assert "group_by" in response.json()["error"]["message"]

    def test_too_many_buckets_is_rejected(self, tenant_a):
        response = tenant_a.client().get(
            reverse("v1:report-profit-loss"),
            {"from": "2020-01-01", "to": "2026-12-31", "group_by": "day"},
        )
        assert response.status_code == 422

    def test_endpoint_accepts_group_by(self, tenant_a):
        child = _child(tenant_a)
        today = timezone.localdate()
        _pay(tenant_a, child, "120000", today)

        response = tenant_a.client().get(
            reverse("v1:report-profit-loss"),
            {"from": today.isoformat(), "to": today.isoformat(), "group_by": "day"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["group_by"] == "day"
        assert len(data["by_period"]) == 1
        assert data["by_period"][0]["revenue"] == "120000.00"


class TestActiveChildren:
    def test_a_child_without_a_group_still_counts(self, tenant_a):
        """
        Guruhga biriktirilmagan bola ham hisobga kiradi.

        CSV import bolani yaratadi, lekin guruhga biriktirmaydi. Agar
        hisob a'zolikni talab qilsa, 60 ta bola kiritgan direktor
        dashboard'da `0` ko'rardi — va bu tizimga ishonchni birinchi
        daqiqadayoq yo'qotadigan turdagi xato.
        """
        _child(tenant_a, name="Guruhsiz")
        with organization_context(tenant_a.organization.id):
            assert selectors.active_children_count(organization_id=tenant_a.organization.id) == 1


class TestDashboard:
    def test_kpis_reflect_reality(self, tenant_a):
        child = _child(tenant_a)
        _pay(tenant_a, child, "750000", timezone.localdate())

        with organization_context(tenant_a.organization.id):
            kpis = services.dashboard_kpis(organization_id=tenant_a.organization.id)

        assert kpis["month_revenue"] == "750000.00"
        assert kpis["recent_payments"][0]["amount"] == "750000.00"
        assert len(kpis["revenue_trend"]) == 6

    def test_attendance_kpi_with_real_records(self, tenant_a):
        """
        Davomat yozuvlari BOR holatni alohida tekshiradi.

        Qolgan dashboard testlari faqat to'lov yaratadi — davomat jadvali
        bo'sh qoladi va `by_group` bo'sh ro'yxat bo'ladi. Bo'sh ro'yxat
        ustidan `sum(...)` bironta qatorga umuman kirmaydi, ya'ni qator
        ichidagi maydon xatosi testdan jimgina o'tib ketadi.

        Aynan shu bo'lgan: "kechikdi" holati olib tashlangach, yig'indida
        `row["late"]` qolib ketgan va `/dashboard` brauzerda `500` bergan,
        558 ta test esa yashil turgan.
        """
        from apps.attendance.services import mark_bulk
        from apps.children.models import Group
        from apps.children.services import enroll_child

        today = timezone.localdate()

        with organization_context(tenant_a.organization.id):
            group = Group.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Quyoshlar",
                capacity=10,
            )
            children = [_child(tenant_a, f"Bola{index}") for index in range(3)]
            for child in children:
                enroll_child(child=child, group=group)

            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=today,
                records=[
                    {"child_id": children[0].id, "status": "present"},
                    {"child_id": children[1].id, "status": "present"},
                    {"child_id": children[2].id, "status": "absent"},
                ],
            )

            report = selectors.attendance_report(
                organization_id=tenant_a.organization.id,
                year=today.year,
                month=today.month,
            )
            kpis = services.dashboard_kpis(organization_id=tenant_a.organization.id)

        assert report["marked_records"] == 3
        assert report["attendance_rate"] == 66.7  # 2 / 3
        assert report["by_group"][0]["present"] == 2
        assert kpis["attendance_month_pct"] == 66.7

    def test_second_call_is_served_from_cache(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            assert (
                services.dashboard_kpis(organization_id=tenant_a.organization.id)["cached"] is False
            )
            assert (
                services.dashboard_kpis(organization_id=tenant_a.organization.id)["cached"] is True
            )

    @pytest.mark.tenancy
    def test_cache_key_is_per_organization(self, tenant_a, tenant_b):
        """
        Kesh kaliti tashkilot bilan boshlanadi.

        Umumiy kalit boshqa bog'chaning daromadini ko'rsatib qo'yardi —
        so'rov to'g'ri bo'lsa ham. Bazadan sizib chiqish emas, lekin
        ekranda ko'rgan odam uchun farqi yo'q.
        """
        child = _child(tenant_a)
        _pay(tenant_a, child, "999000", timezone.localdate())

        with organization_context(tenant_a.organization.id):
            first = services.dashboard_kpis(organization_id=tenant_a.organization.id)
        with organization_context(tenant_b.organization.id):
            second = services.dashboard_kpis(organization_id=tenant_b.organization.id)

        assert first["month_revenue"] == "999000.00"
        assert second["month_revenue"] == "0.00"


class TestEndpoints:
    def test_dashboard_endpoint(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:dashboard-list"))
        assert response.status_code == 200
        assert "active_children" in response.json()["data"]

    def test_revenue_endpoint_accepts_a_range(self, tenant_a):
        child = _child(tenant_a)
        today = timezone.localdate()
        _pay(tenant_a, child, "120000", today)

        response = tenant_a.client().get(
            reverse("v1:report-revenue"),
            {"from": today.replace(day=1).isoformat(), "to": today.isoformat()},
        )
        assert response.status_code == 200
        assert response.json()["data"]["total"] == "120000.00"

    def test_bad_date_is_a_clear_error_not_a_500(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:report-revenue"), {"from": "kecha"})
        assert response.status_code == 422
        assert "Sana formati" in response.json()["error"]["message"]

    def test_out_of_range_month_is_rejected(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:report-attendance"), {"month": "13"})
        assert response.status_code == 422

    def test_unknown_report_type_is_404(self, tenant_a):
        response = tenant_a.client().post("/api/v1/reports/salaries/export", {}, format="json")
        assert response.status_code == 404

    @pytest.mark.tenancy
    def test_reports_never_cross_the_tenant_boundary(self, tenant_a, tenant_b):
        child_b = _child(tenant_b, name="Begona")
        _pay(tenant_b, child_b, "7777000", timezone.localdate())

        response = tenant_a.client().get(reverse("v1:report-revenue"))
        assert response.status_code == 200
        assert response.json()["data"]["total"] == "0.00"

    def test_cashier_reads_reports_but_cannot_export(self, tenant_a):
        """
        Kassirda `reports` faqat o'qish (docs/02 §11.2).

        O'qish kerak — kassir kunlik tushumni solishtiradi. Eksport esa
        butun moliyaviy tarixni fayl qilib chiqarish, va bu boshqa
        darajadagi ish: u `reports.export` talab qiladi.
        """
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir-hisobot@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Kassir",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:report-revenue")).status_code == 200
        assert client.post("/api/v1/reports/revenue/export", {}, format="json").status_code == 403


class TestTrend:
    def test_empty_months_are_kept_in_the_series(self, tenant_a):
        """
        To'lovsiz oy qatorda QOLADI.

        Grafikdan tushib qolsa, tushish o'sish bo'lib ko'rinardi — va bu
        eng noto'g'ri xulosaga olib keladigan turdagi xato.
        """
        child = _child(tenant_a)
        today = timezone.localdate()
        _pay(tenant_a, child, "100000", today)

        with organization_context(tenant_a.organization.id):
            trend = services.dashboard_kpis(organization_id=tenant_a.organization.id)[
                "revenue_trend"
            ]

        assert len(trend) == 6
        assert trend[-1]["total"] == "100000.00"
        assert all(row["total"] == "0.00" for row in trend[:-1])
        # Oylar ketma-ket va takrorlanmasligi kerak.
        assert len({row["month"] for row in trend}) == 6
