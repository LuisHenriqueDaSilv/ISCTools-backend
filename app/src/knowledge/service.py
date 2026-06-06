from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langsmith import traceable
from sqlalchemy.orm import Session

from src.knowledge import repository


@traceable(name="search_knowledge_retriever", run_type="retriever")
def search(
    db: Session,
    query: str,
    api_key: str,
    top_k: int = 5,
    source_type: str | None = None,
    video_source: str | None = None,
) -> list[dict]:
    embedder = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        google_api_key=api_key,
    )
    vec = embedder.embed_query(query)
    chunks = repository.search_similar(db, vec, top_k, source_type, video_source)
    return [
        {
            "video_source": c.video_source,
            "source_type": c.source_type,
            "timestamp_start": c.timestamp_start,
            "timestamp_end": c.timestamp_end,
            "content": c.content,
        }
        for c in chunks
    ]
