"""
Read-side entry points of `children` for other modules (invariant 1).

Other apps' views never import `Child` or `Guardian`; they ask here. The
querysets are the tenant-scoped defaults — the caller adds branch and row
scope (`children/scope.py`) exactly as for its own data.
"""

from __future__ import annotations

from typing import Any

from apps.children.models import Child, Guardian

__all__ = ["children_queryset", "guardian_queryset"]


def children_queryset() -> Any:
    """Children of the current organization that are not archived."""
    return Child.objects.filter(archived_at__isnull=True)


def guardian_queryset() -> Any:
    return Guardian.objects.filter(is_active=True)
