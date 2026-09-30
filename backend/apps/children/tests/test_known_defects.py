"""
Ma'lumot to'g'riligi kamchiliklari — 2026-09-30 auditi (PLAN 2.2, 2.4; Q5, Q7).

Auditda:
  * vasiy telefoni "12345" qabul qilindi, tizim hisobiniki "45";
  * bolani "Chiqib ketgan" holatiga o'tkazganda sana ham, sabab ham
    so'ralmaydi — keyin "qachondan buyon?" degan savolga javob yo'q.

Telefon `CharField(max_length=20)` — formati umuman tekshirilmaydi.
Noto'g'ri raqam SMS'ni jimgina yo'qotadi: bildirishnoma "yuborildi"
bo'lib turadi, ota-ona esa hech narsa olmaydi.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


class TestGuardianPhone:
    """Q7: +998 va 9 raqam (E.164); kiritishda niqob, saqlashda normalizatsiya."""

    @pytest.mark.xfail(strict=True, reason="PLAN 2.4 / Q7: telefon formati tekshirilmaydi")
    @pytest.mark.parametrize("phone", ["12345", "45", "+1 555 0100", "998901234567890"])
    def test_invalid_phone_is_rejected(self, tenant_a, phone):
        response = tenant_a.client().post(
            reverse("v1:guardian-list"),
            {"first_name": "Vasiy", "last_name": "Sinov", "phone": phone},
            format="json",
        )
        assert response.status_code == 400, f"{phone!r} qabul qilindi"
        assert "phone" in str(response.data).lower()

    @pytest.mark.xfail(strict=True, reason="PLAN 2.4 / Q7: normalizatsiya yo'q")
    @pytest.mark.parametrize(
        "typed",
        ["+998 90 123 45 67", "998901234567", "90 123 45 67", "(90) 123-45-67"],
    )
    def test_phone_is_normalised_to_e164(self, tenant_a, typed):
        """Odam qanday yozsa ham, bazada bitta shakl bo'lishi kerak."""
        response = tenant_a.client().post(
            reverse("v1:guardian-list"),
            {"first_name": "Vasiy", "last_name": "Sinov", "phone": typed},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["phone"] == "+998901234567"


class TestChildStatusChange:
    """Q5: holat o'zgarganda sana va sabab so'raladi; shu sanadan keyin faktura yozilmaydi."""

    @pytest.mark.xfail(
        strict=True, reason="PLAN 2.1 / Q5: holat sanasi va sababi uchun maydon yo'q"
    )
    @pytest.mark.parametrize("field", ["status_changed_on", "status_reason"])
    def test_status_change_is_recorded_in_the_schema(self, field):
        """
        Tekshiruv SXEMA ustidan, obyekt ustidan emas.

        Django modelga ixtiyoriy atributni o'zlashtirishga ruxsat beradi:
        `child.status_changed_on = ...` xatosiz ishlaydi, `save()` uni
        jimgina tashlab yuboradi va xotiradagi qiymat qolaveradi. Ya'ni
        obyektni sinagan test maydon yo'qligini KO'RMAS edi.
        """
        from django.core.exceptions import FieldDoesNotExist

        from apps.children.models import Child

        try:
            Child._meta.get_field(field)
        except FieldDoesNotExist:
            pytest.fail(f"Child.{field} maydoni yo'q")

    @pytest.mark.xfail(
        strict=True, reason="PLAN 2.2 / Q6: arxivlash tushunchasi yo'q — faqat is_active"
    )
    def test_archiving_is_distinct_from_deleting(self):
        """
        Q6: bolalar qattiq o'chirilmaydi — faqat arxiv.

        Hozir yagona vosita `is_active=False`, va u "o'chirilgan" degani
        ham, "arxivlangan" degani ham bo'lishi mumkin — ikkisini ajratib
        bo'lmaydi, ya'ni "kim, qachon, nega arxivladi?" javobsiz qoladi.
        """
        from django.core.exceptions import FieldDoesNotExist

        from apps.children.models import Child

        try:
            Child._meta.get_field("archived_at")
        except FieldDoesNotExist:
            pytest.fail("Child.archived_at maydoni yo'q")


class TestDateOfBirth:
    @pytest.mark.xfail(strict=True, reason="PLAN 2.4: yosh oralig'i (0–8) tekshirilmaydi")
    def test_age_out_of_range_is_rejected(self, tenant_a):
        """Kelajakdagi sana allaqachon rad etiladi; 30 yoshli "bola" esa yo'q."""
        response = tenant_a.client().post(
            reverse("v1:child-list"),
            {
                "first_name": "Katta",
                "last_name": "Odam",
                "date_of_birth": (date.today() - timedelta(days=365 * 30)).isoformat(),
                "gender": "male",
            },
            format="json",
        )
        assert response.status_code == 400
