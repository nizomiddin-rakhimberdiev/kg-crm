"""
Hisobotni topshirish va qabul qilish — A / B / C (Bosqich 13.6, brif §2,
§8; ADR-42).

Raqamlar modelga bog'liq EMAS (test 1): paket har doim `pack.build` dan,
model faqat jarayonni tanlaydi.

* **A** — ega tekshiruvlardan keyin "Tasdiqladim" bosadi.
* **B** — boshqaruvchi topshiradi; rahbar raqam yonida savol beradi,
  qaytaradi (sabab bilan) yoki qabul qiladi; har rahbar alohida.
* **C** — har filial B kabi; tashkilot darajasidagi konsolidatsiyani ega
  hamma filial qabul qilingandan keyin tasdiqlaydi.

Topshirish sharti hamma modelda bir xil: har qizil tekshiruv va har "Diqqat"
bandida izoh bor. Topshirilgan yoki tasdiqlangan hisobot — o'zgarmas
`ReportSnapshot`; jarayon tarixi — `ReportEvent`, faqat qo'shiladi.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.reports.models import (
    ReportEvent,
    ReportReview,
    ReportSnapshot,
    ReviewEventKind,
    ReviewStatus,
)

__all__ = [
    "GOVERNANCE_MODELS",
    "accept",
    "answer",
    "approve",
    "ask",
    "blockers",
    "deadline",
    "model_for",
    "note",
    "review_for",
    "send_back",
    "state",
    "submit",
]

GOVERNANCE_MODELS = ("A", "B", "C")

_OPEN = (ReviewStatus.SUBMITTED, ReviewStatus.RESUBMITTED, ReviewStatus.QUESTION)


def _setting(key: str, branch_id: Any) -> Any:
    from apps.settings_app.services import get_setting

    return get_setting(key=key, branch=branch_id)


def model_for(branch_id: Any) -> str:
    """Filial sozlamasi, bo'lmasa tashkilotniki; noma'lum qiymat — "A"."""
    value = str(_setting("governance.model", branch_id) or "A").strip().upper()
    return value if value in GOVERNANCE_MODELS else "A"


def deadline(year: int, month: int, branch_id: Any = None) -> date:
    """Keyingi oyning `governance.deadline_day` sanasi (sukut 5)."""
    try:
        day = int(_setting("governance.deadline_day", branch_id) or 5)
    except (TypeError, ValueError):
        day = 5
    day = min(max(day, 1), 28)
    return date(year + month // 12, month % 12 + 1, day)


def review_for(*, organization: Any, year: int, month: int, branch_id: Any) -> ReportReview:
    review, _ = ReportReview.objects.get_or_create(
        organization=organization,
        branch_id=branch_id,
        period_year=year,
        period_month=month,
    )
    return review


def _locked(review: ReportReview) -> ReportReview:
    return ReportReview.objects.select_for_update().get(pk=review.pk)


# --- Topshirish sharti ---


def attention_path(item: dict[str, Any]) -> str:
    """ "Diqqat" bandining barqaror manzili — izoh unga bog'lanadi."""
    subject = item.get("subject") or {}
    if subject.get("id"):
        return f"attention:{item['rule']}:{subject.get('type', '')}:{subject['id']}"
    digest = hashlib.sha1(str(item.get("message", "")).encode()).hexdigest()[:12]  # noqa: S324
    return f"attention:{item['rule']}:{digest}"


def blockers(review: ReportReview) -> list[dict[str, Any]]:
    """Izohsiz qizil tekshiruvlar va izohsiz "Diqqat" bandlari."""
    from apps.intelligence import control

    scope: dict[str, Any] = {
        "organization_id": review.organization_id,
        "year": review.period_year,
        "month": review.period_month,
        "branch_id": review.branch_id,
    }
    noted = set(review.events.filter(kind=ReviewEventKind.NOTE).values_list("path", flat=True))
    found = [
        {
            "path": f"checks:{row['id']}",
            "kind": "check",
            "title": row["title"],
            "detail": row["detail"],
        }
        for row in control.checks(**scope)
        if row["status"] == "fail"
    ]
    found += [
        {
            "path": attention_path(item),
            "kind": "attention",
            "title": item["title"],
            "detail": item["message"],
        }
        for item in control.attention(**scope)
    ]
    return [row for row in found if row["path"] not in noted]


def _require_ready(review: ReportReview) -> None:
    missing = blockers(review)
    if missing:
        raise BusinessRuleViolation(
            gettext("Izohsiz qolgan: {items}. Har qizil tekshiruv va Diqqatga izoh yozing.").format(
                items="; ".join(row["title"] for row in missing[:6])
            )
        )


# --- Nusxa ---


