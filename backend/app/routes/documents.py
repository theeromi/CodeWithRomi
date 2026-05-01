import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
)
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Document, User
from app.schemas import (
    DocumentDetail, DocumentStatus, DocumentSummary,
    TransactionExtreme, TransactionLineResponse, TransactionStats, TransactionsResponse,
)
from app.services import extraction, transactions as txn_svc
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


@router.post("", response_model=DocumentSummary, status_code=201)
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No filename provided")
    mime = file.content_type or "application/octet-stream"
    if not extraction.is_supported(mime, file.filename):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type: {mime} ({file.filename}). Supported: PDF, DOCX, TXT, MD.",
        )

    user_dir = Path(settings.upload_dir) / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower()
    storage_path = user_dir / f"{uuid.uuid4().hex}{ext}"

    size = 0
    with storage_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            size += len(chunk)

    doc = Document(
        user_id=user.id,
        filename=file.filename,
        mime_type=mime,
        size_bytes=size,
        storage_path=str(storage_path),
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background.add_task(run_pipeline, doc.id)
    return doc


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.get("/{doc_id}/status", response_model=DocumentStatus)
def get_status(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentStatus:
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return DocumentStatus(id=doc.id, status=doc.status, error=doc.error)


@router.post("/{doc_id}/retry", response_model=DocumentSummary)
def retry_document(
    doc_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    """Reset a doc back to 'uploaded' and re-run the ingest pipeline.

    Use after a transient failure (e.g. Ollama was down). Wipes any partial
    artifacts (chunks, vectors, transactions) so the fresh run is clean.
    """
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    from sqlalchemy import text as sa_text
    chunk_ids = [c.id for c in doc.chunks]
    if chunk_ids:
        db.execute(sa_text(
            "DELETE FROM chunk_vec WHERE chunk_id IN (" + ",".join(str(i) for i in chunk_ids) + ")"
        ))
    db.execute(sa_text("DELETE FROM chunks WHERE document_id = :did"), {"did": doc.id})
    db.execute(sa_text("DELETE FROM transaction_lines WHERE document_id = :did"), {"did": doc.id})

    doc.status = "uploaded"
    doc.error = None
    doc.summary = None
    doc.extracted_text = None
    db.commit()
    db.refresh(doc)

    background.add_task(run_pipeline, doc.id)
    return doc


@router.get("/{doc_id}/transactions", response_model=TransactionsResponse)
def get_transactions(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TransactionsResponse:
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    rows = txn_svc.list_for_document(db, doc.id)
    stats = txn_svc.summary_stats(db, doc.id)

    def _ext(r):
        return TransactionExtreme(description=r.description, posted_date=r.posted_date, amount=r.amount) if r else None

    return TransactionsResponse(
        document_id=doc.id,
        source_format=rows[0].source_format if rows else None,
        stats=TransactionStats(
            count_total=stats["count_total"],
            count_debits=stats["count_debits"],
            count_credits=stats["count_credits"],
            total_debits=stats["total_debits"],
            total_credits=stats["total_credits"],
            net=stats["net"],
            max_debit=_ext(stats["max_debit"]),
            max_credit=_ext(stats["max_credit"]),
            min_debit=_ext(stats["min_debit"]),
            min_credit=_ext(stats["min_credit"]),
        ),
        lines=[TransactionLineResponse.model_validate(r) for r in rows],
    )


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    chunk_ids = [c.id for c in doc.chunks]
    if chunk_ids:
        from sqlalchemy import text as sa_text
        db.execute(
            sa_text("DELETE FROM chunk_vec WHERE chunk_id IN (" + ",".join(str(i) for i in chunk_ids) + ")")
        )

    try:
        if doc.storage_path and os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)
    except OSError:
        pass

    db.delete(doc)
    db.commit()
