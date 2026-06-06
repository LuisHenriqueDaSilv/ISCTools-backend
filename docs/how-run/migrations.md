# Como Rodar — Migrations

## Fluxo para adicionar uma nova tabela ou coluna

1. Crie ou edite o modelo em `src/<modulo>/models.py`
2. Importe o modelo em `app/alembic/env.py` (obrigatório para autogenerate detectar a tabela)
3. Gere a migration:
   ```bash
   cd app
   make migration name="add_campo_x_em_tabela_y"
   ```
4. Revise o arquivo gerado em `alembic/versions/`
5. Aplique:
   ```bash
   make migrate
   ```

## Comandos

```bash
# Gerar migration (containers devem estar up)
make migration name="descricao"

# Aplicar todas as migrations pendentes
make migrate

# Desfazer a última migration
make rollback

# Ver histórico de migrations
docker compose exec api alembic history

# Ver migration atual aplicada
docker compose exec api alembic current
```

## Importante

- **Nunca edite** um arquivo de migration já aplicado em produção. Crie uma nova migration para corrigir.
- O `autogenerate` detecta apenas modelos importados em `alembic/env.py`. Se a tabela não aparecer na migration, verifique o import.
- Migrations rodam automaticamente no `make up` via o serviço `migrate` do Docker Compose.
