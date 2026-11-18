"""Aggregated analytics for the frontend dashboard."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.search import SearchHistory
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ---- Document analytics ----
    docs = (await db.execute(
        select(Document).where(Document.owner_id == current_user.id)
    )).scalars().all()

    total_docs = len(docs)
    completed = sum(1 for d in docs if d.status == "completed")
    processing = sum(1 for d in docs if d.status in ("pending", "processing"))
    failed = sum(1 for d in docs if d.status == "failed")

    category_counts = Counter(d.predicted_category for d in docs if d.predicted_category)
    category_distribution = [
        {"name": k, "value": v} for k, v in sorted(category_counts.items(), key=lambda x: -x[1])
    ]

    # upload trend last 14 days
    today = datetime.now(timezone.utc).date()
    trend: dict[str, int] = {}
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        trend[day.isoformat()] = 0
    for d in docs:
        day = d.created_at.date().isoformat()
        if day in trend:
            trend[day] += 1
    upload_trend = [{"date": k, "uploads": v} for k, v in trend.items()]

    # ---- DL performance (based on document predictions) ----
    confs = [d.classification_confidence for d in docs if d.classification_confidence is not None]
    avg_conf = sum(confs) / len(confs) if confs else 0.0

    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.001]
    labels = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]
    conf_hist = {lbl: 0 for lbl in labels}
    for c in confs:
        for i in range(5):
            if bins[i] <= c < bins[i + 1]:
                conf_hist[labels[i]] += 1
                break
    confidence_distribution = [{"bucket": k, "count": v} for k, v in conf_hist.items()]

    # category-wise average confidence
    cat_conf: dict[str, list[float]] = defaultdict(list)
    for d in docs:
        if d.predicted_category and d.classification_confidence is not None:
            cat_conf[d.predicted_category].append(d.classification_confidence)
    category_confidence = [
        {"category": k, "avg": round(sum(v) / len(v), 3), "count": len(v)}
        for k, v in sorted(cat_conf.items())
    ]

    # ---- Retrieval analytics ----
    search_count = (await db.execute(
        select(func.count(SearchHistory.id)).where(SearchHistory.user_id == current_user.id)
    )).scalar_one() or 0

    avg_search_latency = (await db.execute(
        select(func.avg(SearchHistory.latency_ms)).where(SearchHistory.user_id == current_user.id)
    )).scalar() or 0.0

    chunk_count = (await db.execute(
        select(func.count(DocumentChunk.id))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.owner_id == current_user.id)
    )).scalar_one() or 0

    # ---- RAG analytics ----
    conv_ids = (await db.execute(
        select(Conversation.id).where(Conversation.user_id == current_user.id)
    )).scalars().all()

    total_questions = 0
    questions_with_citations = 0
    no_relevant = 0
    if conv_ids:
        messages = (await db.execute(
            select(Message).where(Message.conversation_id.in_(conv_ids))
        )).scalars().all()
        for m in messages:
            if m.role == "user":
                total_questions += 1
            elif m.role == "assistant":
                if m.citations:
                    questions_with_citations += 1
                else:
                    no_relevant += 1

    return {
        "documents": {
            "total": total_docs,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "success_rate": round(completed / (completed + failed) * 100, 1) if (completed + failed) > 0 else 0,
            "category_distribution": category_distribution,
            "upload_trend": upload_trend,
        },
        "dl_performance": {
            "avg_confidence": round(avg_conf, 4),
            "confidence_distribution": confidence_distribution,
            "category_confidence": category_confidence,
        },
        "retrieval": {
            "total_searches": search_count,
            "avg_latency_ms": round(float(avg_search_latency), 1),
            "total_chunks_retrievable": chunk_count,
        },
        "rag": {
            "total_questions": total_questions,
            "questions_with_citations": questions_with_citations,
            "no_relevant_docs": no_relevant,
            "citation_rate": round(questions_with_citations / total_questions * 100, 1) if total_questions else 0,
        },
    }
