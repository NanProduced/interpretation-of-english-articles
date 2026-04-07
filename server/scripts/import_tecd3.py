from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import asyncpg
from bs4 import BeautifulSoup

SOURCE = "tecd3"
PARSE_VERSION = "tecd3_v2"
SECTION_PREVIEW_LENGTH = 180
PROGRESS_EVERY = 10_000

ALIAS_MAP: dict[str, str] = {
    "u.s.": "us",
    "u.k.": "uk",
    "e.g.": "eg",
    "i.e.": "ie",
    "prof.": "prof",
    "dr.": "dr",
    "mr.": "mr",
    "mrs.": "mrs",
    "ms.": "ms",
    "vs.": "vs",
    "etc.": "etc",
}

POS_LABEL_MAP: dict[str, str] = {
    "NOUN 名词": "n.",
    "ADJECTIVE 形容词": "adj.",
    "ADVERB 副词": "adv.",
    "PREPOSITION 介词": "prep.",
    "TRANSITIVE VERB 及物动词": "vt.",
    "INTRANSITIVE VERB 不及物动词": "vi.",
    "PREFIX 前缀": "pref.",
    "CONJUNCTION 连词": "conj.",
    "PRONOUN 代词": "pron.",
    "INTERJECTION 感叹词": "int.",
    "ARTICLE 冠词": "art.",
    "AUXILIARY VERB 助动词": "aux. v.",
    "MODAL VERB 情态动词": "modal v.",
    "COMBINING FORM 组合语素": "comb. form",
}

TRANSLATION_MAP = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "\xa0": " ",
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
    }
)

SUPERSCRIPT_DIGITS = {
    0: "⁰",
    1: "¹",
    2: "²",
    3: "³",
    4: "⁴",
    5: "⁵",
    6: "⁶",
    7: "⁷",
    8: "⁸",
    9: "⁹",
}


@dataclass(frozen=True)
class RawRecord:
    key: str
    kind: str
    value: str


@dataclass(frozen=True)
class ParsedEntry:
    source_entry_key: str
    entry_kind: str
    display_headword: str
    base_headword: str | None
    homograph_no: int | None
    primary_pos: str | None
    phonetic: str | None
    meanings_json: list[dict[str, Any]]
    examples_json: list[dict[str, Any]]
    phrases_json: list[dict[str, Any]]
    sections_json: list[dict[str, Any]]
    raw_html: str


@dataclass(frozen=True)
class ParsedCandidate:
    target_entry_key: str
    label: str
    target_pos: str | None
    preview_text: str | None
    rank: int


@dataclass(frozen=True)
class ParsedDisambiguation:
    lookup_key: str
    lookup_label: str
    normalized_form: str
    candidates: list[ParsedCandidate]


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _visible_node_text(node: Any) -> str:
    if node is None:
        return ""
    return _clean_text(node.get_text(" ", strip=True))


