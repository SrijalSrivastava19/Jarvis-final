"""
Pydantic schemas for API request/response validation and documentation.

Keeping these separate from ORM models (db_models.py) decouples the wire
format from the storage format, so the DB schema can evolve without
breaking API consumers (and vice versa).
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: Optional[str] = Field(
        default=None, description="Existing conversation to continue. Omit to start a new one."
    )


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    model: str


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut] = []

    model_config = {"from_attributes": True}


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class WakeWordDetectionResponse(BaseModel):
    detected: bool
    confidence: float
    matched_phrase: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    whisper_loaded: bool
    piper_available: bool

class NewsItem(BaseModel):
    title: str
    summary: str
    source: str
    url: str
    published: Optional[str] = None


class NewsResponse(BaseModel):
    category: str
    items: List[NewsItem]
    summary: str
    fetched_at: datetime
