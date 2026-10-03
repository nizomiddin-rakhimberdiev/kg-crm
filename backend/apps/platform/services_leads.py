"""Public leadlarni yaratish — alohida platforma oqimi, tenant oqimi emas."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.platform import alerts
from apps.platform.models import Lead

__all__ = ["create_lead", "update_lead_status", "NOT_SET"]

#: "Qiymat berilmagan" — `None` dan farqli. `None` sanani O'CHIRADI.
NOT_SET = object()


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
                source=data.get("source", "website"),
            )
        # Sotuvga darhol xabar (PLAN 3.6). `transaction.on_commit`:
        # ariza BAZAGA tushgandan keyin yuboriladi, aks holda
        # rollback bo'lgan arizaga qo'ng'iroq qilishardi.
        transaction.on_commit(lambda: alerts.notify_new_lead(lead))
        return lead, True
    except IntegrityError:
        # Ikki bir xil request bir vaqtda kelishi mumkin. Transaction
        # rollbackdan keyin yangi so'rovda mavjud qatorni o'qiymiz.
        existing = Lead.objects.get(submission_id=submission_id)
        return existing, False


def update_lead_status(
    *,
    lead: Lead,
    status: str,
    note: str | None,
    actor: Any,
    request: Any = None,
    next_call_at: Any = NOT_SET,
) -> Lead:
    """
    Sotuvchi holatni o'zgartiradi (yangi → bog'lanildi → mos keladi → yopildi).

    Har o'zgarish platforma audit jurnaliga tushadi: kim, qachon, qaysi
    holatga. Lead — mijozning shaxsiy ma'lumoti; u bilan nima qilingani
    izsiz qolmasligi kerak.
    """
    from apps.platform import services as platform_services

    previous = lead.status
    previous_call = lead.next_call_at
    lead.status = status
    if note is not None:
        lead.note = note
    # `NOT_SET` va `None` farqli: birinchisi "tegma", ikkinchisi
    # "sanani olib tashla". Ikkalasini `None` bilan ifodalash
    # sotuvchining rejasini jimgina o'chirardi.
    if next_call_at is not NOT_SET:
        lead.next_call_at = next_call_at
    if previous != status:
        lead.status_changed_at = timezone.now()
    lead.save(update_fields=["status", "note", "next_call_at", "status_changed_at", "updated_at"])
    changes: dict[str, Any] = {"from": previous, "to": status}
    if lead.next_call_at != previous_call:
        changes["next_call_at"] = lead.next_call_at.isoformat() if lead.next_call_at else None
    platform_services.record_platform_action(
        actor=actor,
        action="lead.status",
        entity_type="lead",
        entity_id=lead.id,
        changes=changes,
        request=request,
    )
    return lead
