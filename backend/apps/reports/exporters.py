"""
Hisobotni faylga aylantirish — `.xlsx` (asosiy) va `.csv` (eski fayllar).

Nega XLSX: mijoz faylni Excel'da ochadi va u yerda ishlaydi — filtr,
jami, saralash. CSV'da har safar "ustunlarga ajratish" sehrgari, sana
matnga aylanib qolishi va pul ustuni yig'ilmasligi muammosi chiqardi.
XLSX'da sana sana, pul son bo'lib keladi, sarlavha qatori muzlatilgan
va ustunlar avtofiltrga ulangan.

`openpyxl` allaqachon bog'liqlikda (bolalar importi uni ishlatadi), ya'ni
yangi kutubxona qo'shilmadi.

CSV yozuvchisi qoldi: bazada eski `.csv` fayllar bor va ularni yuklab
olish ishlashda davom etishi kerak.

BOM (`utf-8-sig`) CSV uchun ataylab: Excel'ning Windows versiyasi BOMsiz
UTF-8 ni kirill/lotin diakritikasi bilan buzib ochadi.
"""

from __future__ import annotations

import contextlib
import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.utils.translation import gettext

__all__ = ["COLUMNS", "rows_for", "to_csv", "to_xlsx", "export_filename"]

#: Fayl nomi — TILGA mos (PLAN 4.2).
#:
#: Avval fayl `revenue-20261002-1030.xlsx` deb saqlanardi. Buxgalter
#: yuklab olgan papkasida o'nta shunday fayl bo'lsa, qaysi biri nima
#: ekanini faqat ochib ko'rib bilish mumkin — va u fayllarni
#: buxgalteriyaga uzatadi, ya'ni nom boshqa odam uchun ham ma'noli
#: bo'lishi kerak.
#:
#: Nom ASCII emas: lotin o'zbek va kirill rus harflari fayl tizimida
#: ham, pochtada ham muammosiz ishlaydi. Faqat bo'shliq va `/` dan
#: qochiladi.
FILENAME_BY_TYPE: dict[str, dict[str, str]] = {
    "revenue": {"uz": "tushum", "ru": "vyruchka", "en": "revenue"},
    "expenses": {"uz": "chiqimlar", "ru": "rashody", "en": "expenses"},
    "payroll": {"uz": "oylik", "ru": "zarplata", "en": "payroll"},
    "attendance": {"uz": "davomat", "ru": "poseshchaemost", "en": "attendance"},
    "debtors": {"uz": "qarzdorlar", "ru": "dolzhniki", "en": "debtors"},
    "profit-loss": {"uz": "foyda-zarar", "ru": "pribyl-ubytok", "en": "profit-loss"},
}


def export_filename(report_type: str, *, language: str = "uz", stamp: str = "") -> str:
    """
    `tushum_2026-10-02.xlsx` — hisobot nomi va sana.

    Sana ISO shaklda qoladi (`2026-10-02`), `dd.mm.yyyy` emas: fayl
    nomida ISO alifbo bo'yicha ham xronologik tartibda saqlanadi, ya'ni
    papkadagi ro'yxat o'zi vaqt bo'yicha tiziladi.
    """
    names = FILENAME_BY_TYPE.get(report_type, {})
    base = names.get(language) or names.get("uz") or report_type
    return f"{base}_{stamp}.xlsx" if stamp else f"{base}.xlsx"


Row = dict[str, Any]


def rows_for(report_type: str, payload: dict[str, Any]) -> tuple[list[str], list[Row]]:
    """Hisobot javobidan jadval qatorlarini ajratadi."""
    if report_type == "revenue":
        return (
            ["period", "total", "count"],
            [dict(row) for row in payload["by_period"]],
        )
    if report_type == "expenses":
        return (
            ["category", "total"],
            [dict(row) for row in payload["by_category"]],
        )
    if report_type == "payroll":
        return (
            ["month", "gross", "deductions", "net"],
            [dict(row) for row in payload["by_month"]],
        )
    if report_type == "attendance":
        return (
            ["group", "present", "late", "absent", "excused", "total", "attendance_rate"],
            [{k: v for k, v in row.items() if k != "group_id"} for row in payload["by_group"]],
        )
    if report_type == "debtors":
        return (
            ["full_name", "balance"],
            [{"full_name": row["full_name"], "balance": row["balance"]} for row in payload["rows"]],
        )
    if report_type == "profit-loss":
        return (
            ["period", "revenue", "expenses", "payroll", "net"],
            [dict(row) for row in payload["by_period"]],
        )
    raise ValueError(f"Noma'lum hisobot turi: {report_type}")


