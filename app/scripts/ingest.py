"""
Ingest knowledge chunks from JSON files into the knowledge_chunks table.

Usage:
    python scripts/ingest.py [--data-dir PATH] [--skip-existing] [--force]
                             [--batch-size N] [--max-chars N] [--sleep S]

Expects data directory layout:
    <data-dir>/
        RESULTADO-FINAL-AULAS-OAC/
            RESULTADO-FINAL-AULAS-OAC/
                *.json
        RESULTADO-FINAL-VIDEOSYOUTUBE-ISC/
            RESULTADO-FINAL-VIDEOSYOUTUBE-ISC/
                *.json

Each JSON file is a list of chunk objects with fields:
    id, slide_description, transcription, timestamp_start, timestamp_end, video_source
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.knowledge.models import KnowledgeChunk
from src.knowledge import repository

_FOLDER_TO_SOURCE_TYPE = {
    "RESULTADO-FINAL-AULAS-OAC": "aulas_oac",
    "RESULTADO-FINAL-VIDEOSYOUTUBE-ISC": "youtube_isc",
}

_DEFAULT_BATCH_SIZE = 5
_DEFAULT_MAX_CHARS = 6000   # ~1500 tokens, bem abaixo do limite do modelo
_DEFAULT_SLEEP_S = 3.0      # pausa entre batches para respeitar RPM
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "datas"

_MAX_RETRIES = 5
_RETRY_BASE_WAIT = 60       # segundos iniciais no backoff exponencial


def _build_content(chunk: dict, max_chars: int) -> str:
    text = f"{chunk.get('slide_description', '')}\n\n{chunk.get('transcription', '')}"
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def _embed_with_retry(embedder: GoogleGenerativeAIEmbeddings, texts: list[str]) -> list[list[float]]:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return embedder.embed_documents(texts)
        except Exception as e:
            is_rate_limit = "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
            if is_rate_limit and attempt < _MAX_RETRIES:
                wait = _RETRY_BASE_WAIT * (2 ** (attempt - 1))
                _log(f"  ⚠ rate limit (tentativa {attempt}/{_MAX_RETRIES}), aguardando {wait}s...")
                time.sleep(wait)
            else:
                raise


def ingest(
    data_dir: Path,
    skip_existing: bool,
    force: bool,
    engine,
    batch_size: int,
    max_chars: int,
    sleep_s: float,
) -> None:
    Session = sessionmaker(bind=engine)

    api_key = os.environ["GOOGLE_API_KEY"]
    embedder = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        google_api_key=api_key,
    )

    total_inserted = 0
    total_skipped = 0
    grand_start = time.monotonic()

    for folder_name, source_type in _FOLDER_TO_SOURCE_TYPE.items():
        inner = data_dir / folder_name / folder_name
        if not inner.exists():
            print(f"[skip] folder not found: {inner}")
            continue

        json_files = sorted(inner.glob("*.json"))
        print(f"\n{'='*60}")
        print(f"[{source_type}] {len(json_files)} arquivo(s) | batch={batch_size} | max_chars={max_chars} | sleep={sleep_s}s")
        print(f"{'='*60}")

        for file_idx, json_file in enumerate(json_files, 1):
            with json_file.open(encoding="utf-8") as f:
                chunks = json.load(f)

            if not chunks:
                continue

            video_source = chunks[0]["video_source"]
            total_chunks = len(chunks)
            print(f"\n[{file_idx}/{len(json_files)}] {video_source}  ({total_chunks} chunks)")

            if force:
                _log("--force: deletando chunks existentes...")
                with Session() as db:
                    repository.delete_by_video_source(db, video_source)
                _log("deletados.")

            # Fase 1: filtrar pendentes
            pending_chunks = []
            pending_contents = []
            skipped = 0

            for chunk in chunks:
                chunk_id = chunk["id"]
                content = _build_content(chunk, max_chars)

                if not force and skip_existing:
                    with Session() as db:
                        exists = repository.chunk_exists(db, video_source, chunk_id)
                    if exists:
                        _log(f"chunk {chunk_id:>4} — já existe, pulando")
                        skipped += 1
                        total_skipped += 1
                        continue

                original_len = len(f"{chunk.get('slide_description', '')}\n\n{chunk.get('transcription', '')}")
                if original_len > max_chars:
                    _log(f"chunk {chunk_id:>4} — truncado de {original_len} → {max_chars} chars")

                pending_chunks.append(chunk)
                pending_contents.append(content)

            if skipped:
                _log(f"{skipped} chunk(s) pulados (já existiam)")

            if not pending_chunks:
                _log("nada a inserir.")
                continue

            _log(f"{len(pending_chunks)} chunk(s) pendentes para embed+insert")

            # Fase 2: embed em batches
            inserted = 0
            num_batches = (len(pending_chunks) + batch_size - 1) // batch_size

            for batch_idx, i in enumerate(range(0, len(pending_chunks), batch_size), 1):
                batch_chunks = pending_chunks[i : i + batch_size]
                batch_contents = pending_contents[i : i + batch_size]
                chunk_ids = [c["id"] for c in batch_chunks]
                remaining_after = len(pending_chunks) - (i + len(batch_chunks))

                print(
                    f"\n  batch {batch_idx}/{num_batches}"
                    f" | chunks {chunk_ids[0]}–{chunk_ids[-1]}"
                    f" | {len(batch_chunks)} itens"
                    f" | {remaining_after} restantes após este batch",
                    flush=True,
                )

                t0 = time.monotonic()
                _log(f"→ embed iniciado ({sum(len(c) for c in batch_contents)} chars total)...")
                embeddings = _embed_with_retry(embedder, batch_contents)
                _log(f"← embed concluído em {time.monotonic() - t0:.1f}s")

                _log(f"→ inserindo {len(batch_chunks)} registro(s) no banco...")
                with Session() as db:
                    for chunk, content, embedding in zip(batch_chunks, batch_contents, embeddings):
                        record = KnowledgeChunk(
                            chunk_id=chunk["id"],
                            video_source=video_source,
                            source_type=source_type,
                            timestamp_start=float(chunk.get("timestamp_start", 0)),
                            timestamp_end=float(chunk.get("timestamp_end", 0)),
                            content=content,
                            embedding=embedding,
                        )
                        repository.insert_chunk(db, record)
                        inserted += 1
                _log(f"← inseridos. Total acumulado: {total_inserted + inserted}")

                if remaining_after > 0 and sleep_s > 0:
                    _log(f"aguardando {sleep_s}s antes do próximo batch...")
                    time.sleep(sleep_s)

            total_inserted += inserted
            _log(f"✓ {video_source}: {inserted} inseridos | {skipped} pulados")

    elapsed_total = time.monotonic() - grand_start
    print(f"\n{'='*60}")
    print(f"Ingestão concluída em {elapsed_total:.1f}s")
    print(f"Total inserido: {total_inserted} | Total pulado: {total_skipped}")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest knowledge chunks into pgvector")
    parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--force", action="store_true", default=False,
                        help="Deletar e re-embedar tudo")
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE,
                        help=f"Chunks por chamada de API (padrão: {_DEFAULT_BATCH_SIZE})")
    parser.add_argument("--max-chars", type=int, default=_DEFAULT_MAX_CHARS,
                        help=f"Máximo de caracteres por chunk (padrão: {_DEFAULT_MAX_CHARS})")
    parser.add_argument("--sleep", type=float, default=_DEFAULT_SLEEP_S,
                        help=f"Pausa em segundos entre batches (padrão: {_DEFAULT_SLEEP_S})")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url)

    ingest(
        data_dir=args.data_dir,
        skip_existing=args.skip_existing,
        force=args.force,
        engine=engine,
        batch_size=args.batch_size,
        max_chars=args.max_chars,
        sleep_s=args.sleep,
    )


if __name__ == "__main__":
    main()
