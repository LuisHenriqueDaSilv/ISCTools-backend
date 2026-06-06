from sqlalchemy import text
from sqlalchemy.orm import Session

from src.knowledge.models import KnowledgeChunk


def search_similar(
    db: Session,
    query_embedding: list[float],
    top_k: int = 5,
    source_type: str | None = None,
    video_source: str | None = None,
) -> list[KnowledgeChunk]:
    query = db.query(KnowledgeChunk)
    if source_type:
        query = query.filter(KnowledgeChunk.source_type == source_type)
    if video_source:
        query = query.filter(KnowledgeChunk.video_source == video_source)
    return (
        query
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
        .all()
    )


def chunk_exists(db: Session, video_source: str, chunk_id: int) -> bool:
    return db.query(KnowledgeChunk).filter(
        KnowledgeChunk.video_source == video_source,
        KnowledgeChunk.chunk_id == chunk_id,
    ).first() is not None


def delete_by_video_source(db: Session, video_source: str) -> None:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.video_source == video_source).delete()
    db.commit()


def insert_chunk(db: Session, chunk: KnowledgeChunk) -> None:
    db.add(chunk)
    db.commit()
