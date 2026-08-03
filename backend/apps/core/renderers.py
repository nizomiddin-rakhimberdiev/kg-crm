"""
Yagona javob konverti (docs/04 §2).

Har bir muvaffaqiyatli javob bir xil shaklda chiqadi, shunda frontend'da
bitta handler yetarli bo'ladi:

    {"success": true, "data": ..., "meta": null, "message": null}
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rest_framework.renderers import JSONRenderer

__all__ = ["EnvelopeJSONRenderer"]


class EnvelopeJSONRenderer(JSONRenderer):
    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: Mapping[str, Any] | None = None,
    ) -> bytes:
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")

        # Xatolar `envelope_exception_handler` da to'liq shakllantirilgan —
        # ikkinchi marta o'ramaymiz.
        if response is not None and response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)

        # Paginator allaqachon konvert yasagan bo'lsa, o'zgartirmaymiz.
        if isinstance(data, dict) and "success" in data:
            return super().render(data, accepted_media_type, renderer_context)

        envelope = {
            "success": True,
            "data": data,
            "meta": None,
            "message": None,
        }
        return super().render(envelope, accepted_media_type, renderer_context)
