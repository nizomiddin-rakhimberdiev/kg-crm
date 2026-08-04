"""
Audit jurnali endpointi testlari (docs/04 §17).

Bu endpointda tashkilot filtri **qo'lda** yozilgan: `AuditLog`
`TenantScopedModel` dan meros olmaydi, chunki u append-only va
`organization` platforma harakatlarida `NULL` bo'lishi mumkin. Ya'ni bu
yerda avtomatik himoya yo'q — faqat bitta `filter()` chaqiruvi. Shuning
uchun testi ham alohida.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


def _log(tenant, action: str = "update", entity: str = "child") -> AuditLog:
    with organization_context(tenant.organization.id):
        return _create_log(tenant, action, entity)


def _create_log(tenant, action: str, entity: str) -> AuditLog:
    return AuditLog.objects.create(
        organization=tenant.organization,
        actor=tenant.owner,
        actor_email=tenant.owner.email,
        action=action,
        entity_type=entity,
    )


class TestReadOnly:
    def test_list_returns_own_rows(self, tenant_a):
        _log(tenant_a)
        response = tenant_a.client().get(reverse("v1:audit-log-list"))
        assert response.status_code == 200
        assert len(response.json()["data"]) >= 1

    def test_log_cannot_be_edited_or_deleted(self, tenant_a):
        """
        Tahrirlanadigan audit — audit emas.

        Jurnalning butun ma'nosi shundaki, unga tegib bo'lmaydi; aks
        holda "kim o'chirdi?" degan savolga javob ham o'chirilardi.
        """
        entry = _log(tenant_a)
        client = tenant_a.client()
        url = reverse("v1:audit-log-detail", args=[entry.id])
        assert client.patch(url, {"action": "login"}, format="json").status_code == 405
        assert client.delete(url).status_code == 405

    def test_filters_by_action_and_entity(self, tenant_a):
        _log(tenant_a, action="create", entity="payment")
        _log(tenant_a, action="delete", entity="child")

        rows = (
            tenant_a.client()
            .get(reverse("v1:audit-log-list"), {"action": "create", "entity_type": "payment"})
            .json()["data"]
        )
        assert len(rows) == 1
        assert rows[0]["action"] == "create"


class TestIsolation:
    @pytest.mark.tenancy
    def test_another_organizations_log_is_invisible(self, tenant_a, tenant_b):
        foreign = _log(tenant_b)
        rows = tenant_a.client().get(reverse("v1:audit-log-list")).json()["data"]
        assert str(foreign.id) not in {row["id"] for row in rows}

    @pytest.mark.tenancy
    def test_another_organizations_entry_is_404(self, tenant_a, tenant_b):
        foreign = _log(tenant_b)
        response = tenant_a.client().get(reverse("v1:audit-log-detail", args=[foreign.id]))
        assert response.status_code == 404

    @pytest.mark.tenancy
    def test_platform_rows_without_an_organization_are_invisible(self, tenant_a):
        """
        `organization=NULL` qatorlar mijozga KO'RINMAYDI.

        Ular platforma (vendor) harakatlari — ADR-10 bo'yicha bu alohida
        kirish tekisligi. `filter(organization_id=...)` ularni tabiiy
        ravishda chiqarib tashlaydi; bu test shuni qotiradi.
        """
        # `organization` NULL — platforma tekisligidagi yozuv. U hech
        # qanday tenant kontekstida ko'rinmaydi, va RLS buni bazada
        # ta'minlaydi (ilova filtridan tashqari).
        AuditLog.objects.create(action="login_failed", actor_email="vendor@kg-crm.uz")
        rows = tenant_a.client().get(reverse("v1:audit-log-list")).json()["data"]
        assert all(row["actor_email"] != "vendor@kg-crm.uz" for row in rows)

    def test_requires_the_audit_permission(self, tenant_a):
        """Faqat egada `audit` bor (docs/02 §11.2) — menejerda yo'q."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            manager = User.objects.create_user(
                email="menejer-audit@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Menejer",
                organization=tenant_a.organization,
                role=tenant_a.role("manager"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(manager)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:audit-log-list")).status_code == 403


class TestWiring:
    def test_stock_movement_is_recorded(self, tenant_a):
        """
        Stok tuzatish izsiz qolmaydi.

        `adjustment` — qoldiqni hujjatsiz o'zgartirishning yagona yo'li,
        ya'ni "kim tuzatdi?" degan savol aynan shu yerda tug'iladi.
        """
        from apps.inventory.models import Product, Warehouse

        with organization_context(tenant_a.organization.id):
            product = Product.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Guruch",
                unit="kg",
            )
            warehouse = Warehouse.objects.create(
                organization=tenant_a.organization, branch=tenant_a.branch, name="Ombor"
            )

        response = tenant_a.client().post(
            reverse("v1:stock-movement-list"),
            {
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "movement_type": "purchase",
                "quantity": "20",
            },
            format="json",
        )
        assert response.status_code == 201

        entry = AuditLog.objects.filter(entity_type="stock_movement").first()
        assert entry is not None
        assert entry.changes["quantity"] == "20.000"

    def test_setting_change_records_the_previous_value(self, tenant_a):
        """
        Oldingi qiymat ham yoziladi.

        "SMS nega kelmayapti?" degan savolga javob ko'pincha "kimdir
        o'chirib qo'ygan" bo'ladi — va bu faqat oldingi qiymat saqlangan
        bo'lsa ko'rinadi.
        """
        response = tenant_a.client().put(
            reverse("v1:setting-detail", args=["notifications.sms_enabled"]),
            {"value": False},
            format="json",
        )
        assert response.status_code == 200

        entry = AuditLog.objects.filter(entity_type="system_setting").first()
        assert entry is not None
        assert entry.changes["from"] is True
        assert entry.changes["to"] is False