def to_csv(headers: list[str], rows: list[Row]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8-sig")


# --- Batafsil eksport ---
#
# Ustunlar: (kalit, sarlavha, tur). Tur faqat XLSX formatlash uchun:
# "money" — son + mingliklar ajratkichi, "date" — sana. Sarlavhalar
# `gettext` orqali: eksport so'ralgan tilda keladi (ADR-16).

Column = tuple[str, str, str]


def COLUMNS(report_type: str) -> list[Column]:  # noqa: N802 — jadval nomi kabi o'qiladi
    if report_type == "revenue":
        return [
            ("date", gettext("Sana"), "date"),
            ("child", gettext("Bola"), "text"),
            ("invoice", gettext("Hisob-faktura"), "text"),
            ("method", gettext("Toʻlov usuli"), "text"),
            ("amount", gettext("Summa"), "money"),
            ("reference", gettext("Maʼlumotnoma"), "text"),
            ("received_by", gettext("Qabul qildi"), "text"),
            ("reversed", gettext("Qaytarilgan"), "text"),
        ]
    if report_type == "expenses":
        return [
            ("date", gettext("Sana"), "date"),
            ("category", gettext("Kategoriya"), "text"),
            ("description", gettext("Tavsif"), "text"),
            ("amount", gettext("Summa"), "money"),
            ("status", gettext("Holat"), "text"),
            ("approved_by", gettext("Tasdiqladi"), "text"),
        ]
    if report_type == "payroll":
        return [
            ("period", gettext("Davr"), "text"),
            ("employee", gettext("Xodim"), "text"),
            ("position", gettext("Lavozim"), "text"),
            ("base", gettext("Bazaviy"), "money"),
            ("bonus", gettext("Bonus"), "money"),
            ("advance", gettext("Avans"), "money"),
            ("deduction", gettext("Ushlab qolindi"), "money"),
            ("gross", gettext("Yalpi"), "money"),
            ("net", gettext("Sof"), "money"),
            ("status", gettext("Holat"), "text"),
            ("note", gettext("Izoh"), "text"),
        ]
    if report_type == "debtors":
        return [
            ("child", gettext("Bola"), "text"),
            ("group", gettext("Guruh"), "text"),
            ("guardian", gettext("Vasiy"), "text"),
            ("phone", gettext("Telefon"), "text"),
            ("oldest_due", gettext("Eng eski muddat"), "date"),
            ("days_overdue", gettext("Kechikish (kun)"), "number"),
            ("debt", gettext("Qarz"), "money"),
        ]
    if report_type == "attendance":
        return [
            ("date", gettext("Sana"), "date"),
            ("child", gettext("Bola"), "text"),
            ("group", gettext("Guruh"), "text"),
            ("status", gettext("Holat"), "text"),
            ("reason", gettext("Sabab"), "text"),
        ]
    if report_type == "staff-attendance":
        # Qog'oz tabel ko'rinishi: xodim, 1…31 kun belgisi, jami.
        return [
            ("employee", gettext("Xodim"), "text"),
            ("position", gettext("Lavozim"), "text"),
            ("branch", gettext("Filial"), "text"),
            *[(f"d{day}", str(day), "text") for day in range(1, 32)],
            ("present", gettext("Keldi"), "number"),
            ("absent", gettext("Kelmadi"), "number"),
            ("sick", gettext("Kasal"), "number"),
            ("leave", gettext("Taʼtilda"), "number"),
            ("working_days", gettext("Ish kunlari"), "number"),
        ]
    if report_type == "profit-loss":
        return [
            ("period", gettext("Davr"), "text"),
            ("revenue", gettext("Tushum"), "money"),
            ("expenses", gettext("Chiqimlar"), "money"),
            ("payroll", gettext("Oylik maosh"), "money"),
            ("net", gettext("Sof natija"), "money"),
        ]
    raise ValueError(f"Noma'lum hisobot turi: {report_type}")


def to_xlsx(report_type: str, rows: list[Row], *, title: str = "") -> bytes:
    """
    Qatorlarni `.xlsx` ga yozadi: muzlatilgan sarlavha, avtofiltr,
    pul va sana uchun to'g'ri katak turi, ustun kengligi mazmunga qarab.

    Pul MATN emas, SON bo'lib yoziladi — aks holda Excel'da ustunni
    yig'ib bo'lmasdi va aynan shu narsa uchun fayl ochiladi.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    columns = COLUMNS(report_type)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = (title or report_type)[:31]

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="334155")
    for index, (_, label, _kind) in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=index, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")

    for row_index, row in enumerate(rows, start=2):
        for col_index, (key, _label, kind) in enumerate(columns, start=1):
            value = row.get(key, "")
            if kind == "money" and value not in ("", None):
                value = float(Decimal(str(value)))
            elif kind == "date" and isinstance(value, str) and value:
                with contextlib.suppress(ValueError):
                    value = date.fromisoformat(value)
            elif kind == "number" and value not in ("", None):
                value = int(value)
            cell = sheet.cell(row=row_index, column=col_index, value=value)
            if kind == "money":
                cell.number_format = "#,##0"
            elif kind == "date" and isinstance(value, date | datetime):
                cell.number_format = "DD.MM.YYYY"

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{max(len(rows) + 1, 1)}"
    for index, (key, label, _kind) in enumerate(columns, start=1):
        longest = max((len(str(row.get(key, ""))) for row in rows), default=0)
        sheet.column_dimensions[get_column_letter(index)].width = min(
            max(len(label) + 4, longest + 2), 46
        )

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
