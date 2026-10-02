"""Tashkilot profili — mijozning o'z ma'lumotlari (docs/04 §16)."""

from __future__ import annotations

from rest_framework import serializers

from apps.organizations.models import Organization

__all__ = ["OrganizationSerializer"]


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Tashkilotning o'zi tahrirlaydigan maydonlar.

    `slug` tahrirlanmaydi: u tashkilotning global identifikatori va bir
    nechta joyda (vendor konsoli, havolalar) ishlatiladi — nomni almashtirish
    kerak bo'lsa `name` o'zgaradi, `slug` esa qotib qoladi.

    `onboarded_at` ham faqat o'qish uchun: sinov muddati shu paytdan
    hisoblanadi (docs/01 §4.4), ya'ni uni tahrirlash to'lov shartlarini
    o'zgartirish bo'lardi.
    """

    # Logotip URL'i — fayl yo'li emas (PLAN 4.6). Yuklash alohida
    # endpoint orqali (`PUT /organization/logo`), chunki u
    # `multipart/form-data` talab qiladi va qolgan maydonlar JSON.
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "logo_url",
            "legal_name",
            "tax_id",
            "contact_email",
            "contact_phone",
            "country",
            "locale",
            "onboarded_at",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "logo_url", "onboarded_at", "created_at"]

    def get_logo_url(self, obj: Organization) -> str | None:
        if not obj.logo:
            return None
        request = self.context.get("request")
        url = obj.logo.url
        return request.build_absolute_uri(url) if request else url
