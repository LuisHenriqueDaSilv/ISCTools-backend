# AI Agent — Visão Geral

## Identidade

O agente se chama **Lamarzito**, tutor de Organização e Arquitetura de Computadores (OAC) da UnB. É especializado exclusivamente nos tópicos da disciplina e recusa perguntas fora desse escopo.

## Stack técnica

| Componente | Tecnologia |
|---|---|
| Framework de agente | LangGraph (`create_react_agent`) |
| LLM | Google Gemini (configurável via `GEMINI_MODELS`) |
| Integração LLM | `langchain-google-genai` |
| Observabilidade | LangSmith (`@traceable`) |
| Padrão | ReAct (Reasoning + Acting) — o agente raciocina, decide chamar ferramentas, interpreta resultados e responde |

## Arquivos principais

| Arquivo | Responsabilidade |
|---|---|
| `chat/agent.py` | Cria o agente LangGraph, define `create_agent` e `generate_title` |
| `chat/tools.py` | Implementa todas as ferramentas LangChain disponíveis para o agente |
| `chat/service.py` | Orquestra o streaming SSE e persiste mensagens |

## Criação do agente

```python
# chat/agent.py:85
def create_agent(api_key: str, model: str, db: Session):
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    return create_react_agent(llm, get_tools(db, api_key))
```

O agente é criado por requisição — um novo `create_react_agent` para cada chamada de streaming. O `db` é passado para permitir que `search_knowledge` acesse o banco.

## Geração de título

Na primeira mensagem de cada conversa, `generate_title` chama o modelo `gemini-2.5-flash-lite` com um prompt dedicado para gerar um título de até 5 palavras. O resultado é emitido como evento SSE `title` antes de iniciar o streaming principal.

## Ferramentas disponíveis

Veja [ferramentas.md](ferramentas.md) para a lista completa com descrições e gatilhos.

## Prompt do sistema

Veja [prompts/system-prompt.md](prompts/system-prompt.md) para o prompt completo com análise das seções.
