import json
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
from app.services import ollama, retrieval

router = APIRouter(prefix="/api/chats", tags=["chat"])
settings = get_settings()


RAG_SYSTEM = (
    "You are a helpful assistant that answers questions strictly using the provided document excerpts. "
    "If the answer is not in the excerpts, say you don't know. Do NOT ask the user permission to "
    "do work — just do it.\n\n"
    "Cite excerpts inline using bracketed numbers like [1], [2] that match the excerpt order.\n\n"
    "Aggregate questions (largest/smallest/highest/lowest, total/sum, count, list/all of X):\n"
    "  1. Scan every excerpt. Extract every relevant line item with its amount and date into a list.\n"
    "  2. For 'largest/smallest', sort the list by amount (absolute value) and state the extreme.\n"
    "     Always cross-check: does any other line have a bigger absolute amount? Re-verify before answering.\n"
    "  3. For 'total/sum', list every item with a running total, then state the final sum.\n"
    "  4. Show your working so the user can verify.\n\n"
    "Financial vocabulary: distinguish credits (deposits, money in, '+', 'Credit') from debits "
    "(withdrawals, purchases, money out, '-', 'Debit'). 'Expense' / 'spend' / 'spent' = debits only. "
    "'Income' / 'received' = credits only. 'Largest transaction' = largest by absolute amount, "
    "regardless of direction."
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

        if hits:
            context = "\n\n".join(
                f"[{i+1}] {h['filename']} (chunk {h['ordinal']}):\n{h['chunk_text']}"
                for i, h in enumerate(hits)
            )
            user_block = f"Document excerpts:\n\n{context}\n\nQuestion: {payload.content}"
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
