# Infra — Banco de Dados

## PostgreSQL + pgvector

O projeto usa PostgreSQL 16 com a extensão `pgvector` para armazenar embeddings vetoriais da base de conhecimento.

## Diagrama ER

```mermaid
erDiagram
    users {
        int id PK
        varchar email
        varchar hashed_password
        varchar name
    }

    conversations {
        uuid id PK
        int user_id FK
        varchar title
        timestamp created_at
    }

    messages {
        uuid id PK
        uuid conversation_id FK
        varchar role
        text content
        varchar llm_model
        bool is_error
        varchar error_code
        timestamp created_at
    }

    tool_calls {
        uuid id PK
        uuid message_id FK
        varchar name
        jsonb input
        text output
    }

    knowledge_chunks {
        uuid id PK
        varchar video_source
        varchar source_type
        float timestamp_start
        float timestamp_end
        text content
        vector embedding
    }

    users ||--o{ conversations : "abre"
    conversations ||--o{ messages : "contém"
    messages ||--o{ tool_calls : "registra"
```

## Migrations

Gerenciadas pelo Alembic em `app/alembic/`. Cada migration fica em `alembic/versions/`.

Para adicionar uma nova migration:
```bash
cd app
make migration name="descricao_da_mudanca"
```

A migration é gerada com `--autogenerate` a partir dos modelos SQLAlchemy. **Requisito**: o container da API precisa estar rodando.

## Sessão de banco

`core/database.py` expõe:
- `engine` — engine SQLAlchemy
- `SessionLocal` — factory de sessões
- `get_db` — dependency FastAPI que abre e fecha sessão por request

Cada request recebe uma sessão isolada via `Depends(get_db)`. A sessão é fechada no finally do dependency.
