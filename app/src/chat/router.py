from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
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


@router.get("/models", response_model=list[ModelOption])
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_user_models(db, current_user.id)


@router.patch("/models/{slug}", response_model=list[ModelOption])
def toggle_model(
    slug: str,
    payload: ModelToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return service.set_model_enabled(db, current_user.id, slug, payload.enabled)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/conversations", response_model=ConversationOut)
def start_conversation(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation, created = service.start_conversation(db, current_user.id)
    response.status_code = 201 if created else 200
    return conversation


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_user_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return service.get_conversation_detail(db, str(conversation_id), current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    payload: SendMessage,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = request.headers.get("X-Google-Api-Key", "")
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


@router.post("/conversations/{conversation_id}/retry")
async def retry_message(
    conversation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = request.headers.get("X-Google-Api-Key", "")
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
