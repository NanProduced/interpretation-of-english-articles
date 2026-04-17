"""
Web article content scraper.

Fetches full article content from URLs when the summary is too short.
"""

from __future__ import annotations

import re
from logging import getLogger
from typing import Any

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

logger = getLogger(__name__)


class WebContentScraper:
    """Scraper for extracting article content from web pages."""

    def __init__(self, timeout: int = 15, max_content_length: int = 50000):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def scrape_article(self, url: str) -> str | None:
        """
        Scrape article content from a URL.

        Args:
            url: The article URL to scrape

        Returns:
            Extracted article text or None if failed
        """
        if not url:
            return None

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            ) as client:
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.warning("URL is not HTML: %s (content-type: %s)", url, content_type)
                    return None

                html_content = response.text
                if len(html_content) > self.max_content_length:
                    logger.warning(
                        "Content too large: %d bytes (max: %d)",
                        len(html_content),
                        self.max_content_length,
                    )
                    html_content = html_content[: self.max_content_length]

                article_text = self._extract_article_content(html_content)

                if article_text and len(article_text.strip()) > 100:
                    return article_text
                else:
                    logger.warning("Failed to extract meaningful content from %s", url)
                    return None

        except httpx.HTTPError as e:
            logger.warning("HTTP error scraping %s: %s", url, e)
            return None
        except Exception as e:
            logger.error("Error scraping %s: %s", url, e, exc_info=True)
            return None

    def _extract_article_content(self, html: str) -> str:
        """
        Extract article content from HTML.

        Uses multiple strategies to find the main article content.
        """
        soup = BeautifulSoup(html, "html.parser")

        for unwanted in soup(
            ["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]
        ):
            unwanted.decompose()

        for unwanted in soup.find_all(class_=re.compile(r"nav|header|footer|sidebar|comment|related|social|share|ad-")):
            unwanted.decompose()

        for unwanted in soup.find_all(id=re.compile(r"nav|header|footer|sidebar|comment|related|social|ad-")):
            unwanted.decompose()

        article_selectors = [
            "article",
            'div[itemprop="articleBody"]',
            'div[class*="article-body"]',
            'div[class*="article-content"]',
            'div[class*="post-content"]',
            'div[class*="entry-content"]',
            'div[class*="main-content"]',
            'div[class*="story-content"]',
            ".article-body",
            ".article-content",
            ".post-content",
            ".entry-content",
            "main",
        ]

        for selector in article_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = self._extract_text_from_element(element)
                if len(text.split()) > 100:
                    return text

        paragraphs = soup.find_all("p")
        content_parts: list[str] = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text.split()) > 10:
                content_parts.append(text)

        if content_parts:
            return "\n\n".join(content_parts)

        body = soup.find("body")
        if body:
            return self._extract_text_from_element(body)

        return ""

    def _extract_text_from_element(self, element: Tag) -> str:
        """Extract clean text from a BeautifulSoup element."""
        text_parts: list[str] = []

        for child in element.descendants:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    text_parts.append(text)
            elif child.name in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"]:
                text_parts.append("\n")

        text = " ".join(text_parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = text.strip()

        return text
