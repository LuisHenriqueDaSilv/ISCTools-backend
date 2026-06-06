"""resize knowledge embedding to 3072 dims (gemini-embedding-2)

Revision ID: 006
Revises: 005
Create Date: 2026-06-06
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # HNSW and IVFFlat both cap at 2000 dims — gemini-embedding-2 produces 3072,
    # so we drop the index and rely on sequential scan (fine for small datasets).
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(3072)")


def downgrade() -> None:
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(768)")
    op.execute("""
        CREATE INDEX ix_knowledge_chunks_embedding
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
