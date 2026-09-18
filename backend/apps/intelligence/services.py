"""
Radix Intelligence yozish qatlami (docs/07 §9).

Ikki narsa: (1) `reconcile` — kechasi shart bo'yicha bitta qatorni
yaratish/yangilash/yopish; (2) foydalanuvchi amallari — seen / resolve /
dismiss. Engine yopiq qatorni HECH QACHON qayta ochmaydi: tarix —
qatorlar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.exceptions import BusinessRuleViolation
from apps.intelligence import selectors
from apps.intelligence.models import OPEN_STATUSES, Insight, InsightStatus
from apps.intelligence.rules import InsightDraft, payment_delay
from apps.intelligence.thresholds import DISMISS_SUPPRESSION, PaymentDelayThresholds

__all__ = ["ReconcileResult", "reconcile", "generate_for_branch", "mark_seen", "resolve", "dismiss"]


@dataclass
class ReconcileResult:
    created: int = 0
    refreshed: int = 0
    auto_resolved: int = 0
    suppressed: int = 0
    episodes_ended: int = 0

    def as_dict(self) -> dict[str, int]:
        return self.__dict__.copy()


def _identity(draft_or_row: Any) -> tuple[str, str, Any]:
    return (draft_or_row.type, draft_or_row.subject_type, draft_or_row.subject_id)


@transaction.atomic
def reconcile(*, organization: Any, branch_id: Any, drafts: list[InsightDraft]) -> ReconcileResult:
    """
    Filial uchun bugungi draft'larni mavjud qatorlar bilan solishtiradi
    (docs/07 §9.3 jadvali).

    Har bir SHART (type, subject) uchun:
      bor  + ochiq qator bor          → refresh
      bor  + ochiq yo'q + suppressed  → hech narsa
      bor  + ochiq yo'q               → create
      yo'q + ochiq qator bor          → auto_resolved
      yo'q + suppressed               → epizod tugadi (dismissed_until = now)
    """
    now = timezone.now()
    result = ReconcileResult()

    open_rows = {
        _identity(row): row
        for row in Insight.objects.filter(branch_id=branch_id, status__in=OPEN_STATUSES)
    }
    suppressing = {
        _identity(row): row
        for row in Insight.objects.filter(
            branch_id=branch_id, status=InsightStatus.DISMISSED, dismissed_until__gt=now
        )
    }
    present = {_identity(draft): draft for draft in drafts}

    # --- Shart bor ---
    for key, draft in present.items():
        row = open_rows.pop(key, None)
        if row is not None:
            row.evidence = draft.evidence
            row.evidence_version = draft.evidence_version
            row.severity = draft.severity
            row.recommendation_key = draft.recommendation_key
            row.deep_link = draft.deep_link
            row.refreshed_at = now
            row.save(
                update_fields=[
                    "evidence",
                    "evidence_version",
                    "severity",
                    "recommendation_key",
                    "deep_link",
                    "refreshed_at",
                    "updated_at",
                ]
            )
            result.refreshed += 1
            continue

        if key in suppressing:
            result.suppressed += 1
            continue

        try:
            # Ichki savepoint: poyga (qo'lda ishga tushirish + kechki vazifa)
            # unique indeksga uriladi — yutqazgan tomon refresh qiladi,
            # yiqilmaydi (`create_lead` naqshi).
            with transaction.atomic():
                Insight.objects.create(
                    organization=organization,
                    branch_id=branch_id,
                    type=draft.type,
                    severity=draft.severity,
                    status=InsightStatus.NEW,
                    subject_type=draft.subject_type,
                    subject_id=draft.subject_id,
                    evidence=draft.evidence,
                    evidence_version=draft.evidence_version,
                    recommendation_key=draft.recommendation_key,
                    deep_link=draft.deep_link,
                    generated_at=now,
                )
            result.created += 1
        except IntegrityError:
            existing = Insight.objects.get(
                branch_id=branch_id,
                type=draft.type,
                subject_type=draft.subject_type,
                subject_id=draft.subject_id,
                status__in=OPEN_STATUSES,
            )
            existing.evidence = draft.evidence
            existing.severity = draft.severity
            existing.refreshed_at = now
            existing.save(update_fields=["evidence", "severity", "refreshed_at", "updated_at"])
            result.refreshed += 1

    # --- Shart yo'q ---
    for row in open_rows.values():  # present'da bo'lmaganlar qoldi
        row.status = InsightStatus.AUTO_RESOLVED
        row.auto_resolved_at = now
        row.save(update_fields=["status", "auto_resolved_at", "updated_at"])
        result.auto_resolved += 1

    for key, row in suppressing.items():
        if key not in present:
            # Shart yo'qoldi — epizod tugadi. Qaytsa, yangi qator bo'ladi.
            row.dismissed_until = now
            row.save(update_fields=["dismissed_until", "updated_at"])
            result.episodes_ended += 1

    return result


def generate_for_branch(
    *, organization: Any, branch_id: Any, as_of: date | None = None
) -> ReconcileResult:
    """Bitta filial uchun barcha V1 qoidalarini yuritib, natijani reconcile qiladi."""
    today = as_of or timezone.localdate()
    thresholds = PaymentDelayThresholds()

    drafts: list[InsightDraft] = []
    draft = payment_delay(
        branch_id=branch_id,
        as_of=today,
        active_children=selectors.active_children(
            organization_id=organization.id, branch_id=branch_id
        ),
        overdue=selectors.overdue_children(
            branch_id=branch_id, as_of=today, overdue_days=thresholds.overdue_days
        ),
        thresholds=thresholds,
    )
    if draft is not None:
        drafts.append(draft)

    return reconcile(organization=organization, branch_id=branch_id, drafts=drafts)


# --- Foydalanuvchi amallari ---


def mark_seen(*, insight: Insight) -> Insight:
    """Birinchi ochilishda bir marta; keyin idempotent."""
    if insight.status == InsightStatus.NEW:
        insight.status = InsightStatus.SEEN
        insight.seen_at = timezone.now()
        insight.save(update_fields=["status", "seen_at", "updated_at"])
    return insight


def _require_open(insight: Insight) -> None:
    if not insight.is_open:
        raise BusinessRuleViolation("Bu signal allaqachon yopilgan.")


@transaction.atomic
def resolve(*, insight: Insight, actor: Any, request: Any = None) -> Insight:
    _require_open(insight)
    now = timezone.now()
    insight.status = InsightStatus.RESOLVED
    insight.resolved_at = now
    insight.acted_by = actor
    if insight.seen_at is None:
        insight.seen_at = now
    insight.save(update_fields=["status", "resolved_at", "seen_at", "acted_by", "updated_at"])
    audit.record(
        action="insight.resolve",
        request=request,
        actor=actor,
        organization=insight.organization,
        entity_type="insight",
        entity_id=insight.id,
        changes={"type": insight.type, "severity": insight.severity},
    )
    return insight


@transaction.atomic
def dismiss(*, insight: Insight, actor: Any, request: Any = None) -> Insight:
    """`dismissed` = "hozir emas", "hech qachon" emas: 7 kun jim, keyin yana."""
    _require_open(insight)
    now = timezone.now()
    insight.status = InsightStatus.DISMISSED
    insight.dismissed_at = now
    insight.dismissed_until = now + DISMISS_SUPPRESSION
    insight.acted_by = actor
    if insight.seen_at is None:
        insight.seen_at = now
    insight.save(
        update_fields=[
            "status",
            "dismissed_at",
            "dismissed_until",
            "seen_at",
            "acted_by",
            "updated_at",
        ]
    )
    audit.record(
        action="insight.dismiss",
        request=request,
        actor=actor,
        organization=insight.organization,
        entity_type="insight",
        entity_id=insight.id,
        changes={"type": insight.type, "until": insight.dismissed_until.isoformat()},
    )
    return insight
