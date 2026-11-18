from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_status = "down"
    try:
        await db.execute(text("SELECT 1;"))
        db_status = "up"
    except Exception:
        db_status = "down"
    return HealthResponse(status="ok", database=db_status, version="0.1.0")
