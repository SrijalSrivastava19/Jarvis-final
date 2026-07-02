"""
Wake word ("Hey Jarvis") detection service.

Phase 1 implementation: the client streams short rolling audio chunks to
the backend, each chunk is transcribed via Whisper, and the resulting text
is fuzzy-matched against the configured wake phrase. This is simple and
works fully offline with the existing Whisper pipeline — no extra model to
ship in Phase 1.

Known limitation (documented, not hidden): transcribing every audio chunk
is heavier than a dedicated wake-word model. In a later phase this should
be replaced with a lightweight always-on detector (e.g. openWakeWord or
Picovoice Porcupine) running client-side, which only calls the backend once
the wake word actually fires. The interface below (`detect`) is designed so
that swap doesn't change any call sites.
"""
from difflib import SequenceMatcher

from app.config import settings
from app.logger import get_logger
from app.models.schemas import WakeWordDetectionResponse
from app.services.whisper_service import whisper_service

logger = get_logger(__name__)


class WakeWordService:
    def __init__(self) -> None:
        self.wake_phrase = settings.wake_word.lower().strip()
        self.threshold = settings.wake_word_similarity_threshold

    def _similarity(self, candidate: str) -> float:
        return SequenceMatcher(None, self.wake_phrase, candidate.lower().strip()).ratio()

    def detect_from_text(self, text: str) -> WakeWordDetectionResponse:
        score = self._similarity(text)
        detected = score >= self.threshold
        if detected:
            logger.info("Wake word detected (score=%.2f): '%s'", score, text)
        return WakeWordDetectionResponse(
            detected=detected, confidence=round(score, 3), matched_phrase=text if detected else None
        )

    def detect_from_audio(self, audio_bytes: bytes) -> WakeWordDetectionResponse:
        result = whisper_service.transcribe_bytes(audio_bytes, filename_hint="wake.wav")
        return self.detect_from_text(result["text"])


wakeword_service = WakeWordService()
