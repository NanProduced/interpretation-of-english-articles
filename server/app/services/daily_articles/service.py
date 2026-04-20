"""
Daily articles service.

Handles database operations, article fetching, cleaning, and validation.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from logging import getLogger
from typing import Any
from uuid import UUID

import asyncpg

from app.database.connection import acquire_connection
from app.schemas.daily_articles import (
    DailyArticle,
    DailyArticleFetchLog,
    DailyArticleSummary,
    FetchStatistics,
    FetchStatus,
)
from app.services.daily_articles.cleaner import ArticleCleaner, CleanedArticle
from app.services.daily_articles.fetchers.base import ArticleFetcher, RawArticle
from app.services.daily_articles.fetchers.spaceflight_news import SpaceflightNewsFetcher

logger = getLogger(__name__)

MIN_ARTICLES_PER_DAY = 5
FETCH_BATCH_SIZE = 30


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    status: FetchStatus
    articles_fetched: int
    articles_valid: int
    articles_saved: int
    error_message: str | None = None
    duration_ms: int | None = None
    saved_articles: list[DailyArticle] | None = None


class DailyArticleService:
    """Service for managing daily articles."""

    def __init__(
        self,
        fetchers: list[ArticleFetcher] | None = None,
        cleaner: ArticleCleaner | None = None,
        min_articles: int = MIN_ARTICLES_PER_DAY,
    ):
        self.fetchers = fetchers or [SpaceflightNewsFetcher()]
        self.cleaner = cleaner or ArticleCleaner()
        self.min_articles = min_articles

    async def get_today_articles(self) -> list[DailyArticleSummary]:
        """Get all active articles for today."""
        today = date.today()
        return await self.get_articles_by_date(today)

    async def get_articles_by_date(self, fetch_date: date) -> list[DailyArticleSummary]:
        """Get all active articles for a specific date."""
        async with acquire_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, source_provider, title, content_word_count,
                       source_url, image_url, publish_date, fetch_date,
                       category, tags, created_at
                FROM daily_articles
                WHERE fetch_date = $1 AND status = 'active'
                ORDER BY created_at DESC
                """,
                fetch_date,
            )

            return [
                DailyArticleSummary(
                    id=row["id"],
                    source_provider=row["source_provider"],
                    title=row["title"],
                    content_word_count=row["content_word_count"],
                    source_url=row["source_url"],
                    image_url=row["image_url"],
                    publish_date=row["publish_date"],
                    fetch_date=row["fetch_date"],
                    category=row["category"],
                    tags=row["tags"] or [],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    async def get_article_by_id(self, article_id: UUID) -> DailyArticle | None:
        """Get a single article by ID."""
        async with acquire_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, source_provider, source_id, title, content,
                       content_word_count, source_url, image_url, publish_date,
                       fetch_date, language, category, tags, status,
                       created_at, updated_at
                FROM daily_articles
                WHERE id = $1
                """,
                article_id,
            )

            if not row:
                return None

            return DailyArticle(
                id=row["id"],
                source_provider=row["source_provider"],
                source_id=row["source_id"],
                title=row["title"],
                content=row["content"],
                content_word_count=row["content_word_count"],
                source_url=row["source_url"],
                image_url=row["image_url"],
                publish_date=row["publish_date"],
                fetch_date=row["fetch_date"],
                language=row["language"],
                category=row["category"],
                tags=row["tags"] or [],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def article_exists(self, source_provider: str, source_id: str) -> bool:
        """Check if an article already exists in the database."""
        async with acquire_connection() as conn:
            result = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM daily_articles
                    WHERE source_provider = $1 AND source_id = $2
                )
                """,
                source_provider,
                source_id,
            )
            return bool(result)

    async def save_article(
        self,
        raw_article: RawArticle,
        cleaned: CleanedArticle,
        provider_name: str,
    ) -> DailyArticle | None:
        """Save a cleaned article to the database."""
        if await self.article_exists(provider_name, raw_article.source_id):
            logger.debug(
                "Article already exists: provider=%s, source_id=%s",
                provider_name,
                raw_article.source_id,
            )
            return None

        async with acquire_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO daily_articles (
                    source_provider, source_id, title, content,
                    content_word_count, source_url, image_url,
                    publish_date, fetch_date, language, category,
                    tags, source_metadata_json, status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 'active')
                RETURNING id, created_at, updated_at
                """,
                provider_name,
                raw_article.source_id,
                cleaned.title,
                cleaned.content,
                cleaned.word_count,
                raw_article.source_url,
                raw_article.image_url,
                raw_article.publish_date,
                date.today(),
                "en",
                raw_article.category,
                raw_article.tags,
                raw_article.source_metadata,
            )

            if not row:
                return None

            return DailyArticle(
                id=row["id"],
                source_provider=provider_name,
                source_id=raw_article.source_id,
                title=cleaned.title,
                content=cleaned.content,
                content_word_count=cleaned.word_count,
                source_url=raw_article.source_url,
                image_url=raw_article.image_url,
                publish_date=raw_article.publish_date,
                fetch_date=date.today(),
                language="en",
                category=raw_article.category,
                tags=raw_article.tags,
                status="active",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def log_fetch_operation(
        self,
        source_provider: str,
        status: FetchStatus,
        articles_fetched: int,
        articles_valid: int,
        articles_saved: int,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> DailyArticleFetchLog:
        """Log a fetch operation."""
        async with acquire_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO daily_article_fetch_logs (
                    fetch_date, source_provider, status,
                    articles_fetched, articles_valid, articles_saved,
                    error_message, duration_ms
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, fetch_date, source_provider, status,
                          articles_fetched, articles_valid, articles_saved,
                          error_message, duration_ms, created_at
                """,
                date.today(),
                source_provider,
                status,
                articles_fetched,
                articles_valid,
                articles_saved,
                error_message,
                duration_ms,
            )

            if not row:
                raise RuntimeError("Failed to log fetch operation")

            return DailyArticleFetchLog(
                id=row["id"],
                fetch_date=row["fetch_date"],
                source_provider=row["source_provider"],
                status=row["status"],
                articles_fetched=row["articles_fetched"],
                articles_valid=row["articles_valid"],
                articles_saved=row["articles_saved"],
                error_message=row["error_message"],
                duration_ms=row["duration_ms"],
                created_at=row["created_at"],
            )

    async def fetch_and_save_articles(
        self,
        max_articles: int = 10,
        batch_size: int = FETCH_BATCH_SIZE,
    ) -> FetchResult:
        """
        Fetch articles from all providers, clean them, and save valid ones.

        Args:
            max_articles: Maximum number of articles to save
            batch_size: Number of articles to fetch per provider

        Returns:
            FetchResult with statistics
        """
        start_time = datetime.now()
        total_fetched = 0
        total_valid = 0
        total_saved = 0
        saved_articles: list[DailyArticle] = []
        error_message: str | None = None

        try:
            for fetcher in self.fetchers:
                if total_saved >= max_articles:
                    break

                logger.info("Fetching from provider: %s", fetcher.provider_name)

                try:
                    raw_articles = await fetcher.fetch_latest_articles(limit=batch_size)
                    total_fetched += len(raw_articles)

                    for raw_article in raw_articles:
                        if total_saved >= max_articles:
                            break

                        if not raw_article.content:
                            continue

                        cleaned = self.cleaner.clean_and_validate(
                            raw_article.title,
                            raw_article.content,
                        )

                        if not cleaned.is_valid:
                            logger.debug(
                                "Article invalid: provider=%s, id=%s, "
                                "is_english=%s, word_count=%d",
                                fetcher.provider_name,
                                raw_article.source_id,
                                cleaned.is_english,
                                cleaned.word_count,
                            )
                            continue

                        total_valid += 1

                        saved = await self.save_article(
                            raw_article,
                            cleaned,
                            fetcher.provider_name,
                        )

                        if saved:
                            total_saved += 1
                            saved_articles.append(saved)
                            logger.info(
                                "Saved article: provider=%s, id=%s, word_count=%d",
                                fetcher.provider_name,
                                raw_article.source_id,
                                cleaned.word_count,
                            )

                except Exception as e:
                    logger.error(
                        "Error fetching from provider %s: %s",
                        fetcher.provider_name,
                        e,
                    )
                    error_message = str(e)

        except Exception as e:
            logger.error("Fetch operation failed: %s", e)
            error_message = str(e)

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        if total_saved >= self.min_articles:
            status: FetchStatus = "success"
        elif total_saved > 0:
            status = "partial"
        else:
            status = "failed"

        await self.log_fetch_operation(
            source_provider="combined" if len(self.fetchers) > 1 else self.fetchers[0].provider_name,
            status=status,
            articles_fetched=total_fetched,
            articles_valid=total_valid,
            articles_saved=total_saved,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        return FetchResult(
            status=status,
            articles_fetched=total_fetched,
            articles_valid=total_valid,
            articles_saved=total_saved,
            error_message=error_message,
            duration_ms=duration_ms,
            saved_articles=saved_articles if saved_articles else None,
        )

    async def get_fetch_statistics(self, fetch_date: date | None = None) -> FetchStatistics:
        """Get fetch statistics for a specific date."""
        target_date = fetch_date or date.today()

        async with acquire_connection() as conn:
            article_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM daily_articles
                WHERE fetch_date = $1 AND status = 'active'
                """,
                target_date,
            )

            fetch_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM daily_article_fetch_logs
                WHERE fetch_date = $1
                """,
                target_date,
            )

            last_fetch = await conn.fetchrow(
                """
                SELECT status, created_at
                FROM daily_article_fetch_logs
                WHERE fetch_date = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                target_date,
            )

            return FetchStatistics(
                date=target_date,
                total_articles=int(article_count or 0),
                total_fetches=int(fetch_count or 0),
                last_fetch_status=last_fetch["status"] if last_fetch else None,
                last_fetch_at=last_fetch["created_at"] if last_fetch else None,
            )
