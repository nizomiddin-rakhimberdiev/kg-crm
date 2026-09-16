"""Public leadlarni yaratish — alohida platforma oqimi, tenant oqimi emas."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.platform.models import Lead

__all__ = ["create_lead"]


@transaction.atomic
def create_lead(*, data: dict[str, Any]) -> tuple[Lead, bool]:
    """Lead yaratadi yoki ayni submission qayta kelsa oldingisini qaytaradi.

    Idempotency bazadagi unique UUID bilan kafolatlanadi. Qo'shimcha 10
    daqiqalik semantik tekshiruv foydalanuvchi ikki browser tabidan ayni
    arizani yuborib qo'ygan holatni ham kamaytiradi; u normal keyingi
    sotuv so'rovini abadiy bloklamaydi.
    """
    submission_id = data["submission_id"]
    existing = Lead.objects.filter(submission_id=submission_id).first()
    if existing:
        return existing, False

    duplicate_since = timezone.now() - timedelta(minutes=10)
    likely_duplicate = Lead.objects.filter(
        phone=data["phone"],
        kindergarten_name__iexact=data["kindergarten_name"],
        created_at__gte=duplicate_since,
    ).first()
    if likely_duplicate:
        return likely_duplicate, False

    try:
        # Ichki savepoint: unique poygasi tashqi transaction'ni buzmasin.
        with transaction.atomic():
            lead = Lead.objects.create(
                name=data["name"],
                phone=data["phone"],
                kindergarten_name=data["kindergarten_name"],
                children_count=data["children_count"],
                city=data["city"],
                message=data.get("message", ""),
                language=data["language"],
                consented_at=timezone.now(),
                privacy_policy_version=data["privacy_policy_version"],
                submission_id=submission_id,
            )
        return lead, True
    except IntegrityError:
        # Ikki bir xil request bir vaqtda kelishi mumkin. Transaction
        # rollbackdan keyin yangi so'rovda mavjud qatorni o'qiymiz.
        existing = Lead.objects.get(submission_id=submission_id)
        return existing, False
