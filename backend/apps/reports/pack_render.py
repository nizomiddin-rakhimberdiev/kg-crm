"""
Paketning PDF va Excel ko'rinishlari (Bosqich 13.5, brif §8).

Ikkalasi ham `pack.build` JSON'idan — raqamni qayta hisoblamaydi.
PDF: A4, sahifa raqami, boshida xulosa, oxirida "Tayyorladi / Topshirdi /
Qabul qildi" bloki. Excel: har bo'lim alohida varaq, oxirida xom
ma'lumot varaqlari — mustaqil tekshirish uchun.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

from django.utils.translation import gettext

__all__ = ["to_pdf", "to_xlsx"]

_HIDDEN = {"id", "source", "link", "subject", "at", "user_id", "payment_id", "branch_id"}


def _number(value: Any) -> str:
    """So'm, minglik ajratgich, tiyinsiz; manfiy — minus bilan; nol — "—" (brif §5)."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return escape(str(value))
    if not re.fullmatch(r"-?\d+(\.\d+)?", str(value)):
        return escape(str(value))
    if amount == 0:
        return "—"
    text = f"{abs(int(amount)):,}".replace(",", " ")
    return f'<span class="neg">−{text}</span>' if amount < 0 else text


def _table(rows: list[dict[str, Any]]) -> str:
    columns = [
        key for key in rows[0] if key not in _HIDDEN and not isinstance(rows[0][key], (dict, list))
    ]
    head = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{_number(row.get(column, ''))}</td>" for column in columns) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _render(value: Any, label: str = "") -> str:
    if isinstance(value, dict):
        scalars = {
            k: v for k, v in value.items() if k not in _HIDDEN and not isinstance(v, (dict, list))
        }
        nested = {
            k: v for k, v in value.items() if k not in _HIDDEN and isinstance(v, (dict, list))
        }
        html = ""
        if scalars:
            html += (
                "<table class='kv'>"
                + "".join(
                    f"<tr><th>{escape(str(k))}</th><td>{_number(v)}</td></tr>"
                    for k, v in scalars.items()
                )
                + "</table>"
            )
        for key, item in nested.items():
            html += f"<h3>{escape(str(key))}</h3>" + _render(item, key)
        return html
    if isinstance(value, list):
        if not value:
            return "<p class='muted'>—</p>"
        if all(isinstance(row, dict) for row in value):
            return _table(value)
        return "<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in value) + "</ul>"
    return f"<p>{_number(value)}</p>"


_CSS = """
@page { size: A4; margin: 16mm 14mm 18mm;
  @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; color: #555; } }
body { font-family: "DejaVu Sans", "Noto Sans", sans-serif; font-size: 9.5pt; color: #1d2621; }
h1 { font-size: 17pt; margin: 0 0 4mm; }
h2 { font-size: 12.5pt; margin: 7mm 0 2mm; padding-bottom: 1mm; border-bottom: 1px solid #c9d1cb;
  page-break-after: avoid; }
h3 { font-size: 10pt; margin: 3mm 0 1mm; color: #3c4a42; }
table { width: 100%; border-collapse: collapse; margin: 1mm 0 3mm; }
th, td { padding: 1.2mm 1.5mm; border-bottom: 0.5px solid #e1e6e2; text-align: left; }
td { font-variant-numeric: tabular-nums; }
table.kv th { width: 45%; font-weight: normal; color: #4a574f; }
.neg { color: #b42318; }
.muted { color: #6b776f; }
.sign { margin-top: 10mm; page-break-inside: avoid; }
.sign td { height: 12mm; vertical-align: bottom; }
"""


def to_pdf(data: dict[str, Any], *, title: str, prepared_by: str = "") -> bytes:
    """A4 PDF — serverda, HTML→PDF (WeasyPrint)."""
    from weasyprint import HTML

    parts = [f"<h1>{escape(title)}</h1>"]
    for section in data["sections"]:
        content = {k: v for k, v in section.items() if k not in ("key", "title")}
        parts.append(f"<h2>{escape(section['title'])}</h2>{_render(content)}")
    stamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    parts.append(
        "<table class='sign'><tr>"
        f"<td>{escape(gettext('Tayyorladi'))}: {escape(prepared_by)}<br>{stamp}</td>"
        f"<td>{escape(gettext('Topshirdi'))}: ____________</td>"
        f"<td>{escape(gettext('Qabul qildi'))}: ____________</td>"
        "</tr></table>"
    )
    head = f"<head><meta charset='utf-8'><style>{_CSS}</style></head>"
    html = f"<html>{head}<body>{''.join(parts)}</body></html>"
    return HTML(string=html).write_pdf()


def _sheet_name(text: str, used: set[str]) -> str:
    name = re.sub(r"[\[\]:*?/\\]", " ", text)[:28].strip() or "Sheet"
    candidate, index = name, 2
    while candidate in used:
        candidate, index = f"{name[:25]} {index}", index + 1
    used.add(candidate)
    return candidate


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _HIDDEN:
                continue
            rows.extend(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            label = (
                item.get("label") or item.get("id") or item.get("category")
                if isinstance(item, dict)
                else None
            )
            rows.extend(_flatten(item, f"{prefix}[{label or index}]"))
    else:
        rows.append((prefix, value))
    return rows


def _cell(value: Any) -> Any:
    try:
        if isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value):
            return float(Decimal(value))
    except InvalidOperation:
        pass
    return value


def to_xlsx(data: dict[str, Any], *, raw: dict[str, list[dict[str, Any]]]) -> bytes:
    """Har bo'lim — varaq; oxirida xom ma'lumot varaqlari."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    workbook.remove(workbook.active)
    used: set[str] = set()
    for section in data["sections"]:
        sheet = workbook.create_sheet(_sheet_name(section["title"], used))
        sheet.append([section["title"]])
        sheet["A1"].font = Font(bold=True, size=12)
        content = {k: v for k, v in section.items() if k not in ("key", "title")}
        for path, value in _flatten(content):
            sheet.append([path, _cell(value)])
        sheet.column_dimensions["A"].width = 60
        sheet.column_dimensions["B"].width = 20
    for name, rows in raw.items():
        sheet = workbook.create_sheet(_sheet_name(name, used))
        if not rows:
            sheet.append(["—"])
            continue
        columns = list(rows[0])
        sheet.append(columns)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append([_cell(row.get(column)) for column in columns])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
