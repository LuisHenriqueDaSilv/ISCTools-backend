# Infra — Variáveis de Ambiente

O arquivo `.env` fica em `app/.env` e é carregado tanto pelo Docker Compose (para os containers) quanto pela aplicação Python via `pydantic-settings`.

## Variáveis obrigatórias

| Variável | Usado por | Descrição |
|---|---|---|
| `DATABASE_URL` | `core/config/database.py` | URL de conexão SQLAlchemy (ex: `postgresql+psycopg2://user:pass@db:5432/dbname`) |
| `POSTGRES_USER` | Docker Compose | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Docker Compose | Senha do PostgreSQL |
| `POSTGRES_DB` | Docker Compose | Nome do banco de dados |
| `SECRET_KEY` | `core/config/jwt.py` | Chave para assinar tokens JWT |

## Variáveis opcionais

| Variável | Default | Descrição |
|---|---|---|
| `AGENT_WINDOW_SIZE` | `10` | Número de mensagens do histórico enviadas ao agente por requisição |
| `GEMINI_MODELS` | lista padrão em JSON | Modelos Gemini disponíveis para o usuário selecionar no frontend |
| `LANGSMITH_API_KEY` | — | Habilita rastreamento de traces no LangSmith |
| `LANGSMITH_PROJECT` | — | Nome do projeto no LangSmith |
| `GOOGLE_CLIENT_ID` | — | Client ID para login OAuth com Google |
| `GOOGLE_CLIENT_SECRET` | — | Client Secret para login OAuth com Google |

## Classes de configuração

A configuração é dividida em classes separadas por domínio em `src/core/config/`:

| Arquivo | Classe | Variáveis |
|---|---|---|
| `database.py` | `DatabaseSettings` | `DATABASE_URL` |
| `jwt.py` | `JWTSettings` | `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| `agent.py` | `AgentSettings` | `AGENT_WINDOW_SIZE`, `GEMINI_MODELS` |
| `langsmith.py` | `LangSmithSettings` | `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` |
| `google_oauth.py` | `GoogleOAuthSettings` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |

Todas usam `pydantic-settings` com `env_file=".env"` e `extra="ignore"`.

## Exemplo de `.env`

```dotenv
# Banco de dados
DATABASE_URL=postgresql+psycopg2://isctools:secret@db:5432/isctools
POSTGRES_USER=isctools
POSTGRES_PASSWORD=secret
POSTGRES_DB=isctools

# JWT
SECRET_KEY=your-secret-key-here

# Agente (opcional)
AGENT_WINDOW_SIZE=10

# LangSmith (opcional)
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=isctools-backend
```
