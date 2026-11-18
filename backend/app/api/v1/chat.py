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
