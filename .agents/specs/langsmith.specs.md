# Especificação: LangSmith — Observabilidade 100%

## Objetivo

Traceabilidade completa de todas as operações de IA: cada run do agente, cada embedding, cada tool call e cada chamada de título — com metadados que permitam filtrar por conversa e modelo no dashboard do LangSmith.

---

## Decisões consolidadas

| Decisão | Escolha |
|---|---|
| Ativação | Variáveis de ambiente (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`) |
| Projeto LangSmith | `LANGSMITH_PROJECT` env var (default `"isctools"`) |
| Metadados por run | `conversation_id` + `model` via `RunnableConfig` |
| Embeddings (dentro do agente) | Automático — `GoogleGenerativeAIEmbeddings` é uma classe LangChain |
| `generate_title` | Decorador `@traceable` com `run_type="llm"` |
| `knowledge.search` | Decorador `@traceable` com `run_type="retriever"` |
| `LangSmithSettings` | Novo arquivo `src/core/config/langsmith.py` |
| Ativação em dev | Opt-in via `.env` — `LANGSMITH_TRACING=false` por padrão |

---

## O que já é rastreado automaticamente

Quando `LANGSMITH_TRACING=true` está definido, o LangSmith registra automaticamente:

- Todos os passos do LangGraph (`create_react_agent`)
- Cada chamada ao `ChatGoogleGenerativeAI` (tokens in/out, latência, modelo)
- Cada tool call — nome, inputs, output, duração
- `GoogleGenerativeAIEmbeddings.embed_query()` — é uma classe LangChain; participa do callback system e fica **aninhada sob o run do agente** porque as tools síncronas rodam via `asyncio.to_thread`, que copia o `ContextVar` do LangSmith

**Sem escrever uma linha de código**, ligar as env vars já cobre ~90% do que existe.

---

## O que precisa de trabalho explícito

### 1. `generate_title` — fora do contexto do agente

`generate_title` chama `llm.ainvoke()` diretamente, fora de qualquer execução do LangGraph. Sem intervenção, a chamada aparece como um run anônimo sem nome nem metadados.

**Fix:** decorador `@traceable`.

```python
# chat/agent.py
from langsmith import traceable

@traceable(name="generate_title", run_type="llm")
async def generate_title(user_content: str, api_key: str) -> str:
    ...
```

### 2. `knowledge.search` — retriever nomeado

A função `search()` em `knowledge/service.py` agrupa embed + query vetorial. Mesmo que o `embed_query` já seja rastreado, o retriever como unidade lógica (embed → pgvector → chunks) não tem nome no trace. Ao decorar com `@traceable(run_type="retriever")`, ela vira um span nomeado com inputs e outputs visíveis.

```python
# knowledge/service.py
from langsmith import traceable

@traceable(name="search_knowledge_retriever", run_type="retriever")
def search(
    db: Session,
    query: str,
    api_key: str,
    top_k: int = 5,
    source_type: str | None = None,
    video_source: str | None = None,
) -> list[dict]:
    ...
```

### 3. Metadados por run do agente

Hoje `agent.astream_events()` é chamado sem `config`, então todos os traces aparecem sem `conversation_id` nem `model`. Isso impossibilita filtrar traces por conversa no dashboard.

**Fix:** passar `RunnableConfig` com `metadata` e `run_name`.

```python
# chat/service.py
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(
    run_name="lamarzito_response",
    metadata={
        "conversation_id": conversation_id,
        "model": model,
    },
    tags=["agent"],
)

async for event in agent.astream_events(
    {"messages": langchain_messages},
    config=config,
    version="v2",
):
    ...
```

O mesmo `RunnableConfig` deve ser passado ao run de `generate_title` quando chamado dentro de `_stream`, para que o trace do título apareça na mesma sessão de conversação:

```python
# chat/service.py
title = await generate_title(user_content, api_key, langsmith_extra={"metadata": {"conversation_id": conversation_id}})
```

> `langsmith_extra` é o parâmetro que o `@traceable` aceita para sobrescrever metadados em runtime.

---

## 4. Configuração — `src/core/config/langsmith.py`

Arquivo novo. Segue o padrão dos outros configs do projeto.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LangSmithSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tracing: bool = Field(default=False, validation_alias="LANGSMITH_TRACING")
    api_key: str | None = Field(default=None, validation_alias="LANGSMITH_API_KEY")
    project: str = Field(default="isctools", validation_alias="LANGSMITH_PROJECT")
    endpoint: str = Field(
        default="https://api.smith.langchain.com",
        validation_alias="LANGSMITH_ENDPOINT",
    )
```

Registrar em `src/core/config/__init__.py`:

```python
from src.core.config.langsmith import LangSmithSettings

class Configs:
    ...
    langsmith: LangSmithSettings

    def __init__(self) -> None:
        ...
        self.langsmith = LangSmithSettings()
```

---

## 5. Inicialização em `src/main.py`

O LangSmith lê as env vars automaticamente, mas é boa prática validar na startup para falhar rápido caso `LANGSMITH_TRACING=true` e `LANGSMITH_API_KEY` não esteja definido.

```python
# src/main.py — dentro do lifespan ou no topo
from src.core.config import settings

if settings.langsmith.tracing and not settings.langsmith.api_key:
    raise RuntimeError("LANGSMITH_TRACING=true mas LANGSMITH_API_KEY não está definido.")
```

Não é preciso chamar nenhuma função de init do LangSmith — as variáveis de ambiente são suficientes.

---

## 6. Dependências — `requirements.txt`

```
langsmith>=0.2.0
```

`langchain-core` já depende de `langsmith`, mas fixar a versão mínima explicitamente garante que o `@traceable` com `langsmith_extra` esteja disponível.

---

## 7. Variáveis de ambiente — `.env.example`

```dotenv
# LangSmith — observabilidade (opcional em dev, recomendado em prod)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=isctools
```

---

## Hierarquia de traces esperada

Para uma mensagem que aciona a tool `search_knowledge`:

```
lamarzito_response                    ← RunnableConfig run_name
  ├── ChatGoogleGenerativeAI          ← 1ª chamada LLM (decide usar tool)
  ├── search_knowledge                ← tool call
  │   └── search_knowledge_retriever  ← @traceable retriever
  │       └── GoogleGenerativeAIEmbeddings  ← embed_query automático
  └── ChatGoogleGenerativeAI          ← 2ª chamada LLM (resposta final)
```

Para uma mensagem que NÃO aciona tools:

```
lamarzito_response
  └── ChatGoogleGenerativeAI
```

Para geração de título (primeira mensagem):

```
generate_title                        ← @traceable
  └── ChatGoogleGenerativeAI
```

---

## Arquivos tocados

| Arquivo | Tipo de mudança |
|---|---|
| `requirements.txt` | Adicionar `langsmith>=0.2.0` |
| `app/.env.example` | Adicionar variáveis LangSmith |
| `src/core/config/langsmith.py` | Criar `LangSmithSettings` |
| `src/core/config/__init__.py` | Registrar `LangSmithSettings` em `Configs` |
| `src/main.py` | Guard de startup para tracing inconsistente |
| `src/chat/agent.py` | `@traceable` em `generate_title` |
| `src/chat/service.py` | `RunnableConfig` com `metadata` em `astream_events` |
| `src/knowledge/service.py` | `@traceable` em `search` |

---

## O que NÃO está no escopo

- Datasets / avaliação automatizada no LangSmith (passo seguinte, separado)
- Tracing de operações fora da camada de IA (queries SQL, auth)
- Sampling / rate limiting de traces em produção
