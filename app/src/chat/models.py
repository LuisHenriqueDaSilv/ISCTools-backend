import uuid as _uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(_uuid.uuid4()),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Novo chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    tool_calls: Mapped[list["ToolCall"]] = relationship(back_populates="message")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    input: Mapped[dict] = mapped_column(JSON, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped["Message"] = relationship(back_populates="tool_calls")
