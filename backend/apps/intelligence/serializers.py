"""
Insight API shakli (docs/07 §11–§12).

API GAP qaytarmaydi — kalit + evidence qaytaradi. Matn frontend content
qatlamida tuziladi; wording o'zgarsa baza qayta hisoblanmaydi.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.intelligence.models import Insight


class InsightSerializer(serializers.ModelSerializer):
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Insight
        fields = [
            "id",
            "branch",
            "type",
            "severity",
            "status",
            "is_open",
            "subject_type",
            "subject_id",
            "evidence",
            "evidence_version",
            "recommendation_key",
            "deep_link",
            "generated_at",
            "refreshed_at",
            "seen_at",
            "resolved_at",
            "dismissed_at",
            "dismissed_until",
            "auto_resolved_at",
        ]
        read_only_fields = fields
