# ISCTools — Backend

API do sistema ISCTools, uma plataforma de chatbot com IA para auxiliar estudantes a discutir e explorar o conteúdo de uma disciplina.

---

## Sumário

- [Objetivo](#objetivo)
- [Arquitetura](#arquitetura)
- [Fluxo de interação](#fluxo-de-interação)
- [Diagrama ER](#diagrama-er)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como rodar](#como-rodar)

---

## Objetivo

Fornecer uma API REST que permite ao usuário autenticado abrir conversas com um assistente de IA especializado em uma disciplina e trocar mensagens em linguagem natural. O histórico de cada conversa é persistido no banco de dados para permitir continuidade e futura análise pedagógica.

---

## Arquitetura

O backend é organizado em **módulos por domínio** (feature-based). Cada módulo é autossuficiente e expõe uma camada bem definida de responsabilidades:

| Camada | Arquivo | Responsabilidade |
|---|---|---|
| HTTP | `router.py` | Recebe requests, valida entrada, retorna responses e converte erros de domínio em HTTP |
| Negócio | `service.py` | Aplica regras de negócio, orquestra chamadas ao repositório e ao provedor de IA |
| Dados | `repository.py` | Única camada com acesso direto ao banco via SQLAlchemy |
| Contrato | `schemas.py` | Schemas Pydantic para request/response |
| Entidades | `models.py` | Modelos ORM mapeados para tabelas do PostgreSQL |

**Módulos ativos:**

- **`auth`** — cadastro e autenticação de usuários
- **`chat`** — gerenciamento de conversas e troca de mensagens com a IA

**Infraestrutura compartilhada** em `core/`:

- `config.py` — leitura de variáveis de ambiente via `pydantic-settings`
- `database.py` — engine, sessão e dependency `get_db`

---

## Fluxo de interação

### Autenticação

```mermaid
sequenceDiagram
    actor Cliente
    participant Router as auth/router
    participant Service as auth/service
    participant Repo as auth/repository
    participant DB as PostgreSQL

    Cliente->>Router: POST /auth/register { email, password }
    Router->>Service: register(db, email, password)
    Service->>Repo: get_by_email(db, email)
    Repo-->>Service: None
    Service->>Repo: create(db, email, hashed_password)
    Repo->>DB: INSERT users
    DB-->>Repo: User
    Repo-->>Service: User
    Service-->>Router: User
    Router-->>Cliente: 201 { id, email }
```

### Chat com IA

```mermaid
sequenceDiagram
    actor Cliente
    participant Router as chat/router
    participant Service as chat/service
    participant Repo as chat/repository
    participant DB as PostgreSQL
    participant IA as Provedor de IA

    Cliente->>Router: POST /chat/conversations
    Router->>Service: start_conversation(db, user_id)
    Service->>Repo: create_conversation(db, user_id)
    Repo->>DB: INSERT conversations
    DB-->>Repo: Conversation
    Repo-->>Service: Conversation
    Service-->>Router: Conversation
    Router-->>Cliente: 201 { id }

    Cliente->>Router: POST /chat/conversations/{id}/messages { content }
    Router->>Service: send_message(db, conversation_id, content)
    Service->>Repo: add_message(..., role="user")
    Repo->>DB: INSERT messages
    Service->>IA: envia histórico + mensagem
    IA-->>Service: resposta gerada
    Service->>Repo: add_message(..., role="assistant")
    Repo->>DB: INSERT messages
    Repo-->>Service: Message
    Service-->>Router: Message
    Router-->>Cliente: 200 { id, role, content }
```

---

## Diagrama ER

```mermaid
erDiagram
    users {
        int id PK
        varchar email
        varchar hashed_password
    }

    conversations {
        int id PK
        int user_id FK
    }

    messages {
        int id PK
        int conversation_id FK
        varchar role
        text content
    }

    users ||--o{ conversations : "abre"
    conversations ||--o{ messages : "contém"
```

---

## Estrutura do projeto

```
backend/
├── .agentes/                        # regras de arquitetura para agentes de IA
├── .agents/                         # regras de arquitetura para agentes de IA
├── app/
│   ├── src/
│   │   ├── main.py                  # instância FastAPI e registro de routers
│   │   ├── core/
│   │   │   ├── config.py            # variáveis de ambiente (pydantic-settings)
│   │   │   └── database.py          # engine, SessionLocal, Base, get_db
│   │   ├── auth/
│   │   │   ├── models.py            # User
│   │   │   ├── schemas.py           # UserCreate, UserOut, Token
│   │   │   ├── repository.py        # get_by_email, create
│   │   │   ├── service.py           # register, get_or_raise
│   │   │   └── router.py            # POST /auth/register
│   │   └── chat/
│   │       ├── models.py            # Conversation, Message
│   │       ├── schemas.py           # ConversationOut, MessageOut, SendMessage
│   │       ├── repository.py        # create_conversation, get_conversation, add_message
│   │       ├── service.py           # start_conversation, send_message
│   │       └── router.py            # POST /chat/conversations, POST /chat/conversations/{id}/messages
│   ├── alembic/                     # migrations geradas pelo Alembic
│   ├── alembic.ini
│   ├── docker-compose.yml           # postgres:16 + api
│   ├── Dockerfile
│   ├── Makefile
│   ├── requirements.txt
│   └── .env
├── CLAUDE.md
└── README.md
```

---

## Como rodar

**Pré-requisito:** Docker e Docker Compose instalados.

```bash
cd app
cp .env.example .env   # ajuste as variáveis se necessário

make up                # sobe API + banco
make migrate           # aplica as migrations
```

A API estará disponível em `http://localhost:8000`.
Documentação interativa (Swagger) em `http://localhost:8000/docs`.

### Outros comandos úteis

```bash
make logs                        # acompanha logs da API em tempo real
make migration name="<descricao>" # gera nova migration via autogenerate
make rollback                    # desfaz a última migration
make down                        # encerra os containers
```
