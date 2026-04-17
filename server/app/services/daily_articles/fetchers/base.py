"""
Base article fetcher interface.

Defines the abstract base class for all article fetchers from external sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class RawArticle:
    """Raw article data fetched from external source."""

    source_id: str
    title: str
    content: str
    source_url: str
    image_url: str | None = None
    publish_date: date | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    source_metadata: dict[str, Any] = field(default_factory=dict)


class ArticleFetcher(ABC):
    """Abstract base class for article fetchers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'spaceflight_news')."""
        pass

    @abstractmethod
    async def fetch_latest_articles(self, limit: int = 20) -> list[RawArticle]:
        """
        Fetch latest articles from the source.

        Args:
            limit: Maximum number of articles to fetch.

        Returns:
            List of raw articles.
        """
        pass

    @abstractmethod
    async def fetch_article_by_id(self, source_id: str) -> RawArticle | None:
        """
        Fetch a single article by its source ID.

        Args:
            source_id: The article ID from the source.

        Returns:
            Raw article or None if not found.
        """
        pass
