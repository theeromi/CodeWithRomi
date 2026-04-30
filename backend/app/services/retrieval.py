import struct
from sqlalchemy import text
from sqlalchemy.orm import Session


def _serialize_embedding(emb: list[float]) -> bytes:
    return struct.pack(f"{len(emb)}f", *emb)


def upsert_chunk_vector(db: Session, chunk_id: int, embedding: list[float]) -> None:
    blob = _serialize_embedding(embedding)
    db.execute(text("DELETE FROM chunk_vec WHERE chunk_id = :cid"), {"cid": chunk_id})
    db.execute(
        text("INSERT INTO chunk_vec(chunk_id, embedding) VALUES (:cid, :emb)"),
        {"cid": chunk_id, "emb": blob},
    )


def vector_search(
    db: Session, user_id: int, query_embedding: list[float], top_k: int = 5
) -> list[dict]:
    """Return top-k chunks for the user, ordered by cosine distance.

    sqlite-vec runs KNN globally then we post-filter by user_id, so chunks belonging
    to other users that rank highly will eat into our k. Over-fetch by a large factor
    so user-specific results aren't squeezed out. (Proper fix: add user_id as a vec0
    partition key — schema migration deferred.)
    """
    blob = _serialize_embedding(query_embedding)
    inner_k = max(top_k * 10, 200)
    rows = db.execute(
        text(
            """
            SELECT
                c.id          AS chunk_id,
                c.document_id AS document_id,
                c.ordinal     AS ordinal,
                c.text        AS chunk_text,
                d.filename    AS filename,
                v.distance    AS distance
            FROM chunk_vec v
            JOIN chunks c    ON c.id = v.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE v.embedding MATCH :q
              AND d.user_id = :uid
              AND k = :k
            ORDER BY v.distance
            LIMIT :lim
            """
        ),
        {"q": blob, "uid": user_id, "k": inner_k, "lim": top_k},
    ).mappings().all()
    return [dict(r) for r in rows]


def keyword_search(db: Session, user_id: int, query: str, limit: int = 25) -> list[dict]:
    """FTS5 search across chunks. Returns one row per matching document (for the search UI)."""
    if not query.strip():
        return []
    safe = _sanitize_fts(query)
    rows = db.execute(
        text(
            """
            SELECT
                d.id        AS document_id,
                d.filename  AS filename,
                snippet(chunks_fts, 0, '<mark>', '</mark>', '…', 16) AS snippet,
                MIN(bm25(chunks_fts)) AS score
            FROM chunks_fts
            JOIN chunks c    ON c.id = chunks_fts.rowid
            JOIN documents d ON d.id = c.document_id
            WHERE chunks_fts MATCH :q
              AND d.user_id = :uid
            GROUP BY d.id, d.filename
            ORDER BY score
            LIMIT :lim
            """
        ),
        {"q": safe, "uid": user_id, "lim": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


def keyword_chunk_search(db: Session, user_id: int, query: str, limit: int = 6) -> list[dict]:
    """FTS5 hits at the chunk level (for hybrid retrieval, not the search UI).

    Same row shape as vector_search so the two can be merged trivially.
    """
    if not query.strip():
        return []
    safe = _sanitize_fts(query)
    rows = db.execute(
        text(
            """
            SELECT
                c.id          AS chunk_id,
                c.document_id AS document_id,
                c.ordinal     AS ordinal,
                c.text        AS chunk_text,
                d.filename    AS filename,
                bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks c    ON c.id = chunks_fts.rowid
            JOIN documents d ON d.id = c.document_id
            WHERE chunks_fts MATCH :q
              AND d.user_id = :uid
            ORDER BY score
            LIMIT :lim
            """
        ),
        {"q": safe, "uid": user_id, "lim": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


def hybrid_search(
    db: Session,
    user_id: int,
    query_text: str,
    query_embedding: list[float],
    vector_k: int = 8,
    keyword_k: int = 6,
) -> list[dict]:
    """Union of vector + FTS5 results, deduped by chunk_id.

    Vector results come first (preserving cosine ranking), then any keyword-only hits
    are appended. This closes the vocabulary gap when the question's wording doesn't
    match the document's vocabulary (e.g. asking about 'expenses' on a bank statement
    that uses 'Withdrawal/Debit/Purchase').
    """
    vec = vector_search(db, user_id, query_embedding, top_k=vector_k)
    kw = keyword_chunk_search(db, user_id, query_text, limit=keyword_k)

    seen: set[int] = set()
    out: list[dict] = []
    for r in vec:
        if r["chunk_id"] in seen:
            continue
        seen.add(r["chunk_id"])
        out.append(r)
    for r in kw:
        if r["chunk_id"] in seen:
            continue
        seen.add(r["chunk_id"])
        out.append(r)
    return out


def _sanitize_fts(q: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in q)
    tokens = [t for t in cleaned.split() if t]
    return " ".join(f'"{t}"' for t in tokens)
