"""
Audit jurnali — kim, nima, qachon (docs/03 §19, P7).

Faqat INSERT: yozuvlar hech qachon o'zgartirilmaydi va o'chirilmaydi.
Sprint 1 da auth va foydalanuvchi/rol o'zgarishlari yoziladi; keyingi
sprintlarda pul va operatsion mutatsiyalar qo'shiladi.
"""

from __future__ import annotations

import uuid

from django.db import models

__all__ = ["AuditLog"]


class AuditLog(models.Model):
    """
    Append-only: `updated_at`/`is_active` yo'q — bu o'zgarmas fakt (D3).

    `TenantScopedModel` dan meros olmaydi, chunki:
    (a) u `SoftDeleteModel` — bu jadval uchun noto'g'ri,
    (b) `organization` platforma harakatlarida `NULL` bo'lishi mumkin.
    """

    ACTION_CHOICES = [
        ("login", "Kirish"),
        ("login_failed", "Muvaffaqiyatsiz kirish"),
        ("logout", "Chiqish"),
        ("signup", "Ro'yxatdan o'tish"),
        ("password_change", "Parol o'zgardi"),
        ("create", "Yaratildi"),
        ("update", "Yangilandi"),
        ("delete", "O'chirildi"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.RESTRICT,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,  # yozuv qoladi, aktyor havolasi unutiladi
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    actor_email = models.EmailField(blank=True)

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.UUIDField(null=True, blank=True)

    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.entity_type}"
