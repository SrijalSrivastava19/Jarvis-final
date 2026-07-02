"""
Memory service — persists and retrieves conversation history.

Phase 1 uses relational storage (SQLite) for exact conversational turns.
Semantic long-term memory (ChromaDB vector search over facts/preferences,
per the full Jarvis spec) is intentionally deferred to the Memory feature
phase — this service's interface (`get_recent_context`, `save_turn`) is
kept stable so a vector-search-augmented version can be dropped in later
without changing chat route logic.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import MemoryError
from app.logger import get_logger
from app.models.db_models import Conversation, Message
from app.services.ollama_service import ChatMessage

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful, concise personal AI assistant. "
    "You communicate naturally, remember context from this conversation, "
    "and proactively offer relevant help. Keep spoken replies conversational "
    "and not overly long, since they may be read aloud."
)


class MemoryService:
    async def get_or_create_conversation(
        self, db: AsyncSession, conversation_id: Optional[str]
    ) -> Conversation:
        if conversation_id:
            result = await db.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .options(selectinload(Conversation.messages))
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation
            logger.warning("conversation_id %s not found, creating new one", conversation_id)

        conversation = Conversation()
        conversation.messages = []
        db.add(conversation)
        await db.flush()
        return conversation

    async def get_context_for_llm(
        self, db: AsyncSession, conversation: Conversation
    ) -> List[ChatMessage]:
        """Build the message list (system + recent history) to send to the LLM."""
        recent = conversation.messages[-settings.max_context_messages :]
        context: List[ChatMessage] = [{"role": "system", "content": SYSTEM_PROMPT}]
        context.extend({"role": m.role, "content": m.content} for m in recent)
        return context

    async def save_turn(
        self, db: AsyncSession, conversation: Conversation, user_text: str, assistant_text: str
    ) -> None:
        try:
            db.add(Message(conversation_id=conversation.id, role="user", content=user_text))
            db.add(
                Message(conversation_id=conversation.id, role="assistant", content=assistant_text)
            )
            if conversation.title == "New conversation":
                conversation.title = user_text[:60]
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.exception("Failed to save conversation turn")
            raise MemoryError("Failed to save conversation to memory.") from exc

    async def list_conversations(self, db: AsyncSession) -> List[Conversation]:
        result = await db.execute(
            select(Conversation).order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_conversation(
        self, db: AsyncSession, conversation_id: str
    ) -> Optional[Conversation]:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()


memory_service = MemoryService()
