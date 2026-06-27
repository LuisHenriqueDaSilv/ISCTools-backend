from sqlalchemy import func
from sqlalchemy.orm import Session

from src.chat.models import AIModel, Conversation, Message, ToolCall, UserModel


def create_conversation(db: Session, user_id: int) -> Conversation:
    conversation = Conversation(user_id=user_id, title="Novo chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_empty_conversation_by_user(db: Session, user_id: int) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .filter(~Conversation.messages.any())
        .first()
    )


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_conversations_by_user(db: Session, user_id: int) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def count_messages(db: Session, conversation_id: str) -> int:
    return (
        db.query(func.count(Message.id))
        .filter(Message.conversation_id == conversation_id)
        .scalar()
        or 0
    )


def get_last_n_messages(db: Session, conversation_id: str, n: int) -> list[Message]:
    subquery = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(n)
        .subquery()
    )
    return (
        db.query(Message)
        .filter(Message.id.in_(db.query(subquery.c.id)))
        .order_by(Message.id.asc())
        .all()
    )


def get_last_user_message(db: Session, conversation_id: str) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.id.desc())
        .first()
    )


def get_error_message_after(db: Session, conversation_id: str, after_id: int) -> Message | None:
    return (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.id > after_id,
            Message.is_error == True,  # noqa: E712
        )
        .order_by(Message.id.asc())
        .first()
    )


def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    llm_model: str | None = None,
    is_error: bool = False,
    error_code: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        llm_model=llm_model,
        is_error=is_error,
        error_code=error_code,
    )
    db.add(message)
    db.flush()

    # touch updated_at on the parent conversation
    db.query(Conversation).filter(Conversation.id == conversation_id).update(
        {"updated_at": func.now()}
    )
    db.commit()
    db.refresh(message)
    return message


def add_tool_calls(db: Session, message_id: int, calls: list[dict]) -> None:
    for call in calls:
        db.add(ToolCall(message_id=message_id, name=call["name"], input=call["input"], output=call["output"]))
    db.commit()


def update_conversation_title(db: Session, conversation_id: str, title: str) -> None:
    db.query(Conversation).filter(Conversation.id == conversation_id).update({"title": title})
    db.commit()


def _enabled_expr():
    return func.coalesce(UserModel.enabled, True)


def get_enabled_models_ordered(db: Session, user_id: int) -> list[AIModel]:
    return (
        db.query(AIModel)
        .outerjoin(
            UserModel,
            (UserModel.model_id == AIModel.id) & (UserModel.user_id == user_id),
        )
        .filter(AIModel.is_active == True)  # noqa: E712
        .filter(_enabled_expr() == True)  # noqa: E712
        .order_by(AIModel.priority.asc(), AIModel.id.asc())
        .all()
    )


def get_active_models_with_prefs(db: Session, user_id: int) -> list[tuple[AIModel, bool]]:
    rows = (
        db.query(AIModel, _enabled_expr())
        .outerjoin(
            UserModel,
            (UserModel.model_id == AIModel.id) & (UserModel.user_id == user_id),
        )
        .filter(AIModel.is_active == True)  # noqa: E712
        .order_by(AIModel.priority.asc(), AIModel.id.asc())
        .all()
    )
    return [(model, enabled) for model, enabled in rows]


def get_model_by_slug(db: Session, slug: str) -> AIModel | None:
    return db.query(AIModel).filter(AIModel.slug == slug).first()


def set_user_model(db: Session, user_id: int, model_id: int, enabled: bool) -> None:
    existing = (
        db.query(UserModel)
        .filter(UserModel.user_id == user_id, UserModel.model_id == model_id)
        .first()
    )
    if existing:
        existing.enabled = enabled
    else:
        db.add(UserModel(user_id=user_id, model_id=model_id, enabled=enabled))
    db.commit()


def count_enabled_models(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(AIModel.id))
        .outerjoin(
            UserModel,
            (UserModel.model_id == AIModel.id) & (UserModel.user_id == user_id),
        )
        .filter(AIModel.is_active == True)  # noqa: E712
        .filter(_enabled_expr() == True)  # noqa: E712
        .scalar()
        or 0
    )
