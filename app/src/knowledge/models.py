from pgvector.sqlalchemy import Vector
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[int]
    video_source: Mapped[str]
    source_type: Mapped[str]
    timestamp_start: Mapped[float]
    timestamp_end: Mapped[float]
    content: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(3072))

    __table_args__ = (
        UniqueConstraint("video_source", "chunk_id", name="uq_knowledge_chunk"),
    )
