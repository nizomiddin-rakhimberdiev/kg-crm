"""
Mavjud to'lov↔faktura bog'lanishini taqsimot jadvaliga ko'chiradi.

Bu **sxema ko'chishi, ma'lumot tuzatishi emas**: har bir qator ilgari
`payment.invoice` ustunida turgan aynan o'sha bog'lanishni takrorlaydi.
Shuning uchun migratsiyadan keyin birorta ekrandagi birorta raqam
o'zgarmaydi — `invoice.amount_paid` avvalgidek qiymatda qoladi, faqat
endi u taqsimot qatorlaridan hisoblanadi.

Mavjud AVANSLARNI ochiq fakturalarga qo'llash — bu boshqa ish va u
raqamlarni o'zgartiradi. U ataylab bu yerda emas, `apply_open_credits`
management buyrug'ida (`--dry-run` bilan), va uni egasi o'zi ishga
tushiradi (`docs/big-update/PLAN.md` R3).

**RLS ostida ishlaydi**: kontekstsiz siyosat hech qanday qatorni
ko'rsatmaydi va migratsiya hech narsa qilmasdan "muvaffaqiyatli"
tugardi. Shuning uchun har bir tashkilot alohida aylanib chiqiladi
(`cash/0002_backfill_history` bilan bir xil naqsh).

**Idempotent**: mavjud taqsimoti bor to'lov o'tkazib yuboriladi.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import migrations


def _backfill_organization(apps: Any, organization_id: Any) -> None:
    Payment = apps.get_model("finance", "Payment")
    PaymentAllocation = apps.get_model("finance", "PaymentAllocation")

    already = set(
        PaymentAllocation.objects.filter(
            organization_id=organization_id, released_at__isnull=True
        ).values_list("payment_id", flat=True)
    )

    payments = Payment.objects.filter(
        organization_id=organization_id,
        invoice__isnull=False,
        reversed_at__isnull=True,
    ).exclude(id__in=already)

    rows = [
        PaymentAllocation(
            id=uuid.uuid4(),
            organization_id=payment.organization_id,
            branch_id=payment.branch_id,
            payment_id=payment.id,
            invoice_id=payment.invoice_id,
            amount=payment.amount,
            allocated_at=payment.paid_at,
        )
        for payment in payments.iterator(chunk_size=500)
    ]
    PaymentAllocation.objects.bulk_create(rows, batch_size=500)


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
    """Orqaga yo'l: taqsimot qatorlari o'chadi, `payment.invoice` joyida qoladi."""
    connection = schema_editor.connection
    PaymentAllocation = apps.get_model("finance", "PaymentAllocation")

    if connection.vendor != "postgresql":  # pragma: no cover
        PaymentAllocation.objects.all().delete()
        return

    from apps.core.rls import disable_platform_mode, enable_platform_mode

    enable_platform_mode()
    try:
        PaymentAllocation.objects.all().delete()
    finally:
        disable_platform_mode()


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0008_payment_allocation"),
        ("organizations", "0001_initial"),
    ]

    operations = [migrations.RunPython(backfill, unbackfill)]
