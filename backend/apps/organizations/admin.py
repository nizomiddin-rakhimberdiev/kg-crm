from django.contrib import admin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "contact_email", "is_active", "created_at")
    list_filter = ("is_active", "country")
    search_fields = ("name", "slug", "legal_name", "tax_id", "contact_email")
    readonly_fields = ("id", "created_at", "updated_at")
