"""
ORM models for conversation memory.

Two tables:
- conversations: one row per conversation thread (a user could have many)
- messages: one row per turn (user or assistant), foreign-keyed to a conversation

Phase 1 has a single implicit "default" user (no auth yet — Firebase Auth
lands in a later phase). The `user_id` column is included now so the
schema doesn't need a breaking migration when auth is added.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), default="default_user", index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
