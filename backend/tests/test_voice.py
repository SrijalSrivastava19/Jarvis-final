import io
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_transcribe_rejects_empty_file(client):
    files = {"file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    response = await client.post("/api/voice/transcribe", files=files)
    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_audio"


@pytest.mark.asyncio
async def test_transcribe_success(client):
    fake_result = {"text": "turn on the lights", "language": "en", "duration_seconds": 1.5}
    with patch(
        "app.api.routes_voice.whisper_service.transcribe_bytes", return_value=fake_result
    ):
        files = {"file": ("clip.wav", io.BytesIO(b"fake-audio-bytes"), "audio/wav")}
        response = await client.post("/api/voice/transcribe", files=files)

    assert response.status_code == 200
    assert response.json()["text"] == "turn on the lights"


@pytest.mark.asyncio
async def test_speak_returns_audio_bytes(client):
    with patch(
        "app.api.routes_voice.piper_service.synthesize", return_value=b"RIFF....WAVEfmt "
    ):
        response = await client.post("/api/voice/speak", json={"text": "Hello there"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_speak_rejects_empty_text(client):
    response = await client.post("/api/voice/speak", json={"text": ""})
    assert response.status_code == 422


def test_wake_word_detects_exact_match():
    from app.services.wakeword_service import wakeword_service

    result = wakeword_service.detect_from_text("hey jarvis")
    assert result.detected is True
    assert result.confidence >= 0.95


def test_wake_word_rejects_unrelated_speech():
    from app.services.wakeword_service import wakeword_service

    result = wakeword_service.detect_from_text("what's the weather like today")
    assert result.detected is False
