# Especificação: Tool `search_knowledge` (RAG)

## Decisões consolidadas

| Decisão | Escolha |
|---|---|
| Vector DB | pgvector no Postgres existente |
| Embedding model | `text-embedding-004` via `GoogleGenerativeAIEmbeddings` |
| Chave (ingest) | `GOOGLE_API_KEY` env var |
| Chave (busca) | `api_key` vinda do header `X-Google-Api-Key` por closure |
| Texto a embedar | `slide_description + "\n\n" + transcription` |
| top-k | 5 |
| Filtros | `source_type` e `video_source` opcionais |
| Ingestão | script CLI `--skip-existing` padrão, `--force` para re-embedar |

---

## 1. Infraestrutura — `docker-compose.yml`

**Mudança obrigatória:** `postgres:16-alpine` não tem pgvector. Trocar para:
```yaml
image: pgvector/pgvector:pg16
```

---

## 2. Dependências novas — `requirements.txt`

```
pgvector>=0.3.0
```

`langchain-google-genai>=2.1.0` já suporta `GoogleGenerativeAIEmbeddings` — sem nova dependência.

---

## 3. Novo módulo `src/knowledge/`

Sem `router.py` nem `schemas.py` (uso interno). Três arquivos:

**`models.py`**
```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[int]          # id original do JSON
    video_source: Mapped[str]      # ex: "OAC_2022-01-17.mp4"
    source_type: Mapped[str]       # "aulas_oac" | "youtube_isc"
    timestamp_start: Mapped[float]
    timestamp_end: Mapped[float]
    content: Mapped[str]           # slide_description + "\n\n" + transcription
    embedding: Mapped[list[float]] = mapped_column(Vector(768))

    __table_args__ = (
        UniqueConstraint("video_source", "chunk_id", name="uq_knowledge_chunk"),
    )
```

**`repository.py`**
```python
def search_similar(
    db: Session,
    query_embedding: list[float],
    top_k: int = 5,
    source_type: str | None = None,
    video_source: str | None = None,
) -> list[KnowledgeChunk]:
    # SELECT ... ORDER BY embedding <=> :vec LIMIT top_k
    # + WHERE filtros opcionais
```

**`service.py`**
```python
def search(
    db: Session,
    query: str,
    api_key: str,
    top_k: int = 5,
    source_type: str | None = None,
    video_source: str | None = None,
) -> list[dict]:
    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
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
```

---

## 4. Migration Alembic

Dois passos em sequência numa única migration:
1. `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`
2. `op.create_table("knowledge_chunks", ...)` com coluna `embedding vector(768)`
3. `op.create_index(... using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"embedding": "vector_cosine_ops"})`

HNSW não exige `VACUUM ANALYZE` antes de funcionar, ao contrário de IVFFlat.

---

## 5. Tool — `chat/tools.py`

`get_tools()` vira `get_tools(db: Session, api_key: str)` e cria a tool via closure:

```python
def make_search_knowledge(db: Session, api_key: str):
    @tool
    def search_knowledge(
        query: str,
        source_type: str | None = None,
        video_source: str | None = None,
    ) -> str:
        """Busca trechos relevantes nos materiais da disciplina (aulas OAC e vídeos ISC).
        Use sempre que o estudante referenciar conteúdo de aula, pedir exemplos do professor
        ou mencionar "o professor falou", "nas aulas", "nos vídeos". Prefira sempre buscar
        antes de responder com conhecimento próprio sobre os materiais do curso.

        Args:
            query: Pergunta ou termo de busca em linguagem natural.
            source_type: Filtro opcional — "aulas_oac" ou "youtube_isc".
            video_source: Filtro opcional — nome do arquivo de vídeo (ex: "OAC_2022-01-17.mp4").
        """
        results = knowledge_service.search(db, query, api_key, source_type=source_type, video_source=video_source)
        # formata os chunks como texto para o agente
        ...
    return search_knowledge
```

---

## 6. `chat/agent.py`

```python
def create_agent(api_key: str, model: str, db: Session):
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    return create_react_agent(llm, get_tools(db, api_key))
```

---

## 7. `chat/service.py`

`_stream(db, ...)` já tem `db` — basta passar para `create_agent`:
```python
agent = create_agent(api_key, model, db)
```

---

## 8. `app/scripts/ingest.py`

```
python scripts/ingest.py [--data-dir PATH] [--skip-existing] [--force]
```

- Default `--data-dir`: `../../datas/` relativo ao script
- Detecta `source_type` pelo nome da pasta:
  - `RESULTADO-FINAL-AULAS-OAC` → `"aulas_oac"`
  - `RESULTADO-FINAL-VIDEOSYOUTUBE-ISC` → `"youtube_isc"`
- `GOOGLE_API_KEY` lido via `os.environ`
- Lê `DATABASE_URL` do `.env` para conectar diretamente
- Embeda em batches (50 chunks por chamada de API)
- `--skip-existing`: checa `(video_source, chunk_id)` antes de inserir, pula se já existe
- `--force`: deleta e re-insere tudo

---

## 9. `alembic/env.py`

```python
import src.knowledge.models  # noqa: F401
```

---

## 10. System prompt do agente (`agent.py`)

Adicionar seção para a nova tool:

> **search_knowledge** — chame quando o estudante referenciar conteúdo de aula, pedir exemplos do professor, ou mencionar "o professor falou", "nas aulas", "nos vídeos". Prefira sempre buscar antes de responder com conhecimento próprio sobre os materiais do curso.

---

## Arquivos tocados (resumo)

| Arquivo | Tipo de mudança |
|---|---|
| `docker-compose.yml` | Trocar imagem Postgres |
| `requirements.txt` | Adicionar `pgvector` |
| `src/knowledge/__init__.py` | Criar |
| `src/knowledge/models.py` | Criar |
| `src/knowledge/repository.py` | Criar |
| `src/knowledge/service.py` | Criar |
| `alembic/env.py` | Import knowledge models |
| `alembic/versions/xxx_add_knowledge.py` | Criar migration |
| `src/chat/tools.py` | `get_tools(db, api_key)` + closure |
| `src/chat/agent.py` | `create_agent(..., db)` |
| `src/chat/service.py` | Passar `db` para `create_agent` |
| `app/scripts/ingest.py` | Criar |
