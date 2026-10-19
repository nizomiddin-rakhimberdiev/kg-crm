"""
Import testlari — sinovning muvaffaqiyat sharti (docs/06 Sprint 2).

Import buzuq bo'lsa, mahsulot qanchalik yaxshi bo'lmasin, 15 kunlik sinov
ma'lumot kiritish bilan o'tib ketadi va mijoz ketadi.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.children.importer import import_children, parse_rows
from apps.children.models import Child, Enrollment, Group, Guardian
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

GOOD_CSV = """Familiya,Ism,Tug'ilgan sana,Jinsi,Guruh,Ota-ona,Telefon
Valiyev,Ali,2021-03-14,o'g'il,Quyoshlar,Valiyeva Nodira,+998901112233
Karimova,Zilola,14.05.2020,qiz,Quyoshlar,Karimov Aziz,+998901112244
Toshmatov,Bekzod,2019-11-02,erkak,Yulduzlar,Toshmatova Gul,+998901112255
"""

BAD_CSV = """Familiya,Ism,Tug'ilgan sana,Jinsi
Valiyev,Ali,notogri-sana,o'g'il
,Zilola,2020-05-14,qiz
Toshmatov,Bekzod,2030-01-01,erkak
"""


def _run(tenant, csv_text: str, *, dry_run: bool = True):
    with organization_context(tenant.organization.id):
        return import_children(
            organization=tenant.organization,
            branch=tenant.branch,
            file_bytes=csv_text.encode("utf-8"),
            dry_run=dry_run,
        )


class TestParsing:
    def test_a_header_with_the_uzbek_okina_is_recognised(self):
        """ "Tugʻilgan sana" (U+02BB) — oʻzbek imlosidagi toʻgʻri yozuv."""
        rows, errors = parse_rows("Familiya;Ism;Tugʻilgan sana\nValiyev;Ali;2021-03-14\n".encode())
        assert not errors
        assert rows[0]["date_of_birth"] == "2021-03-14"

    def test_detects_semicolon_delimiter(self):
        rows, errors = parse_rows(b"Familiya;Ism;Tug'ilgan sana\nValiyev;Ali;2021-03-14\n")
        assert not errors
        assert rows[0]["last_name"] == "Valiyev"

    def test_missing_required_column_is_reported_once(self):
        rows, errors = parse_rows(b"Familiya,Ism\nValiyev,Ali\n")
        assert rows == []
        assert len(errors) == 1
        assert "date_of_birth" in errors[0].message

    def test_blank_lines_are_ignored(self):
        rows, _ = parse_rows(b"Familiya,Ism,Tug'ilgan sana\nValiyev,Ali,2021-03-14\n,,\n")
        assert len(rows) == 1

    def test_cp1251_file_is_readable(self):
        """Eski Windows Excel fayllari UTF-8 bo'lmaydi."""
        text = "Familiya,Ism,Tug'ilgan sana\nИванов,Иван,2021-03-14\n"
        rows, errors = parse_rows(text.encode("cp1251"))
        assert not errors
        assert rows[0]["last_name"] == "Иванов"


class TestDryRun:
    def test_dry_run_writes_nothing(self, tenant_a):
        report = _run(tenant_a, GOOD_CSV, dry_run=True)
        assert report.is_valid
        assert report.created == 3
        with organization_context(tenant_a.organization.id):
            assert Child.objects.count() == 0

    def test_dry_run_finds_the_same_errors_as_the_real_run(self, tenant_a):
        """
        Dry-run to'liq validatsiya qiladi.

        Foydalanuvchi "saqlash" bosgandan keyin YANGI xato chiqsa, dry-run'ning
        ma'nosi qolmaydi.
        """
        dry = _run(tenant_a, BAD_CSV, dry_run=True)
        wet = _run(tenant_a, BAD_CSV, dry_run=False)
        assert [(e.row, e.field) for e in dry.errors] == [(e.row, e.field) for e in wet.errors]


class TestErrorReporting:
    def test_errors_point_at_specific_rows(self, tenant_a):
        report = _run(tenant_a, BAD_CSV)
        assert not report.is_valid
        by_row = {(e.row, e.field) for e in report.errors}
        assert (2, "date_of_birth") in by_row  # o'qib bo'lmaydigan sana
        assert (3, "last_name") in by_row  # bo'sh familiya
        assert (4, "date_of_birth") in by_row  # kelajakdagi sana

    def test_nothing_is_written_when_any_row_fails(self, tenant_a):
        """
        Yarim import qilingan fayl eng yomon holat: foydalanuvchi qaysi
        qator o'tganini bilmaydi va qayta yuborsa dublikat oladi.
        """
        _run(tenant_a, BAD_CSV, dry_run=False)
        with organization_context(tenant_a.organization.id):
            assert Child.objects.count() == 0


class TestRealImport:
    def test_creates_children_guardians_and_groups(self, tenant_a):
        report = _run(tenant_a, GOOD_CSV, dry_run=False)
        assert report.created == 3
        with organization_context(tenant_a.organization.id):
            assert Child.objects.count() == 3
            assert Guardian.objects.count() == 3
            assert set(Group.objects.values_list("name", flat=True)) == {
                "Quyoshlar",
                "Yulduzlar",
            }
            assert Enrollment.objects.filter(end_date__isnull=True).count() == 3

    def test_reimport_is_idempotent(self, tenant_a):
        """
        Xatolarni tuzatib faylni QAYTA yuborish — eng ko'p uchraydigan
        stsenariy. U dublikat yaratmasligi shart.
        """
        _run(tenant_a, GOOD_CSV, dry_run=False)
        second = _run(tenant_a, GOOD_CSV, dry_run=False)

        assert second.created == 0
        assert second.skipped_duplicates == 3
        with organization_context(tenant_a.organization.id):
            assert Child.objects.count() == 3

    def test_guardian_is_reused_for_siblings(self, tenant_a):
        """Bir oilaning ikki bolasi bitta vasiyga bog'lanadi."""
        siblings = (
            "Familiya,Ism,Tug'ilgan sana,Jinsi,Ota-ona,Telefon\n"
            "Valiyev,Ali,2021-03-14,o'g'il,Valiyeva Nodira,+998901112233\n"
            "Valiyeva,Aziza,2019-07-01,qiz,Valiyeva Nodira,+998901112233\n"
        )
        _run(tenant_a, siblings, dry_run=False)
        with organization_context(tenant_a.organization.id):
            assert Child.objects.count() == 2
            assert Guardian.objects.count() == 1

    def test_various_date_formats_are_accepted(self, tenant_a):
        mixed = (
            "Familiya,Ism,Tug'ilgan sana\nA,Bir,2021-03-14\nB,Ikki,14.05.2020\nC,Uch,02/11/2019\n"
        )
        report = _run(tenant_a, mixed, dry_run=False)
        assert report.is_valid and report.created == 3


class TestImportEndpoint:
    def test_endpoint_returns_report(self, tenant_a):
        import io

        response = tenant_a.client().post(
            reverse("v1:child-bulk-import"),
            {"file": io.BytesIO(GOOD_CSV.encode()), "dry_run": "true"},
            format="multipart",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["dry_run"] is True
        assert data["created"] == 3
        assert data["errors"] == []

    def test_endpoint_requires_children_create_permission(self, tenant_a):
        """Kassirda `children.create` yo'q (docs/02 §11.2)."""
        import io

        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Kassir",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = client.post(
            reverse("v1:child-bulk-import"),
            {"file": io.BytesIO(GOOD_CSV.encode()), "dry_run": "true"},
            format="multipart",
        )
        assert response.status_code == 403
