"""add knowledge chunks

Revision ID: 005
Revises: 004
Create Date: 2026-06-06
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE knowledge_chunks (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            video_source VARCHAR NOT NULL,
            source_type VARCHAR NOT NULL,
            timestamp_start FLOAT NOT NULL,
            timestamp_end FLOAT NOT NULL,
            content TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            CONSTRAINT uq_knowledge_chunk UNIQUE (video_source, chunk_id)
        )
    """)

    op.execute("""
        CREATE INDEX ix_knowledge_chunks_embedding
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")
    op.drop_table("knowledge_chunks")
