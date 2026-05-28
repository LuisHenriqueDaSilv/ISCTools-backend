from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.chat import service
from src.chat.schemas import ConversationOut, MessageOut, SendMessage
from src.core.database import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def start_conversation(user_id: int, db: Session = Depends(get_db)):
    return service.start_conversation(db, user_id)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
def send_message(conversation_id: int, payload: SendMessage, db: Session = Depends(get_db)):
    try:
        return service.send_message(db, conversation_id, payload.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
