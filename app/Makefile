up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api

migration:
	docker compose exec api alembic revision --autogenerate -m "$(name)"

migrate:
	docker compose exec api alembic upgrade head

rollback:
	docker compose exec api alembic downgrade -1
