import json
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth import get_current_user
from app.config import get_settings
from app.db import SessionLocal, get_db
from app.models import Chat, Message, User
from app.schemas import (
    ChatDetail, ChatMessageRequest, ChatSummary, Citation,
    CreateChatRequest, MessageResponse,
)
from app.services import ollama, retrieval, transactions as txn_svc

router = APIRouter(prefix="/api/chats", tags=["chat"])
settings = get_settings()


RAG_SYSTEM = (
    "You are a helpful assistant that answers questions strictly using the provided document excerpts. "
    "If the answer is not in the excerpts, say you don't know. Do NOT ask the user permission to "
    "do work — just do it.\n\n"
    "Citations: ONLY use bracketed numbers like [1], [2] that match the document-excerpt order. "
    "Never write [pre-computed facts], [facts block], [statement], [doc], or any other citation form — "
    "only [1]/[2]/etc. that point at numbered excerpts.\n\n"
    "If the prompt includes a 'PRE-COMPUTED FACTS' block, those numbers were calculated deterministically "
    "from the source document — TREAT THEM AS GROUND TRUTH and use them verbatim. Do NOT recompute from "
    "the excerpts; the LLM tends to miscount or miss items. Cite the bracketed excerpt number that the "
    "facts came from (the same document appears in both the facts block and the excerpts). NEVER mention "
    "'pre-computed', 'facts block', or the existence of any internal data source — the user doesn't know "
    "it exists.\n\n"
    "Financial vocabulary: distinguish credits (deposits, money in, '+', 'Credit') from debits "
    "(withdrawals, purchases, money out, '-', 'Debit'). 'Expense' / 'spend' / 'spent' = debits only. "
    "'Income' / 'received' = credits only."
)


# Question intent: matches "largest/biggest/most expensive/highest/smallest/lowest/cheapest"
# and "total/sum/how much I spent/count/how many/list all" in financial contexts.
_AGG_INTENT = re.compile(
    r"\b("
    r"largest|biggest|most\s+expensive|highest|max(?:imum)?|"
    r"smallest|lowest|cheapest|least\s+expensive|min(?:imum)?|"
    r"total|sum|how\s+much\s+(?:did|do)\s+(?:i|we)\s+(?:spend|spent|earn|earned|make|made|receive|received)|"
    r"count|how\s+many|list\s+all"
    r")\b",
    re.IGNORECASE,
)


def _build_precomputed_facts(db: Session, doc_ids: list[int]) -> str | None:
    """For each doc with parsed transactions, produce a deterministic facts block
    the LLM can use as ground truth. Returns None if no doc had structured data."""
    blocks: list[str] = []
    for doc_id in doc_ids:
        if not txn_svc.has_transactions(db, doc_id):
            continue
        rows = txn_svc.list_for_document(db, doc_id)
        if not rows:
            continue
        stats = txn_svc.summary_stats(db, doc_id)
        # Use the doc's filename for the header
        from app.models import Document
        doc = db.get(Document, doc_id)
        fname = doc.filename if doc else f"doc#{doc_id}"

        def _fmt(r):
            return f"${r.amount:,.2f} on {r.posted_date or '?'}: {r.description}" if r else "—"

        # Top 5 debits + top 5 credits as a quick reference
        debits_sorted = sorted([r for r in rows if r.direction == "debit"], key=lambda r: -r.amount)[:5]
        credits_sorted = sorted([r for r in rows if r.direction == "credit"], key=lambda r: -r.amount)[:5]
        top_debits = "\n    ".join(f"- {_fmt(r)}" for r in debits_sorted) or "    (none)"
        top_credits = "\n    ".join(f"- {_fmt(r)}" for r in credits_sorted) or "    (none)"

        blocks.append(
            f"From {fname}:\n"
            f"  Debits ({stats['count_debits']} lines): total ${stats['total_debits']:,.2f}\n"
            f"  Credits ({stats['count_credits']} lines): total ${stats['total_credits']:,.2f}\n"
            f"  Net (credits − debits): ${stats['net']:,.2f}\n"
            f"  Largest debit: {_fmt(stats['max_debit'])}\n"
            f"  Smallest debit: {_fmt(stats['min_debit'])}\n"
            f"  Largest credit: {_fmt(stats['max_credit'])}\n"
            f"  Smallest credit: {_fmt(stats['min_credit'])}\n"
            f"  Top 5 debits by amount:\n    {top_debits}\n"
            f"  Top 5 credits by amount:\n    {top_credits}"
        )
    if not blocks:
        return None
    return "PRE-COMPUTED FACTS (deterministic, treat as ground truth):\n\n" + "\n\n".join(blocks)


