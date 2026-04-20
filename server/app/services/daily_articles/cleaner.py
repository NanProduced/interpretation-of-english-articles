"""
Article content cleaner and validator.

Cleans HTML tags, special characters, and validates:
- Language is English
- Word count is between 500-1200 words
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from logging import getLogger

from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException

logger = getLogger(__name__)


MIN_WORD_COUNT = 500
MAX_WORD_COUNT = 1200


@dataclass
class CleanedArticle:
    """Cleaned and validated article data."""

    title: str
    content: str
    word_count: int
    is_english: bool
    is_valid_length: bool
    is_valid: bool


class ArticleCleaner:
    """Cleans and validates article content."""

    def __init__(
        self,
        min_word_count: int = MIN_WORD_COUNT,
        max_word_count: int = MAX_WORD_COUNT,
    ):
        self.min_word_count = min_word_count
        self.max_word_count = max_word_count

    def clean_html(self, html_content: str) -> str:
        """Remove HTML tags and extract text content."""
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator=" ", strip=True)

            text = re.sub(r"\s+", " ", text)
            text = text.strip()

            return text
        except Exception as e:
            logger.warning("Error cleaning HTML: %s", e)
            return html_content

    def clean_text(self, text: str) -> str:
        """Clean plain text: remove excessive whitespace, normalize."""
        if not text:
            return ""

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        return text

    def count_words(self, text: str) -> int:
        """Count words in text (English word count)."""
        if not text:
            return 0

        words = re.findall(r"[a-zA-Z]+(?:['’][a-zA-Z]+)?", text)
        return len(words)

    def detect_language(self, text: str) -> str | None:
        """Detect the language of the text. Returns ISO 639-1 code (e.g., 'en')."""
        if not text or len(text.strip()) < 50:
            return None

        try:
            lang = detect(text)
            return lang
        except LangDetectException as e:
            logger.warning("Language detection failed: %s", e)
            return None

    def is_english(self, text: str) -> bool:
        """Check if the text is in English."""
        lang = self.detect_language(text)
        return lang == "en"

    def is_valid_word_count(self, word_count: int) -> bool:
        """Check if word count is within valid range."""
        return self.min_word_count <= word_count <= self.max_word_count

    def clean_and_validate(self, title: str, content: str) -> CleanedArticle:
        """
        Clean article content and validate it.

        Args:
            title: Article title
            content: Raw article content (may contain HTML)

        Returns:
            CleanedArticle with validation results
        """
        cleaned_content = self.clean_html(content)
        cleaned_content = self.clean_text(cleaned_content)

        cleaned_title = self.clean_text(title)

        word_count = self.count_words(cleaned_content)
        is_english = self.is_english(cleaned_content)
        is_valid_length = self.is_valid_word_count(word_count)

        is_valid = is_english and is_valid_length and word_count > 0

        return CleanedArticle(
            title=cleaned_title,
            content=cleaned_content,
            word_count=word_count,
            is_english=is_english,
            is_valid_length=is_valid_length,
            is_valid=is_valid,
        )

    def clean_title(self, title: str) -> str:
        """Clean and normalize article title."""
        if not title:
            return ""

        title = self.clean_html(title)
        title = self.clean_text(title)

        title = re.sub(r"\s+", " ", title)
        title = title.strip()

        return title
