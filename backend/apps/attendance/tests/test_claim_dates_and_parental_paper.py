"""
Da'voning ikki chegarasi (audit 2026-11-12, B1 va B4).

* Kelajakdagi kunlarga da'vo yozilardi: bola hali kelmagan-kelmasligi
  noma'lum kunlar uchun pul qaytarilardi. Oylik ta'til uchun boshqa yo'l
  bor (oyni to'xtatish) — da'vo bo'lib o'tgan kun uchun.
* "Ota-ona arizasi" hujjatsiz yozilardi. ADR-19: kredit hujjatdan
  keladi; ariza o'zi hujjat, uning raqami iz qoldiradi (egasining
  qarori). Ega yaratsa avto-tasdiq qoladi — hujjat bo'lsa.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.attendance.models_absence import AbsenceClaim, AbsenceKind, ClaimStatus
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


def test_a_claim_reaching_into_the_future_is_refused(tenant_a):
    child = _child(tenant_a)
    today = timezone.localdate()
    response = tenant_a.client().post(
        URL,
        {
            "child_id": str(child.id),
            "kind": "medical",
            "date_from": (today - timedelta(days=2)).isoformat(),
            "date_to": (today + timedelta(days=3)).isoformat(),
            "document_no": "M-4821",
        },
        format="json",
    )
    assert response.status_code == 422, response.json()
    with organization_context(tenant_a.organization.id):
        assert not AbsenceClaim.objects.exists()


def test_a_parental_application_without_its_number_waits(tenant_a):
    child = _child(tenant_a)
    payload = {
        "child_id": str(child.id),
        "kind": "parental",
        "date_from": "2026-09-07",
        "date_to": "2026-09-11",
    }
    response = tenant_a.client().post(URL, payload, format="json")
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["status"] == ClaimStatus.PENDING


def test_a_parental_application_with_its_number_is_approved_by_the_owner(tenant_a):
    child = _child(tenant_a)
    payload = {
        "child_id": str(child.id),
        "kind": "parental",
        "date_from": "2026-09-07",
        "date_to": "2026-09-11",
        "document_no": "A-17",
    }
    response = tenant_a.client().post(URL, payload, format="json")
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["status"] == ClaimStatus.APPROVED


def test_existing_parental_kinds_are_updated_only_on_apply(tenant_a):
    with organization_context(tenant_a.organization.id):
        AbsenceKind.objects.filter(code="parental").delete()
        AbsenceKind.objects.create(
            organization=tenant_a.organization,
            code="parental",
            name="Ota-ona arizasi",
            refund_mode="full_rate",
            min_days=1,
            requires_document=False,
        )

    out = StringIO()
    call_command("require_parental_documents", stdout=out)
    with organization_context(tenant_a.organization.id):
        assert AbsenceKind.objects.get(code="parental").requires_document is False
    assert "1" in out.getvalue()

    call_command("require_parental_documents", "--apply", stdout=StringIO())
    with organization_context(tenant_a.organization.id):
        assert AbsenceKind.objects.get(code="parental").requires_document is True


def test_an_overlap_names_the_days_as_people_write_them(tenant_a):
    """Xabardagi sana `dd.mm.yyyy` — ISO emas (audit 2026-11-12, H7)."""
    child = _child(tenant_a)
    payload = {
        "child_id": str(child.id),
        "kind": "medical",
        "date_from": "2026-09-07",
        "date_to": "2026-09-11",
        "document_no": "M-4821",
    }
    assert tenant_a.client().post(URL, payload, format="json").status_code == 201
    clash = tenant_a.client().post(URL, payload, format="json")
    assert clash.status_code == 422
    message = clash.json()["error"]["message"]
    assert "07.09.2026" in message and "11.09.2026" in message
