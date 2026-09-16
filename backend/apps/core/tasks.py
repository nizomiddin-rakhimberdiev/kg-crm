"""
Fon vazifalari uchun umumiy asos.

Bitta joyda, chunki "qaysi xatoda qayta urinamiz?" degan savolga har bir
vazifa alohida javob bersa, javoblar ertami-kechmi ajralib qoladi — va
ajralish aynan eng kam ishlatiladigan vazifada bo'ladi.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.db import OperationalError

__all__ = ["reliable_task", "TRANSIENT_ERRORS"]

# Qayta urinishga ARZIYDIGAN xatolar — ya'ni "hozir bo'lmadi, keyin
# bo'lishi mumkin" turidagi nosozliklar.
#
# Biznes qoidasi buzilishi (`BusinessRuleViolation`) bu ro'yxatda ATAYLAB
# yo'q: "tarif belgilanmagan" xatosi besh marta qayta urinishdan
# to'g'rilanmaydi, faqat log'ni to'ldiradi va haqiqiy nosozlikni
# ko'mib yuboradi.
TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    OperationalError,  # baza uzilishi, deploy paytidagi qayta ulanish
    ConnectionError,  # Redis/broker (redis.ConnectionError shundan meros)
    TimeoutError,
)


def reliable_task(name: str, **options: Any) -> Any:
    """
    `@shared_task` ustiga qayta urinish siyosatini qo'shadi.

    Kechikish eksponensial va tasodifiy qo'shimcha bilan: baza bir
    daqiqaga yo'qolganda o'nlab vazifa bir vaqtda qayta urinsa, ular
    bazani endigina ko'tarilgan paytda yana yiqitardi. Tasodifiylik
    ularni vaqt bo'yicha yoyadi.

    `max_retries=5` va `retry_backoff_max=300` birgalikda taxminan
    10 daqiqalik urinish oynasini beradi — undan uzoq davom etgan
    nosozlik odam aralashuvini talab qiladi, kutishni emas.
    """
    return shared_task(
        name=name,
        autoretry_for=TRANSIENT_ERRORS,
        retry_backoff=True,
        retry_backoff_max=300,
        retry_jitter=True,
        max_retries=5,
        **options,
    )
