from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.services.ollama_service import ollama_service
from app.services.piper_service import piper_service
from app.services.whisper_service import whisper_service

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Reports liveness of the backend and reachability of each AI dependency,
    so the frontend can show clear status (e.g. "Ollama offline") instead of
    a confusing generic failure when the user tries to talk to Jarvis.
    """
    return HealthResponse(
        status="ok",
        ollama_reachable=await ollama_service.is_reachable(),
        whisper_loaded=whisper_service.is_loaded(),
        piper_available=piper_service.is_available(),
    )
