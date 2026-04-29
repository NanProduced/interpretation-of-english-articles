"""Grammar RAG service — fallback skeleton.

Per grammar-rag-design.md, this module will implement:
- Build query_text from prepared sentences
- Call Bailian Embedding
- Query Zilliz ANN search
- Call Bailian Rerank
- Return final ExampleEntry list

Current status: fallback skeleton (RAG Readiness Gate).
Retrieval backends (Zilliz, Bailian) are not yet wired.
All calls currently return empty results, triggering fallback to baseline.

When the external services are ready, _retrieve_from_backend() will be
replaced with real embedding + ANN + rerank logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.analysis.prompting.example_strategy import ExampleEntry

logger = logging.getLogger(__name__)


@dataclass
class RAGQueryResult:
    """RAG 查询结果，携带诊断信息。"""

    examples: list[ExampleEntry] = field(default_factory=list)
    selection_mode: str = "rag_fallback"
    fallback_reason: str | None = None
    example_count: int = 0
    query_count: int = 0

    @property
    def is_fallback(self) -> bool:
        return self.selection_mode in ("rag_fallback", "baseline")


async def query_grammar_rag(
    variant: str,
    sentences: list[dict],
    output_type: str = "grammar_note",
    top_k: int = 5,
) -> RAGQueryResult:
    """查询 grammar RAG 示例池。

    当前为 fallback 骨架实现：
    - 空结果 → 回退 baseline
    - 异常 → 回退 baseline + 记录 fallback_reason
    - 低置信度 → 回退 baseline

    Args:
        variant: 阅读变体，如 gaokao / cet / kaoyan
        sentences: 输入句子列表 [{"sentence_id": str, "text": str}]
        output_type: grammar_note 或 sentence_analysis
        top_k: 召回上限

    Returns:
        RAGQueryResult，当前始终返回空 examples 触发 fallback。
    """
    if not sentences:
        return RAGQueryResult(
            fallback_reason="no_input_sentences",
            selection_mode="rag_fallback",
        )

    try:
        candidates = await _retrieve_from_backend(
            variant=variant,
            sentences=sentences,
            output_type=output_type,
            top_k=top_k,
        )
    except Exception as exc:
        logger.warning(
            "Grammar RAG retrieval failed, falling back to baseline: %s",
            exc,
            exc_info=True,
        )
        return RAGQueryResult(
            fallback_reason=f"retrieval_error: {type(exc).__name__}: {exc}",
            selection_mode="rag_fallback",
        )

    if not candidates:
        return RAGQueryResult(
            fallback_reason="empty_candidates",
            selection_mode="rag_fallback",
            query_count=len(sentences),
        )

    # 低置信度检查（当外部服务接入后，此处会检查 rerank score）
    filtered = _apply_confidence_filter(candidates)
    if not filtered:
        return RAGQueryResult(
            fallback_reason="low_confidence",
            selection_mode="rag_fallback",
            query_count=len(sentences),
        )

    return RAGQueryResult(
        examples=filtered,
        selection_mode="rag",
        example_count=len(filtered),
        query_count=len(sentences),
    )


async def _retrieve_from_backend(
    variant: str,
    sentences: list[dict],
    output_type: str,
    top_k: int,
) -> list[ExampleEntry]:
    """调用外部检索后端（Zilliz + Bailian）。

    当前返回空列表（RAG Readiness Gate 阶段）。
    后续接入时替换此函数的实现。
    """
    # TODO: 接入 Bailian Embedding + Zilliz ANN + Bailian Rerank
    # 详见 docs/architecture/grammar-rag-design.md §5, §8-§12
    return []


def _apply_confidence_filter(
    candidates: list[ExampleEntry],
    min_score: float = 0.0,
) -> list[ExampleEntry]:
    """过滤低置信度候选。

    当前无评分机制，直接透传。
    后续接入 rerank 后，此处会基于 rerank score 过滤。
    """
    # TODO: 按 rerank score 过滤低质量候选
    return candidates


def build_rag_debug_info(result: RAGQueryResult) -> dict[str, Any]:
    """构造 RAG 调试信息，用于 prompt debug 输出。"""
    return {
        "selection_mode": result.selection_mode,
        "example_count": result.example_count,
        "fallback_reason": result.fallback_reason,
        "query_count": result.query_count,
        "is_fallback": result.is_fallback,
    }