@router.post("", response_model=ChatSummary, status_code=201)
def create_chat(
    payload: CreateChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Chat:
    chat = Chat(user_id=user.id, title=payload.title or "New chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=list[ChatSummary])
def list_chats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Chat]:
    return (
        db.query(Chat)
        .filter(Chat.user_id == user.id)
        .order_by(Chat.created_at.desc())
        .all()
    )


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatDetail:
    chat = db.get(Chat, chat_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    msgs = [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=[Citation(**c) for c in json.loads(m.citations_json or "[]")],
            created_at=m.created_at,
        )
        for m in chat.messages
    ]
    return ChatDetail(id=chat.id, title=chat.title, created_at=chat.created_at, messages=msgs)


@router.delete("/{chat_id}", status_code=204)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    chat = db.get(Chat, chat_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    db.delete(chat)
    db.commit()


@router.post("/{chat_id}/messages")
async def post_message(
    chat_id: int,
    payload: ChatMessageRequest,
    user: User = Depends(get_current_user),
):
    """SSE stream. Events:
       - 'citations' : initial JSON array of cited chunks
       - 'token'     : individual content tokens
       - 'done'      : final assistant message id
    """
    db: Session = SessionLocal()
    try:
        chat = db.get(Chat, chat_id)
        if not chat or chat.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")

        if not chat.messages:
            chat.title = payload.content.strip()[:60] or chat.title
        user_msg = Message(chat_id=chat.id, role="user", content=payload.content)
        db.add(user_msg)
        db.commit()

        q_emb = await ollama.embed(payload.content)
        hits = retrieval.hybrid_search(
            db,
            user.id,
            payload.content,
            q_emb,
            vector_k=settings.rag_top_k,
            keyword_k=settings.rag_keyword_k,
        )

        citations = [
            Citation(
                document_id=h["document_id"],
                filename=h["filename"],
                chunk_ordinal=h["ordinal"],
                snippet=(h["chunk_text"][:300] + ("…" if len(h["chunk_text"]) > 300 else "")),
            )
            for h in hits
        ]

        history = chat.messages[-(settings.chat_history_turns * 2):]
        history_msgs = [{"role": m.role, "content": m.content} for m in history]

        # If the question looks like an aggregate AND any retrieved doc has parsed
        # transactions, prepend a deterministic facts block so the LLM doesn't have
        # to reason over raw rows.
        precomputed = None
        if _AGG_INTENT.search(payload.content) and hits:
            doc_ids_in_hits = list({h["document_id"] for h in hits})
            precomputed = _build_precomputed_facts(db, doc_ids_in_hits)

        if hits:
            context = "\n\n".join(
                f"[{i+1}] {h['filename']} (chunk {h['ordinal']}):\n{h['chunk_text']}"
                for i, h in enumerate(hits)
            )
            parts = []
            if precomputed:
                parts.append(precomputed)
            parts.append(f"Document excerpts:\n\n{context}")
            parts.append(f"Question: {payload.content}")
            user_block = "\n\n".join(parts)
        else:
            user_block = (
                f"No relevant document excerpts were found. "
                f"Answer briefly that you don't have that information.\n\nQuestion: {payload.content}"
            )

        messages_for_llm = [
            {"role": "system", "content": RAG_SYSTEM},
            *history_msgs[:-1],
            {"role": "user", "content": user_block},
        ]
    finally:
        db.close()

    async def event_gen():
        yield {
            "event": "citations",
            "data": json.dumps([c.model_dump() for c in citations]),
        }

        full = []
        try:
            async for token in ollama.chat_stream(messages_for_llm):
                full.append(token)
                yield {"event": "token", "data": token}
        except ollama.OllamaError as e:
            yield {"event": "error", "data": str(e)}
            return

        db2: Session = SessionLocal()
        try:
            asst = Message(
                chat_id=chat_id,
                role="assistant",
                content="".join(full),
                citations_json=json.dumps([c.model_dump() for c in citations]),
            )
            db2.add(asst)
            db2.commit()
            db2.refresh(asst)
            yield {"event": "done", "data": json.dumps({"message_id": asst.id})}
        finally:
            db2.close()

    return EventSourceResponse(event_gen())
