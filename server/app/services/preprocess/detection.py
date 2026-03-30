from __future__ import annotations

import re

from app.schemas.preprocess import LanguageDetection, NoiseDetection, TextTypeDetection

HTML_PATTERN = re.compile(r"<[^>]+>")
CODE_LIKE_PATTERN = re.compile(
    r"(```|`[^`]+`|def\s+\w+\(|class\s+\w+[:(]|function\s+\w+\(|=>|#include|SELECT\s+.+FROM)",
    re.IGNORECASE,
)


def detect_language(clean_text: str) -> LanguageDetection:
    alphabetic_chars = [char for char in clean_text if char.isalpha()]
    english_chars = [char for char in alphabetic_chars if "a" <= char.lower() <= "z"]
    total = len(alphabetic_chars)
    english_ratio = len(english_chars) / total if total else 0.0

    return LanguageDetection(
        primary_language="en" if english_ratio >= 0.5 else "mixed",
        english_ratio=round(english_ratio, 4),
        non_english_ratio=round(max(0.0, 1.0 - english_ratio), 4),
    )


def detect_noise(clean_text: str) -> NoiseDetection:
    html_matches = HTML_PATTERN.findall(clean_text)
    code_like = bool(CODE_LIKE_PATTERN.search(clean_text))
    appears_truncated = clean_text.endswith(("...", "…")) or clean_text.count("(") > clean_text.count(")")

    noise_units = sum(len(match) for match in html_matches)
    if code_like:
        noise_units += max(10, len(clean_text) // 8)

    noise_ratio = min(1.0, noise_units / max(1, len(clean_text)))
    return NoiseDetection(
        noise_ratio=round(noise_ratio, 4),
        has_html=bool(html_matches),
        has_code_like_content=code_like,
        appears_truncated=appears_truncated,
    )


def detect_text_type(clean_text: str, noise: NoiseDetection, sentence_count: int) -> TextTypeDetection:
    if noise.has_code_like_content:
        predicted_type = "code"
        confidence = 0.85
    elif "@" in clean_text and clean_text.lower().count("subject:"):
        predicted_type = "email"
        confidence = 0.7
    elif clean_text.count("\n") > 2 and clean_text.count("- ") + clean_text.count("* ") >= 2:
        predicted_type = "list"
        confidence = 0.7
    elif len(clean_text) < 60 and sentence_count <= 1:
        predicted_type = "subtitle"
        confidence = 0.6
    else:
        predicted_type = "article"
        confidence = 0.8

    return TextTypeDetection(predicted_type=predicted_type, confidence=confidence)

