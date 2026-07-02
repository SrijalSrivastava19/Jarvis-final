"""
Whisper speech-to-text service, backed by faster-whisper (CTranslate2).

faster-whisper is used instead of openai-whisper because it is significantly
faster on CPU (4x+) and has a lower memory footprint, which matters for a
desktop assistant that should not hog resources while idle. The model is
loaded once at import time and reused across requests (loading a Whisper
model is expensive — doing it per-request would make every transcription
take seconds longer).
"""
import tempfile
from pathlib import Path

from app.config import settings
from app.core.exceptions import InvalidAudioError, TranscriptionError
from app.logger import get_logger

logger = get_logger(__name__)

_model = None  # lazy-loaded singleton


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        logger.info(
            "Loading Whisper model '%s' (device=%s, compute_type=%s)...",
            settings.whisper_model_size,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("Whisper model loaded.")
    return _model


class WhisperService:
    def is_loaded(self) -> bool:
        return _model is not None

    def transcribe_bytes(self, audio_bytes: bytes, filename_hint: str = "audio.wav") -> dict:
        """
        Transcribe raw audio bytes (wav/mp3/webm/ogg — anything ffmpeg supports)
        into text. Audio is written to a temp file because faster-whisper
        (via ffmpeg) expects a file path or file-like object on disk.
        """
        if not audio_bytes:
            raise InvalidAudioError("No audio data received.")

        suffix = Path(filename_hint).suffix or ".wav"
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()

                model = _get_model()
                segments, info = model.transcribe(tmp.name, beam_size=5, vad_filter=True)
                text = " ".join(segment.text.strip() for segment in segments).strip()

        except Exception as exc:  # noqa: BLE001 - we re-raise as a typed error
            logger.exception("Transcription failed")
            raise TranscriptionError(f"Failed to transcribe audio: {exc}") from exc

        if not text:
            raise TranscriptionError("No speech detected in audio.")

        logger.info("Transcribed %d chars (lang=%s)", len(text), info.language)
        return {
            "text": text,
            "language": info.language,
            "duration_seconds": info.duration,
        }


whisper_service = WhisperService()
