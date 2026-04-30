"""Aggregate queries over parsed transaction_lines.

The chat endpoint uses these to produce authoritative numerical answers
(max/sum/count/list) for documents that had structured extraction at ingest.
The LLM never does the arithmetic — we hand it the result; it only phrases
and cites.
"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Document, TransactionLine


def has_transactions(db: Session, doc_id: int) -> bool:
    return db.execute(
        select(func.count()).select_from(TransactionLine).where(TransactionLine.document_id == doc_id)
    ).scalar() > 0


def list_for_document(db: Session, doc_id: int) -> list[TransactionLine]:
    return list(db.execute(
        select(TransactionLine)
        .where(TransactionLine.document_id == doc_id)
        .order_by(TransactionLine.ordinal)
    ).scalars())


def summary_stats(db: Session, doc_id: int) -> dict:
    """High-level numbers for one doc."""
    rows = list_for_document(db, doc_id)
    debits = [r for r in rows if r.direction == "debit"]
    credits_ = [r for r in rows if r.direction == "credit"]
    return {
        "count_total": len(rows),
        "count_debits": len(debits),
        "count_credits": len(credits_),
        "total_debits": round(sum(r.amount for r in debits), 2),
        "total_credits": round(sum(r.amount for r in credits_), 2),
        "net": round(sum(r.amount for r in credits_) - sum(r.amount for r in debits), 2),
        "max_debit": max(debits, key=lambda r: r.amount, default=None),
        "max_credit": max(credits_, key=lambda r: r.amount, default=None),
        "min_debit": min(debits, key=lambda r: r.amount, default=None),
        "min_credit": min(credits_, key=lambda r: r.amount, default=None),
    }


def user_doc_ids_with_transactions(db: Session, user_id: int) -> list[int]:
    """Document ids for the given user that have parsed transactions."""
    return list(db.execute(
        select(Document.id)
        .join(TransactionLine, TransactionLine.document_id == Document.id)
        .where(Document.user_id == user_id)
        .group_by(Document.id)
    ).scalars())
