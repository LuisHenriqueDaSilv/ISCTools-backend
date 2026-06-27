import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from src.chat import repository
from src.chat.agent import _SYSTEM_PROMPT, create_agent, generate_title
from src.chat.models import Conversation
from src.chat.schemas import ModelOption
from src.core.config import settings

logger = logging.getLogger(__name__)


_GEMINI_ERROR_MESSAGES: dict[str, str] = {
    "gemini.exceeded_quota": (
        "Sua cota da API do Gemini foi excedida. "
        "Aguarde alguns minutos e tente novamente."
    ),
    "gemini.invalid_api_key": (
        "Chave de API inválida ou sem permissão para o modelo selecionado. "
        "Verifique suas configurações."
    ),
    "gemini.model_unavailable": (
        "O modelo está temporariamente indisponível. Tentando o próximo modelo habilitado."
    ),
    "gemini.all_models_exhausted": (
        "Todos os modelos habilitados estão sem cota ou indisponíveis. "
        "Aguarde alguns minutos e tente novamente."
    ),
    "gemini.no_models_enabled": (
        "Nenhum modelo está habilitado. Habilite ao menos um modelo nas configurações."
    ),
    "gemini.unknown_error": (
        "Ocorreu um erro inesperado ao consultar o modelo. Tentando o próximo modelo habilitado."
    ),
}


def _classify_gemini_error(exc: Exception) -> str | None:
    msg = str(exc)
    if "RESOURCE_EXHAUSTED" in msg or "exceeded your current quota" in msg:
        return "gemini.exceeded_quota"
    if "API_KEY_INVALID" in msg or ("INVALID_ARGUMENT" in msg and "API key" in msg):
        return "gemini.invalid_api_key"
    if "UNAVAILABLE" in msg or "overloaded" in msg or "503" in msg or "NOT_FOUND" in msg:
        return "gemini.model_unavailable"
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


def get_user_models(db: Session, user_id: int) -> list[ModelOption]:
    rows = repository.get_active_models_with_prefs(db, user_id)
    return [
        ModelOption(slug=model.slug, name=model.name, priority=model.priority, enabled=enabled)
        for model, enabled in rows
    ]


def set_model_enabled(db: Session, user_id: int, slug: str, enabled: bool) -> list[ModelOption]:
    model = repository.get_model_by_slug(db, slug)
    if not model or not model.is_active:
        raise ValueError("Modelo não encontrado")

    if not enabled:
        candidates = repository.get_enabled_models_ordered(db, user_id)
        is_currently_enabled = any(c.id == model.id for c in candidates)
        if is_currently_enabled and len(candidates) <= 1:
            raise ValueError("Não é possível desabilitar o último modelo habilitado")

    repository.set_user_model(db, user_id, model.id, enabled)
    return get_user_models(db, user_id)


def create_message_stream(
    db: Session,
    conversation_id: str,
    user_id: int,
    user_email: str,
    user_content: str,
    api_key: str,
) -> AsyncGenerator[str, None]:
    conversation = repository.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise ValueError("Conversa não encontrada")

    is_first = repository.count_messages(db, conversation_id) == 0
    repository.add_message(db, conversation_id, "user", user_content)

    return _stream(db, conversation_id, user_id, user_email, user_content, api_key, is_first)


def retry_last_message(
    db: Session,
    conversation_id: str,
    user_id: int,
    user_email: str,
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
        db, conversation_id, user_id, user_email, last_user_msg.content, api_key,
        is_first=False, inject_tool_calls=inject_tool_calls,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream(
    db: Session,
    conversation_id: str,
    user_id: int,
    user_email: str,
    user_content: str,
    api_key: str,
    is_first: bool,
    inject_tool_calls: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    candidates = repository.get_enabled_models_ordered(db, user_id)
    if not candidates:
        yield _sse("error", {
            "error_code": "gemini.no_models_enabled",
            "message": _GEMINI_ERROR_MESSAGES["gemini.no_models_enabled"],
        })
        yield _sse("done", {})
        return

    if is_first:
        try:
            title = await generate_title(
                user_content,
                api_key,
                model=candidates[0].slug,
                langsmith_extra={"metadata": {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "user_email": user_email,
                }},
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

    last_code: str | None = None

    for i, candidate in enumerate(candidates):
        yield _sse("model", {
            "slug": candidate.slug,
            "name": candidate.name,
            "attempt": i + 1,
            "total": len(candidates),
            "previous_error": last_code,
        })

        agent = create_agent(api_key, candidate.slug, db)
        full_response = ""
        collected_tool_calls: list[dict] = []
        text_streamed = False

        config = RunnableConfig(
            run_name="lamarzito_response",
            metadata={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_email": user_email,
                "model": candidate.slug,
            },
            tags=["agent"],
        )

        try:
            async for event in agent.astream_events(
                {"messages": langchain_messages}, config=config, version="v2"
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if isinstance(content, str) and content:
                        full_response += content
                        text_streamed = True
                        yield _sse("token", {"content": content})
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text = part.get("text", "")
                                if text:
                                    full_response += text
                                    text_streamed = True
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

            message = repository.add_message(
                db, conversation_id, "assistant", full_response, llm_model=candidate.slug
            )
            if collected_tool_calls:
                repository.add_tool_calls(db, message.id, collected_tool_calls)
            yield _sse("done", {})
            return

        except Exception as e:
            code = _classify_gemini_error(e)

            if code == "gemini.invalid_api_key":
                message = repository.add_message(
                    db, conversation_id, "assistant", full_response,
                    llm_model=candidate.slug, is_error=True, error_code=code,
                )
                if collected_tool_calls:
                    repository.add_tool_calls(db, message.id, collected_tool_calls)
                yield _sse("error", {
                    "error_code": code,
                    "message": _GEMINI_ERROR_MESSAGES[code],
                })
                yield _sse("done", {})
                return

            if not text_streamed:
                if code is None:
                    logger.exception("Erro não classificado no modelo %s", candidate.slug)
                last_code = code or "gemini.unknown_error"
                continue

            message = repository.add_message(
                db, conversation_id, "assistant", full_response,
                llm_model=candidate.slug, is_error=True, error_code=code,
            )
            if collected_tool_calls:
                repository.add_tool_calls(db, message.id, collected_tool_calls)
            yield _sse("error", {
                "error_code": code,
                "message": _GEMINI_ERROR_MESSAGES.get(code, str(e)),
            })
            yield _sse("done", {})
            return

    repository.add_message(
        db, conversation_id, "assistant", "",
        llm_model=candidates[-1].slug, is_error=True, error_code="gemini.all_models_exhausted",
    )
    yield _sse("error", {
        "error_code": "gemini.all_models_exhausted",
        "message": _GEMINI_ERROR_MESSAGES["gemini.all_models_exhausted"],
    })
    yield _sse("done", {})
