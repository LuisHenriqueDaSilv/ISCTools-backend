"""
Popula/atualiza o catálogo de modelos (tabela `models`) a partir de
`src.core.config.agent.DEFAULT_MODELS`. Idempotente: faz upsert por `slug`.

A prioridade é a posição na lista (índice + 1). Gerência futura do catálogo
(adicionar modelo, mudar prioridade/is_active) é feita editando esta lista
e rodando o script novamente, ou via SQL direto (D8 — sem endpoint de admin).

Usage:
    python scripts/seed_models.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.chat.models import AIModel
from src.core.config.agent import DEFAULT_MODELS


def seed(engine) -> None:
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for index, entry in enumerate(DEFAULT_MODELS, start=1):
            model = db.query(AIModel).filter(AIModel.slug == entry["slug"]).first()
            if model:
                model.name = entry["name"]
                model.priority = index
                model.is_active = True
            else:
                db.add(AIModel(slug=entry["slug"], name=entry["name"], priority=index, is_active=True))
                print(f"+ {entry['slug']} (priority={index})")
        db.commit()
    print("Catálogo de modelos atualizado.")


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url)
    seed(engine)


if __name__ == "__main__":
    main()
