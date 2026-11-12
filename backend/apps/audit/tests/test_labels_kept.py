"""
Jurnaldagi nom — yozuv PAYTIDAGI nom (audit 2026-11-12, G1).

Nom jonli olinardi: bola "Karimov Ali" deb yaratilib, keyin "Karimov
Alisher" ga o'zgartirilsa, YARATISH yozuvi ham "Alisher" deb ko'rinardi
— ya'ni jurnal o'zi yozilgan paytdagi haqiqatni aytmasdi. Kalitlar esa
xom qoldi: `method: cash`, `period: 2026-10`, `role: cashier`.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse

from apps.audit import services as audit
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _rows(tenant_a):
    return tenant_a.client().get(reverse("v1:audit-log-list")).json()["data"]


def test_the_label_is_the_name_at_the_time(tenant_a):
    with organization_context(tenant_a.organization.id):
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Karimov",
            date_of_birth=date(2021, 5, 5),
        )
        audit.record(
            action="create",
            organization=tenant_a.organization,
            actor=tenant_a.owner,
            entity_type="child",
            entity_id=child.id,
        )
        Child.objects.filter(pk=child.pk).update(first_name="Alisher")
    assert _rows(tenant_a)[0]["entity_label"] == "Karimov Ali"


def test_a_tariff_is_named(tenant_a):
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Yarim kun",
            amount=1,
        )
        audit.record(
            action="create",
            organization=tenant_a.organization,
            actor=tenant_a.owner,
            entity_type="tariff",
            entity_id=tariff.id,
        )
    assert _rows(tenant_a)[0]["entity_label"].startswith("Yarim kun")


def test_raw_values_are_spoken(tenant_a):
    with organization_context(tenant_a.organization.id):
        audit.record(
            action="update",
            organization=tenant_a.organization,
            actor=tenant_a.owner,
            entity_type="payment",
            changes={
                "method": {"before": "cash", "after": "terminal"},
                "period": "2026-10",
                "role": "cashier",
            },
        )
    labels = _rows(tenant_a)[0]["changes_labels"]
    assert labels["method"] == "Naqd → Terminal"
    assert labels["period"] == "10.2026"
    assert labels["role"] == "Kassir"
