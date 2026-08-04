"""
Eksport testlari (docs/04 §14.2).

Asosiy savol: "tayyor faylni boshqa bog'cha yuklab ololadimi?" Hisobot
fayli — butun moliyaviy tarix bitta hujjatda, ya'ni sizib chiqishi eng
qimmat turdagi ma'lumot.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.reports.models import ExportStatus, ReportExport
from apps.reports.tasks import generate_export

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid_child(tenant_a) -> Child:
    with organization_context(tenant_a.organization.id):
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
        finance.record_payment(child=child, amount=Decimal("640000"), method="cash")
        return child


class TestExportJob:
    def test_queued_then_ready_with_a_file(self, tenant_a, paid_child):
        response = tenant_a.client().post(
            "/api/v1/reports/revenue/export", {"params": {}}, format="json"
        )
        assert response.status_code == 202
        job_id = response.json()["data"]["id"]
        assert response.json()["data"]["status"] == "queued"

        generate_export(job_id, str(tenant_a.organization.id))

        with organization_context(tenant_a.organization.id):
            export = ReportExport.objects.get(pk=job_id)
        assert export.status == ExportStatus.READY
        assert export.file.name.endswith(".csv")
        assert export.row_count >= 1

    def test_csv_has_a_bom_so_excel_opens_it_correctly(self, tenant_a, paid_child):
        """
        BOMsiz UTF-8 ni Windows Excel buzib ochadi.

        Foydalanuvchi buni "tizim krakozyabra chiqardi" deb ko'radi va
        aybni hisobotga qo'yadi.
        """
        with organization_context(tenant_a.organization.id):
            export = ReportExport.objects.create(
                organization=tenant_a.organization, report_type="revenue"
            )
            generate_export(str(export.id), str(tenant_a.organization.id))
            export.refresh_from_db()
            content = export.file.read()

        assert content.startswith(b"\xef\xbb\xbf")
        assert b"month,total,count" in content

    def test_failure_is_recorded_not_silent(self, tenant_a):
        """
        Xato yozuvda qoladi.

        "Eksport bosdim, hech narsa bo'lmadi" — javobsiz qoladigan
        shikoyat; sabab jurnalda bo'lishi kerak.
        """
        with organization_context(tenant_a.organization.id):
            export = ReportExport.objects.create(
                organization=tenant_a.organization,
                report_type="revenue",
                params={"date_from": "buguncha"},
            )
            generate_export(str(export.id), str(tenant_a.organization.id))
            export.refresh_from_db()

        assert export.status == ExportStatus.FAILED
        assert export.error

    def test_download_streams_the_file(self, tenant_a, paid_child):
        client = tenant_a.client()
        job_id = client.post("/api/v1/reports/revenue/export", {}, format="json").json()["data"][
            "id"
        ]
        generate_export(job_id, str(tenant_a.organization.id))

        response = client.get(f"/api/v1/reports/exports/{job_id}/download")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert b"month,total,count" in b"".join(response.streaming_content)

    def test_download_before_ready_is_a_clear_error(self, tenant_a):
        client = tenant_a.client()
        job_id = client.post("/api/v1/reports/revenue/export", {}, format="json").json()["data"][
            "id"
        ]
        with organization_context(tenant_a.organization.id):
            ReportExport.objects.filter(pk=job_id).update(status=ExportStatus.QUEUED, file="")

        response = client.get(f"/api/v1/reports/exports/{job_id}/download")
        assert response.status_code == 422
        assert "tayyor emas" in response.json()["error"]["message"]

    @pytest.mark.tenancy
    def test_another_tenant_cannot_download_the_file(self, tenant_a, tenant_b, paid_child):
        """
        Fayl `/media/` havolasi orqali BERILMAYDI.

        Statik media URL'i na autentifikatsiyani, na tashkilotni biladi:
        havolani topgan har kim boshqa bog'chaning moliyaviy hisobotini
        yuklab olardi. Bu yerda begona ish oddiygina "mavjud emas".
        """
        job_id = (
            tenant_a.client()
            .post("/api/v1/reports/revenue/export", {}, format="json")
            .json()["data"]["id"]
        )
        generate_export(job_id, str(tenant_a.organization.id))

        response = tenant_b.client().get(f"/api/v1/reports/exports/{job_id}/download")
        assert response.status_code == 404

    @pytest.mark.tenancy
    def test_export_list_shows_only_own_jobs(self, tenant_a, tenant_b):
        tenant_a.client().post("/api/v1/reports/revenue/export", {}, format="json")
        response = tenant_b.client().get(reverse("v1:report-exports"))
        assert response.status_code == 200
        assert response.json()["data"] == []


class TestWorkerContext:
    def test_task_restores_the_tenant_context(self, tenant_a, paid_child):
        """
        Ishchi tenant kontekstini O'ZI tiklaydi.

        Celery boshqa jarayonda ishlaydi va so'rovdagi `ContextVar` unga
        o'tmaydi. Kontekstsiz har qanday so'rov `TenantScopeMissing`
        bilan yiqiladi — ya'ni unutish jimgina hamma tashkilotni
        o'qishga emas, ochiq xatoga olib keladi.
        """
        with organization_context(tenant_a.organization.id):
            export = ReportExport.objects.create(
                organization=tenant_a.organization, report_type="debtors"
            )
            export_id = str(export.id)

        # Kontekstdan TASHQARIDA chaqiramiz — aynan ishchi kabi.
        assert generate_export(export_id, str(tenant_a.organization.id)) == ExportStatus.READY

    def test_generated_at_is_stamped(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            export = ReportExport.objects.create(
                organization=tenant_a.organization, report_type="debtors"
            )
            generate_export(str(export.id), str(tenant_a.organization.id))
            export.refresh_from_db()
        assert export.completed_at is not None
        assert export.completed_at <= timezone.now()
