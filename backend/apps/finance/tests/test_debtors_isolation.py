"""
Qarzdorlar endpointining tenant izolyatsiyasi.

Bu fayl sweep'dagi yangi tekshiruv tufayli paydo bo'ldi: `/debtors`
`ViewSet` bo'lgani uchun (ortida jadval yo'q — ADR-7) avtomatik qamrovga
tushmagan va Sprint 4 dan beri hech qanday izolyatsiya testisiz turgan
edi. Kod to'g'ri ishlayotgan bo'lib chiqdi, lekin "to'g'ri ishlayotgani
tekshirilmagan" degani — ertaga selektor o'zgarsa, hech kim sezmaydi.

Qarzdorlar ro'yxati bolaning ismi va oiladan qancha qarz borligini
ko'rsatadi. Boshqa bog'chaga ko'rinib qolsa, bu shaxsiy ma'lumot ham,
tijorat ma'lumoti ham.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = [pytest.mark.django_db, pytest.mark.tenancy]


def _indebted_child(tenant, name: str) -> Child:
    """Qarzdor bola yaratadi: tarif + yozilgan, to'lanmagan hisob-faktura."""
    with organization_context(tenant.organization.id):
        # Tarif nomi filial ichida noyob — har bir bola uchun o'ziniki.
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"Tarif — {name}",
            amount=Decimal("1500000"),
        )
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Qarzdorov",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
        )
        finance.issue_invoice(child=child, period_year=2026, period_month=7)
        return child


def test_debtor_list_shows_only_own_organization(tenant_a, tenant_b):
    _indebted_child(tenant_a, "Ozimniki")
    foreign = _indebted_child(tenant_b, "Begona")

    response = tenant_a.client().get(reverse("v1:debtor-list"))
    assert response.status_code == 200

    body = response.json()["data"]
    ids = {row["child"]["id"] for row in body["results"]}
    assert str(foreign.id) not in ids
    assert body["count"] == 1
    assert body["total_debt"] == "1500000.00"


def test_debtor_statement_of_another_tenant_is_404(tenant_a, tenant_b):
    """
    403 emas, 404.

    403 "bunday bola bor, lekin sizga ruxsat yo'q" degani bo'lardi — ya'ni
    boshqa bog'chada shu ID borligini tasdiqlardi (docs/04 §2).
    """
    foreign = _indebted_child(tenant_b, "Begona")
    response = tenant_a.client().get(reverse("v1:debtor-detail", args=[foreign.id]))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_debtor_list_requires_authentication(api_client):
    assert api_client.get(reverse("v1:debtor-list")).status_code == 401


def test_total_debt_never_includes_another_tenant(tenant_a, tenant_b):
    """
    Yig'indi ham chegaradan o'tmaydi.

    Ro'yxat to'g'ri filtrlangan, lekin summa alohida hisoblansa, u
    boshqa tashkilotning qarzini ham qo'shib yuborishi mumkin edi —
    ro'yxatda ko'rinmaydigan, lekin raqamda bor bo'lgan pul.
    """
    _indebted_child(tenant_a, "Birinchi")
    _indebted_child(tenant_b, "Ikkinchi")
    _indebted_child(tenant_b, "Uchinchi")

    body = tenant_a.client().get(reverse("v1:debtor-list")).json()["data"]
    assert body["total_debt"] == "1500000.00"
    assert len(body["results"]) == 1
