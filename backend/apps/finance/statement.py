"""
Ota-onaga yillik to'lovlar ma'lumotnomasi (Bosqich 13.8, brif §9; test 14).

Nodavlat bog'chaga to'lov ota-onaning JShDS'idan bir bola uchun oylik limit
doirasida ozod (`tax.parent_exemption_monthly`, sukut 3 000 000 — buxgalter
tasdiqlaydi). Ma'lumotnoma har oy to'langanini, qaytarilganini va limit
ichidagi qismini ko'rsatadi; to'lovchi ish beruvchi bo'lsa — nomi va STIR.

Oy — pul to'langan oy (qaytarish — qaytarilgan oy). Hisob shu yerda emas:
summalar to'lov va qaytarish hujjatlaridan o'qiladi.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from django.utils.translation import gettext

__all__ = ["annual_statement", "statement_pdf"]

ZERO = Decimal("0")


def _m(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _limit(branch_id: Any) -> Decimal:
    from apps.settings_app.services import get_setting

    try:
        return Decimal(str(get_setting(key="tax.parent_exemption_monthly", branch=branch_id) or 0))
    except ArithmeticError:
        return ZERO


def annual_statement(*, child: Any, year: int) -> dict[str, Any]:
    from apps.finance.models import Payment, Refund

    payments = Payment.objects.filter(child=child, reversed_at__isnull=True, paid_at__year=year)
    paid = dict(
        payments.annotate(m=ExtractMonth("paid_at", tzinfo=timezone.get_current_timezone()))
        .values("m")
        .annotate(total=Sum("amount"))
        .values_list("m", "total")
    )
    refunded = dict(
        Refund.objects.filter(child=child, refunded_on__year=year)
        .annotate(m=ExtractMonth("refunded_on"))
        .values("m")
        .annotate(total=Sum("amount"))
        .values_list("m", "total")
    )
    payers = sorted(
        {
            (row["payer_kind"], row["payer_name"], row["payer_tin"])
            for row in payments.values("payer_kind", "payer_name", "payer_tin")
            if row["payer_name"]
        }
    )
    limit = _limit(child.branch_id)
    months: list[dict[str, Any]] = []
    for month in range(1, 13):
        net = (paid.get(month) or ZERO) - (refunded.get(month) or ZERO)
        months.append(
            {
                "month": month,
                "paid": _m(paid.get(month) or ZERO),
                "refunded": _m(refunded.get(month) or ZERO),
                "net": _m(net),
                "exempt": _m(min(max(net, ZERO), limit) if limit > 0 else ZERO),
            }
        )
    guardians = [
        link.guardian.full_name for link in child.guardian_links.select_related("guardian")
    ]
    return {
        "year": year,
        "child": child.full_name,
        "date_of_birth": child.date_of_birth.isoformat() if child.date_of_birth else None,
        "guardians": guardians,
        "payers": [{"kind": kind, "name": name, "tin": tin} for kind, name, tin in payers],
        "limit": _m(limit),
        "months": months,
        "total_paid": _m(sum((Decimal(row["paid"]) for row in months), ZERO)),
        "total_refunded": _m(sum((Decimal(row["refunded"]) for row in months), ZERO)),
        "total_exempt": _m(sum((Decimal(row["exempt"]) for row in months), ZERO)),
    }


def _som(value: str) -> str:
    amount = Decimal(value)
    return "—" if amount == 0 else f"{int(amount):,}".replace(",", " ")


_CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "DejaVu Sans", "Noto Sans", sans-serif; font-size: 10pt; color: #1d2621; }
h1 { font-size: 15pt; margin: 0 0 2mm; }
p { margin: 1mm 0; }
table { width: 100%; border-collapse: collapse; margin: 4mm 0; }
th, td { padding: 1.4mm 2mm; border-bottom: 0.5px solid #d9dfda; text-align: right; }
th:first-child, td:first-child { text-align: left; }
tfoot td { font-weight: bold; border-top: 1px solid #1d2621; }
.muted { color: #5b675f; font-size: 9pt; }
.sign { margin-top: 14mm; }
"""


def statement_pdf(*, child: Any, year: int, organization: Any) -> bytes:
    from weasyprint import HTML

    from apps.settings_app.services import get_setting

    data = annual_statement(child=child, year=year)
    director = str(get_setting(key="contracts.director_name", branch=child.branch_id) or "")
    names = [
        gettext("Yanvar"), gettext("Fevral"), gettext("Mart"), gettext("Aprel"),
        gettext("May"), gettext("Iyun"), gettext("Iyul"), gettext("Avgust"),
        gettext("Sentabr"), gettext("Oktabr"), gettext("Noyabr"), gettext("Dekabr"),
    ]  # fmt: skip
    rows = "".join(
        f"<tr><td>{escape(names[row['month'] - 1])}</td><td>{_som(row['paid'])}</td>"
        f"<td>{_som(row['refunded'])}</td><td>{_som(row['exempt'])}</td></tr>"
        for row in data["months"]
    )
    payers = "; ".join(
        escape(item["name"] + (f" (STIR {item['tin']})" if item["tin"] else ""))
        for item in data["payers"]
    )
    html = f"""
<html><head><meta charset="utf-8"><style>{_CSS}</style></head><body>
<h1>{escape(gettext("Bogʻcha toʻlovlari haqida maʼlumotnoma — {year}").format(year=year))}</h1>
<p>{escape(organization.name)}</p>
<p>{escape(gettext("Bola"))}: <b>{escape(data["child"])}</b>
{escape(gettext("Vasiylar"))}: {escape(", ".join(data["guardians"]) or "—")}</p>
<p>{escape(gettext("Toʻlovchilar"))}: {payers or "—"}</p>
<table>
<thead><tr><th>{escape(gettext("Oy"))}</th><th>{escape(gettext("Toʻlandi"))}</th>
<th>{escape(gettext("Qaytarildi"))}</th><th>{escape(gettext("Limit ichida"))}</th></tr></thead>
<tbody>{rows}</tbody>
<tfoot><tr><td>{escape(gettext("Jami"))}</td><td>{_som(data["total_paid"])}</td>
<td>{_som(data["total_refunded"])}</td><td>{_som(data["total_exempt"])}</td></tr></tfoot>
</table>
<p class="muted">{
        escape(
            gettext(
                "Nodavlat maktabgacha taʼlim tashkilotiga toʻlov — ota-onaning JShDS imtiyozi "
                "uchun. Oylik limit: {limit} soʻm (bogʻcha sozlamasi, buxgalter tasdiqlaydi)."
            ).format(limit=_som(data["limit"]))
        )
    }</p>
<p class="sign">{escape(gettext("Direktor"))}: {escape(director) or "____________"}
&nbsp;&nbsp; {escape(gettext("Sana"))}: {timezone.localdate().strftime("%d.%m.%Y")}</p>
</body></html>"""
    return HTML(string=html).write_pdf()
