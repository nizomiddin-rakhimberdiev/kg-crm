"""
Test uchun konkret tenant-scoped model.

`TenantScopedModel` abstrakt bo'lgani uchun uni bevosita sinab bo'lmaydi.
Bu model ATAYLAB `models.py` da emas, `tests/` ichida: `makemigrations` uni
ko'rmaydi va u production sxemasiga hech qachon chiqmaydi. Jadval
`conftest.py` dagi `django_db_setup` fixture'ida yaratiladi.
"""

from django.db import models

from apps.core.models import TenantScopedModel


class TenantThing(TenantScopedModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "core"
        db_table = "test_tenant_thing"
