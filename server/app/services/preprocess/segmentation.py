from __future__ import annotations

import re

from app.schemas.preprocess import SegmentedParagraph, SegmentedSentence, SegmentationResult

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def split_sentences(paragraph_text: str) -> list[str]:
    if not paragraph_text.strip():
        return []
    return [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(paragraph_text.strip()) if part.strip()]


def segment_text(clean_text: str) -> SegmentationResult:
    paragraphs: list[SegmentedParagraph] = []
    sentences: list[SegmentedSentence] = []
    offset = 0

    for paragraph_index, raw_paragraph in enumerate(clean_text.split("\n\n"), start=1):
        paragraph_text = raw_paragraph.strip()
        if not paragraph_text:
            continue

        start = clean_text.find(paragraph_text, offset)
        end = start + len(paragraph_text)
        offset = end
        paragraph_id = f"p{paragraph_index}"

        sentence_offset = start
        for sentence_text in split_sentences(paragraph_text):
            sentence_start = clean_text.find(sentence_text, sentence_offset)
            sentence_end = sentence_start + len(sentence_text)
            sentence_id = f"s{len(sentences) + 1}"
            sentence_offset = sentence_end
            sentences.append(
                SegmentedSentence(
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    text=sentence_text,
                    start=sentence_start,
                    end=sentence_end,
                )
            )

        paragraphs.append(
            SegmentedParagraph(
                paragraph_id=paragraph_id,
                text=paragraph_text,
                start=start,
                end=end,
            )
        )

    return SegmentationResult(
        paragraph_count=len(paragraphs),
        sentence_count=len(sentences),
        paragraphs=paragraphs,
        sentences=sentences,
    )

