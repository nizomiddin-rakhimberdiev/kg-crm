"""
Insight — Radix Intelligence'ning saqlanadigan fakti (docs/07 §9–§10).

Bitta qator = bitta HOLAT (shart), bitta kun emas. Shart davom etar ekan
qator yangilanadi; yo'qolsa `auto_resolved` bilan yopiladi; qaytsa —
yangi qator. Tarix — qatorlar, holat almashinuvi emas.

`evidence` — generatsiya paytidagi raqamlar va id'lar SNAPSHOT'i (ADR-11
intizomi). Ism, telefon — YO'Q: yorliqlar render paytida id bo'yicha,
RLS ostida olinadi (docs/07 §6).
"""

from __future__ import annotations

from django.db import models

from apps.core.models import BranchScopedModel


class InsightType(models.TextChoices):
    PAYMENT_DELAY = "payment_delay", "To'lov kechikishi"
    ATTENDANCE_DROP = "attendance_drop", "Davomat pasayishi"


class InsightSeverity(models.TextChoices):
    WARNING = "warning", "Ogohlantirish"
    CRITICAL = "critical", "Jiddiy"


class InsightStatus(models.TextChoices):
    NEW = "new", "Yangi"
    SEEN = "seen", "Ko'rilgan"
    RESOLVED = "resolved", "Hal qilingan"
    DISMISSED = "dismissed", "Rad etilgan"
    AUTO_RESOLVED = "auto_resolved", "O'zi hal bo'lgan"


class SubjectType(models.TextChoices):
    BRANCH = "branch", "Filial"
    GROUP = "group", "Guruh"


OPEN_STATUSES = (InsightStatus.NEW, InsightStatus.SEEN)


class Insight(BranchScopedModel):
    type = models.CharField(max_length=40, choices=InsightType.choices)
    severity = models.CharField(max_length=10, choices=InsightSeverity.choices)
    status = models.CharField(
        max_length=14, choices=InsightStatus.choices, default=InsightStatus.NEW
    )

    subject_type = models.CharField(max_length=20, choices=SubjectType.choices)
    # Filial darajasida `= branch_id`, guruh darajasida `= group_id`. Hech
    # qachon NULL: `NULLS NOT DISTINCT` PG15+ da, lokal va CI esa PG14 —
    # Django u yerda constraint'ni jimgina tashlab ketardi (docs/07 §10).
    subject_id = models.UUIDField()

    evidence = models.JSONField()
    evidence_version = models.PositiveSmallIntegerField(default=1)
    recommendation_key = models.CharField(max_length=60)
    deep_link = models.CharField(max_length=200)

    generated_at = models.DateTimeField()
    refreshed_at = models.DateTimeField(null=True, blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    dismissed_until = models.DateTimeField(null=True, blank=True)
    auto_resolved_at = models.DateTimeField(null=True, blank=True)
    acted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "insight"
        ordering = ["-severity", "-generated_at"]
        constraints = [
            # Bir shart uchun BITTA ochiq qator — bazada, ilovada emas.
            models.UniqueConstraint(
                fields=["branch", "type", "subject_type", "subject_id"],
                condition=models.Q(status__in=("new", "seen")),
                name="uq_insight_open_condition",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[c for c, _ in InsightStatus.choices]),
                name="ck_insight_status",
            ),
            models.CheckConstraint(
                condition=models.Q(severity__in=[c for c, _ in InsightSeverity.choices]),
                name="ck_insight_severity",
            ),
            # Filial darajasidagi insight'ning subject'i — o'sha filial.
            models.CheckConstraint(
                condition=models.Q(subject_type="branch", subject_id=models.F("branch_id"))
                | models.Q(subject_type="group"),
                name="ck_insight_branch_subject_is_branch",
            ),
            # Suppression oynasi faqat rad etilgan qatorda bo'ladi.
            models.CheckConstraint(
                condition=models.Q(dismissed_until__isnull=True) | models.Q(status="dismissed"),
                name="ck_insight_dismissed_until_only_when_dismissed",
            ),
            # Yopiq qatorda aynan bitta yopilish vaqti; ochiq qatorda hech biri.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=("new", "seen"),
                        resolved_at__isnull=True,
                        dismissed_at__isnull=True,
                        auto_resolved_at__isnull=True,
                    )
                    | models.Q(
                        status="resolved",
                        resolved_at__isnull=False,
                        dismissed_at__isnull=True,
                        auto_resolved_at__isnull=True,
                    )
                    | models.Q(
                        status="dismissed",
                        dismissed_at__isnull=False,
                        resolved_at__isnull=True,
                        auto_resolved_at__isnull=True,
                    )
                    | models.Q(
                        status="auto_resolved",
                        auto_resolved_at__isnull=False,
                        resolved_at__isnull=True,
                        dismissed_at__isnull=True,
                    )
                ),
                name="ck_insight_exactly_one_closing_timestamp",
            ),
        ]
        indexes = [
            # Dashboard so'rovi: ochiq insight'lar.
            models.Index(
                fields=["organization", "branch", "severity"],
                condition=models.Q(status__in=("new", "seen")),
                name="ix_insight_open",
            ),
            # Shart tarixi.
            models.Index(fields=["branch", "type", "-generated_at"], name="ix_insight_history"),
            # Suppression qidiruvi.
            models.Index(
                fields=["branch", "type", "subject_type", "subject_id", "dismissed_until"],
                condition=models.Q(status="dismissed"),
                name="ix_insight_suppression",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.type} · {self.status} · {self.branch_id}"

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES
