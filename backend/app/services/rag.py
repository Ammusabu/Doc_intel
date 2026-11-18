"""RAG pipeline: retrieval → prompt → Groq → citation validation."""
from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import Citation
from app.services.prompts import build_rag_prompt
from app.services.retrieval.dense import dense_search
from app.services.retrieval.hybrid import reciprocal_rank_fusion
from app.services.retrieval.keyword import keyword_search
from app.services.retrieval.rerank import rerank_results
from app.ml.embedder import Embedder
from app.ml.reranker import Reranker

log = logging.getLogger("docintel.rag")
settings = get_settings()


class RAGError(Exception):
    pass


async def _retrieve(
    db: AsyncSession,
    *,
    user: User,
    query: str,
    embedder: Embedder,
    reranker: Reranker,
    top_k: int,
) -> list[dict]:
    dense = await dense_search(db, embedder=embedder, query=query, owner_id=user.id, top_k=30)
    keyword = await keyword_search(db, query=query, owner_id=user.id, top_k=30)
    fused = reciprocal_rank_fusion(dense, keyword, k=60)
    if not fused:
        return []
    return rerank_results(reranker, query, fused, top_k=top_k)


def _call_groq(prompt: str, model: str = "openai/gpt-oss-20b") -> str:
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.1,
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RAGError(f"Groq {r.status_code}: {r.text[:300]}")
    content = r.json()["choices"][0]["message"]["content"].strip()
    if not content and model != "llama-3.3-70b-versatile":
        return _call_groq(prompt, model="llama-3.3-70b-versatile")
    return content


async def answer_question(
    db: AsyncSession,
    *,
    user: User,
    question: str,
    embedder: Embedder,
    reranker: Reranker,
    conversation_id: uuid.UUID | None,
    top_k: int = 5,
) -> tuple[uuid.UUID, str, list[Citation], bool]:
    conv = None
    if conversation_id:
        conv = (await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )).scalar_one_or_none()
    if conv is None:
        conv = Conversation(user_id=user.id, title=question[:80])
        db.add(conv)
        await db.flush()

    db.add(Message(conversation_id=conv.id, role="user", content=question, citations=[]))
    await db.flush()

    hits = await _retrieve(db, user=user, query=question, embedder=embedder,
                           reranker=reranker, top_k=top_k)

    if not hits:
        answer = "The provided documents do not contain enough information to answer this question."
        citations: list[Citation] = []
        no_docs = True
    else:
        prompt = build_rag_prompt(question, [
            {"title": h["document_title"], "page_number": h["page_number"], "content": h["content"]}
            for h in hits
        ])
        answer = _call_groq(prompt)
        citations = [
            Citation(
                chunk_id=h["chunk_id"],
                document_id=h["document_id"],
                document_title=h["document_title"],
                page_number=h["page_number"],
                excerpt=h["content"][:200],
            )
            for h in hits
        ]
        no_docs = False

    db.add(Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        citations=[c.model_dump(mode="json") for c in citations],
    ))
    await db.commit()
    return conv.id, answer, citations, no_docs
