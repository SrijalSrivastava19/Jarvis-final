import json

from fastapi import APIRouter, Depends, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session_factory, get_db
from app.logger import get_logger
from app.models.schemas import SpeakRequest, TranscriptionResponse, WakeWordDetectionResponse
from app.services.memory_service import memory_service
from app.services.ollama_service import ollama_service
from app.services.piper_service import piper_service
from app.services.wakeword_service import wakeword_service
from app.services.whisper_service import whisper_service

router = APIRouter(prefix="/api/voice", tags=["voice"])
logger = get_logger(__name__)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile) -> TranscriptionResponse:
    """Speech-to-text: upload an audio file, get back transcribed text."""
    audio_bytes = await file.read()
    result = whisper_service.transcribe_bytes(audio_bytes, filename_hint=file.filename or "audio.wav")
    return TranscriptionResponse(**result)


@router.post("/speak")
async def speak(request: SpeakRequest) -> Response:
    """Text-to-speech: send text, get back WAV audio bytes."""
    audio_bytes = await piper_service.synthesize(request.text)
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post("/wake-word/detect", response_model=WakeWordDetectionResponse)
async def detect_wake_word(file: UploadFile) -> WakeWordDetectionResponse:
    """Check whether a short audio clip contains the wake word."""
    audio_bytes = await file.read()
    return wakeword_service.detect_from_audio(audio_bytes)


@router.websocket("/ws")
async def voice_conversation_ws(websocket: WebSocket) -> None:
    """
    Full-duplex voice conversation socket.

    Protocol (binary + JSON control messages over one connection):
    1. Client sends a JSON text frame: {"type": "audio_chunk", "conversation_id": "..."}
    2. Client immediately sends a binary frame: raw audio bytes (wav/webm).
    3. Server transcribes -> sends {"type": "transcript", "text": "..."}
    4. Server queries Ollama with memory -> sends {"type": "reply_text", "text": "...", "conversation_id": "..."}
    5. Server synthesizes speech -> sends a binary frame with WAV audio.
    6. Server sends {"type": "done"} to signal the turn is complete.

    Errors at any stage send {"type": "error", "message": "..."} instead of
    crashing the connection, so the client can recover and try again.
    """
    await websocket.accept()
    logger.info("Voice WebSocket connected")

    try:
        while True:
            control_raw = await websocket.receive_text()
            control = json.loads(control_raw)

            if control.get("type") != "audio_chunk":
                await websocket.send_json({"type": "error", "message": "Expected audio_chunk control frame"})
                continue

            conversation_id = control.get("conversation_id")
            audio_bytes = await websocket.receive_bytes()

            try:
                transcription = whisper_service.transcribe_bytes(audio_bytes)
                user_text = transcription["text"]
                await websocket.send_json({"type": "transcript", "text": user_text})

                async with async_session_factory() as db:
                    conversation = await memory_service.get_or_create_conversation(
                        db, conversation_id
                    )
                    context = await memory_service.get_context_for_llm(db, conversation)
                    context.append({"role": "user", "content": user_text})

                    reply = await ollama_service.generate_reply(context)
                    await memory_service.save_turn(db, conversation, user_text, reply)
                    active_conversation_id = conversation.id

                await websocket.send_json(
                    {"type": "reply_text", "text": reply, "conversation_id": active_conversation_id}
                )

                audio_reply = await piper_service.synthesize(reply)
                await websocket.send_bytes(audio_reply)
                await websocket.send_json({"type": "done"})

            except Exception as exc:  # noqa: BLE001 - convert any failure into a recoverable error frame
                logger.exception("Error during voice turn")
                await websocket.send_json({"type": "error", "message": str(exc)})

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