def _freeze(review: ReportReview, user: Any) -> ReportSnapshot:
    """Jonli paket → nusxa. Ma'lumot o'zgarmagan bo'lsa — oxirgi versiya."""
    from apps.reports import pack

    data = pack.build(
        organization_id=review.organization_id,
        year=review.period_year,
        month=review.period_month,
        branch_id=review.branch_id,
    )
    digest = pack.checksum(data)
    latest = (
        ReportSnapshot.objects.select_for_update()
        .filter(
            branch_id=review.branch_id,
            period_year=review.period_year,
            period_month=review.period_month,
        )
        .order_by("-version")
        .first()
    )
    if latest is not None and latest.checksum == digest:
        return latest
    return ReportSnapshot.objects.create(
        organization_id=review.organization_id,
        branch_id=review.branch_id,
        period_year=review.period_year,
        period_month=review.period_month,
        version=(latest.version + 1) if latest else 1,
        data=data,
        checksum=digest,
        created_by=user,
    )


def _event(review: ReportReview, user: Any, kind: str, **fields: Any) -> ReportEvent:
    return ReportEvent.objects.create(
        organization_id=review.organization_id, review=review, kind=kind, author=user, **fields
    )


def _period(review: ReportReview) -> str:
    where = f", {review.branch.name}" if review.branch is not None else ""
    return f"{review.period_month:02d}.{review.period_year}{where}"


def _tell_submitter(review: ReportReview, text: str) -> None:
    from apps.intelligence import alerts

    if review.submitted_by_id:
        alerts.notify_user(user=review.submitted_by, text=text)


# --- Amallar ---


def submit(*, review: ReportReview, user: Any) -> ReportReview:
    """B/C: boshqaruvchi topshiradi — nusxa muzlaydi, rahbarlarga xabar."""
    from apps.intelligence import alerts

    model = model_for(review.branch_id)
    if model == "A":
        raise BusinessRuleViolation(
            gettext("A modelda hisobotni topshirish yoʻq — ega oʻzi tasdiqlaydi.")
        )
    if model == "C" and review.branch_id is None and _branches(review):
        raise BusinessRuleViolation(
            gettext("C modelda filiallar topshiradi; konsolidatsiyani ega tasdiqlaydi.")
        )
    with transaction.atomic():
        review = _locked(review)
        if review.status not in (ReviewStatus.DRAFT, ReviewStatus.RETURNED):
            raise BusinessRuleViolation(gettext("Hisobot allaqachon topshirilgan."))
        _require_ready(review)
        snapshot = _freeze(review, user)
        again = review.events.filter(kind=ReviewEventKind.SUBMIT).exists()
        review.status = ReviewStatus.RESUBMITTED if again else ReviewStatus.SUBMITTED
        review.snapshot = snapshot
        review.submitted_by = user
        review.submitted_at = timezone.now()
        review.save(
            update_fields=["status", "snapshot", "submitted_by", "submitted_at", "updated_at"]
        )
        _event(review, user, ReviewEventKind.SUBMIT, snapshot=snapshot)
        alerts.notify(
            organization_id=review.organization_id,
            text=gettext("📄 Hisobot topshirildi: {period} (v{version}), {who}.").format(
                period=_period(review), version=snapshot.version, who=user.full_name
            ),
        )
    return review


def _branches(review: ReportReview) -> list[Any]:
    from apps.branches.models import Branch

    rows = list(Branch.objects.filter(is_active=True).order_by("name"))
    return rows if len(rows) > 1 else []


def approve(*, review: ReportReview, user: Any) -> ReportReview:
    """A (va C konsolidatsiyasi): ega tekshiruvlardan keyin tasdiqlaydi."""
    model = model_for(review.branch_id)
    consolidation = model == "C" and review.branch_id is None and _branches(review)
    if model != "A" and not consolidation:
        raise BusinessRuleViolation(
            gettext("Bu modelda hisobot topshiriladi va qabul qilinadi, tasdiqlanmaydi.")
        )
    with transaction.atomic():
        review = _locked(review)
        if consolidation:
            waiting = [
                branch.name
                for branch in _branches(review)
                if not ReportReview.objects.filter(
                    branch=branch,
                    period_year=review.period_year,
                    period_month=review.period_month,
                    status=ReviewStatus.ACCEPTED,
                ).exists()
            ]
            if waiting:
                raise BusinessRuleViolation(
                    gettext("Filiallar hali qabul qilinmagan: {names}.").format(
                        names=", ".join(waiting)
                    )
                )
        _require_ready(review)
        snapshot = _freeze(review, user)
        if review.status == ReviewStatus.ACCEPTED and review.snapshot_id == snapshot.pk:
            raise BusinessRuleViolation(gettext("Hisobot allaqachon tasdiqlangan."))
        review.status = ReviewStatus.ACCEPTED
        review.snapshot = snapshot
        review.save(update_fields=["status", "snapshot", "updated_at"])
        _event(review, user, ReviewEventKind.APPROVE, snapshot=snapshot)
    return review


