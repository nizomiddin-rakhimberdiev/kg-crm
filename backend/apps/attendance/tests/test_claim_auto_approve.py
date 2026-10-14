"""
Kelmaslik daʼvosi qoʻshilganda oʻzi tasdiqlanadi (mijoz soʻrovi, 2026-10-14).

Mijoz: *"Kelmagan kunlar uchun qayta hisob qoʻshilayotganda avtomatik
qoʻshiladigan qilish kerak, tasdiqlash soʻralmasligi kerak"*.

ADR-19 oʻzgarmaydi: pulni faqat HUJJAT qoʻzgʻatadi, davomat jadvali
emas. Oʻzgargani — daʼvoni yozgan odam uni tasdiqlashga ham haqli
boʻlsa (`attendance.approve`), ikkinchi bosish soʻralmaydi. Haqli
boʻlmasa (menejer), daʼvo avvalgidek tasdiq kutadi: aks holda
yaratish huquqi jimgina pulni harakatga keltirish huquqiga aylanardi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.attendance.models_absence import AbsenceClaim, ClaimStatus
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db

URL = "/api/v1/absence-claims"


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Toʻliq kun",
            amount=Decimal("2200000"),
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Laylo",
            last_name="Sharipova",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
        )


def _as(tenant: Any, role: str) -> APIClient:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=f"{role}@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=role,
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _post(client: APIClient, child: Child, start: str = "2026-09-07", end: str = "2026-09-11"):
    return client.post(
        URL,
        {"child_id": str(child.id), "kind": "medical", "date_from": start, "date_to": end},
        format="json",
    )


@pytest.mark.parametrize("role", ["director", "attendance_manager"])
def test_a_claim_by_someone_who_may_approve_is_approved_at_once(tenant_a: Any, role: str):
    child = _child(tenant_a)
    response = _post(_as(tenant_a, role), child)

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert data["status"] == ClaimStatus.APPROVED
    assert Decimal(data["credit_amount"]) > 0


def test_the_owner_is_approved_at_once_too(tenant_a: Any):
    response = _post(tenant_a.client(), _child(tenant_a))
    assert response.json()["data"]["status"] == ClaimStatus.APPROVED


def test_a_claim_by_someone_who_may_not_approve_waits(tenant_a: Any):
    """Menejer daʼvo yoza oladi, tasdiqlay olmaydi — pul uning bosishi bilan qimirlamaydi."""
    response = _post(_as(tenant_a, "manager"), _child(tenant_a))

    assert response.status_code == 201, response.json()
    assert response.json()["data"]["status"] == ClaimStatus.PENDING


def test_a_claim_with_no_working_day_is_not_created_at_all(tenant_a: Any):
    """Shanba–yakshanba: qaytariladigan kun yoʻq — tasdiqlanmaydigan daʼvo qolib ketmasin."""
    child = _child(tenant_a)
    response = _post(tenant_a.client(), child, "2026-09-12", "2026-09-13")

    assert response.status_code == 422
    with organization_context(tenant_a.organization.id):
        assert not AbsenceClaim.objects.filter(child=child).exists()


def test_the_paper_can_follow_an_approved_claim_once(tenant_a: Any):
    """
    Qogʻoz koʻpincha keyin keladi; birinchi hujjatni biriktirish
    dalilni almashtirish emas. Ikkinchisi esa — almashtirish, u yopiq.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile

    client = tenant_a.client()
    claim_id = _post(client, _child(tenant_a)).json()["data"]["id"]

    def pdf() -> Any:
        return SimpleUploadedFile("s.pdf", b"%PDF-1.4 x", content_type="application/pdf")

    first = client.post(f"{URL}/{claim_id}/document", {"file": pdf()}, format="multipart")
    second = client.post(f"{URL}/{claim_id}/document", {"file": pdf()}, format="multipart")

    assert first.status_code == 200, first.content
    assert second.status_code == 422
