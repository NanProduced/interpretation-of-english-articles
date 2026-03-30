from __future__ import annotations

import re

from app.schemas.preprocess import NormalizedText

MULTISPACE_PATTERN = re.compile(r"[ \t]+")


def normalize_text(source_text: str) -> NormalizedText:
    actions: list[str] = []
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    if text != source_text:
        actions.append("normalize_line_breaks")

    stripped_lines = [MULTISPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(stripped_lines).strip()
    if cleaned != text.strip():
        actions.append("collapse_spaces")

    return NormalizedText(
        source_text=source_text,
        clean_text=cleaned,
        text_changed=cleaned != source_text,
        normalization_actions=actions,
    )