def _text(value: Any, message: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise BusinessRuleViolation(message)
    return text[:4000]


def ask(*, review: ReportReview, user: Any, path: str, text: str) -> ReportEvent:
    """Rahbar raqam yonida savol beradi."""
    body = _text(text, gettext("Savol matnini yozing."))
    where = _text(path, gettext("Savol qaysi raqamga ekanini koʻrsating."))
    with transaction.atomic():
        review = _locked(review)
        if review.status not in _OPEN:
            raise BusinessRuleViolation(gettext("Savol faqat topshirilgan hisobotga beriladi."))
        event = _event(
            review,
            user,
            ReviewEventKind.QUESTION,
            path=where[:200],
            text=body,
            snapshot=review.snapshot,
        )
        review.status = ReviewStatus.QUESTION
        review.save(update_fields=["status", "updated_at"])
    _tell_submitter(
        review,
        gettext("❓ {who} savol berdi ({period}): {text}").format(
            who=user.full_name, period=_period(review), text=body
        ),
    )
    return event


def _open_questions(review: ReportReview) -> Any:
    return review.events.filter(kind=ReviewEventKind.QUESTION, replies__isnull=True)


def _resting_status(review: ReportReview) -> str:
    submits = review.events.filter(kind=ReviewEventKind.SUBMIT).count()
    return ReviewStatus.RESUBMITTED if submits > 1 else ReviewStatus.SUBMITTED


def answer(*, question: ReportEvent, user: Any, text: str) -> ReportEvent:
    """Javob o'sha joyda — savolga bog'lanadi; savol qolmasa holat qaytadi."""
    body = _text(text, gettext("Javob matnini yozing."))
    if question.kind != ReviewEventKind.QUESTION:
        raise BusinessRuleViolation(gettext("Bu savol emas."))
    with transaction.atomic():
        review = _locked(question.review)
        if question.replies.exists():
            raise BusinessRuleViolation(gettext("Bu savolga javob berilgan."))
        event = _event(
            review,
            user,
            ReviewEventKind.ANSWER,
            path=question.path,
            text=body,
            parent=question,
            snapshot=review.snapshot,
        )
        if review.status == ReviewStatus.QUESTION and not _open_questions(review).exists():
            review.status = _resting_status(review)
            review.save(update_fields=["status", "updated_at"])
    return event


def note(*, review: ReportReview, user: Any, path: str, text: str) -> ReportEvent:
    """Izoh yoki hujjat havolasi — raqamni o'zgartirmaydi."""
    body = _text(text, gettext("Izoh matnini yozing."))
    where = _text(path, gettext("Izoh qaysi joyga ekanini koʻrsating."))
    return _event(
        review, user, ReviewEventKind.NOTE, path=where[:200], text=body, snapshot=review.snapshot
    )


def acceptor_codes(branch_id: Any) -> list[str]:
    parts = {part.strip() for part in str(_setting("governance.acceptors", branch_id)).split(",")}
    return ["org_owner"] + (["director"] if "director" in parts else [])


def _acceptors(review: ReportReview) -> list[Any]:
    from django.db.models import Q

    from apps.accounts.models import User

    leaders = User.objects.filter(is_active=True, role__code__in=acceptor_codes(review.branch_id))
    if review.branch_id:
        # Filial hisobotini o'sha filial rahbari va butun tashkilot rahbari.
        leaders = leaders.filter(Q(branch__isnull=True) | Q(branch_id=review.branch_id))
    return list(leaders)


def _accepted_by(review: ReportReview) -> set[Any]:
    last_submit = review.events.filter(kind=ReviewEventKind.SUBMIT).order_by("-created_at").first()
    accepts = review.events.filter(kind=ReviewEventKind.ACCEPT)
    if last_submit is not None:
        accepts = accepts.filter(created_at__gte=last_submit.created_at)
    return set(accepts.values_list("author_id", flat=True))


def accept(*, review: ReportReview, user: Any) -> ReportReview:
    """Har rahbar alohida; hammasi bosganda — "Qabul qilindi"."""
    from rest_framework.exceptions import PermissionDenied

    if getattr(user.role, "code", "") not in acceptor_codes(review.branch_id):
        raise PermissionDenied(gettext("Siz bu hisobotni qabul qiluvchilar roʻyxatida emassiz."))
    with transaction.atomic():
        review = _locked(review)
        if review.status == ReviewStatus.QUESTION or _open_questions(review).exists():
            raise BusinessRuleViolation(gettext("Javobsiz savol bor — avval javobni kuting."))
        if review.status not in (ReviewStatus.SUBMITTED, ReviewStatus.RESUBMITTED):
            raise BusinessRuleViolation(gettext("Qabul qilish uchun hisobot topshirilmagan."))
        if user.pk in _accepted_by(review):
            raise BusinessRuleViolation(gettext("Siz allaqachon qabul qilgansiz."))
        _event(review, user, ReviewEventKind.ACCEPT, snapshot=review.snapshot)
        required = {row.pk for row in _acceptors(review)}
        if required <= _accepted_by(review):
            review.status = ReviewStatus.ACCEPTED
            review.save(update_fields=["status", "updated_at"])
    if review.status == ReviewStatus.ACCEPTED:
        _tell_submitter(
            review, gettext("✅ Hisobot qabul qilindi: {period}.").format(period=_period(review))
        )
    return review


def send_back(*, review: ReportReview, user: Any, text: str) -> ReportReview:
    """Qaytarish — sabab majburiy."""
    reason = _text(text, gettext("Qaytarish sababini yozing."))
    with transaction.atomic():
        review = _locked(review)
        if review.status not in _OPEN:
            raise BusinessRuleViolation(gettext("Qaytarish uchun hisobot topshirilmagan."))
        _event(review, user, ReviewEventKind.RETURN, text=reason, snapshot=review.snapshot)
        review.status = ReviewStatus.RETURNED
        review.save(update_fields=["status", "updated_at"])
    _tell_submitter(
        review,
        gettext("↩️ Hisobot qaytarildi ({period}): {text}").format(
            period=_period(review), text=reason
        ),
    )
    return review


# --- Ko'rinish ---


def _opens(review: ReportReview) -> list[dict[str, Any]]:
    from apps.audit.models import AuditLog

    rows = AuditLog.objects.filter(
        action="view",
        entity_type="report_pack",
        changes__period=f"{review.period_year}-{review.period_month:02d}",
    )
    if review.branch_id:
        rows = rows.filter(changes__branch=str(review.branch_id))
    return [
        {
            "user": row.actor.full_name if row.actor is not None else row.actor_email,
            "at": row.created_at.isoformat(),
            "format": (row.changes or {}).get("format", "web"),
        }
        for row in rows.select_related("actor").order_by("-created_at")[:50]
    ]


def state(*, review: ReportReview, user: Any, live_checksum: str | None) -> dict[str, Any]:
    """Ekran uchun hammasi bitta javobda."""
    model = model_for(review.branch_id)
    due = deadline(review.period_year, review.period_month, review.branch_id)
    waiting = blockers(review)
    accepted = _accepted_by(review) if review.status != ReviewStatus.DRAFT else set()
    acceptors = _acceptors(review)
    codes = acceptor_codes(review.branch_id)
    snapshot = review.snapshot
    consolidation = model == "C" and review.branch_id is None and bool(_branches(review))
    events = review.events.select_related("author", "snapshot").order_by("created_at")
    return {
        "model": model,
        "consolidation": consolidation,
        "status": review.status,
        "ready": not waiting,
        "blockers": waiting,
        "deadline": due.isoformat(),
        "late": review.status in (ReviewStatus.DRAFT, ReviewStatus.RETURNED)
        and timezone.localdate() > due,
        "snapshot": {
            "version": snapshot.version,
            "checksum": snapshot.checksum,
            "created_at": snapshot.created_at.isoformat(),
        }
        if snapshot
        else None,
        "changed": bool(snapshot and live_checksum and snapshot.checksum != live_checksum),
        "submitted_by": review.submitted_by.full_name if review.submitted_by is not None else "",
        "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
        "acceptors": [row.full_name for row in acceptors],
        "accepted_by": [row.full_name for row in acceptors if row.pk in accepted],
        "can_accept": getattr(user.role, "code", "") in codes,
        "events": [
            {
                "id": str(event.id),
                "kind": event.kind,
                "path": event.path,
                "text": event.text,
                "parent": str(event.parent_id) if event.parent_id else None,
                "author": event.author.full_name,
                "version": event.snapshot.version if event.snapshot is not None else None,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "opens": _opens(review),
        "share_links": [
            {
                "id": str(link.id),
                "label": link.label,
                "version": link.snapshot.version,
                "expires_at": link.expires_at.isoformat(),
                "revoked": link.revoked_at is not None,
                "opened": link.opened_count,
                "last_opened_at": link.last_opened_at.isoformat() if link.last_opened_at else None,
            }
            for link in _links(review)
        ],
    }


def _links(review: ReportReview) -> Any:
    from apps.reports.models import ReportShareLink

    return ReportShareLink.objects.filter(
        snapshot__branch_id=review.branch_id,
        snapshot__period_year=review.period_year,
        snapshot__period_month=review.period_month,
    ).select_related("snapshot")
