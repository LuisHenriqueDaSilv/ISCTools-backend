# Infra — Docker

## Serviços (`docker-compose.yml`)

O `docker-compose.yml` está em `app/docker-compose.yml` e define três serviços:

### `db` — PostgreSQL com pgvector

```yaml
image: pgvector/pgvector:pg16
ports: 5432:5432
volumes: postgres_data:/var/lib/postgresql/data
```

Usa a imagem `pgvector/pgvector:pg16` para ter suporte nativo a vetores (extensão `pgvector`) usada pela busca semântica do módulo `knowledge`.

O healthcheck garante que `api` e `migrate` só sobem após o banco estar pronto:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  interval: 5s
  retries: 5
```

### `migrate` — Alembic runner

```yaml
dockerfile: Dockerfile.migrate
depends_on:
  db: { condition: service_healthy }
restart: "no"
```

Roda as migrations e termina (`restart: "no"`). O serviço `api` só sobe após `migrate` completar com sucesso.

### `api` — FastAPI

```yaml
build: .
ports: 8000:8000
volumes: .:/app  # hot reload
depends_on:
  db: { condition: service_healthy }
  migrate: { condition: service_completed_successfully }
```

Volume `.:/app` monta o código local dentro do container, permitindo hot reload via `--reload` do Uvicorn.

## Dockerfiles

### `Dockerfile` (API)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### `Dockerfile.migrate`

Roda `alembic upgrade head` e encerra. Compartilha as mesmas dependências do `Dockerfile` principal.

## Ordem de inicialização

```
db (healthy) → migrate (completed) → api (running)
```

## Volume persistente

`postgres_data` é um volume Docker nomeado. Os dados sobrevivem a `docker compose down`. Para destruir os dados:

```bash
docker compose down -v
```
