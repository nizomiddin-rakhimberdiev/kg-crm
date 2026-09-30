"""
To'langan eski oylik hisoblashlarini kassa jurnaliga ko'chiradi.

`cash.0002_backfill_history` to'lov, chiqim va avansni ko'chirgan edi,
lekin oylikni EMAS — u o'shanda hali `payroll_payout` jadvalisiz edi.
Natijada yangilanishdan keyin kassa qoldig'i to'langan oylik summasiga
YUQORI ko'rinardi: mijozda 118,5 mln, demoda 188 mln.

Aynan shu — jimgina noto'g'ri raqam — butun ADR-17 oldini olmoqchi
bo'lgan narsa, shuning uchun u kodda emas, MIGRATSIYADA tuzatiladi.

**Tarixiy satrlarning hammasi naqd.** `official_base` bu jadvalga
sukut 0 bilan qo'shilgan (ADR-18), ya'ni o'tgan oyliklar to'liq naqd
qism sifatida yozilgan — va ular haqiqatda ham shunday to'langan.

**Idempotent:** to'lov qatori allaqachon bor hisoblash o'tkazib
yuboriladi.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Any

from django.db import migrations
from django.utils import timezone


def _aware(value: Any, fallback: Any) -> Any:
    if isinstance(value, datetime):
        return value
    if value is None:
        value = fallback
    return timezone.make_aware(datetime.combine(value, time.min))


def _backfill_organization(apps: Any, organization_id: Any) -> None:
    CashAccount = apps.get_model("cash", "CashAccount")
    CashMovement = apps.get_model("cash", "CashMovement")
    PayrollRun = apps.get_model("payroll", "PayrollRun")
    PayrollPayout = apps.get_model("payroll", "PayrollPayout")

    tills = {
        account.branch_id: account
        for account in CashAccount.objects.filter(
            organization_id=organization_id, kind="cash", is_active=True
        )
    }
    banks = {
        account.branch_id: account
        for account in CashAccount.objects.filter(
            organization_id=organization_id, kind="bank", is_active=True
        )
    }
    if not tills:
        return

    paid_runs = PayrollRun.objects.filter(organization_id=organization_id, status="paid")
    already = set(
        PayrollPayout.objects.filter(organization_id=organization_id).values_list(
            "payroll_run_id", flat=True
        )
    )

    payouts: list[Any] = []
    movements: list[Any] = []

    for run in paid_runs:
        if run.id in already:
            continue
        till = tills.get(run.branch_id)
        if till is None:
            continue
        bank = banks.get(run.branch_id, till)
        when = run.paid_at.date() if run.paid_at else None
        occurred = _aware(when, run.finalized_at.date() if run.finalized_at else None)

        for item in run.items.all():
            for part, amount, account in (
                ("official", item.official_net, bank),
                ("cash", item.cash_net if item.cash_net else item.net, till),
            ):
                # Eski satrlarda `official_net` 0, `cash_net` esa
                # `net` ga tenglashtirilgan (payroll.0004) — shuning
                # uchun amalda faqat naqd qator yoziladi.
                if part == "cash" and item.official_net:
                    amount = item.cash_net
                if not amount or amount <= 0:
                    continue

                payout_id = uuid.uuid4()
                payouts.append(
                    PayrollPayout(
                        id=payout_id,
                        organization_id=organization_id,
                        branch_id=run.branch_id,
                        payroll_run_id=run.id,
                        payroll_item_id=item.id,
                        cash_account_id=account.id,
                        part=part,
                        amount=amount,
                        paid_on=occurred.date(),
                        note="Yangilanishdan oldin to'langan",
                        is_active=True,
                    )
                )
                movements.append(
                    CashMovement(
                        id=uuid.uuid4(),
                        organization_id=organization_id,
                        branch_id=run.branch_id,
                        cash_account_id=account.id,
                        direction="out",
                        amount=amount,
                        source_type="payroll",
                        source_id=payout_id,
                        occurred_at=occurred,
                        description=f"Oylik {run.period_year}-{run.period_month:02d}"[:255],
                        is_active=True,
                    )
                )

    PayrollPayout.objects.bulk_create(payouts, batch_size=500)
    CashMovement.objects.bulk_create(movements, batch_size=500)


def backfill(apps: Any, schema_editor: Any) -> None:
    connection = schema_editor.connection
    Organization = apps.get_model("organizations", "Organization")

    if connection.vendor != "postgresql":  # pragma: no cover — testlarda Postgres
        for organization_id in Organization.objects.values_list("id", flat=True):
            _backfill_organization(apps, organization_id)
        return

    from apps.core.rls import (
        apply_tenant_setting,
        clear_tenant_setting,
        disable_platform_mode,
        enable_platform_mode,
    )

    enable_platform_mode()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM organization")
            organization_ids = [row[0] for row in cursor.fetchall()]
    finally:
        disable_platform_mode()

    try:
        for organization_id in organization_ids:
            apply_tenant_setting(organization_id)
            _backfill_organization(apps, organization_id)
    finally:
        clear_tenant_setting()


def unbackfill(apps: Any, schema_editor: Any) -> None:
    """Orqaga: faqat shu migratsiya yozgan qatorlar."""
    connection = schema_editor.connection
    CashMovement = apps.get_model("cash", "CashMovement")
    PayrollPayout = apps.get_model("payroll", "PayrollPayout")

    if connection.vendor != "postgresql":  # pragma: no cover
        CashMovement.objects.filter(source_type="payroll").delete()
        PayrollPayout.objects.filter(note="Yangilanishdan oldin to'langan").delete()
        return

    from apps.core.rls import disable_platform_mode, enable_platform_mode

    enable_platform_mode()
    try:
        CashMovement.objects.filter(source_type="payroll").delete()
        PayrollPayout.objects.filter(note="Yangilanishdan oldin to'langan").delete()
    finally:
        disable_platform_mode()


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0004_payroll_split_and_payout"),
        ("cash", "0002_backfill_history"),
        ("organizations", "0001_initial"),
    ]

    operations = [migrations.RunPython(backfill, unbackfill)]
