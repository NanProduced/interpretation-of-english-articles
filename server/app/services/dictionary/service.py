from app.services.dictionary.providers.dictionaryapi import DictionaryApiProvider
from app.services.dictionary.schemas import DictionaryResult


class DictionaryService:
    """词典服务"""

    def __init__(self) -> None:
        self._provider = DictionaryApiProvider()

    def lookup(self, word: str) -> DictionaryResult:
        """
        查询单词释义。

        - 归一化查询词（trim + lowercase）
        - 调用 provider.fetch()（内部处理缓存）
        - 404 → ValueError → 映射为 HTTP 404
        - 其他错误 → HTTP 502
        """
        normalized = word.strip().lower()
        if not normalized:
            raise ValueError("Word cannot be empty")

        try:
            data = self._provider.fetch(normalized)
            return DictionaryResult.model_validate(data)
        except ValueError as exc:
            # 404 来自 provider，转换为外部异常
            raise LookupError(str(exc)) from exc
