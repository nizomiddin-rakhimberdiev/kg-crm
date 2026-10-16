"""
Tezkor kiritish (Bosqich 13.3a, brif §4): chek rasmi va oxirgi ishlatilgan
toifalar tepada. Hisobot faqat kiritilgan ma'lumotchalik yaxshi — chek
biriktirish bir harakat bo'lishi kerak.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.cash.models import CashAccount
from apps.core.tenancy import organization_context
from apps.expenses.models import ExpenseCategory

pytestmark = pytest.mark.django_db

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def _funded(tenant_a: Any) -> None:
    tenant_a.fund(kind="all")


def _category(tenant: Any, name: str) -> ExpenseCategory:
    with organization_context(tenant.organization.id):
        return ExpenseCategory.objects.create(
            organization=tenant.organization, branch=tenant.branch, name=name
        )


def _expense(tenant: Any, category: ExpenseCategory, amount: str = "150000") -> str:
    with organization_context(tenant.organization.id):
        till = CashAccount.objects.get(branch=tenant.branch, kind="cash", is_active=True)
    response = tenant.client().post(
        "/api/v1/expenses",
        {
            "category_id": str(category.id),
            "amount": amount,
            "expense_date": "2026-10-10",
            "cash_account_id": str(till.id),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    return response.json()["data"]["id"]


def test_a_receipt_photo_is_attached_and_downloaded(tenant_a: Any):
    expense_id = _expense(tenant_a, _category(tenant_a, "Bozorlik"))

    upload = tenant_a.client().post(
        f"/api/v1/expenses/{expense_id}/receipt",
        {"file": SimpleUploadedFile("chek.png", PNG, content_type="image/png")},
        format="multipart",
    )

    assert upload.status_code == 200, upload.json()
    assert upload.json()["data"]["has_receipt"] is True
    download = tenant_a.client().get(f"/api/v1/expenses/{expense_id}/receipt/download")
    assert download.status_code == 200
    assert b"".join(download.streaming_content).startswith(b"\x89PNG")


def test_a_receipt_must_be_a_picture_or_pdf(tenant_a: Any):
    expense_id = _expense(tenant_a, _category(tenant_a, "Bozorlik"))
    response = tenant_a.client().post(
        f"/api/v1/expenses/{expense_id}/receipt",
        {"file": SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")},
        format="multipart",
    )
    assert response.status_code == 422


@pytest.mark.tenancy
def test_another_tenants_receipt_is_404(tenant_a: Any, tenant_b: Any):
    expense_id = _expense(tenant_a, _category(tenant_a, "Bozorlik"))
    tenant_a.client().post(
        f"/api/v1/expenses/{expense_id}/receipt",
        {"file": SimpleUploadedFile("chek.png", PNG, content_type="image/png")},
        format="multipart",
    )
    assert (
        tenant_a.client().get(f"/api/v1/expenses/{expense_id}/receipt/download").status_code == 200
    )
    stranger = tenant_b.client()
    assert stranger.get(f"/api/v1/expenses/{expense_id}/receipt/download").status_code == 404


def test_recently_used_categories_come_first(tenant_a: Any):
    rent, food, fuel = (_category(tenant_a, name) for name in ("Ijara", "Bozorlik", "Yoqilgʻi"))
    _expense(tenant_a, rent)
    _expense(tenant_a, food)

    rows = (
        tenant_a.client().get("/api/v1/expense-categories", {"ordering": "recent"}).json()["data"]
    )
    items = rows["results"] if isinstance(rows, dict) else rows
    names = [row["name"] for row in items]
    assert names.index("Bozorlik") < names.index("Ijara") < names.index("Yoqilgʻi")
    assert next(row for row in items if row["name"] == "Bozorlik")["last_used_at"]
