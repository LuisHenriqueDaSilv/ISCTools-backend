from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.auth.models import User
from src.chat import service
from src.chat.schemas import (
    ConversationOut,
    ConversationSummary,
    GeminiModelOption,
    SendMessage,
)
from src.core.config import settings
from src.core.database import get_db
from src.core.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/models", response_model=list[GeminiModelOption])
def list_models():
    return settings.agent.get_models()


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def start_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.start_conversation(db, current_user.id)


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_user_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return service.get_conversation_detail(db, conversation_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
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
            conversation_id=conversation_id,
            user_id=current_user.id,
            user_content=payload.content,
            model=payload.model,
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
