from __future__ import annotations

import html
import re

from app.schemas.common import TextSpan
from app.schemas.internal.analysis import (
    PreparedInput,
    PreparedParagraph,
    PreparedSentence,
    SanitizeReport,
)

__all__ = ["prepare_input", "PreparedInput"]

CODE_FENCE_PATTERN = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
URL_PATTERN = re.compile(r"https?://[^\s]+|www\.[^\s]+")
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
HTML_BLOCK_BREAK_PATTERN = re.compile(
    r"</?(?:p|div|section|article|li|ul|ol|br|h[1-6])[^>]*>",
    re.IGNORECASE,
)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
CONTROL_CHAR_PATTERN = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
MULTISPACE_PATTERN = re.compile(r"[ \t]+")
SENTENCE_PATTERN = re.compile(r".+?(?:[.!?](?:\"|'|”)?(?=\s+[A-Z0-9])|$)", re.DOTALL)
LATIN_LETTER_PATTERN = re.compile(r"[A-Za-z]")
ALPHANUMERIC_PATTERN = re.compile(r"[A-Za-z0-9]")


def _replace_pattern(
    text: str,
    pattern: re.Pattern[str],
    replacement: str,
    action: str,
) -> tuple[str, bool]:
    replaced = pattern.sub(replacement, text)
    return replaced, replaced != text


def sanitize_text(source_text: str) -> tuple[str, SanitizeReport]:
    """生成安全可渲染的正文文本，避免标签、链接和代码片段污染结果页。"""
    actions: list[str] = []
    removed_segment_count = 0

    text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    if text != source_text:
        actions.append("normalize_line_breaks")

    text = html.unescape(text)

    text, changed = _replace_pattern(text, CODE_FENCE_PATTERN, "\n", "remove_code_fence")
    if changed:
        actions.append("remove_code_fence")
        removed_segment_count += 1

    text, changed = _replace_pattern(text, INLINE_CODE_PATTERN, " ", "remove_inline_code")
    if changed:
        actions.append("remove_inline_code")
        removed_segment_count += 1

    markdown_link_count = len(MARKDOWN_LINK_PATTERN.findall(text))
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    if markdown_link_count:
        actions.append("strip_markdown_link_url")
        removed_segment_count += markdown_link_count

    url_count = len(URL_PATTERN.findall(text))
    text = URL_PATTERN.sub(" ", text)
    if url_count:
        actions.append("remove_url")
        removed_segment_count += url_count

    email_count = len(EMAIL_PATTERN.findall(text))
    text = EMAIL_PATTERN.sub(" ", text)
    if email_count:
        actions.append("remove_email")
        removed_segment_count += email_count

    html_break_count = len(HTML_BLOCK_BREAK_PATTERN.findall(text))
    text = HTML_BLOCK_BREAK_PATTERN.sub("\n", text)
    if html_break_count:
        actions.append("convert_html_block_breaks")
        removed_segment_count += html_break_count

    html_tag_count = len(HTML_TAG_PATTERN.findall(text))
    text = HTML_TAG_PATTERN.sub(" ", text)
    if html_tag_count:
        actions.append("remove_html_tags")
        removed_segment_count += html_tag_count

    text, changed = _replace_pattern(text, CONTROL_CHAR_PATTERN, "", "remove_control_chars")
    if changed:
        actions.append("remove_control_chars")
        removed_segment_count += 1

    stripped_lines = [MULTISPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in stripped_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if cleaned != text.strip():
        actions.append("collapse_spaces")

    return cleaned, SanitizeReport(actions=actions, removed_segment_count=removed_segment_count)


def _split_sentences(paragraph_text: str) -> list[str]:
    if not paragraph_text.strip():
        return []
    matches = [
        match.group(0).strip()
        for match in SENTENCE_PATTERN.finditer(paragraph_text)
        if match.group(0).strip()
    ]
    return matches or [paragraph_text.strip()]


def _english_ratio(text: str) -> float:
    meaningful_chars = [char for char in text if not char.isspace()]
    if not meaningful_chars:
        return 0.0
    english_chars = len(LATIN_LETTER_PATTERN.findall(text))
    return min(1.0, english_chars / len(meaningful_chars))


def _noise_ratio(source_text: str, sanitize_report: SanitizeReport) -> float:
    if not source_text:
        return 0.0
    if sanitize_report.removed_segment_count == 0:
        return 0.0
    removed_proxy = min(len(source_text), sanitize_report.removed_segment_count * 12)
    return min(1.0, removed_proxy / max(len(source_text), 1))


def _detect_text_type(render_text: str) -> str:
    lines = [line for line in render_text.split("\n") if line.strip()]
    if not render_text.strip():
        return "other"
    if "{" in render_text and "}" in render_text and ";" in render_text:
        return "code"
    bullet_count = sum(line.lstrip().startswith(("-", "*", "•")) for line in lines)
    if lines and bullet_count >= max(2, len(lines) // 2):
        return "list"
    if len(ALPHANUMERIC_PATTERN.findall(render_text)) < 20:
        return "other"
    return "article"


def prepare_input(source_text: str) -> PreparedInput:
    """把原始输入转换成安全可渲染的正文结构，供主教学节点消费。"""
    render_text, sanitize_report = sanitize_text(source_text)

    paragraphs: list[PreparedParagraph] = []
    sentences: list[PreparedSentence] = []
    offset = 0

    for paragraph_index, raw_paragraph in enumerate(render_text.split("\n\n"), start=1):
        paragraph_text = raw_paragraph.strip()
        if not paragraph_text:
            continue

        paragraph_start = render_text.find(paragraph_text, offset)
        paragraph_end = paragraph_start + len(paragraph_text)
        paragraph_id = f"p{paragraph_index}"
        offset = paragraph_end

        sentence_ids: list[str] = []
        sentence_offset = paragraph_start
        for sentence_text in _split_sentences(paragraph_text):
            sentence_start = render_text.find(sentence_text, sentence_offset)
            sentence_end = sentence_start + len(sentence_text)
            sentence_id = f"s{len(sentences) + 1}"
            sentence_ids.append(sentence_id)
            sentence_offset = sentence_end
            sentences.append(
                PreparedSentence(
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    text=sentence_text,
                    sentence_span=TextSpan(start=sentence_start, end=sentence_end),
                )
            )

        paragraphs.append(
            PreparedParagraph(
                paragraph_id=paragraph_id,
                text=paragraph_text,
                render_span=TextSpan(start=paragraph_start, end=paragraph_end),
                sentence_ids=sentence_ids,
            )
        )

    return PreparedInput(
        source_text=source_text,
        render_text=render_text,
        paragraphs=paragraphs,
        sentences=sentences,
        sanitize_report=sanitize_report,
        english_ratio=_english_ratio(render_text),
        noise_ratio=_noise_ratio(source_text, sanitize_report),
        text_type=_detect_text_type(render_text),
    )
