from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import SearchHit
from app.services.retrieval import keyword_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchHit])
def search(
    q: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SearchHit]:
    rows = keyword_search(db, user.id, q)
    return [
        SearchHit(
            document_id=r["document_id"],
            filename=r["filename"],
            snippet=r["snippet"] or "",
            score=float(r["score"] or 0.0),
        )
        for r in rows
    ]
