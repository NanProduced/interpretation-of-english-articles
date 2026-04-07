from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class DictionaryMeaningDefinition(BaseModel):
    meaning: str = Field(description="释义内容")
    example: str | None = Field(default=None, description="例句")
    example_translation: str | None = Field(default=None, description="例句中文翻译")


class DictionaryMeaning(BaseModel):
    part_of_speech: str = Field(description="词性，如 'n.', 'v.', 'adj.'")
    definitions: list[DictionaryMeaningDefinition] = Field(description="释义列表")


class DictionaryExample(BaseModel):
    example: str = Field(description="英文例句")
    example_translation: str | None = Field(default=None, description="例句中文翻译")


class DictionaryPhrase(BaseModel):
    phrase: str = Field(description="短语")
    meaning: str | None = Field(default=None, description="短语释义")


class DictionaryEntryPayload(BaseModel):
    id: int = Field(description="词条 ID")
    word: str = Field(description="当前展示的词头")
    base_word: str | None = Field(default=None, description="去掉同形编号的基础词头")
    homograph_no: int | None = Field(default=None, description="同形编号")
    phonetic: str | None = Field(default=None, description="音标")
    primary_pos: str | None = Field(default=None, description="主词性")
    meanings: list[DictionaryMeaning] = Field(default_factory=list, description="词性及释义列表")
    examples: list[DictionaryExample] = Field(default_factory=list, description="例句列表")
    phrases: list[DictionaryPhrase] = Field(default_factory=list, description="短语列表")
    entry_kind: Literal["entry", "fragment"] = Field(description="词条类型")


class DictionaryCandidate(BaseModel):
    entry_id: int = Field(description="候选词条 ID")
    label: str = Field(description="候选标签")
    part_of_speech: str | None = Field(default=None, description="候选词性")
    preview: str | None = Field(default=None, description="候选预览")
    entry_kind: Literal["entry", "fragment"] = Field(description="候选词条类型")


class DictionaryResultBase(BaseModel):
    result_type: str = Field(description="结果类型")
    query: str = Field(description="原始查询词")
    provider: str = Field(default="tecd3", description="数据来源 provider")
    cached: bool = Field(default=False, description="是否来自缓存")


class DictionaryEntryResult(DictionaryResultBase):
    result_type: Literal["entry"] = "entry"
    entry: DictionaryEntryPayload = Field(description="词条详情")


class DictionaryDisambiguationResult(DictionaryResultBase):
    result_type: Literal["disambiguation"] = "disambiguation"
    candidates: list[DictionaryCandidate] = Field(default_factory=list, description="候选词条列表")


DictionaryLookupResult = Annotated[
    DictionaryEntryResult | DictionaryDisambiguationResult,
    Field(discriminator="result_type"),
]

_LOOKUP_RESULT_ADAPTER = TypeAdapter(DictionaryLookupResult)


def validate_lookup_result(data: object) -> dict:
    validated = _LOOKUP_RESULT_ADAPTER.validate_python(data)
    if isinstance(validated, BaseModel):
        return validated.model_dump()
    return validated
