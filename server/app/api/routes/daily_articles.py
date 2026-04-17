"""
Daily Articles API Routes.

Endpoints for:
- GET /daily-articles/today - Get today's articles
- GET /daily-articles/{id} - Get a single article
- POST /daily-articles/fetch - Manually trigger a fetch
- GET /daily-articles/stats - Get fetch statistics
"""

from __future__ import annotations

from datetime import date
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.daily_articles import (
    DailyArticle,
    DailyArticleFetchLog,
    DailyArticleSummary,
    FetchStatus,
    GetArticleResponse,
    GetFetchStatsResponse,
    GetTodayArticlesResponse,
    ManualFetchTriggerResponse,
)
from app.services.daily_articles.service import DailyArticleService, FetchResult

logger = getLogger("app.api")

router = APIRouter(prefix="/daily-articles", tags=["daily-articles"])


def get_daily_article_service() -> DailyArticleService:
    """Get or create the daily article service instance."""
    return DailyArticleService()


@router.get("/today", response_model=GetTodayArticlesResponse)
async def get_today_articles() -> GetTodayArticlesResponse:
    """
    Get all active daily articles for today.

    Returns today's articles that are ready for the "每日精读" feature.
    """
    service = get_daily_article_service()
    articles = await service.get_today_articles()

    return GetTodayArticlesResponse(
        date=date.today(),
        articles=articles,
        total_count=len(articles),
    )


@router.get("/date/{target_date}", response_model=GetTodayArticlesResponse)
async def get_articles_by_date(
    target_date: date,
) -> GetTodayArticlesResponse:
    """
    Get articles for a specific date.

    Args:
        target_date: Date in YYYY-MM-DD format
    """
    service = get_daily_article_service()
    articles = await service.get_articles_by_date(target_date)

    return GetTodayArticlesResponse(
        date=target_date,
        articles=articles,
        total_count=len(articles),
    )


@router.get("/{article_id}", response_model=GetArticleResponse)
async def get_article(article_id: UUID) -> GetArticleResponse:
    """
    Get a single article by ID with full content.

    Args:
        article_id: UUID of the article
    """
    service = get_daily_article_service()
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return GetArticleResponse(article=article)


@router.post("/fetch", response_model=ManualFetchTriggerResponse)
async def trigger_manual_fetch(
    max_articles: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of articles to fetch and save",
    ),
) -> ManualFetchTriggerResponse:
    """
    Manually trigger an article fetch operation.

    This endpoint allows administrators to manually trigger a fetch
    instead of waiting for the scheduled daily run at 9:00 AM UTC+8.

    Args:
        max_articles: Maximum number of articles to save (default 10)

    Returns:
        Result of the fetch operation including statistics
    """
    service = get_daily_article_service()

    logger.info("Manual fetch triggered, max_articles=%d", max_articles)

    try:
        result = await service.fetch_and_save_articles(max_articles=max_articles)

        message = (
            f"Fetch completed: saved {result.articles_saved} articles "
            f"(fetched: {result.articles_fetched}, valid: {result.articles_valid})"
        )

        fetch_log: DailyArticleFetchLog | None = None
        if result.duration_ms is not None:
            fetch_log = DailyArticleFetchLog(
                id=UUID(int=0),
                fetch_date=date.today(),
                source_provider="combined",
                status=result.status,
                articles_fetched=result.articles_fetched,
                articles_valid=result.articles_valid,
                articles_saved=result.articles_saved,
                error_message=result.error_message,
                duration_ms=result.duration_ms,
                created_at=date.today(),
            )

        return ManualFetchTriggerResponse(
            success=result.status in ("success", "partial"),
            message=message,
            fetch_log=fetch_log,
        )

    except Exception as e:
        logger.error("Manual fetch failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")


@router.get("/stats", response_model=GetFetchStatsResponse)
async def get_fetch_stats(
    target_date: date | None = Query(
        default=None,
        description="Date to get stats for (defaults to today)",
    ),
) -> GetFetchStatsResponse:
    """
    Get fetch statistics for a specific date.

    Returns:
        Statistics including article count, fetch count, and last fetch status
    """
    service = get_daily_article_service()
    stats = await service.get_fetch_statistics(target_date)

    return GetFetchStatsResponse(stats=stats)
