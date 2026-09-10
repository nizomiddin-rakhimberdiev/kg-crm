"""
Excel shabloni va `.xlsx` import testlari (docs/06 Sprint 2).

Import — sinov davrining muvaffaqiyat sharti: bog'cha 150 bolani
kiritmaguncha tizimning qiymatini sezmaydi. Shuning uchun bu yerdagi
asosiy test **aylanma**: shablonni yaratamiz, uni to'ldiramiz va
importerga qaytaramiz. Ustun nomlari ikki joyda ajralib qolsa, aynan
shu test qizaradi.
"""

from __future__ import annotations

import io

import pytest
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from apps.children.importer import build_template, parse_rows
from apps.children.models import Child
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


def _fill(rows: list[tuple[str, ...]]) -> bytes:
    """Shablonni oladi, namuna qatorlarni o'chirib, berilganini yozadi."""
    workbook = load_workbook(io.BytesIO(build_template()))
    sheet = workbook["Bolalar"]
    sheet.delete_rows(2, sheet.max_row)
    for row_index, row in enumerate(rows, start=2):
        for column_index, value in enumerate(row, start=1):
            sheet.cell(row=row_index, column=column_index, value=value)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class TestTemplate:
    def test_template_is_a_real_xlsx(self):
        content = build_template()
        assert content.startswith(b"PK\x03\x04"), "xlsx — ZIP arxiv bo'lishi kerak"
        workbook = load_workbook(io.BytesIO(content))
        assert workbook.sheetnames == ["Bolalar", "Yo'riqnoma"]

    def test_the_importer_can_read_its_own_template(self):
        """
        Aylanma: shablon → importer.

        Bu testning butun ma'nosi shu. Ustun nomlari shablonda va
        importerda ALOHIDA yozilgan bo'lsa, ular ertami-kechmi
        ajraladi — va o'shanda mijoz to'ldirgan fayl "majburiy ustun
        topilmadi" deb rad etilardi.
        """
        rows, errors = parse_rows(build_template())
        assert errors == []
        assert len(rows) == 2, "namuna qatorlar o'qilishi kerak"
        assert rows[0]["last_name"] == "Valiyev"
        assert rows[0]["date_of_birth"] == "14.03.2021"
        assert rows[0]["guardian_phone"] == "+998901112233"

    def test_examples_show_the_expected_date_format(self):
        """
        Namuna qator — hujjat o'rnini bosadi.

        Bo'sh jadval "sanani qanday yozay?" degan savolni ochiq
        qoldiradi; namuna javobni ko'rsatib turadi.
        """
        rows, _ = parse_rows(build_template())
        for row in rows:
            assert "." in row["date_of_birth"], "namunada kun.oy.yil ko'rsatilishi kerak"

    def test_guide_sheet_is_ignored_by_the_importer(self):
        """Import faqat birinchi varaqni o'qiydi — yo'riqnoma xalaqit bermaydi."""
        rows, errors = parse_rows(build_template())
        assert errors == []
        assert all(row["last_name"] not in ("", "Qanday to'ldiriladi") for row in rows)


class TestXlsxImport:
    def test_filled_template_imports(self, tenant_a):
        content = _fill(
            [
                (
                    "Sobirov",
                    "Jasur",
                    "05.09.2021",
                    "o'g'il",
                    "",
                    "",
                    "Sobirova Malika",
                    "+998901239001",
                ),
                (
                    "Nazarova",
                    "Sevara",
                    "17.01.2021",
                    "qiz",
                    "",
                    "",
                    "Nazarov Alisher",
                    "+998901239002",
                ),
            ]
        )
        response = tenant_a.client().post(
            reverse("v1:child-bulk-import"),
            {"file": io.BytesIO(content), "dry_run": "false"},
            format="multipart",
        )
        assert response.status_code == 200, response.json()
        report = response.json()["data"]
        assert report["created"] == 2
        assert report["errors"] == []

        with organization_context(tenant_a.organization.id):
            assert Child.objects.filter(last_name="Sobirov").exists()

    def test_dates_survive_as_real_excel_dates(self, tenant_a):
        """
        Excel sanani `datetime` qilib beradi, matn emas.

        Foydalanuvchi yacheykani sana formatida to'ldirsa (Excel buni
        avtomatik qiladi), import baribir uni tushunishi kerak.
        """
        from datetime import date as date_type

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Familiya", "Ism", "Tug'ilgan sana"])
        sheet.append(["Excelov", "Sana", date_type(2021, 3, 14)])
        buffer = io.BytesIO()
        workbook.save(buffer)

        rows, errors = parse_rows(buffer.getvalue())
        assert errors == []
        assert rows[0]["date_of_birth"] == "14.03.2021"

    def test_phone_is_not_mangled_into_a_float(self, tenant_a):
        """Excel raqamlarni `float` qiladi — telefon `9.98e11` bo'lib qolmasin."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Familiya", "Ism", "Tug'ilgan sana", "Telefon"])
        sheet.append(["Raqamov", "Test", "14.03.2021", 998901234567])
        buffer = io.BytesIO()
        workbook.save(buffer)

        rows, _ = parse_rows(buffer.getvalue())
        assert rows[0]["guardian_phone"] == "998901234567"

    def test_trailing_empty_rows_are_ignored(self, tenant_a):
        """
        Excel faylining oxirida yuzlab bo'sh qator bo'lishi mumkin.

        Ular xato hisobotini to'ldirib, haqiqiy xatolarni ko'rinmas
        qilib qo'yardi.
        """
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Familiya", "Ism", "Tug'ilgan sana"])
        sheet.append(["Yagona", "Bola", "14.03.2021"])
        for _ in range(50):
            sheet.append([None, None, None])
        buffer = io.BytesIO()
        workbook.save(buffer)

        rows, errors = parse_rows(buffer.getvalue())
        assert len(rows) == 1
        assert errors == []

    def test_csv_still_works(self, tenant_a):
        """Eski CSV oqimi buzilmasligi kerak — mijozlarda tayyor fayllar bor."""
        csv_bytes = ("Familiya;Ism;Tug'ilgan sana\nCsvov;Eski;14.03.2021\n").encode("utf-8-sig")
        rows, errors = parse_rows(csv_bytes)
        assert errors == []
        assert rows[0]["last_name"] == "Csvov"

    def test_a_broken_file_gives_a_clear_message(self, tenant_a):
        rows, errors = parse_rows(b"PK\x03\x04buzuq-arxiv")
        assert rows == []
        assert errors and "Excel" in errors[0].message


class TestTemplateEndpoint:
    def test_download(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:child-import-template"))
        assert response.status_code == 200
        assert "spreadsheetml" in response["Content-Type"]
        assert "bolalar-shablon.xlsx" in response["Content-Disposition"]

    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("v1:child-import-template")).status_code == 401

    def test_downloaded_file_round_trips(self, tenant_a):
        """Endpointdan kelgan aynan shu bayt oqimi importga yaraydi."""
        response = tenant_a.client().get(reverse("v1:child-import-template"))
        content = b"".join(response.streaming_content)
        rows, errors = parse_rows(content)
        assert errors == []
        assert len(rows) == 2
