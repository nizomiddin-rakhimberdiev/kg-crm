"""
Eksport — iz qoldiradi va o'z tilida nomlanadi (audit 2026-11-12, F4).

Hisobot fayli bog'chadan chiqib ketadigan yagona yo'l: kim, qachon,
qaysi hisobotni olgani audit jurnalida turishi kerak. Rus tilidagi
fayl nomi esa "vyruchka" emas — "выручка".
"""

from __future__ import annotations

import pytest

from apps.audit.models import AuditLog
from apps.core.tenancy import organization_context
from apps.reports import exporters

pytestmark = pytest.mark.django_db


def test_requesting_an_export_is_audited(tenant_a):
    response = tenant_a.client().post("/api/v1/reports/revenue/export", {}, format="json")
    assert response.status_code == 202, response.json()
    with organization_context(tenant_a.organization.id):
        log = AuditLog.objects.get(entity_type="report_export")
    assert log.action == "export"
    assert log.changes["report_type"] == "revenue"


def test_a_russian_file_name_is_russian():
    assert exporters.export_filename("revenue", language="ru") == "выручка.xlsx"
