from __future__ import annotations

from rest_framework import serializers

from apps.contracts.models import Contract, ContractTemplate


class ContractTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractTemplate
        fields = ["id", "name", "language", "body", "version", "is_active", "updated_at"]
        read_only_fields = ["id", "version", "is_active", "updated_at"]

    def validate_language(self, value: str) -> str:
        if value not in ("uz", "ru", "en"):
            raise serializers.ValidationError("uz | ru | en")
        return value


class ContractSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    guardian_name = serializers.SerializerMethodField()
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id",
            "number",
            "child",
            "child_name",
            "guardian",
            "guardian_name",
            "template",
            "template_name",
            "template_version",
            "rendered_text",
            "status",
            "signed_on",
            "terminated_on",
            "termination_reason",
            "created_at",
        ]
        read_only_fields = fields

    def get_guardian_name(self, obj: Contract) -> str:
        return obj.guardian.full_name if obj.guardian else ""


class CreateContractSerializer(serializers.Serializer):
    child_id = serializers.UUIDField()
    template_id = serializers.UUIDField()
    guardian_id = serializers.UUIDField(required=False, allow_null=True)


class SignSerializer(serializers.Serializer):
    signed_on = serializers.DateField()


class TerminateSerializer(serializers.Serializer):
    terminated_on = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
