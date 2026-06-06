# Como Rodar — Desenvolvimento

## Pré-requisitos

- Docker e Docker Compose instalados
- Arquivo `.env` configurado em `app/`

## Setup inicial

```bash
cd app
cp .env.example .env   # ajuste as variáveis conforme necessário
```

Veja [../infra/variaveis-de-ambiente.md](../infra/variaveis-de-ambiente.md) para a lista completa de variáveis.

## Subir o ambiente

```bash
cd app

make up        # build das imagens + sobe API, banco e executa migrations
```

Isso executa, em ordem:
1. Sobe o container `db` (PostgreSQL + pgvector)
2. Aguarda o healthcheck do banco
3. Roda o container `migrate` (alembic upgrade head)
4. Sobe o container `api` (FastAPI com hot reload)

## Endpoints disponíveis

| URL | Descrição |
|---|---|
| `http://localhost:8000` | API REST |
| `http://localhost:8000/docs` | Swagger UI (documentação interativa) |
| `http://localhost:8000/redoc` | ReDoc |

## Comandos do dia a dia

Todos os comandos devem ser executados dentro de `app/`:

```bash
make logs                         # acompanha logs da API em tempo real
make migration name="add_campo"   # gera nova migration (containers devem estar up)
make migrate                      # aplica migrations pendentes
make rollback                     # desfaz a última migration
make down                         # encerra os containers (dados persistem)
docker compose down -v            # encerra e destrói volumes (apaga dados)
```

## Hot reload

O volume `.:/app` no `docker-compose.yml` monta o código local dentro do container. O Uvicorn roda com `--reload`, então qualquer alteração em arquivos `.py` reinicia o servidor automaticamente.

## Acessar o banco diretamente

```bash
docker compose exec db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

## Logs detalhados por serviço

```bash
docker compose logs -f db       # logs do PostgreSQL
docker compose logs -f migrate  # logs das migrations
docker compose logs -f api      # logs da API (mesmo que make logs)
```
