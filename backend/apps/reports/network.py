"""
Tarmoq ko'rinishi — filiallar yonma-yon (Bosqich 13.6, brif §5.4, test 18).

Har filial uchun o'sha `pack.build` — raqam boshqa formuladan kelmaydi.
Eng yaxshi va eng yomon qiymat ajratiladi. Konsolidatsiyada filiallar
orasidagi o'tkazmalar chiqarib tashlanadi (`money.cash_flow`).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

__all__ = ["METRICS", "network"]

#: Ko'rsatkich → yuqori qiymat yaxshimi.
METRICS: dict[str, bool] = {
    "occupancy": True,
    "average_per_child": True,
    "collection_rate": True,
    "payroll_share": False,
    "margin": True,
    "food_per_child_day": False,
    "attention": False,
}


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    return next(section for section in data["sections"] if section["key"] == key)


def _occupancy(children: dict[str, Any]) -> str | None:
    capacity = sum(row["capacity"] or 0 for row in children["groups"])
    seated = sum(row["children"] for row in children["groups"])
    return f"{Decimal(seated) * 100 / Decimal(capacity):.1f}" if capacity else None


def _row(branch: Any, data: dict[str, Any]) -> dict[str, Any]:
    revenue = _section(data, "revenue")
    return {
        "branch_id": str(branch.id),
        "branch": branch.name,
        "children": _section(data, "children")["movement"]["end"],
        "occupancy": _occupancy(_section(data, "children")),
        "average_per_child": revenue["kpi"]["average_per_child"],
        "collection_rate": revenue["kpi"]["collection_rate"],
        "payroll_share": _section(data, "payroll")["share_of_revenue"],
        "margin": _section(data, "pnl")["current"]["margin"],
        "food_per_child_day": _section(data, "expenses")["food_per_child_day"],
        "attention": len(_section(data, "attention")["items"]),
    }


def network(*, organization_id: Any, year: int, month: int) -> dict[str, Any]:
    from apps.branches.models import Branch
    from apps.reports import money, pack

    rows = [
        _row(
            branch,
            pack.build(
                organization_id=organization_id, year=year, month=month, branch_id=branch.id
            ),
        )
        for branch in Branch.objects.filter(is_active=True).order_by("name")
    ]
    best: dict[str, str | None] = {}
    worst: dict[str, str | None] = {}
    for metric, higher_is_better in METRICS.items():
        valued = [
            (Decimal(str(row[metric])), row["branch_id"]) for row in rows if row[metric] is not None
        ]
        if len(valued) < 2:
            best[metric] = worst[metric] = None
            continue
        ordered = sorted(valued, key=lambda pair: pair[0], reverse=higher_is_better)
        best[metric], worst[metric] = ordered[0][1], ordered[-1][1]
    flow = money.cash_flow(organization_id=organization_id, year=year, month=month)
    return {
        "period": f"{year}-{month:02d}",
        "rows": rows,
        "best": best,
        "worst": worst,
        "eliminated_transfers": flow["transfers"]["eliminated"],
    }
