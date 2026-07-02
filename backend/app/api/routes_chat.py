from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.logger import get_logger
from app.models.db_models import Conversation
from app.models.schemas import ChatRequest, ChatResponse, ConversationOut
from app.services.memory_service import memory_service
from app.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """
    Send a text message to Jarvis and get a reply. Conversation history is
    loaded from memory, sent to Ollama as context, and the new turn is
    persisted afterward — this is the core text-chat loop that voice chat
    also relies on (after STT) and that all future channels (Gmail, Slack,
    etc.) will reuse.
    """
    conversation: Conversation = await memory_service.get_or_create_conversation(
        db, request.conversation_id
    )

    context = await memory_service.get_context_for_llm(db, conversation)
    context.append({"role": "user", "content": request.message})

    reply = await ollama_service.generate_reply(context)

    await memory_service.save_turn(db, conversation, request.message, reply)

    return ChatResponse(conversation_id=conversation.id, reply=reply, model=settings.ollama_model)


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    return await memory_service.list_conversations(db)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    conversation = await memory_service.get_conversation(db, conversation_id)
    if not conversation:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
