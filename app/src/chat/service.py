import json
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from src.chat import repository
from src.chat.agent import _SYSTEM_PROMPT, create_agent, generate_title
from src.chat.models import Conversation
from src.core.config import settings


def start_conversation(db: Session, user_id: int) -> Conversation:
    return repository.create_conversation(db, user_id)


def get_user_conversations(db: Session, user_id: int) -> list[Conversation]:
    return repository.get_conversations_by_user(db, user_id)


def get_conversation_detail(db: Session, conversation_id: int, user_id: int) -> Conversation:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise ValueError("Conversa não encontrada")
    return conversation


def create_message_stream(
    db: Session,
    conversation_id: int,
    user_id: int,
    user_content: str,
    model: str,
    api_key: str,
) -> AsyncGenerator[str, None]:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise ValueError("Conversa não encontrada")

    is_first = repository.count_messages(db, conversation_id) == 0
    repository.add_message(db, conversation_id, "user", user_content)

    return _stream(db, conversation_id, user_content, model, api_key, is_first)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream(
    db: Session,
    conversation_id: int,
    user_content: str,
    model: str,
    api_key: str,
    is_first: bool,
) -> AsyncGenerator[str, None]:
    if is_first:
        try:
            title = await generate_title(user_content, api_key, model)
        except Exception:
            title = user_content[:50]
        repository.update_conversation_title(db, conversation_id, title)
        yield _sse("title", {"title": title})

    window = settings.agent.agent_window_size
    messages = repository.get_last_n_messages(db, conversation_id, window)

    langchain_messages = [SystemMessage(content=_SYSTEM_PROMPT)] + [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in messages
    ]

    agent = create_agent(api_key, model)
    full_response = ""

    try:
        async for event in agent.astream_events({"messages": langchain_messages}, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = chunk.content
                if isinstance(content, str) and content:
                    full_response += content
                    yield _sse("token", {"content": content})
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text = part.get("text", "")
                            if text:
                                full_response += text
                                yield _sse("token", {"content": text})

            elif kind == "on_tool_end":
                yield _sse("tool_call", {
                    "name": event["name"],
                    "input": event["data"].get("input", {}),
                    "output": str(event["data"].get("output", "")),
                })

    except Exception as e:
        yield _sse("error", {"message": str(e)})

    if full_response:
        repository.add_message(db, conversation_id, "assistant", full_response)

    yield _sse("done", {})
