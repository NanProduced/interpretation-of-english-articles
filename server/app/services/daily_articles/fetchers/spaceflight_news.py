"""
SpaceFlight News API fetcher.

Fetches articles from https://api.spaceflightnewsapi.net/
This is a free API that provides space-related news articles.
"""

from __future__ import annotations

from datetime import date, datetime
from logging import getLogger
from typing import Any

import httpx

from app.services.daily_articles.fetchers.base import ArticleFetcher, RawArticle

logger = getLogger(__name__)

SPACEFLIGHT_NEWS_API_BASE = "https://api.spaceflightnewsapi.net/v4"


class SpaceflightNewsFetcher(ArticleFetcher):
    """Fetcher for SpaceFlight News API."""

    def __init__(self, api_base: str | None = None, timeout: int = 30):
        self.api_base = api_base or SPACEFLIGHT_NEWS_API_BASE
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "spaceflight_news"

    async def fetch_latest_articles(self, limit: int = 20) -> list[RawArticle]:
        """Fetch latest articles from SpaceFlight News API."""
        articles: list[RawArticle] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params: dict[str, Any] = {
                    "limit": min(limit, 100),
                    "ordering": "-published_at",
                }

                response = await client.get(
                    f"{self.api_base}/articles/",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                for item in results:
                    raw_article = self._parse_article(item)
                    if raw_article:
                        articles.append(raw_article)

                logger.info(
                    "Fetched %d articles from SpaceFlight News API",
                    len(articles),
                )

        except httpx.HTTPError as e:
            logger.error("HTTP error fetching from SpaceFlight News: %s", e)
            raise
        except Exception as e:
            logger.error("Error fetching from SpaceFlight News: %s", e)
            raise

        return articles

    async def fetch_article_by_id(self, source_id: str) -> RawArticle | None:
        """Fetch a single article by ID from SpaceFlight News API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base}/articles/{source_id}/",
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return self._parse_article(data)

        except httpx.HTTPError as e:
            logger.error("HTTP error fetching article %s: %s", source_id, e)
            return None
        except Exception as e:
            logger.error("Error fetching article %s: %s", source_id, e)
            return None

    def _parse_article(self, data: dict[str, Any]) -> RawArticle | None:
        """Parse API response into RawArticle."""
        try:
            source_id = str(data.get("id", ""))
            if not source_id:
                return None

            title = data.get("title", "")
            if not title:
                return None

            content = data.get("summary", "") or data.get("description", "")
            if not content:
                return None

            source_url = data.get("url", "")
            if not source_url:
                return None

            image_url = data.get("image_url")

            publish_date: date | None = None
            published_at = data.get("published_at")
            if published_at:
                try:
                    if isinstance(published_at, str):
                        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        publish_date = dt.date()
                except (ValueError, TypeError):
                    pass

            category = data.get("news_site")

            tags: list[str] = []
            launches = data.get("launches", [])
            if launches:
                for launch in launches:
                    if launch.get("name"):
                        tags.append(launch["name"])

            events = data.get("events", [])
            if events:
                for event in events:
                    if event.get("name"):
                        tags.append(event["name"])

            source_metadata: dict[str, Any] = {
                "news_site": data.get("news_site"),
                "featured": data.get("featured"),
                "launches": launches,
                "events": events,
            }

            return RawArticle(
                source_id=source_id,
                title=title,
                content=content,
                source_url=source_url,
                image_url=image_url,
                publish_date=publish_date,
                category=category,
                tags=tags,
                source_metadata=source_metadata,
            )

        except Exception as e:
            logger.warning("Failed to parse article: %s", e)
            return None
