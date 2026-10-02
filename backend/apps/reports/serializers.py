"""Eksport serializerlari (docs/04 §14.2)."""

from __future__ import annotations

from rest_framework import serializers

from apps.reports.models import ReportExport

__all__ = ["ReportExportSerializer", "ExportRequestSerializer"]


class ReportExportSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(
        source="requested_by.full_name", read_only=True, default=None
    )
    # Fayl yo'li EMAS, faqat bayroq: yuklab olish autentifikatsiya
    # talab qiladigan endpoint orqali ketadi (views.download).
    is_ready = serializers.SerializerMethodField()
    # Fayl NOMI esa kerak (PLAN 4.2): brauzerga saqlashda aynan shu
    # nom beriladi, va u so'rov tilida ("tushum_2026-10-02.xlsx").
    # Yo'l emas, faqat nom — fayl tizimining tuzilishi oshkor
    # bo'lmasligi kerak.
    filename = serializers.SerializerMethodField()

    class Meta:
        model = ReportExport
        fields = [
            "id",
            "report_type",
            "params",
            "status",
            "row_count",
            "error",
            "is_ready",
            "filename",
            "requested_by_name",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_ready(self, obj: ReportExport) -> bool:
        return obj.status == "ready" and bool(obj.file)

    def get_filename(self, obj: ReportExport) -> str:
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else ""


class ExportRequestSerializer(serializers.Serializer):
    params = serializers.DictField(required=False, default=dict)
