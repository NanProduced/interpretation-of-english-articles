"""V3 Workflow Nodes for article_analysis.

v3 节点设计：
1. prepare_input - 输入清洗、分段分句
2. derive_user_config - 用户配置推导
3. vocabulary_agent - 词汇维度标注（并行）
4. grammar_agent - 结构维度标注（并行）
5. translation_agent - 逐句翻译（并行）
6. normalize_and_ground - 确定性归一化
7. repair_agent - 可选修复
8. project_render_scene - 前端协议投影
9. assemble_result - 结果收敛
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any

from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable

from app.agents.grammar_agent import GrammarAgentDeps
from app.agents.repair_agent import RepairAgentDeps
from app.agents.translation_agent import TranslationAgentDeps
from app.agents.vocabulary_agent import VocabularyAgentDeps
from app.config.settings import get_settings
from app.llm.agent_runner import extract_run_usage
from app.llm.router import resolve_model_config
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import get_model_selection
from app.llm.types import ModelSelection
from app.schemas.analysis import AnalyzeRequestMeta, ArticleStructure, RenderSceneModel, Warning
from app.schemas.internal.analysis import PreparedSentence
from app.services.analysis.draft_validators import validate_all_drafts
from app.services.analysis.input_preparation import prepare_input
from app.services.analysis.normalize_and_ground import normalize_and_ground
from app.services.analysis.projection import project_to_render_scene
from app.services.analysis.runners import (
    run_grammar_agent,
    run_translation_agent,
    run_vocabulary_agent,
)
from app.services.analysis.strategy_builder import (
    build_grammar_bundle,
    build_translation_bundle,
    build_vocabulary_bundle,
)
from app.services.analysis.user_rules import derive_user_rules
from app.workflow.analyze_state import AnalyzeState
from app.workflow.tracing import build_llm_trace_metadata

logger = logging.getLogger(__name__)
WORKFLOW_NAME = "article_analysis"
WORKFLOW_VERSION = "3.0.0"
MAX_ANNOTATION_ATTEMPTS = 3

# 触发 repair 的条件
ANCHOR_FAILURE_THRESHOLD = 0.20


def _annotation_count_by_type(annotations: list[Any]) -> dict[str, int]:
    counts = Counter(getattr(a, "type", str(type(a).__name__)) for a in annotations)
    return dict(sorted(counts.items()))


def _model_selection(config: RunnableConfig | None) -> ModelSelection | None:
    return get_model_selection(config)


def _aggregate_usage_summary(
    usages: dict[str, dict[str, object] | None],
) -> dict[str, object]:
    per_agent = {name: usage for name, usage in usages.items() if usage}
    if not per_agent:
        return {
            "available": False,
            "per_agent": {},
            "aggregate": {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            },
            "note": "workflow 当前未从 agent 结果中提取到 usage。",
        }

    def _sum_token(field: str) -> int:
        return sum(int(usage.get(field, 0) or 0) for usage in per_agent.values())

    return {
        "available": True,
        "per_agent": per_agent,
        "aggregate": {
            "input_tokens": _sum_token("input_tokens"),
            "output_tokens": _sum_token("output_tokens"),
            "total_tokens": _sum_token("total_tokens"),
        },
    }


def _empty_result(
    *,
    request_id: str,
    payload: Any,
    profile_id: str,
) -> RenderSceneModel:
    return RenderSceneModel(
        request=AnalyzeRequestMeta(
            request_id=request_id,
            source_type=payload.source_type,
            reading_goal=payload.reading_goal,
            reading_variant=payload.reading_variant,
            profile_id=profile_id,
        ),
        article=ArticleStructure(
            source_type=payload.source_type,
            source_text=payload.text,
            render_text="",
            paragraphs=[],
            sentences=[],
        ),
        translations=[],
        inline_marks=[],
        sentence_entries=[],
        warnings=[],
    )


def _build_agent_trace_metadata(
    state: AnalyzeState,
    node_name: str,
    model_selection: ModelSelection | None = None,
) -> dict[str, object]:
    payload = state["payload"]
    user_rules = state.get("user_rules") or derive_user_rules(
        payload.reading_goal, payload.reading_variant
    )
    model_config = resolve_model_config(
        get_settings(), MODEL_ROUTE_ANNOTATION_GENERATION, model_selection
    )
    return build_llm_trace_metadata(
        workflow_name=WORKFLOW_NAME,
        workflow_version=WORKFLOW_VERSION,
        request_id=payload.request_id or "",
        source_type=payload.source_type,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
        profile_id=user_rules.profile_id,
        model_name=model_config.model_name if model_config else "unconfigured",
        model_provider=model_config.provider if model_config else "unconfigured",
        extra={
            "node": node_name,
            "model_profile": model_config.profile_name if model_config else "unconfigured",
            "sentence_count": len(state["prepared_input"].sentences),
        },
    )


@traceable(name="vocabulary_llm_call", run_type="llm")
async def _run_vocabulary_llm_span(
    *,
    deps: VocabularyAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_vocabulary_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        vocab_count = (
            len(output.vocab_highlights)
            + len(output.phrase_glosses)
            + len(output.context_glosses)
        )
        current_run.set(
            metadata={
                **metadata,
                "vocabulary_annotation_count": vocab_count,
                **({"usage": usage} if usage else {}),
            },
            outputs={"vocabulary_draft": output.model_dump(mode="json")},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="grammar_llm_call", run_type="llm")
async def _run_grammar_llm_span(
    *,
    deps: GrammarAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_grammar_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        grammar_count = len(output.grammar_notes) + len(output.sentence_analyses)
        current_run.set(
            metadata={
                **metadata,
                "grammar_annotation_count": grammar_count,
                **({"usage": usage} if usage else {}),
            },
            outputs={"grammar_draft": output.model_dump(mode="json")},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="translation_llm_call", run_type="llm")
async def _run_translation_llm_span(
    *,
    deps: TranslationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_translation_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        current_run.set(
            metadata={
                **metadata,
                "translation_count": len(output.sentence_translations),
                **({"usage": usage} if usage else {}),
            },
            outputs={"translation_draft": output.model_dump(mode="json")},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


# -------------------------------------------------------------------
# Node implementations
# -------------------------------------------------------------------


async def prepare_input_node(state: AnalyzeState) -> AnalyzeState:
    payload = state["payload"]
    prepared_input = prepare_input(payload.text)
    warnings: list[Any] = []

    if not prepared_input.render_text.strip():
        return {
            "prepared_input": prepared_input,
            "warnings": warnings,
            "render_scene": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id="unresolved",
            ),
        }

    if prepared_input.text_type in {"code", "other"}:
        # 弱拦截：记录 warning 但继续流程，让 agent 有机会处理
        warnings.append(
            Warning(
                code="UNSUPPORTED_TEXT_TYPE",
                level="warning",
                message=f"文本类型为 {prepared_input.text_type}，可能影响标注质量。",
            )
        )

    if prepared_input.english_ratio < 0.45 or not prepared_input.sentences:
        # 弱拦截：记录 warning 但继续流程
        warnings.append(
            Warning(
                code="LOW_ENGLISH_RATIO",
                level="warning",
                message=f"英文占比 {prepared_input.english_ratio:.0%} 低于阈值，或无有效句子。",
            )
        )

    if prepared_input.noise_ratio >= 0.55:
        warnings.append(
            Warning(
                code="HIGH_NOISE_RATIO",
                level="warning",
                message="输入中存在较多噪音内容，结果可能需要结合原文查看。",
            )
        )

    return {"prepared_input": prepared_input, "warnings": warnings}


async def derive_user_config_node(state: AnalyzeState) -> AnalyzeState:
    payload = state["payload"]
    user_rules = derive_user_rules(payload.reading_goal, payload.reading_variant)
    return {"user_rules": user_rules}


async def _run_parallel_agents(
    state: AnalyzeState,
    model_selection: ModelSelection | None,
) -> dict[str, Any]:
    """并行运行三个 agent。"""
    prepared_input = state["prepared_input"]
    user_rules = state["user_rules"]

    sentences_data = [
        {"sentence_id": s.sentence_id, "text": s.text}
        for s in prepared_input.sentences
    ]

    vocab_bundle = build_vocabulary_bundle(user_rules)
    grammar_bundle = build_grammar_bundle(user_rules)
    translation_bundle = build_translation_bundle(user_rules)

    vocab_deps = VocabularyAgentDeps(
        sentences=sentences_data,
        prompt_strategy=vocab_bundle.prompt_strategy,
        examples=vocab_bundle.example_strategy.examples,
    )
    grammar_deps = GrammarAgentDeps(
        sentences=sentences_data,
        prompt_strategy=grammar_bundle.prompt_strategy,
        examples=grammar_bundle.example_strategy.examples,
    )
    translation_deps = TranslationAgentDeps(
        sentences=sentences_data,
        prompt_strategy=translation_bundle.prompt_strategy,
        examples=translation_bundle.example_strategy.examples,
    )

    # 构建 metadata
    vocab_meta = _build_agent_trace_metadata(state, "vocabulary_agent", model_selection)
    grammar_meta = _build_agent_trace_metadata(state, "grammar_agent", model_selection)
    translation_meta = _build_agent_trace_metadata(state, "translation_agent", model_selection)

    # 并行执行
    vocab_task = _run_vocabulary_llm_span(
        deps=vocab_deps, metadata=vocab_meta, model_selection=model_selection
    )
    grammar_task = _run_grammar_llm_span(
        deps=grammar_deps, metadata=grammar_meta, model_selection=model_selection
    )
    translation_task = _run_translation_llm_span(
        deps=translation_deps, metadata=translation_meta, model_selection=model_selection
    )

    results = await asyncio.gather(vocab_task, grammar_task, translation_task, return_exceptions=True)

    # 解析结果
    vocab_result = results[0] if not isinstance(results[0], Exception) else None
    grammar_result = results[1] if not isinstance(results[1], Exception) else None
    translation_result = results[2] if not isinstance(results[2], Exception) else None

    # 处理异常
    errors: list[Warning] = []
    if isinstance(results[0], Exception):
        logger.exception("vocabulary_agent 调用失败")
        errors.append(
            Warning(
                code="VOCABULARY_AGENT_FAILED",
                level="error",
                message=f"vocabulary agent 调用失败: {results[0]}",
            )
        )
    if isinstance(results[1], Exception):
        logger.exception("grammar_agent 调用失败")
        errors.append(
            Warning(
                code="GRAMMAR_AGENT_FAILED",
                level="error",
                message=f"grammar agent 调用失败: {results[1]}",
            )
        )
    if isinstance(results[2], Exception):
        logger.exception("translation_agent 调用失败")
        errors.append(
            Warning(
                code="TRANSLATION_AGENT_FAILED",
                level="error",
                message=f"translation agent 调用失败: {results[2]}",
            )
        )

    # 提取 output
    vocabulary_output = vocab_result.get("output") if vocab_result else None
    grammar_output = grammar_result.get("output") if grammar_result else None
    translation_output = translation_result.get("output") if translation_result else None
    vocabulary_usage = vocab_result.get("usage") if vocab_result else None
    grammar_usage = grammar_result.get("usage") if grammar_result else None
    translation_usage = translation_result.get("usage") if translation_result else None
    usage_summary = _aggregate_usage_summary(
        {
            "vocabulary": vocabulary_usage,
            "grammar": grammar_usage,
            "translation": translation_usage,
        }
    )

    return {
        "vocabulary_draft": vocabulary_output,
        "grammar_draft": grammar_output,
        "translation_draft": translation_output,
        "vocabulary_usage": vocabulary_usage,
        "grammar_usage": grammar_usage,
        "translation_usage": translation_usage,
        "usage_summary": usage_summary,
        "agent_errors": errors,
    }


async def vocabulary_agent_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    """Vocabulary agent node - returns immediately if vocabulary_draft already exists (set by parallel_agents_node)."""
    if state.get("vocabulary_draft") is not None:
        return {}
    # This node should not be reached if the graph is structured correctly
    # The parallel_agents_node handles all three agents
    return {}


async def grammar_agent_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    """Grammar agent node - returns immediately if grammar_draft already exists (set by parallel_agents_node)."""
    if state.get("grammar_draft") is not None:
        return {}
    return {}


async def translation_agent_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    """Translation agent node - returns immediately if translation_draft already exists (set by parallel_agents_node)."""
    if state.get("translation_draft") is not None:
        return {}
    return {}


async def parallel_agents_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    """Parallel agents node - runs all three agents concurrently using asyncio.gather.

    This is the single entry point for all three agents to avoid duplicate LLM calls.
    """
    if (
        state.get("vocabulary_draft") is not None
        and state.get("grammar_draft") is not None
        and state.get("translation_draft") is not None
    ):
        return {}

    model_selection = _model_selection(config)
    result = await _run_parallel_agents(state, model_selection)
    errors = result.get("agent_errors", [])

    return {
        "vocabulary_draft": result.get("vocabulary_draft"),
        "grammar_draft": result.get("grammar_draft"),
        "translation_draft": result.get("translation_draft"),
        "vocabulary_usage": result.get("vocabulary_usage"),
        "grammar_usage": result.get("grammar_usage"),
        "translation_usage": result.get("translation_usage"),
        "usage_summary": result.get("usage_summary"),
        "warnings": [*state.get("warnings", []), *errors],
    }


@traceable(name="normalize_and_ground", run_type="chain")
async def normalize_and_ground_node(state: AnalyzeState) -> AnalyzeState:
    """Normalize and ground node。"""
    payload = state["payload"]
    prepared_input = state["prepared_input"]
    vocabulary_draft = state.get("vocabulary_draft")
    grammar_draft = state.get("grammar_draft")
    translation_draft = state.get("translation_draft")

    # 如果任何 draft 缺失，返回错误
    if vocabulary_draft is None or grammar_draft is None or translation_draft is None:
        user_rules = state.get("user_rules")
        profile_id = user_rules.profile_id if user_rules else "unresolved"
        return {
            "normalized_result": None,
            "render_scene": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id=profile_id,
            ),
            "warnings": [
                *state.get("warnings", []),
                Warning(
                    code="NORMALIZE_AND_GROUND_FAILED",
                    level="error",
                    message="并行 agent 未返回有效结果，无法进行归一化",
                ),
            ],
        }

    sentences = [
        PreparedSentence.model_validate(s)
        if not isinstance(s, PreparedSentence)
        else s
        for s in prepared_input.sentences
    ]

    # 收集 draft 校验 warnings（不丢弃）
    validation_warnings = validate_all_drafts(
        vocabulary_draft, grammar_draft, translation_draft, sentences
    )
    draft_warnings = [
        Warning(code="DRAFT_VALIDATION", level="warning", message=msg)
        for msg in validation_warnings
    ]

    normalized_result = normalize_and_ground(
        vocabulary_draft=vocabulary_draft,
        grammar_draft=grammar_draft,
        translation_draft=translation_draft,
        sentences=sentences,
        profile_id=state["user_rules"].profile_id,
    )

    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata={
                "normalized_annotation_count": len(normalized_result.annotations),
                "drop_log_count": len(normalized_result.drop_log),
                "translation_count": len(normalized_result.sentence_translations),
            },
            outputs={
                "normalized_result": normalized_result.model_dump(mode="json"),
                "drop_log": [d.model_dump(mode="json") for d in normalized_result.drop_log],
            },
        )

    return {
        "normalized_result": normalized_result,
        "drop_log": normalized_result.drop_log,
        "warnings": [*state.get("warnings", []), *draft_warnings],
    }


async def repair_agent_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    """Repair agent node（条件触发）。"""
    normalized_result = state.get("normalized_result")

    # 检查是否需要 repair
    if normalized_result is not None:
        drop_count = len(normalized_result.drop_log) if normalized_result.drop_log else 0
        annotation_count = len(normalized_result.annotations)
        if annotation_count > 0:
            failure_ratio = drop_count / (annotation_count + drop_count)
        else:
            failure_ratio = 0.0

        if failure_ratio <= ANCHOR_FAILURE_THRESHOLD:
            # 不需要 repair
            return {"repair_request": None}

    # 需要 repair
    prepared_input = state["prepared_input"]
    vocabulary_draft = state.get("vocabulary_draft")
    grammar_draft = state.get("grammar_draft")
    translation_draft = state.get("translation_draft")

    if vocabulary_draft is None or grammar_draft is None or translation_draft is None:
        return {"repair_request": None}

    error_context = (
        f"normalized_result 锚点失败率过高或结构异常。"
        f"drop_log: {len(normalized_result.drop_log) if normalized_result else 0} items"
    )

    repair_deps = RepairAgentDeps(
        sentences=[
            {"sentence_id": s.sentence_id, "text": s.text}
            for s in prepared_input.sentences
        ],
        original_drafts={
            "vocabulary_draft": vocabulary_draft.model_dump(mode="json") if vocabulary_draft else {},
            "grammar_draft": grammar_draft.model_dump(mode="json") if grammar_draft else {},
            "translation_draft": translation_draft.model_dump(mode="json") if translation_draft else {},
        },
    )
    repair_meta = _build_agent_trace_metadata(state, "repair_agent", _model_selection(config))
    repair_meta["extra"] = {**(repair_meta.get("extra") or {}), "error_context": error_context}

    try:
        repair_result = await _run_repair_llm_span(
            deps=repair_deps, metadata=repair_meta, error_context=error_context
        )
        repaired_result = repair_result.get("output")
        repair_usage = repair_result.get("usage")
        usage_summary = _aggregate_usage_summary(
            {
                "vocabulary": state.get("vocabulary_usage"),
                "grammar": state.get("grammar_usage"),
                "translation": state.get("translation_usage"),
                "repair": repair_usage,
            }
        )
        return {
            "repair_request": {"error_context": error_context, "repaired": True},
            "normalized_result": repaired_result,
            "drop_log": repaired_result.drop_log if repaired_result else state.get("drop_log", []),
            "repair_usage": repair_usage,
            "usage_summary": usage_summary,
        }
    except Exception:
        logger.exception("repair_agent 调用失败")
        return {
            "repair_request": {"error_context": error_context, "repaired": False},
            "warnings": [
                *state.get("warnings", []),
                Warning(
                    code="REPAIR_AGENT_FAILED",
                    level="warning",
                    message="repair agent 调用失败，继续使用归一化结果",
                ),
            ],
        }


@traceable(name="repair_llm_call", run_type="llm")
async def _run_repair_llm_span(
    *,
    deps: RepairAgentDeps,
    metadata: dict[str, object],
    error_context: str,
) -> dict[str, Any]:
    from app.agents.repair_agent import build_repair_prompt, get_repair_agent
    from app.llm.agent_runner import run_agent_with_route
    from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION

    result = await run_agent_with_route(
        agent=get_repair_agent(),
        prompt=build_repair_prompt(deps, error_context),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=None,
    )
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None and usage is not None:
        current_run.set(metadata={**metadata, "usage": usage})
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="project_render_scene", run_type="chain")
async def project_render_scene_node(state: AnalyzeState) -> AnalyzeState:
    """Project to render scene node。"""
    payload = state["payload"]
    prepared_input = state["prepared_input"]
    normalized_result = state.get("normalized_result")
    user_rules = state.get("user_rules")

    if normalized_result is None:
        return {
            "render_scene": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id=user_rules.profile_id if user_rules else "unresolved",
            ),
        }

    # 将 NormalizedAnnotationResult 转换为 AnnotationOutput 格式以兼容现有 projection
    from app.schemas.internal.analysis import AnnotationOutput

    annotation_output = AnnotationOutput(
        annotations=normalized_result.annotations,
        sentence_translations=normalized_result.sentence_translations,
    )

    projection_outcome = project_to_render_scene(
        annotation_output=annotation_output,
        prepared_input=prepared_input,
        source_type=payload.source_type,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
        profile_id=user_rules.profile_id if user_rules else "unknown",
        request_id=payload.request_id or "",
    )

    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata={
                "inline_marks_count": len(projection_outcome.result.inline_marks),
                "sentence_entries_count": len(projection_outcome.result.sentence_entries),
                "projection_warnings_count": len(projection_outcome.warnings),
            },
        )

    return {
        "render_scene": projection_outcome.result,
        "warnings": [
            *state.get("warnings", []),
            *[Warning(**w) for w in projection_outcome.warnings],
        ],
    }


async def assemble_result_node(state: AnalyzeState) -> AnalyzeState:
    """Assemble result node。"""
    render_scene = state.get("render_scene")

    if render_scene is None:
        payload = state["payload"]
        user_rules = state.get("user_rules")
        profile_id = user_rules.profile_id if user_rules else "unresolved"
        return {
            "render_scene": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id=profile_id,
            ),
        }

    # 确保 warnings 不重复（project_render_scene_node 已将 projection warnings
    # 合并进 render_scene.warnings）
    existing_warnings = state.get("warnings", [])
    if existing_warnings and hasattr(render_scene, "warnings"):
        # 去重：基于 code + sentence_id 组合键，保留首次出现的 warning
        seen_keys = {(w.code, w.sentence_id) for w in render_scene.warnings}
        for w in existing_warnings:
            key = (w.code, w.sentence_id)
            if key not in seen_keys:
                render_scene.warnings.append(w)
                seen_keys.add(key)

    return {"render_scene": render_scene}
