"""
Contract templates and contracts (PLAN 6.5, design §5).

A template is the kindergarten's own text with placeholders
(`{{bola.fio}}`, `{{tarif.summa}}` …); it is tenant data, so it is never
translated (ADR-16). A contract is that text with the values filled in
AT THE MOMENT it was made — the same principle as an invoice: if the
tariff changes next month, the signed contract still says what was
agreed. Changing terms means a new contract, never an edit; the database
refuses an edit of the frozen columns (`trg_contract_frozen`).

Printing is the browser's (decision D1): plain text, no PDF library —
and plain text rather than HTML, so a value typed into a child's card can
never become markup on someone's print-out.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel, TenantScopedModel

__all__ = ["ContractTemplate", "Contract", "ContractStatus"]


class ContractTemplate(TenantScopedModel):
    name = models.CharField(max_length=150)
    language = models.CharField(max_length=2, default="uz")
    body = models.TextField()
    #: Grows on every change of `body`; a contract records the version it used.
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "contract_template"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                condition=models.Q(is_active=True),
                name="uq_contract_template_name",
            ),
            models.CheckConstraint(
                condition=models.Q(language__in=["uz", "ru", "en"]),
                name="ck_contract_template_language",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class ContractStatus(models.TextChoices):
    DRAFT = "draft", gettext_lazy("Qoralama")
    SIGNED = "signed", gettext_lazy("Imzolangan")
    TERMINATED = "terminated", gettext_lazy("Bekor qilingan")


class Contract(BranchScopedModel):
    number = models.CharField(max_length=30)
    child = models.ForeignKey("children.Child", on_delete=models.RESTRICT, related_name="contracts")
    guardian = models.ForeignKey(
        "children.Guardian",
        on_delete=models.RESTRICT,
        related_name="contracts",
        null=True,
        blank=True,
    )
    template = models.ForeignKey(
        ContractTemplate, on_delete=models.RESTRICT, related_name="contracts"
    )
    template_version = models.PositiveIntegerField()
    # Frozen at creation (DB trigger):
    values = models.JSONField(default=dict)
    rendered_text = models.TextField()

    status = models.CharField(
        max_length=12, choices=ContractStatus.choices, default=ContractStatus.DRAFT
    )
    signed_on = models.DateField(null=True, blank=True)
    terminated_on = models.DateField(null=True, blank=True)
    termination_reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="+", null=True, blank=True
    )

    class Meta:
        db_table = "contract"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "number"], name="uq_contract_number"),
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "signed", "terminated"]),
                name="ck_contract_status",
            ),
            # A signed contract has a signing date; a draft has none.
            models.CheckConstraint(
                condition=(
                    models.Q(status="draft", signed_on__isnull=True)
                    | models.Q(status="signed", signed_on__isnull=False)
                    | models.Q(status="terminated")
                ),
                name="ck_contract_signed_on",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="terminated", terminated_on__isnull=False)
                    | (~models.Q(status="terminated") & models.Q(terminated_on__isnull=True))
                ),
                name="ck_contract_terminated_on",
            ),
        ]
        indexes = [models.Index(fields=["child", "-created_at"], name="ix_contract_child")]

    def __str__(self) -> str:
        return self.number
