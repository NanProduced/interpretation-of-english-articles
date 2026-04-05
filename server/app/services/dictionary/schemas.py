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
