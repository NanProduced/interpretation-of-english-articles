"""Daily Reader user-facing API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.daily_reader import (
    DailyReaderArticleResponse,
    DailyReaderListResponse,
    DailyReaderTodayResponse,
)
from app.services.daily_reader.service import (
    get_article_by_id,
    get_today_articles,
    list_articles,
)

router = APIRouter(prefix="/daily-reader", tags=["daily-reader"])


@router.get("/today", response_model=DailyReaderTodayResponse)
async def today_articles() -> DailyReaderTodayResponse:
    articles = await get_today_articles()
    return DailyReaderTodayResponse(articles=articles)


@router.get("", response_model=DailyReaderListResponse)
async def article_list(
    cursor: str | None = None,
    limit: int = 10,
) -> DailyReaderListResponse:
    return await list_articles(cursor=cursor, limit=limit)


@router.get("/{article_id}", response_model=DailyReaderArticleResponse)
async def article_detail(article_id: str) -> DailyReaderArticleResponse:
    article = await get_article_by_id(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
