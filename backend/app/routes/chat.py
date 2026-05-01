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
from app.services.merchant_categories import expand_query as expand_category_query

router = APIRouter(prefix="/api/chats", tags=["chat"])
settings = get_settings()


RAG_SYSTEM = (
    "You answer questions about the user's documents.\n\n"
    "CRITICAL — when the user message includes a section that starts with '— EXACT FIGURES —', "
    "those numbers are authoritative. Use them WORD-FOR-WORD. Do NOT add up the lines yourself, "
    "do NOT estimate, do NOT recompute. The total/largest/count fields are correct as given.\n\n"
    "VOICE — speak as if you read the document yourself. Never say 'pre-computed', 'facts', "
    "'figures', 'data block', 'I see', 'according to the data', or anything that hints at internal "
    "machinery. Just answer the question. Examples of forbidden phrases: 'According to the figures', "
    "'The data shows', 'Per the pre-computed totals'. Examples of allowed phrasing: 'You spent $X on Y', "
    "'The largest was $Z'.\n\n"
    "CITATIONS — only use bracketed numbers like [1], [2] that match the numbered document excerpts. "
    "Never write [figures], [data], [exact], [statement], [doc], etc.\n\n"
    "FINANCIAL VOCABULARY — credits = deposits / money in / '+' / 'Credit'. Debits = withdrawals, "
    "purchases, money out, '-' / 'Debit'. 'Spend' / 'spent' / 'expense' = debits only. "
    "'Income' / 'received' = credits only.\n\n"
    "If nothing in the excerpts answers the question, say you don't know. Don't ask permission — "
    "just answer."
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


def _fmt_line(r) -> str:
    return f"${r.amount:,.2f} on {r.posted_date or '?'}: {r.description}" if r else "—"


def _build_precomputed_facts(
    db: Session, doc_ids: list[int], question: str
) -> str | None:
    """For each doc with parsed transactions, produce a deterministic facts block
    the LLM can use as ground truth. If the question implies a category set
    (e.g. 'food' → groceries+dining+delivery), the block scopes to those rows
    instead of dumping the whole-doc summary."""
    categories = expand_category_query(question)
    blocks: list[str] = []
    for doc_id in doc_ids:
        if not txn_svc.has_transactions(db, doc_id):
            continue
        from app.models import Document
        doc = db.get(Document, doc_id)
        fname = doc.filename if doc else f"doc#{doc_id}"

        if categories:
            blocks.append(_facts_block_for_categories(db, doc_id, fname, categories))
        else:
            blocks.append(_facts_block_whole_doc(db, doc_id, fname))

    if not blocks:
        return None
    return "— EXACT FIGURES —\n\n" + "\n\n".join(blocks) + "\n\n— END EXACT FIGURES —"


def _facts_block_whole_doc(db: Session, doc_id: int, fname: str) -> str:
    rows = txn_svc.list_for_document(db, doc_id)
    stats = txn_svc.summary_stats(db, doc_id)
    breakdown = txn_svc.category_breakdown(db, doc_id)

    debits_sorted = sorted([r for r in rows if r.direction == "debit"], key=lambda r: -r.amount)[:5]
    credits_sorted = sorted([r for r in rows if r.direction == "credit"], key=lambda r: -r.amount)[:5]
    top_debits = "\n    ".join(f"- {_fmt_line(r)}" for r in debits_sorted) or "    (none)"
    top_credits = "\n    ".join(f"- {_fmt_line(r)}" for r in credits_sorted) or "    (none)"

    cat_lines = "\n    ".join(
        f"- {b['category']:>22}: {b['count']:>3} txns, debits ${b['debit_total']:>10,.2f}, credits ${b['credit_total']:>10,.2f}"
        for b in breakdown
    ) or "    (none)"

    return (
        f"From {fname}:\n"
        f"  Debits ({stats['count_debits']} lines): total ${stats['total_debits']:,.2f}\n"
        f"  Credits ({stats['count_credits']} lines): total ${stats['total_credits']:,.2f}\n"
        f"  Net (credits − debits): ${stats['net']:,.2f}\n"
        f"  Largest debit: {_fmt_line(stats['max_debit'])}\n"
        f"  Smallest debit: {_fmt_line(stats['min_debit'])}\n"
        f"  Largest credit: {_fmt_line(stats['max_credit'])}\n"
        f"  Smallest credit: {_fmt_line(stats['min_credit'])}\n"
        f"  Top 5 debits by amount:\n    {top_debits}\n"
        f"  Top 5 credits by amount:\n    {top_credits}\n"
        f"  By category:\n    {cat_lines}"
    )


def _facts_block_for_categories(
    db: Session, doc_id: int, fname: str, categories: set[str]
) -> str:
    s = txn_svc.stats_for_categories(db, doc_id, categories)
    cats = ", ".join(s["categories"])
    if s["count_total"] == 0:
        return f"From {fname}: no transactions matched categories [{cats}]."

    # List up to 20 lines (sorted by amount desc among debits, then credits)
    debits = sorted([r for r in s["lines"] if r.direction == "debit"], key=lambda r: -r.amount)
    credits_ = sorted([r for r in s["lines"] if r.direction == "credit"], key=lambda r: -r.amount)
    listing = (debits + credits_)[:20]
    listing_str = "\n    ".join(
        f"- {r.posted_date or '?'} {r.direction[:6]:>6} ${r.amount:>9,.2f} [{r.category}] {r.description}"
        for r in listing
    ) or "    (none)"

    extra = ""
    total_in_set = len(s["lines"])
    if total_in_set > 20:
        extra = f"\n    (+ {total_in_set - 20} more lines in this category set)"

    return (
        f"From {fname}, scoped to categories [{cats}]:\n"
        f"  Matching txns: {s['count_total']} total ({s['count_debits']} debits, {s['count_credits']} credits)\n"
        f"  Total debits (spend in this set): ${s['total_debits']:,.2f}\n"
        f"  Total credits (income in this set): ${s['total_credits']:,.2f}\n"
        f"  Largest debit: {_fmt_line(s['max_debit'])}\n"
        f"  Largest credit: {_fmt_line(s['max_credit'])}\n"
        f"  Lines (sorted by amount desc):\n    {listing_str}{extra}"
    )


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

        # If the question looks like an aggregate (or names a category like "food",
        # "subscriptions", "uber") AND any retrieved doc has parsed transactions,
        # prepend a deterministic facts block. Category questions get scoped facts;
        # general aggregates get the whole-doc summary with a category breakdown.
        precomputed = None
        category_intent = expand_category_query(payload.content)
        wants_facts = bool(_AGG_INTENT.search(payload.content) or category_intent)
        if wants_facts and hits:
            doc_ids_in_hits = list({h["document_id"] for h in hits})
            precomputed = _build_precomputed_facts(db, doc_ids_in_hits, payload.content)

        if hits:
            context = "\n\n".join(
                f"[{i+1}] {h['filename']} (chunk {h['ordinal']}):\n{h['chunk_text']}"
                for i, h in enumerate(hits)
            )
            # Order: excerpts first, then exact figures (so they're the most recent
            # context the LLM sees), then the question. LLMs attend more to recent
            # tokens, which makes them more likely to use the figures verbatim.
            parts = [f"Document excerpts:\n\n{context}"]
            if precomputed:
                parts.append(precomputed)
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
