from pydantic import BaseModel, Field


class DictionaryMeaningDefinition(BaseModel):
    """词典释义项"""
    meaning: str = Field(description="释义内容")
    example: str | None = Field(default=None, description="例句")
    example_translation: str | None = Field(default=None, description="例句中文翻译")


class DictionaryMeaning(BaseModel):
    """词典词性及释义"""
    part_of_speech: str = Field(description="词性，如 'n.', 'v.', 'adj.'")
    definitions: list[DictionaryMeaningDefinition] = Field(description="释义列表")


class DictionaryResult(BaseModel):
    """词典查询结果"""
    word: str = Field(description="查询的单词或短语")
    phonetic: str | None = Field(default=None, description="音标，如 '/fəˈnetɪk/'")
    audio_url: str | None = Field(default=None, description="发音音频 URL")
    meanings: list[DictionaryMeaning] = Field(default_factory=list, description="词性及释义列表")
    cached: bool = Field(default=False, description="是否来自缓存")
    # MVP 新增字段
    provider: str = Field(default="ecdict_local", description="数据来源 provider")
    entry: "EcdictEntry | None" = Field(default=None, description="ECDICT 词条详情")


class EcdictEntry(BaseModel):
    """ECDICT 词条详情（MVP 扩展）"""
    word: str = Field(description="当前展示的单词")
    lemma: str | None = Field(default=None, description="词形还原后的原形")
    phonetic: str | None = Field(default=None, description="音标")
    short_meaning: str | None = Field(default=None, description="中文短释义（前50字符）")
    meanings: list[DictionaryMeaning] = Field(default_factory=list, description="词性及释义列表")
    tags: list[str] = Field(default_factory=list, description="标签列表，如 CET4/高考 等")
    exchange: list[str] = Field(default_factory=list, description="词形变换列表")
