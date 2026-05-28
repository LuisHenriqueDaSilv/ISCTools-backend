from sqlalchemy.orm import Session

from src.chat import repository
from src.chat.models import Conversation, Message


def start_conversation(db: Session, user_id: int) -> Conversation:
    return repository.create_conversation(db, user_id)


def send_message(db: Session, conversation_id: int, user_content: str) -> Message:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    repository.add_message(db, conversation_id, role="user", content=user_content)

    # TODO: call AI provider and store the response
    reply = "placeholder AI response"
    return repository.add_message(db, conversation_id, role="assistant", content=reply)
