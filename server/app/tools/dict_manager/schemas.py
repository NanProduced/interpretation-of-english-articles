"""词典数据管理工具的数据模型定义。"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MeaningDefinition(BaseModel):
    meaning: str = Field(description="释义内容")
    example: str | None = Field(default=None, description="例句")
    example_translation: str | None = Field(default=None, description="例句中文翻译")


class MeaningGroup(BaseModel):
    part_of_speech: str = Field(description="词性，如 'n.', 'v.', 'adj.'")
    definitions: list[MeaningDefinition] = Field(description="释义列表")


class ExampleItem(BaseModel):
    example: str = Field(description="英文例句")
    example_translation: str | None = Field(default=None, description="例句中文翻译")


class PhraseItem(BaseModel):
    phrase: str = Field(description="短语")
    meaning: str | None = Field(default=None, description="短语释义")


class EntryKind(str, Enum):
    ENTRY = "entry"
    FRAGMENT = "fragment"


class MatchKind(str, Enum):
    HEADWORD = "headword"
    ALIAS = "alias"
    DISAMB = "disamb"
    REDIRECT = "redirect"
    NLP = "nlp"


class RedirectKind(str, Enum):
    MDX_LINK = "mdx_link"
    NORMALIZED_ALIAS = "normalized_alias"


class DictionaryEntryBase(BaseModel):
    id: int = Field(description="词条 ID")
    source: str = Field(default="tecd3", description="词典来源")
    source_entry_key: str = Field(description="词典原生词条键")
    entry_kind: EntryKind = Field(description="词条类型")
    display_headword: str = Field(description="展示词头")
    base_headword: str | None = Field(default=None, description="基础词头（无同形编号）")
    homograph_no: int | None = Field(default=None, description="同形编号")
    phonetic: str | None = Field(default=None, description="音标")
    exam_tags: list[str] = Field(default_factory=list, description="考试标签")
    parse_version: str = Field(default="tecd3_v2", description="解析版本")


class DictionaryEntryDetail(DictionaryEntryBase):
    meanings: list[MeaningGroup] = Field(default_factory=list, description="词性及释义列表")
    examples: list[ExampleItem] = Field(default_factory=list, description="例句列表")
    phrases: list[PhraseItem] = Field(default_factory=list, description="短语列表")
    meanings_json_raw: str | None = Field(default=None, description="原始 meanings_json 字符串（用于调试）")
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)


class DictionaryEntrySummary(BaseModel):
    id: int
    source_entry_key: str
    display_headword: str
    entry_kind: str
    phonetic: str | None
    has_meanings: bool
    preview: str | None
    created_at: datetime | None
    updated_at: datetime | None


class LookupTargetRow(BaseModel):
    id: int
    normalized_form: str
    lookup_label: str
    entry_id: int
    target_label: str
    target_pos: str | None
    preview_text: str | None
    rank: int
    match_kind: str
    created_at: datetime | None


class RedirectRow(BaseModel):
    id: int
    redirect_key: str
    target_entry_key: str
    redirect_kind: str
    created_at: datetime | None


class DashboardStats(BaseModel):
    total_entries: int
    total_fragments: int
    entries_with_meanings: int
    entries_without_meanings: int
    total_lookup_targets: int
    total_redirects: int
    entries_without_lookup_targets: int
    duplicate_lookup_keys: int
    orphan_redirects: int


class EntryUpdateRequest(BaseModel):
    meanings: list[MeaningGroup] = Field(default_factory=list)
    examples: list[ExampleItem] = Field(default_factory=list)
    phrases: list[PhraseItem] = Field(default_factory=list)
    phonetic: str | None = Field(default=None)
    base_headword: str | None = Field(default=None)
    homograph_no: int | None = Field(default=None)
    entry_kind: EntryKind | None = Field(default=None)
    update_note: str | None = Field(default=None, description="更新说明（用于日志）")


class LookupTargetUpdateRequest(BaseModel):
    normalized_form: str
    lookup_label: str
    target_label: str
    target_pos: str | None = None
    preview_text: str | None = None
    rank: int = 0
    match_kind: MatchKind = MatchKind.HEADWORD


class RedirectUpdateRequest(BaseModel):
    redirect_key: str
    target_entry_key: str
    redirect_kind: RedirectKind = RedirectKind.NORMALIZED_ALIAS


class OperationLogEntry(BaseModel):
    id: int
    entry_id: int | None
    operation: str
    table_name: str
    record_id: int | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    note: str | None
    created_at: datetime


class PaginatedResult(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[dict[str, Any]]


class DataQualityIssue(BaseModel):
    issue_type: str
    issue_code: str
    severity: str
    count: int
    sample_records: list[dict[str, Any]]


class DataQualityReport(BaseModel):
    summary: dict[str, int]
    issues: list[DataQualityIssue]


def meanings_to_json(meanings: list[MeaningGroup]) -> str:
    return json.dumps([m.model_dump() for m in meanings], ensure_ascii=False)


def examples_to_json(examples: list[ExampleItem]) -> str:
    return json.dumps([e.model_dump() for e in examples], ensure_ascii=False)


def phrases_to_json(phrases: list[PhraseItem]) -> str:
    return json.dumps([p.model_dump() for p in phrases], ensure_ascii=False)


def json_to_meanings(data: Any) -> list[MeaningGroup]:
    if not data:
        return []
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return []
        data = parsed
    if not isinstance(data, list):
        return []
    result: list[MeaningGroup] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            result.append(MeaningGroup.model_validate(item))
        except Exception:
            continue
    return result


def json_to_examples(data: Any) -> list[ExampleItem]:
    if not data:
        return []
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return []
        data = parsed
    if not isinstance(data, list):
        return []
    result: list[ExampleItem] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            result.append(ExampleItem.model_validate(item))
        except Exception:
            continue
    return result


def json_to_phrases(data: Any) -> list[PhraseItem]:
    if not data:
        return []
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return []
        data = parsed
    if not isinstance(data, list):
        return []
    result: list[PhraseItem] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            result.append(PhraseItem.model_validate(item))
        except Exception:
            continue
    return result
