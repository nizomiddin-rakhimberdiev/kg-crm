import pytest

from apps.memories.telegram import RecordingTelegramClient


@pytest.fixture(autouse=True)
def _telegram_recorder():
    RecordingTelegramClient.reset()
    yield RecordingTelegramClient
    RecordingTelegramClient.reset()
