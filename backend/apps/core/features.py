"""
Product modules that are built but switched off (owner's decision, 2026-10-03).

Contracts (PLAN 6.5) and the kitchen (PLAN 6.6) are finished and tested,
but no customer uses them yet, so they are FROZEN rather than removed:
their tables exist (migrations always run — a switch never changes the
schema), but their endpoints are not registered and their screens are not
shown. Switching one on is one `.env` line, no deploy of code:

    FEATURE_CONTRACTS=True
    FEATURE_KITCHEN=True

The frontend reads the same switches from `/auth/me` (`user.features`), so
the two sides can never disagree the way two separate flags would.
"""

from __future__ import annotations

from typing import Final

from django.conf import settings

__all__ = ["CONTRACTS", "KITCHEN", "enabled", "enabled_features"]

CONTRACTS: Final[str] = "contracts"
KITCHEN: Final[str] = "kitchen"

_SETTINGS: Final[dict[str, str]] = {
    CONTRACTS: "FEATURE_CONTRACTS",
    KITCHEN: "FEATURE_KITCHEN",
}


def enabled(feature: str) -> bool:
    return bool(getattr(settings, _SETTINGS[feature], False))


def enabled_features() -> list[str]:
    return sorted(feature for feature in _SETTINGS if enabled(feature))
