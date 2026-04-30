import asyncio
import logging
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Chunk, Document, TransactionLine
from app.services import bank_parsers, extraction, chunking, ollama, retrieval

logger = logging.getLogger(__name__)
settings = get_settings()


SUMMARY_SYSTEM = (
    "You write concise, accurate document summaries. "
    "Given the document text, produce a 3-5 sentence summary that captures the "
    "purpose, key points, and any concrete details (names, dates, amounts, parties)."
)


def run_pipeline(document_id: int) -> None:
    """Sync entrypoint for FastAPI BackgroundTasks. Runs the async pipeline."""
    asyncio.run(_run(document_id))


async def _run(document_id: int) -> None:
    db: Session = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            return

        try:
            _set_status(db, doc, "extracting")
            text = extraction.extract_text(doc.storage_path, doc.mime_type, doc.filename)
            doc.extracted_text = text
            db.commit()

            if not text.strip():
                _set_status(db, doc, "failed", error="No text could be extracted")
                return

            _set_status(db, doc, "chunking")
            pieces = chunking.chunk_text(
                text,
                target_tokens=settings.chunk_size_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            )
            if not pieces:
                _set_status(db, doc, "failed", error="No chunks produced from text")
                return

            chunk_rows: list[Chunk] = []
            for ordinal, (chunk_text, tcount) in enumerate(pieces):
                row = Chunk(document_id=doc.id, ordinal=ordinal, text=chunk_text, token_count=tcount)
                db.add(row)
                chunk_rows.append(row)
            db.commit()

            _set_status(db, doc, "embedding")
            for row in chunk_rows:
                emb = await ollama.embed(row.text)
                retrieval.upsert_chunk_vector(db, row.id, emb)
            db.commit()

            _set_status(db, doc, "parsing")
            txns = bank_parsers.detect_and_parse(text)
            if txns:
                for t in txns:
                    db.add(TransactionLine(document_id=doc.id, **t.to_dict()))
                db.commit()
                logger.info("doc %s: parsed %d transaction lines (%s)",
                            doc.id, len(txns), txns[0].source_format)

            _set_status(db, doc, "summarizing")
            summary = await ollama.chat_complete(
                [
                    {"role": "system", "content": SUMMARY_SYSTEM},
                    {"role": "user", "content": _truncate_for_summary(text)},
                ]
            )
            doc.summary = summary.strip()
            db.commit()

            _set_status(db, doc, "ready")
        except Exception as e:
            logger.exception("pipeline failed for doc %s", document_id)
            _set_status(db, doc, "failed", error=str(e)[:1000])
    finally:
        db.close()


def _set_status(db: Session, doc: Document, status: str, error: str | None = None) -> None:
    doc.status = status
    doc.error = error
    db.commit()


def _truncate_for_summary(text: str, max_chars: int = 16000) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-max_chars // 2:]
    return f"{head}\n\n[...document truncated for summarization...]\n\n{tail}"
