"""Sahifalash — konvert ichida `meta.pagination` sifatida (docs/04 §2–3)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

__all__ = ["EnvelopePageNumberPagination"]


class EnvelopePageNumberPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100  # docs/04 §3: cheklanmagan ro'yxat endpointi bo'lmaydi

    def get_paginated_response(self, data: Sequence[Any]) -> Response:
        # DRF `paginate_queryset()` dan keyin ikkalasi ham o'rnatilgan bo'ladi;
        # assert shartnomani aniq qiladi va stub'lardagi Optional'ni yopadi.
        assert self.request is not None and self.page is not None

        page_size = self.get_page_size(self.request) or self.page_size
        count = self.page.paginator.count
        return Response(
            {
                "success": True,
                "data": data,
                "meta": {
                    "pagination": {
                        "count": count,
                        "page": self.page.number,
                        "page_size": page_size,
                        "total_pages": math.ceil(count / page_size) if page_size else 0,
                        "next": self.get_next_link(),
                        "previous": self.get_previous_link(),
                    }
                },
                "message": None,
            }
        )
