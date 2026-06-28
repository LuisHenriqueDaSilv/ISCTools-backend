from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.auth.models import User
from src.chat import service
from src.chat.schemas import (
    ConversationOut,
    ConversationSummary,
    ModelOption,
    ModelToggle,
    SendMessage,
)
from src.core.database import get_db
from src.core.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


# Documentação compartilhada do corpo SSE para o OpenAPI/Swagger.
_SSE_DESCRIPTION = """\
Resposta em **streaming Server-Sent Events** (`text/event-stream`).

Cada linha `event:` é seguida de uma linha `data:` com um JSON. Eventos possíveis:

- `title` — `{ "title": str }` — título gerado para a conversa (apenas na 1ª mensagem).
- `model` — `{ "slug", "name", "attempt", "total", "previous_error" }` — modelo em uso na tentativa atual (fallback por prioridade).
- `token` — `{ "content": str }` — fragmento de texto da resposta.
- `tool_call` — `{ "name", "input", "output" }` — execução de uma ferramenta pelo agente.
- `error` — `{ "error_code", "message" }` — falha tratada (ex.: cota excedida, chave inválida).
- `done` — `{}` — fim do stream.
"""

_SSE_RESPONSES = {
    200: {
        "description": _SSE_DESCRIPTION,
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    },
    400: {"description": "Header `X-Google-Api-Key` ausente."},
    404: {"description": "Conversa não encontrada."},
}

_API_KEY_HEADER = Header(
    default="",
    alias="X-Google-Api-Key",
    description="Chave da API do Gemini (BYOK). Não é armazenada pelo servidor.",
)


@router.get(
    "/models",
    response_model=list[ModelOption],
    summary="Lista modelos disponíveis",
    response_description="Catálogo de modelos ativos com a preferência (habilitado) do usuário.",
)
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna os modelos Gemini ativos, ordenados por prioridade, indicando quais
    estão habilitados para o usuário autenticado."""
    return service.get_user_models(db, current_user.id)


@router.patch(
    "/models/{slug}",
    response_model=list[ModelOption],
    summary="Habilita/desabilita um modelo",
    responses={
        200: {"description": "Catálogo atualizado."},
        409: {"description": "Modelo inexistente ou tentativa de desabilitar o último habilitado."},
    },
)
def toggle_model(
    slug: str,
    payload: ModelToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liga ou desliga um modelo para o usuário. Não é permitido desabilitar o
    último modelo habilitado (ao menos um precisa permanecer ativo para o fallback)."""
    try:
        return service.set_model_enabled(db, current_user.id, slug, payload.enabled)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/conversations",
    response_model=ConversationOut,
    summary="Inicia (ou reaproveita) uma conversa",
    status_code=201,
    responses={
        200: {"description": "Conversa vazia preexistente reutilizada."},
        201: {"description": "Nova conversa criada."},
    },
)
def start_conversation(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria uma nova conversa. Se já existir uma conversa vazia do usuário, ela é
    reaproveitada (resposta `200`) em vez de criar outra (`201`)."""
    conversation, created = service.start_conversation(db, current_user.id)
    response.status_code = 201 if created else 200
    return conversation


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    summary="Lista conversas do usuário",
    response_description="Conversas do usuário ordenadas da mais recente para a mais antiga.",
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista as conversas do usuário autenticado (sem as mensagens), ordenadas por
    `updated_at` decrescente."""
    return service.get_user_conversations(db, current_user.id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    summary="Detalha uma conversa",
    responses={404: {"description": "Conversa não encontrada ou de outro usuário."}},
)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna uma conversa com todas as mensagens, suas tool calls e metadados de erro."""
    try:
        return service.get_conversation_detail(db, str(conversation_id), current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Envia mensagem (resposta em streaming SSE)",
    responses=_SSE_RESPONSES,
)
async def send_message(
    conversation_id: UUID,
    payload: SendMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    api_key: str = _API_KEY_HEADER,
):
    """Adiciona a mensagem do usuário e transmite a resposta do agente em **SSE**.

    Na primeira mensagem da conversa, um título é gerado e emitido no evento `title`.
    O agente pode chamar ferramentas (RISC-V, busca na base de conhecimento) e, em caso
    de falha de um modelo, faz fallback para o próximo modelo habilitado por prioridade.
    """
    if not api_key:
        raise HTTPException(status_code=400, detail="Header X-Google-Api-Key é obrigatório")

    try:
        stream = service.create_message_stream(
            db=db,
            conversation_id=str(conversation_id),
            user_id=current_user.id,
            user_email=current_user.email,
            user_content=payload.content,
            api_key=api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/conversations/{conversation_id}/retry",
    summary="Reprocessa a última mensagem (streaming SSE)",
    responses={
        **_SSE_RESPONSES,
        404: {"description": "Conversa não encontrada ou sem mensagem de usuário para reprocessar."},
    },
)
async def retry_message(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    api_key: str = _API_KEY_HEADER,
):
    """Reprocessa a última mensagem do usuário (por exemplo, após um erro), reaproveitando
    eventuais tool calls já executadas. A resposta também é transmitida via **SSE**."""
    if not api_key:
        raise HTTPException(status_code=400, detail="Header X-Google-Api-Key é obrigatório")

    try:
        stream = service.retry_last_message(
            db=db,
            conversation_id=str(conversation_id),
            user_id=current_user.id,
            user_email=current_user.email,
            api_key=api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
