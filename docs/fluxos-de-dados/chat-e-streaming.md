# Fluxo de Dados — Chat e Streaming SSE

## Criar conversa

```
POST /chat/conversations
```

O serviço reutiliza a última conversa vazia do usuário, se existir, em vez de criar uma nova (`start_conversation` em `chat/service.py:36`).

```mermaid
sequenceDiagram
    actor Cliente
    participant Router as chat/router.py
    participant Service as chat/service.py
    participant Repo as chat/repository.py
    participant DB as PostgreSQL

    Cliente->>Router: POST /chat/conversations
    Router->>Service: start_conversation(db, user_id)
    Service->>Repo: get_empty_conversation_by_user(db, user_id)
    alt conversa vazia já existe
        Repo-->>Service: Conversation existente
        Service-->>Router: (conversation, is_new=False)
    else
        Repo->>DB: INSERT conversations
        DB-->>Repo: Conversation
        Repo-->>Service: nova Conversation
        Service-->>Router: (conversation, is_new=True)
    end
    Router-->>Cliente: 201 { id }
```

## Enviar mensagem (streaming SSE)

```
POST /chat/conversations/{id}/messages  { content, model, api_key }
```

A resposta é um stream Server-Sent Events. O cliente lê eventos em tempo real enquanto o agente processa.

```mermaid
sequenceDiagram
    actor Cliente
    participant Router as chat/router.py
    participant Service as chat/service.py
    participant Repo as chat/repository.py
    participant DB as PostgreSQL
    participant Agent as LangGraph ReAct Agent
    participant Gemini as Google Gemini API
    participant Tools as chat/tools.py

    Cliente->>Router: POST /conversations/{id}/messages { content, model, api_key }
    Router->>Service: create_message_stream(...)
    Service->>Repo: count_messages(db, conversation_id)
    Service->>Repo: add_message(db, ..., role="user")
    Repo->>DB: INSERT messages

    alt primeira mensagem
        Service->>Gemini: generate_title(user_content)
        Gemini-->>Service: título curto
        Service->>Repo: update_conversation_title(db, ...)
        Service-->>Cliente: SSE event: title { title }
    end

    Service->>Repo: get_last_n_messages(db, ..., window=AGENT_WINDOW_SIZE)
    Service->>Agent: astream_events({ messages: [SystemMessage, ...HumanMessage/AIMessage] })

    loop streaming
        Agent->>Gemini: chamada LLM
        Gemini-->>Agent: token stream

        alt on_chat_model_stream
            Agent-->>Service: chunk de texto
            Service-->>Cliente: SSE event: token { content }
        end

        alt on_tool_end (ferramenta chamada)
            Agent->>Tools: executa ferramenta (assembler, base_converter, etc.)
            Tools-->>Agent: resultado
            Agent-->>Service: tool result
            Service-->>Cliente: SSE event: tool_call { name, input, output }
        end
    end

    alt erro (quota, API key inválida, etc.)
        Service-->>Cliente: SSE event: error { error_code, message }
        Service->>Repo: add_message(..., is_error=True)
        Service->>Repo: add_tool_calls(db, message_id, tool_calls)
    else sucesso
        Service->>Repo: add_message(db, ..., role="assistant")
        Service->>Repo: add_tool_calls(db, message_id, tool_calls)
    end

    Service-->>Cliente: SSE event: done {}
```

## Eventos SSE emitidos

| Evento | Payload | Quando |
|---|---|---|
| `title` | `{ title: string }` | Só na primeira mensagem da conversa |
| `token` | `{ content: string }` | A cada fragmento de texto gerado |
| `tool_call` | `{ name, input, output }` | Após cada ferramenta executada |
| `error` | `{ error_code?, message }` | Em exceções do LLM ou rede |
| `done` | `{}` | Sempre ao final, com ou sem erro |

## Retry de mensagem

```
POST /chat/conversations/{id}/messages/retry
```

Busca a última mensagem do usuário e re-executa o stream. Se a mensagem anterior falhou com tool calls registrados, eles são reinjetados no histórico para evitar reprocessamento.

## Janela de contexto

Controlada por `AGENT_WINDOW_SIZE` (padrão: 10). O serviço busca as últimas N mensagens via `repository.get_last_n_messages` antes de montar o histórico do LangGraph. Mensagens com `is_error=True` são ignoradas na construção do contexto.
