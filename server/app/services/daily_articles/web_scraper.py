"""
Web article content scraper using trafilatura.

trafilatura is a powerful library for extracting text from web pages,
handling boilerplate removal, navigation, ads, etc. automatically.
"""

from __future__ import annotations

from logging import getLogger
from typing import Any

import httpx
from trafilatura import extract
from trafilatura.settings import use_config

logger = getLogger(__name__)


class WebContentScraper:
    """Scraper for extracting article content from web pages using trafilatura."""

    def __init__(
        self,
        timeout: int = 30,
        max_content_length: int = 100000,
        include_images: bool = False,
        include_links: bool = False,
        include_tables: bool = True,
    ):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.include_images = include_images
        self.include_links = include_links
        self.include_tables = include_tables

        self._trafilatura_config = use_config()
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def scrape_article(self, url: str) -> str | None:
        """
        Scrape article content from a URL using trafilatura.

        Args:
            url: The article URL to scrape

        Returns:
            Extracted article text or None if failed
        """
        if not url:
            return None

        try:
            html_content = await self._fetch_html(url)
            if not html_content:
                return None

            article_text = self._extract_with_trafilatura(html_content, url)

            if article_text and len(article_text.strip()) > 100:
                logger.info(
                    "Successfully extracted %d characters from %s",
                    len(article_text),
                    url,
                )
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

    async def _fetch_html(self, url: str) -> str | None:
        """Fetch HTML content from URL."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            ) as client:
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.warning(
                        "URL is not HTML: %s (content-type: %s)",
                        url,
                        content_type,
                    )
                    return None

                html_content = response.text
                if len(html_content) > self.max_content_length:
                    logger.warning(
                        "Content too large: %d bytes (max: %d), truncating",
                        len(html_content),
                        self.max_content_length,
                    )
                    html_content = html_content[: self.max_content_length]

                return html_content

        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching %s: %s", url, e)
            return None

    def _extract_with_trafilatura(self, html_content: str, url: str | None = None) -> str | None:
        """
        Extract article content using trafilatura.

        trafilatura automatically:
        - Removes boilerplate (headers, footers, navigation)
        - Removes ads and irrelevant sections
        - Extracts main article content
        - Handles different website structures
        """
        try:
            extracted = extract(
                html_content,
                url=url,
                no_fallback=True,
                include_links=self.include_links,
                include_images=self.include_images,
                include_tables=self.include_tables,
                include_comments=False,
                output_format="txt",
                config=self._trafilatura_config,
            )

            if extracted:
                return self._clean_extracted_text(extracted)
            else:
                return None

        except Exception as e:
            logger.error("trafilatura extraction error: %s", e, exc_info=True)
            return None

    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""

        lines = text.split("\n")
        cleaned_lines: list[str] = []
        skip_next = False

        for i, line in enumerate(lines):
            line = line.strip()

            if not line:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                continue

            if self._is_boilerplate_line(line):
                continue

            if self._is_update_line(line):
                continue

            if self._is_byline(line) and i < 5:
                continue

            cleaned_lines.append(line)

        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)

        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        result = "\n".join(cleaned_lines)

        import re

        result = re.sub(r"\n{3,}", "\n\n", result)
        result = re.sub(r"[ \t]+", " ", result)
        result = result.strip()

        return result

    def _is_boilerplate_line(self, line: str) -> bool:
        """Check if line is boilerplate that should be removed."""
        lower_line = line.lower()

        boilerplate_patterns = [
            "share this article",
            "share on facebook",
            "share on twitter",
            "share on linkedin",
            "email to",
            "print this",
            "comments",
            "related articles",
            "read more",
            "also read",
            "see also",
            "subscribe",
            "newsletter",
            "advertisement",
            "ad -",
            "continue reading",
            "click here",
            "cookie policy",
            "privacy policy",
            "terms of use",
            "terms and conditions",
            "about us",
            "contact us",
            "sitemap",
            "copyright",
            "all rights reserved",
            "©",
            "entry-header",
            "entry-content",
            "entry-footer",
            "post-header",
            "post-content",
            "post-footer",
        ]

        for pattern in boilerplate_patterns:
            if pattern in lower_line:
                return True

        return False

    def _is_update_line(self, line: str) -> bool:
        """Check if line is an 'Updated' or 'Last Updated' line."""
        import re

        patterns = [
            r"^last\s+updated\s*:?",
            r"^updated\s*:?",
            r"^last\s+modified\s*:?",
            r"^published\s*:?",
            r"^posted\s*:?",
        ]

        lower_line = line.lower()
        for pattern in patterns:
            if re.match(pattern, lower_line, re.IGNORECASE):
                return True

        return False

    def _is_byline(self, line: str) -> bool:
        """Check if line is a byline (author info)."""
        import re

        patterns = [
            r"^by\s+",
            r"^written\s+by\s+",
            r"^contributed\s+by\s+",
            r"^reported\s+by\s+",
        ]

        lower_line = line.lower()
        for pattern in patterns:
            if re.match(pattern, lower_line, re.IGNORECASE):
                return True

        return False

    async def extract_metadata(self, html_content: str, url: str | None = None) -> dict[str, Any]:
        """
        Extract article metadata using trafilatura.

        Returns:
            Dict containing title, author, date, etc.
        """
        try:
            extracted_json = extract(
                html_content,
                url=url,
                no_fallback=False,
                output_format="json",
                include_links=False,
                include_images=False,
                config=self._trafilatura_config,
            )

            if extracted_json:
                import orjson

                return orjson.loads(extracted_json)

            return {}

        except Exception as e:
            logger.error("trafilatura metadata extraction error: %s", e)
            return {}
