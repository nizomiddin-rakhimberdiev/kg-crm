"""
API kompozitsiya ildizi — barcha modul router'lari shu yerda yig'iladi.

Har bir yangi app o'z `urls.py` sini shu yerga ulaydi (docs/02 §5).
Sprint 0 da hali biznes moduli yo'q — ro'yxat ataylab bo'sh.
"""

from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)

# Sprint 1+ da: router.registry.extend(children_router.registry) va h.k.

__all__ = ["router"]
