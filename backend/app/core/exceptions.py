"""
Typed exception hierarchy for Jarvis.

Using specific exception types (rather than generic Exception/HTTPException
everywhere) lets the API layer return consistent, machine-readable error
payloads and lets services fail loudly with clear causes instead of
swallowing errors.
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.logger import get_logger

logger = get_logger(__name__)


class JarvisError(Exception):
    """Base class for all Jarvis application errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class OllamaUnavailableError(JarvisError):
    status_code = 503
    error_code = "ollama_unavailable"


class TranscriptionError(JarvisError):
    status_code = 422
    error_code = "transcription_failed"


class SpeechSynthesisError(JarvisError):
    status_code = 422
    error_code = "speech_synthesis_failed"

class NewsServiceError(JarvisError):
    status_code = 503
    error_code = "news_service_error"

class MemoryError(JarvisError):  # noqa: A001 - intentional domain-specific name
    status_code = 500
    error_code = "memory_error"


class InvalidAudioError(JarvisError):
    status_code = 400
    error_code = "invalid_audio"


async def jarvis_error_handler(request: Request, exc: JarvisError) -> JSONResponse:
    logger.error("Handled error on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "message": "An unexpected error occurred. Please try again.",
        },
    )
