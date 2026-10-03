"""
Frozen product modules (owner's decision, 2026-10-03): contracts and the
kitchen are off unless `.env` switches them on, and the screens follow the
same switch through `/auth/me`.
"""

from __future__ import annotations

import pytest

from apps.core import features

pytestmark = pytest.mark.django_db


def test_both_are_off_by_default():
    """The base settings' defaults — what production gets without a .env line."""
    from pathlib import Path

    text = Path(__file__).resolve().parents[3].joinpath("config/settings/base.py").read_text()
    assert 'env.bool("FEATURE_CONTRACTS", default=False)' in text
    assert 'env.bool("FEATURE_KITCHEN", default=False)' in text


def test_the_switch_is_read_from_settings(settings):
    settings.FEATURE_KITCHEN = False
    settings.FEATURE_CONTRACTS = True
    assert features.enabled_features() == ["contracts"]


def test_the_frontend_gets_the_same_switch(tenant_a, settings):
    settings.FEATURE_KITCHEN = False
    settings.FEATURE_CONTRACTS = False
    data = tenant_a.client().get("/api/v1/auth/me").json()["data"]
    assert data["user"]["features"] == []
    settings.FEATURE_KITCHEN = True
    data = tenant_a.client().get("/api/v1/auth/me").json()["data"]
    assert data["user"]["features"] == ["kitchen"]
