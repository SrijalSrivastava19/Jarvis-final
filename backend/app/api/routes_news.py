"""News routes — GET /api/news/{category}"""
from fastapi import APIRouter
from app.models.schemas import NewsResponse
from app.services.news_service import news_service

router = APIRouter(prefix="/api/news", tags=["news"])

VALID_CATEGORIES = ["top", "world", "technology", "ai", "sports", "science", "business", "india"]

@router.get("/{category}", response_model=NewsResponse)
async def get_news(category: str = "top") -> NewsResponse:
    """Fetch latest headlines for a category. Cached for 5 minutes."""
    return await news_service.get_news(category)

@router.get("", response_model=NewsResponse)
async def get_top_news() -> NewsResponse:
    return await news_service.get_news("top")
