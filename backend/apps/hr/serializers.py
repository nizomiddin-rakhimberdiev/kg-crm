"""HR serializerlari (docs/04 §11.1)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.serializer_fields import PhoneField
from apps.hr.models import Employee, Position

__all__ = ["PositionSerializer", "EmployeeSerializer", "EmployeeWriteSerializer"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "title", "department", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    position_title = serializers.CharField(source="position.title", read_only=True, default=None)
    # Tizim hisobi (PLAN 2.8) — usiz "men qaysi guruhning
    # tarbiyachisiman?" degan savolga javob yo'q.
    user_email = serializers.EmailField(source="user.email", read_only=True, default=None)
    user_name = serializers.CharField(source="user.full_name", read_only=True, default=None)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "position",
            "position_title",
            "employment_status",
            "hire_date",
            "termination_date",
            "base_salary",
            "official_salary",
            "work_mode",
            "work_days",
            "hours_per_day",
            "hourly_rate",
            "user",
            "user_email",
            "user_name",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class EmployeeWriteSerializer(serializers.ModelSerializer):
    # Xodim telefoni ham normalizatsiya qilinadi (Q7): oylik to'langanda
    # va smena almashinuvida unga SMS ketadi.
    phone = PhoneField(required=False, allow_blank=True)
    position_id = TenantPrimaryKeyRelatedField(
        model=Position, source="position", required=False, allow_null=True
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "position_id",
            "employment_status",
            "hire_date",
            "termination_date",
            "base_salary",
            "official_salary",
            # Ish grafigi (PLAN 9.1) — oylik hisoblashning maxraji.
            "work_mode",
            "work_days",
            "hours_per_day",
            "hourly_rate",
        ]
        read_only_fields = ["id"]
        # `user_id` ATAYLAB yo'q (PLAN 9.1b): hisob xodimga emas, xodim
        # hisobga bog'lanadi — ya'ni bog'lash foydalanuvchi yaratish
        # formasida. Ish tartibi ham shunday: avval odam ishga olinadi,
        # kirish huquqi esa keyin va hammaga ham emas.

    def validate_work_days(self, value: str) -> str:
        """`"1,3,5"` — ISO kunlar, takrorsiz va tartibda. Boʻsh = filial kalendari."""
        if not value.strip():
            return ""
        days = []
        for part in value.split(","):
            part = part.strip()
            if not part.isdigit() or not 1 <= int(part) <= 7:
                raise serializers.ValidationError(
                    gettext("Ish kunlari 1–7 (dushanba–yakshanba) oraligʻida boʻlishi kerak.")
                )
            days.append(int(part))
        return ",".join(str(day) for day in sorted(set(days)))

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Soatbay xodimda soat narxi va kunlik soat boʻlishi shart."""
        mode = attrs.get("work_mode", getattr(self.instance, "work_mode", "monthly"))
        rate = attrs.get("hourly_rate", getattr(self.instance, "hourly_rate", 0) or 0)
        hours = attrs.get("hours_per_day", getattr(self.instance, "hours_per_day", 0) or 0)
        if mode == "hourly" and (rate <= 0 or hours <= 0):
            raise serializers.ValidationError(
                {
                    "hourly_rate": gettext(
                        "Soatbay xodim uchun soat narxi va kunlik soat koʻrsatilishi kerak."
                    )
                }
            )
        return attrs
