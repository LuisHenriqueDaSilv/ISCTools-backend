from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.chat.router import router as chat_router
from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_api_settings()
    if settings.langsmith.tracing and not settings.langsmith.api_key:
        raise RuntimeError("LANGSMITH_TRACING=true mas LANGSMITH_API_KEY não está definido.")
    yield


_DESCRIPTION = """\
API do **ISCTools** — disponibiliza o **Lamarzito**, um tutor de IA especializado em
**Organização e Arquitetura de Computadores (OAC)** da UnB.

## Autenticação

1. O cliente obtém um `id_token` do Google (login OAuth no frontend).
2. `POST /auth/google` troca esse token por um **JWT** próprio da aplicação.
3. As demais rotas exigem o header `Authorization: Bearer <access_token>`.

## Chave do Gemini (BYOK)

A chave da API do Gemini **não é armazenada no servidor**. Cada requisição de chat
deve enviá-la no header `X-Google-Api-Key`.

## Streaming (SSE)

As rotas de mensagem respondem com `text/event-stream`. Os eventos emitidos são:
`title`, `model`, `token`, `tool_call`, `error` e `done`.
"""

_TAGS_METADATA = [
    {"name": "auth", "description": "Login com Google e emissão de JWT."},
    {
        "name": "chat",
        "description": (
            "Conversas, mensagens em streaming (SSE) e catálogo de modelos Gemini "
            "habilitados pelo usuário."
        ),
    },
]

app = FastAPI(
    title="ISCTools API",
    version="0.1.0",
    description=_DESCRIPTION,
    openapi_tags=_TAGS_METADATA,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"], summary="Health check")
def health_check():
    """Verificação de liveness — retorna `{"status": "ok"}` se a API está de pé."""
    return {"status": "ok"}


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)
