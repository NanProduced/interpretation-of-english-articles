"""Daily Reader admin API routes."""

from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header

from app.config.settings import get_settings
from app.schemas.daily_reader import (
    ArticleActionResponse,
    DailyReaderGenerateRequest,
    DailyReaderGenerateResponse,
    DailyReaderListItem,
    DailyReaderListResponse,
    DailyReaderPublishRequest,
    DailyReaderRetryRequest,
    DailyReaderUnpublishRequest,
    RetryWorkflowResponse,
)
from app.services.daily_reader import service

logger = logging.getLogger("app.api")

router = APIRouter(prefix="/daily-reader/admin", tags=["daily-reader-admin"])


async def verify_admin_api_key(x_admin_api_key: str = Header(...)) -> str:
    settings = get_settings()
    if not settings.daily_reader_admin_api_key:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if not secrets.compare_digest(x_admin_api_key, settings.daily_reader_admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return x_admin_api_key


@router.post("/generate", response_model=DailyReaderGenerateResponse)
async def generate_articles(
    request: DailyReaderGenerateRequest,
    _auth: str = Depends(verify_admin_api_key),
) -> DailyReaderGenerateResponse:
    from app.services.daily_reader.pipeline import run_daily_pipeline

    task_id = f"dr_gen_{uuid.uuid4().hex[:8]}"

    try:
        result = await run_daily_pipeline(
            max_count=request.max_count,
            force=request.force,
        )
        return DailyReaderGenerateResponse(
            task_id=task_id,
            status="completed",
            message=f"Generated {len(result.articles)} articles, {len(result.errors)} errors",
        )
    except Exception as e:
        logger.error("generate_articles pipeline failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Pipeline execution failed",
        ) from e


@router.post("/publish", response_model=ArticleActionResponse)
async def publish_article(
    request: DailyReaderPublishRequest,
    _auth: str = Depends(verify_admin_api_key),
) -> dict:
    success = await service.publish_article(request.id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found or not in draft status")
    return {"status": "published"}


@router.post("/unpublish", response_model=ArticleActionResponse)
async def unpublish_article(
    request: DailyReaderUnpublishRequest,
    _auth: str = Depends(verify_admin_api_key),
) -> dict:
    success = await service.unpublish_article(request.id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found or not published")
    return {"status": "unpublished"}


@router.delete("/{article_id}", response_model=ArticleActionResponse)
async def delete_article(
    article_id: str,
    _auth: str = Depends(verify_admin_api_key),
) -> dict:
    success = await service.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found or not in draft status")
    return {"status": "deleted"}


@router.get("/drafts", response_model=DailyReaderListResponse)
async def list_drafts(
    limit: int = 20,
    _auth: str = Depends(verify_admin_api_key),
) -> DailyReaderListResponse:
    items = await service.get_draft_articles(limit=limit)
    return DailyReaderListResponse(items=items, has_more=False)


@router.post("/retry", response_model=RetryWorkflowResponse)
async def retry_workflow(
    request: DailyReaderRetryRequest,
    _auth: str = Depends(verify_admin_api_key),
) -> dict:
    article = await service.get_article_by_id(request.id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"status": "retry_not_implemented", "message": "Retry workflow will be implemented in future iteration"}
