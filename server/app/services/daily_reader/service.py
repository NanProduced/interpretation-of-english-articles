"""Daily Reader CRUD service."""

from __future__ import annotations

import logging
from datetime import date

import orjson

from app.database import connection as db_connection
from app.schemas.daily_reader import (
    DailyReaderArticleResponse,
    DailyReaderListItem,
    DailyReaderListResponse,
)

logger = logging.getLogger(__name__)


async def get_today_articles() -> list[DailyReaderArticleResponse]:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    today = date.today()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM daily_readers
            WHERE status = 'published' AND publish_date = $1
            ORDER BY score DESC
            """,
            today,
        )
    return [_row_to_article_response(row) for row in rows]


async def get_article_by_id(article_id: str) -> DailyReaderArticleResponse | None:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM daily_readers WHERE id = $1",
            article_id,
        )
    if row is None:
        return None
    return _row_to_article_response(row)


async def list_articles(
    cursor: str | None = None,
    limit: int = 10,
) -> DailyReaderListResponse:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    params: list[object] = [limit + 1]

    if cursor:
        params.append(cursor)
        query = """
            SELECT id, title, subtitle, source, publish_date, difficulty,
                   read_time_minutes, tags, cover_image_url, cover_theme
            FROM daily_readers
            WHERE status = 'published' AND publish_date < $2
            ORDER BY publish_date DESC
            LIMIT $1
        """
    else:
        query = """
            SELECT id, title, subtitle, source, publish_date, difficulty,
                   read_time_minutes, tags, cover_image_url, cover_theme
            FROM daily_readers
            WHERE status = 'published'
            ORDER BY publish_date DESC
            LIMIT $1
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    has_more = len(rows) > limit
    items = [_row_to_list_item(row) for row in rows[:limit]]

    next_cursor = None
    if has_more and items:
        next_cursor = str(items[-1].publish_date)

    return DailyReaderListResponse(items=items, cursor=next_cursor, has_more=has_more)


async def publish_article(article_id: str) -> bool:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE daily_readers
            SET status = 'published', published_at = NOW()
            WHERE id = $1 AND status = 'draft'
            """,
            article_id,
        )
    return result == "UPDATE 1"


async def unpublish_article(article_id: str) -> bool:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE daily_readers
            SET status = 'draft', published_at = NULL
            WHERE id = $1 AND status = 'published'
            """,
            article_id,
        )
    return result == "UPDATE 1"


async def delete_article(article_id: str) -> bool:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM daily_readers WHERE id = $1 AND status = 'draft'",
            article_id,
        )
    return result == "DELETE 1"


async def get_draft_articles(limit: int = 20) -> list[DailyReaderListItem]:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, subtitle, source, publish_date, difficulty,
                   read_time_minutes, tags, cover_image_url, cover_theme
            FROM daily_readers
            WHERE status = 'draft'
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [_row_to_list_item(row) for row in rows]


def _row_to_article_response(row: object) -> DailyReaderArticleResponse:
    return DailyReaderArticleResponse(
        id=row["id"],
        title=row["title"],
        subtitle=row["subtitle"],
        source=row["source"],
        source_url=row["source_url"],
        publish_date=row["publish_date"],
        difficulty=row["difficulty"],
        read_time_minutes=row["read_time_minutes"],
        tags=orjson.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
        cover_image_url=row["cover_image_url"],
        cover_theme=row["cover_theme"],
        body=orjson.loads(row["body_json"]) if isinstance(row["body_json"], str) else row["body_json"],
        highlights=orjson.loads(row["highlights_json"]) if isinstance(row["highlights_json"], str) else row["highlights_json"],
        footer_analysis=orjson.loads(row["footer_analysis_json"]) if isinstance(row["footer_analysis_json"], str) else row["footer_analysis_json"],
    )


def _row_to_list_item(row: object) -> DailyReaderListItem:
    return DailyReaderListItem(
        id=row["id"],
        title=row["title"],
        subtitle=row["subtitle"],
        source=row["source"],
        publish_date=row["publish_date"],
        difficulty=row["difficulty"],
        read_time_minutes=row["read_time_minutes"],
        tags=orjson.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
        cover_image_url=row["cover_image_url"],
        cover_theme=row["cover_theme"],
    )