def _canonicalize_headword(value: str) -> str:
    text = _clean_text(value.translate(TRANSLATION_MAP))
    text = text.replace("·", "").replace("•", "")
    text = re.sub(r"(?<=\S)\s+([0-9]+)$", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _canonicalize_display_headword(value: str) -> str:
    text = _clean_text(
        value.translate(
            str.maketrans(
                {
                    "’": "'",
                    "‘": "'",
                    "“": '"',
                    "”": '"',
                    "\xa0": " ",
                }
            )
        )
    )
    text = text.replace("·", "").replace("•", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _format_homograph_display(base: str, homograph_no: int | None) -> str:
    if homograph_no is None:
        return base
    suffix = "".join(SUPERSCRIPT_DIGITS.get(int(ch), ch) for ch in str(homograph_no))
    return f"{base}{suffix}"


def normalize_query(word: str) -> str:
    normalized = _canonicalize_headword(word).lower()
    normalized = ALIAS_MAP.get(normalized, normalized)
    normalized = re.sub(r"^[^\w]+|[^\w]+$", "", normalized)
    return ALIAS_MAP.get(normalized, normalized)


def _normalize_meaning_text(value: str) -> str:
    text = _clean_text(value.translate(TRANSLATION_MAP))
    text = re.sub(r"\s*=\s*", "=", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    return text


def _normalize_pos_label(value: str | None, nav_label: str | None = None) -> str:
    if nav_label:
        return _clean_text(nav_label)
    text = _clean_text(value)
    return POS_LABEL_MAP.get(text, text)


def _iter_txt_entries(path: Path) -> Iterator[tuple[str, str]]:
    current_key: str | None = None
    current_lines: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if line == "</>":
                if current_key is not None:
                    yield current_key, "\n".join(current_lines).strip()
                current_key = None
                current_lines = []
                continue
            if current_key is None:
                current_key = line.strip()
            else:
                current_lines.append(line)

    if current_key is not None:
        yield current_key, "\n".join(current_lines).strip()


def load_txt_records(input_dir: Path) -> dict[str, RawRecord]:
    records: dict[str, RawRecord] = {}
    for path in sorted(input_dir.glob("*.mdx.*.txt")):
        if path.name.endswith(".title.html") or path.name.endswith(".description.html"):
            continue
        for key, content in _iter_txt_entries(path):
            if not key:
                continue
            if key in records:
                raise ValueError(f"Duplicate mdict key detected: {key!r} in {path.name}")
            if content.startswith("@@@LINK="):
                records[key] = RawRecord(key=key, kind="redirect", value=content.split("=", 1)[1].strip())
            else:
                records[key] = RawRecord(
                    key=key,
                    kind="html",
                    value=content.replace("\u2028", " ").replace("\u2029", " "),
                )
    return records


def _extract_examples(container: Any) -> list[dict[str, str | None]]:
    examples: list[dict[str, str | None]] = []
    for block in container.select(".egBlock"):
        example_node = block.select_one(".ex")
        translation_node = block.select_one(".tr")
        example = _clean_text(example_node.get_text(" ", strip=True) if example_node else "")
        translation = _clean_text(
            translation_node.get_text(" ", strip=True) if translation_node else ""
        )
        if example:
            examples.append(
                {
                    "example": example,
                    "example_translation": translation or None,
                }
            )
    return examples


def _iter_meaning_sections(soup: BeautifulSoup) -> list[Any]:
    sections: list[Any] = []
    for section in soup.select(".se1"):
        subsections = section.select(".subse1")
        if subsections:
            sections.extend(subsections)
        else:
            sections.append(section)
    if sections:
        return sections

    return soup.select(".se2g")


def _build_nav_pos_map(soup: BeautifulSoup) -> dict[str, str]:
    nav_map: dict[str, str] = {}
    for link in soup.select(".mdict-entry-nav-link[href^='#mdict-pos-']"):
        href = str(link.get("href") or "").strip()
        label = _clean_text(link.get_text(" ", strip=True))
        if href and label:
            nav_map[href.lstrip("#")] = label
    return nav_map


def _find_section_anchor_id(section: Any) -> str | None:
    current = section
    while current is not None:
        anchor = current.find_previous(
            lambda tag: getattr(tag, "name", None) == "a"
            and str(tag.get("id") or "").startswith("mdict-pos-")
        )
        if anchor is not None:
            return str(anchor.get("id"))
        current = current.parent
    return None


def _extract_definition_texts(section: Any) -> list[str]:
    definition_nodes = section.select(".se2g .df")
    if not definition_nodes:
        definition_nodes = section.select(".df")
    if definition_nodes:
        return [
            meaning
            for node in definition_nodes
            if (meaning := _normalize_meaning_text(node.get_text(" ", strip=True)))
        ]

    fallback_nodes = section.select(".se2g .se2")
    if not fallback_nodes and section.name == "li" and "se2" in (section.get("class") or []):
        fallback_nodes = [section]
    if not fallback_nodes and section.select_one(".corrSe2FirstLine"):
        fallback_nodes = [section]

    meanings: list[str] = []
    for node in fallback_nodes:
        first_line = node.select_one(".corrSe2FirstLine") or node
        meaning = _normalize_meaning_text(first_line.get_text(" ", strip=True))
        if meaning:
            meanings.append(meaning)
    return meanings


def _parse_meaning_groups(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    groups: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    primary_pos: str | None = None
    nav_pos_map = _build_nav_pos_map(soup)

    for section in _iter_meaning_sections(soup):
        pos_node = section.select_one(".sgPosDiv .pos") or section.select_one(".pos")
        anchor_id = _find_section_anchor_id(section)
        nav_label = nav_pos_map.get(anchor_id or "")
        pos = _normalize_pos_label(
            pos_node.get_text(" ", strip=True) if pos_node else "",
            nav_label=nav_label,
        )
        if pos and primary_pos is None:
            primary_pos = pos

        group_examples = _extract_examples(section)
        definitions: list[dict[str, str | None]] = []
        for idx, meaning in enumerate(_extract_definition_texts(section)):
            example_payload = group_examples[idx] if idx < len(group_examples) else None
            definitions.append(
                {
                    "meaning": meaning,
                    "example": example_payload["example"] if example_payload else None,
                    "example_translation": (
                        example_payload["example_translation"] if example_payload else None
                    ),
                }
            )

        if definitions:
            groups.append(
                {
                    "part_of_speech": pos or primary_pos or "",
                    "definitions": definitions,
                }
            )

        examples.extend(group_examples)

    return groups, examples, primary_pos


def _parse_phrases(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    phrases: list[dict[str, str | None]] = []
    blocks = soup.select(".phrase .phrasediv") or soup.select(".phrase")
    for block in blocks:
        phrase_node = block.select_one(".l, .hwSpan")
        phrase = _clean_text(phrase_node.get_text(" ", strip=True) if phrase_node else "")
        if not phrase:
            strong = block.find(["strong", "b"])
            if strong is not None:
                phrase = _clean_text(strong.get_text(" ", strip=True))
        meaning_node = block.select_one(".df")
        meaning = _clean_text(meaning_node.get_text(" ", strip=True) if meaning_node else "")
        if not phrase:
            lines = [line.strip() for line in block.get_text("\n", strip=True).splitlines() if line.strip()]
            if lines:
                phrase = lines[0]
                if not meaning and len(lines) > 1:
                    meaning = lines[1]
        if phrase:
            phrases.append({"phrase": phrase, "meaning": meaning or None})
    return phrases


def _extract_headword_parts(soup: BeautifulSoup, fallback: str) -> tuple[str, str | None, int | None]:
    spans = soup.select(".hwgDiv > .hwSpan")
    if spans:
        texts = [_canonicalize_display_headword(_visible_node_text(span)) for span in spans]
        texts = [text for text in texts if text]
        if len(texts) > 1:
            display = ", ".join(dict.fromkeys(texts))
            return display, display, None

        hw_span = spans[0]
        display = texts[0] if texts else _canonicalize_display_headword(fallback)
        homograph_no: int | None = None

        hw_node = hw_span.find("hw")
        if hw_node is not None and hw_node.get("homograph"):
            raw_homograph = _clean_text(str(hw_node.get("homograph")))
            homograph_no = int(raw_homograph) if raw_homograph.isdigit() else None

        if homograph_no is None:
            sup = hw_span.find("sup")
            if sup is not None:
                raw_sup = _canonicalize_headword(sup.get_text("", strip=True))
                homograph_no = int(raw_sup) if raw_sup.isdigit() else None

        if hw_node is not None:
            base = _canonicalize_display_headword(_visible_node_text(hw_node))
        elif homograph_no is not None:
            base = _canonicalize_display_headword(re.sub(rf"{homograph_no}$", "", display).rstrip(" -"))
        else:
            base = display
        display_label = _format_homograph_display(base or display, homograph_no)
        return display_label, base or display_label, homograph_no

    for selector in (".mdict-fragment-title", ".mdict-disamb-title"):
        node = soup.select_one(selector)
        if not node:
            continue
        text = _canonicalize_display_headword(node.get_text(" ", strip=True))
        if text:
            return text, text, None
    display = _canonicalize_display_headword(fallback)
    return display, display or None, None


def _child_nodes_with_class(parent: Any, class_name: str) -> list[Any]:
    if parent is None:
        return []
    return parent.find_all(
        lambda tag: getattr(tag, "name", None) and class_name in (tag.get("class") or []),
        recursive=False,
    )


def _build_sections_summary(soup: BeautifulSoup, entry_kind: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []

    if entry_kind == "entry":
        candidates: list[tuple[str, Any]] = []
        root = soup.select_one(".eDiv")
        if root is not None:
            for sg in _child_nodes_with_class(root, "sg"):
                se1_nodes = _child_nodes_with_class(sg, "se1")
                if se1_nodes:
                    candidates.extend(("meanings", node) for node in se1_nodes)
                else:
                    candidates.append(("meanings", sg))
            for kind, class_name in (
                ("phrases", "phrase"),
                ("derivatives", "derivative"),
                ("notes", "note"),
                ("etymology", "etym"),
            ):
                candidates.extend((kind, node) for node in _child_nodes_with_class(root, class_name))
    else:
        body = soup.select_one(".mdict-fragment-body")
        candidates: list[tuple[str, Any]] = []
        if body is not None:
            for kind, class_name in (
                ("phrases", "phrasediv"),
                ("derivatives", "derivativeDiv"),
                ("notes", "noteDiv"),
                ("meanings", "se1"),
                ("meanings", "se2g"),
            ):
                candidates.extend((kind, node) for node in _child_nodes_with_class(body, class_name))

    seen: set[tuple[str, str]] = set()
    for kind, node in candidates:
        preview = _clean_text(node.get_text(" ", strip=True))
        if not preview:
            continue
        preview = preview[:SECTION_PREVIEW_LENGTH]
        key = (kind, preview)
        if key in seen:
            continue
        seen.add(key)
        sections.append({"kind": kind, "preview": preview})
    return sections


def parse_entry_html(source_entry_key: str, html: str) -> ParsedEntry | None:
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one(".mdict-disamb"):
        return None

    entry_kind = "fragment" if soup.select_one(".mdict-fragment-header") else "entry"
    display_headword, base_headword, homograph_no = _extract_headword_parts(soup, source_entry_key)
    phonetic_node = soup.select_one(".hg .prLine pr") or soup.select_one(".hg pr") or soup.select_one(".pr")
    phonetic = _clean_text(phonetic_node.get_text(" ", strip=True) if phonetic_node else "") or None
    meanings_json, examples_json, primary_pos = _parse_meaning_groups(soup)
    phrases_json = _parse_phrases(soup)
    if not examples_json:
        examples_json = _extract_examples(soup)
    sections_json = _build_sections_summary(soup, entry_kind)

    return ParsedEntry(
        source_entry_key=source_entry_key,
        entry_kind=entry_kind,
        display_headword=display_headword,
        base_headword=base_headword,
        homograph_no=homograph_no,
        primary_pos=primary_pos,
        phonetic=phonetic,
        meanings_json=meanings_json,
        examples_json=examples_json,
        phrases_json=phrases_json,
        sections_json=sections_json,
        raw_html=html,
    )


def parse_disambiguation_html(lookup_key: str, html: str) -> ParsedDisambiguation | None:
    soup = BeautifulSoup(html, "html.parser")
    if not soup.select_one(".mdict-disamb"):
        return None

    lookup_label, _, _ = _extract_headword_parts(soup, lookup_key)
    candidates: list[ParsedCandidate] = []
    for rank, item in enumerate(soup.select(".mdict-disamb-item")):
        link_node = item.select_one(".mdict-target-link")
        href = str(link_node.get("href") if link_node else "").strip()
        if not href.startswith("entry://"):
            continue
        target_entry_key = href.removeprefix("entry://").strip()
        label = _canonicalize_display_headword(
            _visible_node_text(link_node) if link_node else target_entry_key
        )
        pos_node = item.select_one(".pos")
        preview_node = item.select_one(".mdict-target-preview")
        candidates.append(
            ParsedCandidate(
                target_entry_key=target_entry_key,
                label=label or target_entry_key,
                target_pos=_clean_text(pos_node.get_text(" ", strip=True) if pos_node else "") or None,
                preview_text=_clean_text(preview_node.get_text(" ", strip=True) if preview_node else "") or None,
                rank=rank,
            )
        )

    if not candidates:
        return None

    return ParsedDisambiguation(
        lookup_key=lookup_key,
        lookup_label=lookup_label,
        normalized_form=normalize_query(lookup_key),
        candidates=candidates,
    )


def build_lookup_forms(*values: str | None) -> list[str]:
    forms: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        if value and value not in seen:
            seen.add(value)
            forms.append(value)

    for raw in values:
        if not raw:
            continue
        normalized = normalize_query(raw)
        if not normalized:
            continue
        queue = [normalized]
        processed: set[str] = set()
        while queue:
            candidate = queue.pop(0)
            if candidate in processed:
                continue
            processed.add(candidate)
            add(candidate)
            if "'" in candidate:
                queue.append(candidate.replace("'", ""))
            if "-" in candidate:
                queue.append(candidate.replace("-", " "))
                queue.append(candidate.replace("-", ""))
            if " " in candidate:
                queue.append(candidate.replace(" ", ""))

    return forms


def _resolve_redirect_target(key: str, records: dict[str, RawRecord]) -> str | None:
    current = key
    seen: set[str] = set()
    while current in records and records[current].kind == "redirect":
        if current in seen:
            return None
        seen.add(current)
        current = records[current].value
    return current if current in records else None


def _log_progress(message: str) -> None:
    print(f"[import_tecd3] {message}", flush=True)


def _build_preview(entry: ParsedEntry) -> str | None:
    if entry.meanings_json:
        preview_parts: list[str] = []
        for group in entry.meanings_json[:2]:
            for definition in group.get("definitions", [])[:2]:
                meaning = _clean_text(str(definition.get("meaning") or ""))
                if meaning:
                    preview_parts.append(meaning)
        preview = "；".join(preview_parts)
        return preview[:SECTION_PREVIEW_LENGTH] if preview else None
    if entry.sections_json:
        return entry.sections_json[0].get("preview")
    return None


async def _upsert_entries(conn: asyncpg.Connection, entries: list[ParsedEntry]) -> None:
    sql = """
    INSERT INTO dict_entries (
      source,
      source_entry_key,
      entry_kind,
      display_headword,
      base_headword,
      homograph_no,
      phonetic,
      primary_pos,
      meanings_json,
      examples_json,
      phrases_json,
      sections_json,
      raw_html,
      parse_version
    ) VALUES (
      $1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11::jsonb, $12::jsonb, $13, $14
    )
    ON CONFLICT (source, source_entry_key) DO UPDATE SET
      entry_kind = EXCLUDED.entry_kind,
      display_headword = EXCLUDED.display_headword,
      base_headword = EXCLUDED.base_headword,
      homograph_no = EXCLUDED.homograph_no,
      phonetic = EXCLUDED.phonetic,
      primary_pos = EXCLUDED.primary_pos,
      meanings_json = EXCLUDED.meanings_json,
      examples_json = EXCLUDED.examples_json,
      phrases_json = EXCLUDED.phrases_json,
      sections_json = EXCLUDED.sections_json,
      raw_html = EXCLUDED.raw_html,
      parse_version = EXCLUDED.parse_version,
      updated_at = NOW()
    """
    rows = [
        (
            SOURCE,
            item.source_entry_key,
            item.entry_kind,
            item.display_headword,
            item.base_headword,
            item.homograph_no,
            item.phonetic,
            item.primary_pos,
            json.dumps(item.meanings_json, ensure_ascii=False),
            json.dumps(item.examples_json, ensure_ascii=False),
            json.dumps(item.phrases_json, ensure_ascii=False),
            json.dumps(item.sections_json, ensure_ascii=False),
            item.raw_html,
            PARSE_VERSION,
        )
        for item in entries
    ]
    total = len(rows)
    for offset in range(0, total, PROGRESS_EVERY):
        chunk = rows[offset : offset + PROGRESS_EVERY]
        await conn.executemany(sql, chunk)
        _log_progress(f"upserted entries: {min(offset + len(chunk), total)}/{total}")


async def _replace_lookup_targets(
    conn: asyncpg.Connection,
    lookup_rows: list[tuple[str, str, str, int, str, str | None, str | None, int, str]],
) -> None:
    await conn.execute("DELETE FROM dict_lookup_targets WHERE source = $1", SOURCE)
    if not lookup_rows:
        return
    sql = """
    INSERT INTO dict_lookup_targets (
      source,
      normalized_form,
      lookup_label,
      entry_id,
      target_label,
      target_pos,
      preview_text,
      rank,
      match_kind
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (source, normalized_form, entry_id, match_kind) DO UPDATE SET
      lookup_label = EXCLUDED.lookup_label,
      target_label = EXCLUDED.target_label,
      target_pos = EXCLUDED.target_pos,
      preview_text = EXCLUDED.preview_text,
      rank = EXCLUDED.rank
    """
    total = len(lookup_rows)
    for offset in range(0, total, PROGRESS_EVERY):
        chunk = lookup_rows[offset : offset + PROGRESS_EVERY]
        await conn.executemany(sql, chunk)
        _log_progress(f"inserted lookup targets: {min(offset + len(chunk), total)}/{total}")


async def _replace_redirects(
    conn: asyncpg.Connection,
    redirect_rows: list[tuple[str, str, str, str]],
) -> None:
    await conn.execute("DELETE FROM dict_redirects WHERE source = $1", SOURCE)
    if not redirect_rows:
        return
    sql = """
    INSERT INTO dict_redirects (source, redirect_key, target_entry_key, redirect_kind)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (source, redirect_key, target_entry_key, redirect_kind) DO NOTHING
    """
    total = len(redirect_rows)
    for offset in range(0, total, PROGRESS_EVERY):
        chunk = redirect_rows[offset : offset + PROGRESS_EVERY]
        await conn.executemany(sql, chunk)
        _log_progress(f"inserted redirects: {min(offset + len(chunk), total)}/{total}")


async def import_tecd3(input_dir: Path, database_url: str) -> dict[str, int]:
    _log_progress(f"loading txt records from {input_dir}")
    records = load_txt_records(input_dir)
    _log_progress(f"loaded raw records: {len(records)}")
    entry_records: dict[str, ParsedEntry] = {}
    disambiguation_records: dict[str, ParsedDisambiguation] = {}
    redirect_records: dict[str, str] = {}

    total_records = len(records)
    for index, (key, record) in enumerate(records.items(), start=1):
        if record.kind == "redirect":
            redirect_records[key] = record.value
        else:
            disambiguation = parse_disambiguation_html(key, record.value)
            if disambiguation is not None:
                disambiguation_records[key] = disambiguation
            else:
                entry = parse_entry_html(key, record.value)
                if entry is not None:
                    entry_records[key] = entry
        if index % PROGRESS_EVERY == 0 or index == total_records:
            _log_progress(
                "classified records: "
                f"{index}/{total_records} "
                f"(entries={len(entry_records)}, disamb={len(disambiguation_records)}, redirects={len(redirect_records)})"
            )

    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=1,
        max_size=4,
        server_settings={"application_name": "tecd3_import"},
    )
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await _upsert_entries(conn, list(entry_records.values()))

                rows = await conn.fetch(
                    """
                    SELECT id, source_entry_key
                    FROM dict_entries
                    WHERE source = $1
                    """,
                    SOURCE,
                )
                entry_id_by_key = {row["source_entry_key"]: row["id"] for row in rows}
                _log_progress(f"loaded entry ids: {len(entry_id_by_key)}")

                lookup_rows: list[tuple[str, str, str, int, str, str | None, str | None, int, str]] = []
                redirect_rows: list[tuple[str, str, str, str]] = []
                seen_lookup: set[tuple[str, int, str]] = set()
                seen_redirects: set[tuple[str, str, str]] = set()

                for key, entry in entry_records.items():
                    entry_id = entry_id_by_key.get(key)
                    if entry_id is None:
                        continue
                    preview = _build_preview(entry)
                    for rank, form in enumerate(build_lookup_forms(entry.display_headword, entry.base_headword, key)):
                        lookup_key = (form, entry_id, "headword")
                        if lookup_key in seen_lookup:
                            continue
                        seen_lookup.add(lookup_key)
                        lookup_rows.append(
                            (
                                SOURCE,
                                form,
                                entry.display_headword,
                                entry_id,
                                entry.display_headword,
                                entry.primary_pos,
                                preview,
                                rank,
                                "headword",
                            )
                        )
                    for form in build_lookup_forms(entry.display_headword, entry.base_headword, key):
                        redirect_key = (form, key, "normalized_alias")
                        if redirect_key in seen_redirects:
                            continue
                        seen_redirects.add(redirect_key)
                        redirect_rows.append((SOURCE, form, key, "normalized_alias"))

                for key, disambiguation in disambiguation_records.items():
                    forms = build_lookup_forms(key, disambiguation.lookup_label)
                    for item in disambiguation.candidates:
                        resolved_key = _resolve_redirect_target(item.target_entry_key, records)
                        if resolved_key not in entry_records:
                            continue
                        entry = entry_records[resolved_key]
                        entry_id = entry_id_by_key.get(resolved_key)
                        if entry_id is None:
                            continue
                        for extra_rank, form in enumerate(forms):
                            lookup_key = (form, entry_id, "disamb")
                            if lookup_key in seen_lookup:
                                continue
                            seen_lookup.add(lookup_key)
                            lookup_rows.append(
                                (
                                    SOURCE,
                                    form,
                                    disambiguation.lookup_label,
                                    entry_id,
                                    item.label or entry.display_headword,
                                    item.target_pos or entry.primary_pos,
                                    item.preview_text or _build_preview(entry),
                                    item.rank + extra_rank,
                                    "disamb",
                                )
                            )

                for redirect_key, redirect_target in redirect_records.items():
                    resolved_target = _resolve_redirect_target(redirect_target, records)
                    if not resolved_target:
                        continue
                    redirect_kind = "mdx_link"
                    if resolved_target in entry_records:
                        entry = entry_records[resolved_target]
                        entry_id = entry_id_by_key.get(resolved_target)
                        if entry_id is None:
                            continue
                        for rank, form in enumerate(build_lookup_forms(redirect_key)):
                            lookup_key = (form, entry_id, "redirect")
                            if lookup_key in seen_lookup:
                                continue
                            seen_lookup.add(lookup_key)
                            lookup_rows.append(
                                (
                                    SOURCE,
                                    form,
                                    redirect_key,
                                    entry_id,
                                    entry.display_headword,
                                    entry.primary_pos,
                                    _build_preview(entry),
                                    100 + rank,
                                    "redirect",
                                )
                            )
                            redirect_dedup = (form, resolved_target, redirect_kind)
                            if redirect_dedup not in seen_redirects:
                                seen_redirects.add(redirect_dedup)
                                redirect_rows.append((SOURCE, form, resolved_target, redirect_kind))
                        continue

                    if resolved_target in disambiguation_records:
                        disambiguation = disambiguation_records[resolved_target]
                        forms = build_lookup_forms(redirect_key)
                        for item in disambiguation.candidates:
                            candidate_target = _resolve_redirect_target(item.target_entry_key, records)
                            if candidate_target not in entry_records:
                                continue
                            entry = entry_records[candidate_target]
                            entry_id = entry_id_by_key.get(candidate_target)
                            if entry_id is None:
                                continue
                            for extra_rank, form in enumerate(forms):
                                lookup_key = (form, entry_id, "redirect")
                                if lookup_key in seen_lookup:
                                    continue
                                seen_lookup.add(lookup_key)
                                lookup_rows.append(
                                    (
                                        SOURCE,
                                        form,
                                        redirect_key,
                                        entry_id,
                                        item.label or entry.display_headword,
                                        item.target_pos or entry.primary_pos,
                                        item.preview_text or _build_preview(entry),
                                        100 + item.rank + extra_rank,
                                        "redirect",
                                    )
                                )

                _log_progress(
                    "prepared relational rows: "
                    f"lookup_targets={len(lookup_rows)}, redirects={len(redirect_rows)}"
                )
                await _replace_lookup_targets(conn, lookup_rows)
                await _replace_redirects(conn, redirect_rows)

        return {
            "entries": len(entry_records),
            "disambiguations": len(disambiguation_records),
            "redirects": len(redirect_records),
        }
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TECD3 unpacked txt into PostgreSQL")
    parser.add_argument("--input-dir", required=True, help="mdict-utils 解包后的 txt 目录")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL DSN（默认读取 DATABASE_URL）",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("错误: 未提供 --database-url 或 DATABASE_URL 环境变量", file=sys.stderr)
        raise SystemExit(1)

    result = asyncio.run(import_tecd3(Path(args.input_dir), args.database_url))
    print(
        f"Imported {result['entries']} entries, "
        f"{result['disambiguations']} disambiguations and "
        f"{result['redirects']} redirects"
    )


if __name__ == "__main__":
    main()
