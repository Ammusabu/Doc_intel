"""RAG chat endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    ChatRequest, ChatResponse, ConversationDetail, ConversationOut, MessageOut,
)
from app.services.rag import RAGError, answer_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        conv_id, answer, citations, no_docs = await answer_question(
            db,
            user=current_user,
            question=body.message,
            embedder=request.app.state.embedder,
            reranker=request.app.state.reranker,
            conversation_id=body.conversation_id,
            top_k=body.top_k,
        )
    except RAGError as e:
        raise HTTPException(503, str(e))
    return ChatResponse(
        conversation_id=conv_id, answer=answer, citations=citations, no_relevant_docs=no_docs,
    )




import json as _json
from fastapi.responses import StreamingResponse

from app.services.rag import stream_groq, _retrieve
from app.services.prompts import build_rag_prompt
from app.models.conversation import Message as Msg


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select as _sel
    conv = None
    if body.conversation_id:
        conv = (await db.execute(
            _sel(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )).scalar_one_or_none()
    if conv is None:
        conv = Conversation(user_id=current_user.id, title=body.message[:80])
        db.add(conv)
        await db.flush()

    db.add(Msg(conversation_id=conv.id, role="user", content=body.message, citations=[]))
    await db.flush()

    hits = await _retrieve(
        db,
        user=current_user,
        query=body.message,
        embedder=request.app.state.embedder,
        reranker=request.app.state.reranker,
        top_k=body.top_k,
    )

    citations_payload = [
        {
            "chunk_id": str(h["chunk_id"]),
            "document_id": str(h["document_id"]),
            "document_title": h["document_title"],
            "page_number": h["page_number"],
            "excerpt": h["content"][:300],
        }
        for h in hits
    ]

    async def gen():
        yield f"event: meta\ndata: {_json.dumps({'conversation_id': str(conv.id), 'citations': citations_payload, 'no_relevant_docs': len(hits) == 0})}\n\n"

        if not hits:
            msg = "The provided documents do not contain enough information to answer this question."
            yield f"event: token\ndata: {_json.dumps({'t': msg})}\n\n"
            db.add(Msg(conversation_id=conv.id, role="assistant", content=msg, citations=[]))
            await db.commit()
            yield "event: done\ndata: {}\n\n"
            return

        prompt = build_rag_prompt(body.message, [
            {"title": h["document_title"], "page_number": h["page_number"], "content": h["content"]}
            for h in hits
        ])

        full = ""
        try:
            for token in stream_groq(prompt):
                full += token
                yield f"event: token\ndata: {_json.dumps({'t': token})}\n\n"
        except RAGError as e:
            yield f"event: error\ndata: {_json.dumps({'error': str(e)})}\n\n"
            return

        db.add(Msg(conversation_id=conv.id, role="assistant", content=full, citations=citations_payload))
        await db.commit()
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Conversation).where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )).scalars().all()
    return list(rows)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = (await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    )).scalar_one_or_none()
    if conv is None:
        raise HTTPException(404, "conversation not found")
    return ConversationDetail(
        conversation=ConversationOut.model_validate(conv),
        messages=[MessageOut.model_validate(m) for m in conv.messages],
    )


from pydantic import BaseModel as _BM


class RenameBody(_BM):
    title: str


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: RenameBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = (await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if conv is None:
        raise HTTPException(404, "conversation not found")
    conv.title = body.title[:255]
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = (await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if conv is None:
        raise HTTPException(404, "conversation not found")
    await db.delete(conv)
    await db.commit()
