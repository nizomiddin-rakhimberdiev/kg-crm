"""
Hisobotni CSV'ga aylantirish.

CSV — Excel emas. Bu ongli qaror: CSV'ni Excel ham, Google Sheets ham,
1C ham ochadi, va u qo'shimcha kutubxona talab qilmaydi. `.xlsx`
formatlash (rang, birlashtirilgan katak, formula) kerak bo'lganda
qo'shiladi; hozircha "ma'lumotni chiqarib olish" ehtiyoji shu bilan
qoplanadi.

BOM (`utf-8-sig`) ataylab: Excel'ning Windows versiyasi BOMsiz UTF-8 ni
kirill/lotin diakritikasi bilan buzib ochadi va foydalanuvchi buni
"tizim krakozyabra chiqardi" deb ko'radi.
"""

from __future__ import annotations

import csv
import io
from typing import Any

__all__ = ["to_csv", "rows_for"]

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
