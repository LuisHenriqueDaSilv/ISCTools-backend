import json
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from src.chat import repository
from src.chat.agent import _SYSTEM_PROMPT, create_agent, generate_title
from src.chat.models import Conversation
from src.core.config import settings


_GEMINI_ERROR_MESSAGES: dict[str, str] = {
    "gemini.exceeded_quota": (
        "Sua cota da API do Gemini foi excedida. "
        "Aguarde alguns minutos e tente novamente."
    ),
    "gemini.invalid_api_key": (
        "Chave de API inválida ou sem permissão para o modelo selecionado. "
        "Verifique suas configurações."
    ),
}


def _classify_gemini_error(exc: Exception) -> str | None:
    msg = str(exc)
    if "RESOURCE_EXHAUSTED" in msg or "exceeded your current quota" in msg:
        return "gemini.exceeded_quota"
    if "API_KEY_INVALID" in msg or ("INVALID_ARGUMENT" in msg and "API key" in msg):
        return "gemini.invalid_api_key"
    return None


def start_conversation(db: Session, user_id: int) -> tuple[Conversation, bool]:
    existing = repository.get_empty_conversation_by_user(db, user_id)
    if existing:
        return existing, False
    return repository.create_conversation(db, user_id), True


def get_user_conversations(db: Session, user_id: int) -> list[Conversation]:
    return repository.get_conversations_by_user(db, user_id)


def get_conversation_detail(db: Session, conversation_id: str, user_id: int) -> Conversation:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise ValueError("Conversa não encontrada")
    return conversation


def create_message_stream(
    db: Session,
    conversation_id: str,
    user_id: int,
    user_content: str,
    model: str,
    api_key: str,
) -> AsyncGenerator[str, None]:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise ValueError("Conversa não encontrada")

    is_first = repository.count_messages(db, conversation_id) == 0
    repository.add_message(db, conversation_id, "user", user_content, llm_model=model)

    return _stream(db, conversation_id, user_content, model, api_key, is_first)


def retry_last_message(
    db: Session,
    conversation_id: str,
    user_id: int,
    model: str,
    api_key: str,
) -> AsyncGenerator[str, None]:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise ValueError("Conversa não encontrada")

    last_user_msg = repository.get_last_user_message(db, conversation_id)
    if not last_user_msg:
        raise ValueError("Nenhuma mensagem de usuário encontrada")

    error_msg = repository.get_error_message_after(db, conversation_id, last_user_msg.id)

    inject_tool_calls: list[dict] = []
    if error_msg and error_msg.tool_calls:
        inject_tool_calls = [
            {"id": tc.id, "name": tc.name, "input": tc.input, "output": tc.output}
            for tc in error_msg.tool_calls
        ]

    return _stream(
        db, conversation_id, last_user_msg.content, model, api_key,
        is_first=False, inject_tool_calls=inject_tool_calls,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream(
    db: Session,
    conversation_id: str,
    user_content: str,
    model: str,
    api_key: str,
    is_first: bool,
    inject_tool_calls: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    if is_first:
        try:
            title = await generate_title(
                user_content,
                api_key,
                langsmith_extra={"metadata": {"conversation_id": conversation_id}},
            )
        except Exception:
            title = user_content[:50]
        repository.update_conversation_title(db, conversation_id, title)
        yield _sse("title", {"title": title})

    window = settings.agent.agent_window_size
    messages = repository.get_last_n_messages(db, conversation_id, window)

    langchain_messages: list = [SystemMessage(content=_SYSTEM_PROMPT)]
    for m in messages:
        if m.is_error:
            continue
        if m.role == "user":
            langchain_messages.append(HumanMessage(content=m.content))
        else:
            langchain_messages.append(AIMessage(content=m.content))

    if inject_tool_calls:
        tool_call_list = [
            {"id": f"call_{tc['id']}", "name": tc["name"], "args": tc["input"]}
            for tc in inject_tool_calls
        ]
        langchain_messages.append(AIMessage(content="", tool_calls=tool_call_list))
        for tc in inject_tool_calls:
            langchain_messages.append(
                ToolMessage(content=tc["output"], tool_call_id=f"call_{tc['id']}")
            )

    agent = create_agent(api_key, model, db)
    full_response = ""
    collected_tool_calls: list[dict] = []
    error_occurred = False

    config = RunnableConfig(
        run_name="lamarzito_response",
        metadata={
            "conversation_id": conversation_id,
            "model": model,
        },
        tags=["agent"],
    )

    try:
        async for event in agent.astream_events({"messages": langchain_messages}, config=config, version="v2"):
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
                raw_output = event["data"].get("output", "")
                output = raw_output.content if hasattr(raw_output, "content") else str(raw_output)
                call = {
                    "name": event["name"],
                    "input": event["data"].get("input", {}),
                    "output": output,
                }
                collected_tool_calls.append(call)
                yield _sse("tool_call", call)

    except Exception as e:
        error_occurred = True
        error_code = _classify_gemini_error(e)
        if error_code:
            yield _sse("error", {"error_code": error_code, "message": _GEMINI_ERROR_MESSAGES[error_code]})
        else:
            yield _sse("error", {"message": str(e)})
        message = repository.add_message(
            db, conversation_id, "assistant", full_response,
            llm_model=model, is_error=True, error_code=error_code,
        )
        if collected_tool_calls:
            repository.add_tool_calls(db, message.id, collected_tool_calls)

    if not error_occurred and full_response:
        message = repository.add_message(db, conversation_id, "assistant", full_response, llm_model=model)
        if collected_tool_calls:
            repository.add_tool_calls(db, message.id, collected_tool_calls)

    yield _sse("done", {})
