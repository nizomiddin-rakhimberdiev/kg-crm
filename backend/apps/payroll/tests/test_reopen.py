"""
Yakunlangan hisoblashni qayta ochish.

Birinchi mijozda chiqqan holat: sentabr hisoblashi yakunlangan, ichida
esa xato — va uni tuzatishning hech qanday yo'li yo'q edi. "Keyingi
oyda tuzatuv kiriting" degan qoida buxgalteriyada to'g'ri, lekin
oylikni hali bermagan bog'cha uchun javob emas.

Qayta ochish — bepul amal emas: sabab majburiy, audit jurnaliga
tushadi va uni faqat `payroll.approve` haqli rol bajara oladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import Permission, Role, RolePermission, User
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.hr.models import Employee
from apps.payroll import services
from apps.payroll.models import PayrollStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee(tenant_a: Any) -> Employee:
    with organization_context(tenant_a.organization.id):
        return Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Dilnoza",
            last_name="Ergasheva",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal("4000000"),
        )


def _client_with(tenant: Any, codes: list[str], email: str) -> APIClient:
    """Aynan berilgan ruxsatlarga ega maxsus rol — bogʻcha egasi yasagani kabi."""
    with organization_context(tenant.organization.id):
        role = Role.objects.create(
            organization=tenant.organization, code=email.split("@")[0], name="Maxsus"
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in Permission.objects.filter(code__in=codes)
            ]
        )
        user = User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106 — test ma'lumoti
            full_name="Xodim",
            organization=tenant.organization,
            role=role,
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _finalized(tenant_a: Any):
    run = services.create_run(
        organization=tenant_a.organization,
        branch=tenant_a.branch,
        period_year=2026,
        period_month=9,
    )
    return services.finalize_run(run=run)


def test_reopened_run_becomes_editable_again(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        run = _finalized(tenant_a)
        assert run.is_editable is False

        services.reopen_run(run=run, reason="Bonus kiritilmay qolgan")
        run.refresh_from_db()

        assert run.status == PayrollStatus.DRAFT
        assert run.is_editable is True
        assert run.finalized_at is None
        assert run.finalized_by is None

        # Endi satr yana tahrirlanadi — qayta ochishdan maqsad shu.
        item = run.items.get(employee=employee)
        services.update_item(item=item, bonus=Decimal("500000"))
        item.refresh_from_db()
        assert item.net == Decimal("4500000.00")


def test_paid_run_can_be_reopened_too(tenant_a: Any, employee: Employee):
    """
    To'langan hisoblash ham ochiladi.

    Bir tugma bilan "toʻlandi" deb belgilab qo'yish oson, va shundan
    keyin hech narsa qilib bo'lmasligi mijozni tuzatib bo'lmaydigan
    holatda qoldirardi.
    """
    with organization_context(tenant_a.organization.id):
        run = _finalized(tenant_a)
        services.mark_run_paid(run=run)
        services.reopen_run(run=run, reason="Xato toʻlangan deb belgilangan")
        run.refresh_from_db()

        assert run.status == PayrollStatus.DRAFT
        assert run.paid_at is None


def test_reason_is_required(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        run = _finalized(tenant_a)
        with pytest.raises(BusinessRuleViolation):
            services.reopen_run(run=run, reason="   ")

        run.refresh_from_db()
        assert run.status == PayrollStatus.FINALIZED


def test_draft_cannot_be_reopened(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        run = services.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=8,
        )
        with pytest.raises(BusinessRuleViolation):
            services.reopen_run(run=run, reason="shunchaki")


def test_advance_recorded_after_finalizing_lands_in_the_reopened_run(
    tenant_a: Any, employee: Employee
):
    """
    Qayta ochilgan davrda avans satrlarga TUSHADI.

    Aks holda "avans keyinroq berilgan" holat qayta ochishdan keyin ham
    hisoblanmay qolardi — ya'ni tuzatish yarim bo'lardi.
    """
    with organization_context(tenant_a.organization.id):
        run = _finalized(tenant_a)
        services.record_advance(
            employee=employee, amount=Decimal("1000000"), paid_on=date(2026, 9, 15)
        )

        item = run.items.get(employee=employee)
        assert item.advance == Decimal("0.00"), "yakunlangan hisoblash oʻzgarmasligi kerak"

        services.reopen_run(run=run, reason="Avans keyin berilgan")
        item.refresh_from_db()
        run.refresh_from_db()

        assert item.advance == Decimal("1000000.00")
        assert item.net == Decimal("3000000.00")
        assert run.total_net == Decimal("3000000.00")


def test_endpoint_requires_the_approve_permission(tenant_a: Any, employee: Employee):
    """
    `payroll.update` yetarli emas — qayta ochish `approve` talab qiladi.

    Yakunlashni bajara oladigan rol uni bekor ham qila olishi kerak
    degani emas (docs/02 §11.2).
    """
    with organization_context(tenant_a.organization.id):
        run = _finalized(tenant_a)

    url = reverse("v1:payroll-run-reopen", args=[run.id])
    limited = _client_with(tenant_a, ["payroll.read", "payroll.update"], "cheklangan@alfa.uz")
    assert limited.post(url, {"reason": "test"}, format="json").status_code == 403

    response = tenant_a.client().post(url, {"reason": "Bonus unutilgan"}, format="json")
    assert response.status_code == 200, response.content
    assert response.json()["data"]["status"] == "draft"


@pytest.mark.tenancy
def test_other_tenant_cannot_reopen(tenant_a: Any, tenant_b: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        run = _finalized(tenant_a)

    url = reverse("v1:payroll-run-reopen", args=[run.id])
    response = tenant_b.client().post(url, {"reason": "begona"}, format="json")
    assert response.status_code == 404

    with organization_context(tenant_a.organization.id):
        run.refresh_from_db()
        assert run.status == PayrollStatus.FINALIZED
