"""
Eskiz.uz provayderi (PLAN 3.1, Q8).

Tarmoqqa CHIQILMAYDI: `requests.post` almashtiriladi. Test haqiqiy
shlyuzni emas, bizning xatti-harakatimizni tekshiradi — token keshi,
`401` da bir marta yangilash va xato matnining saqlanishi.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.notifications.providers import EskizProvider, is_test_mode

pytestmark = pytest.mark.big_update


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.delete(EskizProvider.TOKEN_CACHE_KEY)
    yield
    cache.delete(EskizProvider.TOKEN_CACHE_KEY)


@pytest.fixture
def configured(settings):
    settings.ESKIZ_EMAIL = "bogcha@example.uz"
    settings.ESKIZ_PASSWORD = "secret"  # noqa: S105 — test qiymati
    settings.ESKIZ_FROM = "4546"
    return settings


def _response(status_code: int, payload: dict | None = None, text: str = "") -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    response.text = text
    response.raise_for_status = Mock()
    return response


class TestConfiguration:
    @override_settings(ESKIZ_EMAIL="", ESKIZ_PASSWORD="", ESKIZ_FROM="")
    def test_without_credentials_the_provider_refuses_to_start(self):
        """
        Yarim sozlangan provayder eng yomon holat.

        U xabarni qabul qiladi, yetkazmaydi, va jurnalda "yuborildi"
        deb turadi. Shuning uchun u umuman ishga tushmasligi kerak.
        """
        with pytest.raises(ImproperlyConfigured):
            EskizProvider()

    def test_test_mode_banner_is_off_only_for_a_live_provider(self, configured):
        with override_settings(NOTIFICATION_PROVIDER="console"):
            assert is_test_mode() is True
        with override_settings(NOTIFICATION_PROVIDER="eskiz"):
            assert is_test_mode() is False


class TestSending:
    def test_token_is_fetched_once_and_reused(self, configured):
        login = _response(200, {"data": {"token": "jwt-1"}})
        send = _response(200, {"status": "waiting", "id": "msg-1"})

        with patch("requests.post", side_effect=[login, send, send]) as post:
            provider = EskizProvider()
            first = provider.send(address="+998901234567", body="Salom")
            second = provider.send(address="+998901234567", body="Salom")

        assert first.success and first.provider_message_id == "msg-1"
        assert second.success
        # Uchta chaqiruv: bitta login + ikkita yuborish. Har yuborishda
        # qayta login shlyuzni ortiqcha yuklardi.
        assert post.call_count == 3

    def test_the_country_code_plus_is_stripped(self, configured):
        login = _response(200, {"data": {"token": "jwt-1"}})
        send = _response(200, {"status": "waiting", "id": "msg-1"})
        with patch("requests.post", side_effect=[login, send]) as post:
            EskizProvider().send(address="+998901234567", body="Salom")
        assert post.call_args_list[-1].kwargs["data"]["mobile_phone"] == "998901234567"

    def test_an_expired_token_is_refreshed_once(self, configured):
        cache.set(EskizProvider.TOKEN_CACHE_KEY, "eski-token", 60)
        expired = _response(401, {}, text="token expired")
        login = _response(200, {"data": {"token": "jwt-2"}})
        send = _response(200, {"status": "waiting", "id": "msg-2"})

        with patch("requests.post", side_effect=[expired, login, send]):
            result = EskizProvider().send(address="+998901234567", body="Salom")

        assert result.success
        assert cache.get(EskizProvider.TOKEN_CACHE_KEY) == "jwt-2"

    def test_an_error_keeps_the_reason_not_just_a_flag(self, configured):
        login = _response(200, {"data": {"token": "jwt-1"}})
        refused = _response(400, {}, text="invalid sender name")

        with patch("requests.post", side_effect=[login, refused]):
            result = EskizProvider().send(address="+998901234567", body="Salom")

        assert result.success is False
        # "SMS kelmadi" shikoyatiga javob jurnalda bo'lishi kerak.
        assert "invalid sender name" in result.error

    def test_a_network_failure_is_not_a_crash(self, configured):
        import requests

        login = _response(200, {"data": {"token": "jwt-1"}})
        with patch("requests.post", side_effect=[login, requests.ConnectionError("tarmoq yo'q")]):
            result = EskizProvider().send(address="+998901234567", body="Salom")

        assert result.success is False
        assert "Tarmoq" in result.error

    def test_a_live_send_is_never_marked_test_mode(self, configured):
        login = _response(200, {"data": {"token": "jwt-1"}})
        send = _response(200, {"status": "waiting", "id": "msg-9"})
        with patch("requests.post", side_effect=[login, send]):
            result = EskizProvider().send(address="+998901234567", body="Salom")
        assert result.test_mode is False
