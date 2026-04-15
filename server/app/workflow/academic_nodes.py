"""Workflow Nodes for Academic workflow.

节点设计：
1. prepare_input - 输入清洗、分段分句（复用 learning 节点）
2. derive_user_config - 用户配置推导（复用 learning 节点）
3. parallel_academic_agents - 术语、逻辑、解释性理解并行标注
4. structure_agent - 结构分析（段落功能 + 全文摘要）
5. academic_translation_agent - 学术翻译
6. normalize_academic - 学术标注归一化
7. project_academic_scene - 学术场景投影
8. assemble_academic_result - 结果收敛
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable

from app.agents.academic_translation_agent import AcademicTranslationAgentDeps
from app.agents.interpretation_agent import InterpretationAgentDeps
from app.agents.logic_agent import LogicAgentDeps
from app.agents.structure_agent import StructureAgentDeps
from app.agents.term_agent import TermAgentDeps
from app.config.settings import get_settings
from app.llm.agent_runner import extract_run_usage
from app.llm.router import resolve_model_config
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import get_model_selection
from app.llm.types import ModelSelection
from app.schemas.analysis import AnalyzeRequestMeta, ArticleStructure, Warning
from app.schemas.internal.analysis import (
    AcademicAnnotationOutput,
    DocumentSummary,
    InterpretationNote,
    LogicNote,
    ParagraphRole,
    PreparedSentence,
    TermNote,
)
from app.schemas.internal.academic_drafts import (
    InterpretationDraft,
    LogicDraft,
    StructureDraft,
    TermDraft,
    AcademicTranslationDraft,
)
from app.services.analysis.postprocess.anchor_resolution import resolve_text_anchor
from app.services.analysis.preprocess.input_preparation import PreparedInput
from app.services.analysis.prompting.academic_strategy_builder import (
    build_academic_translation_bundle,
    build_interpretation_bundle,
    build_logic_bundle,
    build_structure_bundle,
    build_term_bundle,
)
from app.services.analysis.runtime.academic_runners import (
    run_academic_translation_agent,
    run_interpretation_agent,
    run_logic_agent,
    run_structure_agent,
    run_term_agent,
)
from app.workflow.academic_state import AcademicState
from app.workflow.tracing import build_llm_trace_metadata

logger = logging.getLogger(__name__)
WORKFLOW_NAME = "academic_analysis"
WORKFLOW_VERSION = "1.0.0"


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


def _set_current_run(
    *,
    run_tree: Any,
    metadata: dict[str, object],
    outputs: dict[str, object] | None = None,
    usage_metadata: dict[str, object] | None = None,
) -> None:
    kwargs: dict[str, object] = {"metadata": metadata}
    if outputs is not None:
        kwargs["outputs"] = outputs
    if usage_metadata is not None:
        kwargs["usage_metadata"] = usage_metadata
    run_tree.set(**kwargs)


def _empty_academic_result(
    *,
    request_id: str,
    payload: Any,
    profile_id: str,
) -> dict[str, object]:
    return {
        "schema_version": "3.0.0",
        "request": AnalyzeRequestMeta(
            request_id=request_id,
            source_type=payload.source_type,
            reading_goal=payload.reading_goal,
            reading_variant=payload.reading_variant,
            profile_id=profile_id,
        ).model_dump(mode="json"),
        "article": ArticleStructure(
            source_type=payload.source_type,
            source_text=payload.text,
            render_text="",
            paragraphs=[],
            sentences=[],
        ).model_dump(mode="json"),
        "user_facing_state": "normal",
        "translations": [],
        "term_notes": [],
        "logic_notes": [],
        "interpretation_notes": [],
        "paragraph_roles": [],
        "document_summary": None,
        "warnings": [],
    }


def _build_academic_agent_trace_metadata(
    state: AcademicState,
    node_name: str,
    model_selection: ModelSelection | None = None,
) -> dict[str, object]:
    payload = state["payload"]
    plan = state["goal_execution_plan"]
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
        profile_id=plan.prompt_profile,
        model_name=model_config.model_name if model_config else "unconfigured",
        model_provider=model_config.provider if model_config else "unconfigured",
        extra={
            "node": node_name,
            "model_profile": model_config.profile_name if model_config else "unconfigured",
            "sentence_count": len(state["prepared_input"].sentences),
        },
    )


@traceable(name="term_llm_call", run_type="llm")
async def _run_term_llm_span(
    *,
    deps: TermAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_term_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        term_count = len(output.term_notes) if output and hasattr(output, "term_notes") else 0
        _set_current_run(
            run_tree=current_run,
            metadata={
                **metadata,
                "term_annotation_count": term_count,
            },
            usage_metadata=usage,
            outputs={"term_draft": output.model_dump(mode="json") if output else {}},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="logic_llm_call", run_type="llm")
async def _run_logic_llm_span(
    *,
    deps: LogicAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_logic_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        logic_count = len(output.logic_notes) if output and hasattr(output, "logic_notes") else 0
        _set_current_run(
            run_tree=current_run,
            metadata={
                **metadata,
                "logic_annotation_count": logic_count,
            },
            usage_metadata=usage,
            outputs={"logic_draft": output.model_dump(mode="json") if output else {}},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="interpretation_llm_call", run_type="llm")
async def _run_interpretation_llm_span(
    *,
    deps: InterpretationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_interpretation_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        interpretation_count = len(output.interpretation_notes) if output and hasattr(output, "interpretation_notes") else 0
        _set_current_run(
            run_tree=current_run,
            metadata={
                **metadata,
                "interpretation_annotation_count": interpretation_count,
            },
            usage_metadata=usage,
            outputs={"interpretation_draft": output.model_dump(mode="json") if output else {}},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="structure_llm_call", run_type="llm")
async def _run_structure_llm_span(
    *,
    deps: StructureAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_structure_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        paragraph_count = len(output.paragraph_roles) if output and hasattr(output, "paragraph_roles") else 0
        has_summary = output.document_summary is not None if output and hasattr(output, "document_summary") else False
        _set_current_run(
            run_tree=current_run,
            metadata={
                **metadata,
                "paragraph_role_count": paragraph_count,
                "has_document_summary": has_summary,
            },
            usage_metadata=usage,
            outputs={"structure_draft": output.model_dump(mode="json") if output else {}},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


@traceable(name="academic_translation_llm_call", run_type="llm")
async def _run_academic_translation_llm_span(
    *,
    deps: AcademicTranslationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_academic_translation_agent(deps, model_selection=model_selection)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        output = result.output if hasattr(result, "output") else result
        translation_count = len(output.sentence_translations) if output and hasattr(output, "sentence_translations") else 0
        _set_current_run(
            run_tree=current_run,
            metadata={
                **metadata,
                "translation_count": translation_count,
            },
            usage_metadata=usage,
            outputs={"academic_translation_draft": output.model_dump(mode="json") if output else {}},
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def _run_parallel_academic_agents(
    state: AcademicState,
    model_selection: ModelSelection | None,
) -> dict[str, Any]:
    """并行运行 term、logic、interpretation 三个 agent。"""
    prepared_input = state["prepared_input"]
    plan = state["goal_execution_plan"]

    sentences_data = [
        {"sentence_id": s.sentence_id, "text": s.text}
        for s in prepared_input.sentences
    ]

    term_bundle = build_term_bundle(plan)
    logic_bundle = build_logic_bundle(plan)
    interpretation_bundle = build_interpretation_bundle(plan)

    term_deps = TermAgentDeps(
        sentences=sentences_data,
        prompt_strategy=term_bundle.prompt_strategy,
        examples=term_bundle.example_strategy.examples,
    )
    logic_deps = LogicAgentDeps(
        sentences=sentences_data,
        prompt_strategy=logic_bundle.prompt_strategy,
        examples=logic_bundle.example_strategy.examples,
    )
    interpretation_deps = InterpretationAgentDeps(
        sentences=sentences_data,
        prompt_strategy=interpretation_bundle.prompt_strategy,
        examples=interpretation_bundle.example_strategy.examples,
    )

    term_meta = _build_academic_agent_trace_metadata(state, "term_agent", model_selection)
    logic_meta = _build_academic_agent_trace_metadata(state, "logic_agent", model_selection)
    interpretation_meta = _build_academic_agent_trace_metadata(state, "interpretation_agent", model_selection)

    term_task = _run_term_llm_span(
        deps=term_deps, metadata=term_meta, model_selection=model_selection
    )
    logic_task = _run_logic_llm_span(
        deps=logic_deps, metadata=logic_meta, model_selection=model_selection
    )
    interpretation_task = _run_interpretation_llm_span(
        deps=interpretation_deps, metadata=interpretation_meta, model_selection=model_selection
    )

    results = await asyncio.gather(term_task, logic_task, interpretation_task, return_exceptions=True)

    term_result = results[0] if not isinstance(results[0], Exception) else None
    logic_result = results[1] if not isinstance(results[1], Exception) else None
    interpretation_result = results[2] if not isinstance(results[2], Exception) else None

    errors: list[Warning] = []
    if isinstance(results[0], Exception):
        logger.exception("term_agent 调用失败")
        errors.append(Warning(code="TERM_AGENT_FAILED", level="error", message=f"term agent 调用失败: {results[0]}"))
    if isinstance(results[1], Exception):
        logger.exception("logic_agent 调用失败")
        errors.append(Warning(code="LOGIC_AGENT_FAILED", level="error", message=f"logic agent 调用失败: {results[1]}"))
    if isinstance(results[2], Exception):
        logger.exception("interpretation_agent 调用失败")
        errors.append(Warning(code="INTERPRETATION_AGENT_FAILED", level="error", message=f"interpretation agent 调用失败: {results[2]}"))

    term_output = term_result.get("output") if term_result else None
    logic_output = logic_result.get("output") if logic_result else None
    interpretation_output = interpretation_result.get("output") if interpretation_result else None
    term_usage = term_result.get("usage") if term_result else None
    logic_usage = logic_result.get("usage") if logic_result else None
    interpretation_usage = interpretation_result.get("usage") if interpretation_result else None

    return {
        "term_draft": term_output,
        "logic_draft": logic_output,
        "interpretation_draft": interpretation_output,
        "term_usage": term_usage,
        "logic_usage": logic_usage,
        "interpretation_usage": interpretation_usage,
        "agent_errors": errors,
    }


async def parallel_academic_agents_node(state: AcademicState, config: RunnableConfig) -> AcademicState:
    """Parallel academic agents node."""
    model_selection = _model_selection(config)
    result = await _run_parallel_academic_agents(state, model_selection)
    errors = result.get("agent_errors", [])

    return {
        "term_draft": result.get("term_draft"),
        "logic_draft": result.get("logic_draft"),
        "interpretation_draft": result.get("interpretation_draft"),
        "term_usage": result.get("term_usage"),
        "logic_usage": result.get("logic_usage"),
        "interpretation_usage": result.get("interpretation_usage"),
        "parallel_agent_errors": errors,
    }


async def structure_agent_node(state: AcademicState, config: RunnableConfig) -> AcademicState:
    """Structure agent node（段落功能 + 全文摘要）。"""
    model_selection = _model_selection(config)
    prepared_input = state["prepared_input"]
    plan = state["goal_execution_plan"]

    paragraphs_data = [
        {"paragraph_id": p.paragraph_id, "text": p.text}
        for p in prepared_input.paragraphs
    ]

    structure_bundle = build_structure_bundle(plan)
    structure_deps = StructureAgentDeps(
        paragraphs=paragraphs_data,
        full_text=prepared_input.render_text,
        prompt_strategy=structure_bundle.prompt_strategy,
        examples=structure_bundle.example_strategy.examples,
    )

    structure_meta = _build_academic_agent_trace_metadata(state, "structure_agent", model_selection)

    try:
        result = await _run_structure_llm_span(
            deps=structure_deps, metadata=structure_meta, model_selection=model_selection
        )
        structure_output = result.get("output")
        structure_usage = result.get("usage")

        return {
            "structure_draft": structure_output,
            "structure_usage": structure_usage,
        }
    except Exception:
        logger.exception("structure_agent 调用失败")
        return {
            "structure_draft": None,
            "structure_agent_errors": [
                Warning(code="STRUCTURE_AGENT_FAILED", level="warning", message="structure agent 调用失败，继续使用其他结果"),
            ],
        }


async def academic_translation_agent_node(state: AcademicState, config: RunnableConfig) -> AcademicState:
    """Academic translation agent node。"""
    model_selection = _model_selection(config)
    prepared_input = state["prepared_input"]
    plan = state["goal_execution_plan"]

    sentences_data = [
        {"sentence_id": s.sentence_id, "text": s.text}
        for s in prepared_input.sentences
    ]

    translation_bundle = build_academic_translation_bundle(plan)
    translation_deps = AcademicTranslationAgentDeps(
        sentences=sentences_data,
        prompt_strategy=translation_bundle.prompt_strategy,
        examples=translation_bundle.example_strategy.examples,
    )

    translation_meta = _build_academic_agent_trace_metadata(state, "academic_translation_agent", model_selection)

    try:
        result = await _run_academic_translation_llm_span(
            deps=translation_deps, metadata=translation_meta, model_selection=model_selection
        )
        translation_output = result.get("output")
        translation_usage = result.get("usage")

        return {
            "translation_draft": translation_output,
            "translation_usage": translation_usage,
        }
    except Exception:
        logger.exception("academic_translation_agent 调用失败")
        return {
            "translation_draft": None,
            "translation_agent_errors": [
                Warning(code="ACADEMIC_TRANSLATION_AGENT_FAILED", level="warning", message="academic translation agent 调用失败，继续使用其他结果"),
            ],
        }


@traceable(name="normalize_academic", run_type="chain")
async def normalize_academic_node(state: AcademicState) -> AcademicState:
    """Normalize academic annotations node。

    对 academic 标注进行归一化处理：
    1. 验证锚点有效性
    2. 去重
    3. 密度控制
    """
    prepared_input = state["prepared_input"]
    term_draft = state.get("term_draft")
    logic_draft = state.get("logic_draft")
    interpretation_draft = state.get("interpretation_draft")
    structure_draft = state.get("structure_draft")
    translation_draft = state.get("translation_draft")

    sentence_map = {s.sentence_id: s for s in prepared_input.sentences}
    paragraph_map = {p.paragraph_id: p for p in prepared_input.paragraphs}

    term_notes: list[TermNote] = []
    logic_notes: list[LogicNote] = []
    interpretation_notes: list[InterpretationNote] = []
    paragraph_roles: list[ParagraphRole] = []
    document_summary: DocumentSummary | None = None
    warnings: list[Warning] = []

    if term_draft and hasattr(term_draft, "term_notes"):
        for note in term_draft.term_notes:
            sentence_obj = sentence_map.get(note.sentence_id)
            if sentence_obj is None:
                warnings.append(Warning(
                    code="TERM_NOTE_INVALID_SENTENCE",
                    level="warning",
                    message=f"TermNote 引用无效 sentence_id: {note.sentence_id}",
                    sentence_id=note.sentence_id,
                ))
                continue
            resolved = resolve_text_anchor(sentence_obj, note.text, note.occurrence)
            if resolved is None:
                warnings.append(Warning(
                    code="TERM_NOTE_ANCHOR_FAILED",
                    level="warning",
                    message=f"TermNote 锚点解析失败: {note.text}",
                    sentence_id=note.sentence_id,
                ))
                continue
            term_notes.append(note)

    if logic_draft and hasattr(logic_draft, "logic_notes"):
        for note in logic_draft.logic_notes:
            sentence_obj = sentence_map.get(note.sentence_id)
            if sentence_obj is None:
                warnings.append(Warning(
                    code="LOGIC_NOTE_INVALID_SENTENCE",
                    level="warning",
                    message=f"LogicNote 引用无效 sentence_id: {note.sentence_id}",
                    sentence_id=note.sentence_id,
                ))
                continue
            logic_notes.append(note)

    if interpretation_draft and hasattr(interpretation_draft, "interpretation_notes"):
        for note in interpretation_draft.interpretation_notes:
            sentence_obj = sentence_map.get(note.sentence_id)
            if sentence_obj is None:
                warnings.append(Warning(
                    code="INTERPRETATION_NOTE_INVALID_SENTENCE",
                    level="warning",
                    message=f"InterpretationNote 引用无效 sentence_id: {note.sentence_id}",
                    sentence_id=note.sentence_id,
                ))
                continue
            interpretation_notes.append(note)

    if structure_draft and hasattr(structure_draft, "paragraph_roles"):
        for role in structure_draft.paragraph_roles:
            paragraph_obj = paragraph_map.get(role.paragraph_id)
            if paragraph_obj is None:
                warnings.append(Warning(
                    code="PARAGRAPH_ROLE_INVALID_PARAGRAPH",
                    level="warning",
                    message=f"ParagraphRole 引用无效 paragraph_id: {role.paragraph_id}",
                ))
                continue
            paragraph_roles.append(role)

    if structure_draft and hasattr(structure_draft, "document_summary"):
        document_summary = structure_draft.document_summary

    sentence_translations = []
    if translation_draft and hasattr(translation_draft, "sentence_translations"):
        sentence_translations = translation_draft.sentence_translations

    academic_output = AcademicAnnotationOutput(
        term_notes=term_notes,
        logic_notes=logic_notes,
        interpretation_notes=interpretation_notes,
        paragraph_roles=paragraph_roles,
        document_summary=document_summary,
        sentence_translations=sentence_translations,
    )

    term_usage = state.get("term_usage")
    logic_usage = state.get("logic_usage")
    interpretation_usage = state.get("interpretation_usage")
    structure_usage = state.get("structure_usage")
    translation_usage = state.get("translation_usage")

    usage_summary = _aggregate_usage_summary({
        "term": term_usage,
        "logic": logic_usage,
        "interpretation": interpretation_usage,
        "structure": structure_usage,
        "academic_translation": translation_usage,
    })

    parallel_agent_errors = state.get("parallel_agent_errors", [])
    structure_agent_errors = state.get("structure_agent_errors", [])
    translation_agent_errors = state.get("translation_agent_errors", [])

    all_warnings = [
        *state.get("warnings", []),
        *parallel_agent_errors,
        *structure_agent_errors,
        *translation_agent_errors,
        *warnings,
    ]

    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata={
                "term_notes_count": len(term_notes),
                "logic_notes_count": len(logic_notes),
                "interpretation_notes_count": len(interpretation_notes),
                "paragraph_roles_count": len(paragraph_roles),
                "has_document_summary": document_summary is not None,
                "translation_count": len(sentence_translations),
            },
            outputs={
                "academic_output": academic_output.model_dump(mode="json"),
            },
        )

    return {
        "academic_output": academic_output,
        "usage_summary": usage_summary,
        "warnings": all_warnings,
    }


def _build_academic_article(prepared_input: PreparedInput, source_type: str) -> dict[str, object]:
    return {
        "source_type": source_type,
        "source_text": prepared_input.source_text,
        "render_text": prepared_input.render_text,
        "paragraphs": [
            {
                "paragraph_id": paragraph.paragraph_id,
                "text": paragraph.text,
                "render_span": {
                    "start": paragraph.render_span.start,
                    "end": paragraph.render_span.end,
                },
                "sentence_ids": paragraph.sentence_ids,
            }
            for paragraph in prepared_input.paragraphs
        ],
        "sentences": [
            {
                "sentence_id": sentence.sentence_id,
                "paragraph_id": sentence.paragraph_id,
                "text": sentence.text,
                "sentence_span": {
                    "start": sentence.sentence_span.start,
                    "end": sentence.sentence_span.end,
                },
            }
            for sentence in prepared_input.sentences
        ],
    }


@traceable(name="project_academic_scene", run_type="chain")
async def project_academic_scene_node(state: AcademicState) -> AcademicState:
    """Project to academic scene node。

    将 academic 标注投影为前端可渲染的格式。
    """
    payload = state["payload"]
    prepared_input = state["prepared_input"]
    academic_output = state.get("academic_output")
    plan = state.get("goal_execution_plan")

    if academic_output is None:
        return {
            "render_scene": _empty_academic_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id=plan.prompt_profile if plan else "unresolved",
            ),
        }

    translations = [
        {"sentence_id": item.sentence_id, "translation_zh": item.translation_zh}
        for item in academic_output.sentence_translations
    ]

    term_notes = [
        {
            "type": note.type,
            "sentence_id": note.sentence_id,
            "text": note.text,
            "occurrence": note.occurrence,
            "category": note.category,
            "term_zh": note.term_zh,
            "definition": note.definition,
            "context_hint": note.context_hint,
        }
        for note in academic_output.term_notes
    ]

    logic_notes = [
        {
            "type": note.type,
            "sentence_id": note.sentence_id,
            "spans": [
                {"text": span.text, "occurrence": span.occurrence, "role": span.role}
                for span in note.spans
            ],
            "relation": note.relation,
            "label": note.label,
            "explanation_zh": note.explanation_zh,
        }
        for note in academic_output.logic_notes
    ]

    interpretation_notes = [
        {
            "type": note.type,
            "sentence_id": note.sentence_id,
            "spans": [
                {"text": span.text, "occurrence": span.occurrence, "role": span.role}
                for span in note.spans
            ] if note.spans else None,
            "literal_translation": note.literal_translation,
            "intended_meaning_zh": note.intended_meaning_zh,
            "why_not_literal": note.why_not_literal,
            "rhetorical_purpose": note.rhetorical_purpose,
        }
        for note in academic_output.interpretation_notes
    ]

    paragraph_roles = [
        {
            "type": role.type,
            "paragraph_id": role.paragraph_id,
            "role": role.role,
            "label": role.label,
            "summary_zh": role.summary_zh,
            "key_claim": role.key_claim,
        }
        for role in academic_output.paragraph_roles
    ]

    document_summary = None
    if academic_output.document_summary:
        document_summary = {
            "type": academic_output.document_summary.type,
            "research_problem_zh": academic_output.document_summary.research_problem_zh,
            "methodology_zh": academic_output.document_summary.methodology_zh,
            "key_findings_zh": academic_output.document_summary.key_findings_zh,
            "limitations_zh": academic_output.document_summary.limitations_zh,
            "overall_significance_zh": academic_output.document_summary.overall_significance_zh,
        }

    existing_warnings = state.get("warnings", [])
    warning_dicts = [
        {
            "code": w.code,
            "level": w.level,
            "message": w.message,
            "sentence_id": w.sentence_id,
            "annotation_id": None,
        }
        for w in existing_warnings
    ]

    render_scene = {
        "schema_version": "3.0.0",
        "request": {
            "request_id": payload.request_id or "",
            "source_type": payload.source_type,
            "reading_goal": payload.reading_goal,
            "reading_variant": payload.reading_variant,
            "profile_id": plan.prompt_profile if plan else "unknown",
        },
        "article": _build_academic_article(prepared_input, payload.source_type),
        "user_facing_state": "normal",
        "translations": translations,
        "term_notes": term_notes,
        "logic_notes": logic_notes,
        "interpretation_notes": interpretation_notes,
        "paragraph_roles": paragraph_roles,
        "document_summary": document_summary,
        "warnings": warning_dicts,
    }

    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(metadata={
            "term_notes_count": len(term_notes),
            "logic_notes_count": len(logic_notes),
            "interpretation_notes_count": len(interpretation_notes),
            "paragraph_roles_count": len(paragraph_roles),
            "has_document_summary": document_summary is not None,
        })

    return {
        "render_scene": render_scene,
        "warnings": existing_warnings,
    }


async def assemble_academic_result_node(state: AcademicState) -> AcademicState:
    """Assemble academic result node。"""
    render_scene = state.get("render_scene")

    if render_scene is None:
        payload = state["payload"]
        plan = state.get("goal_execution_plan")
        return {
            "render_scene": _empty_academic_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id=plan.prompt_profile if plan else "unresolved",
            ),
        }

    existing_warnings = state.get("warnings", [])
    if existing_warnings:
        scene_warnings = render_scene.get("warnings", [])
        seen_keys = {(w.get("code"), w.get("sentence_id")) for w in scene_warnings}
        for w in existing_warnings:
            key = (w.code, w.sentence_id)
            if key not in seen_keys:
                scene_warnings.append({
                    "code": w.code,
                    "level": w.level,
                    "message": w.message,
                    "sentence_id": w.sentence_id,
                    "annotation_id": None,
                })
                seen_keys.add(key)
        render_scene["warnings"] = scene_warnings

    heavy_failure_codes = {
        "TERM_AGENT_FAILED",
        "LOGIC_AGENT_FAILED",
        "INTERPRETATION_AGENT_FAILED",
        "STRUCTURE_AGENT_FAILED",
        "ACADEMIC_TRANSLATION_AGENT_FAILED",
    }
    has_heavy_failure = any(
        w.code in heavy_failure_codes for w in existing_warnings
    ) if existing_warnings else False

    has_no_entries = (
        len(render_scene.get("term_notes", [])) == 0
        and len(render_scene.get("logic_notes", [])) == 0
        and len(render_scene.get("interpretation_notes", [])) == 0
        and len(render_scene.get("paragraph_roles", [])) == 0
    )

    informational_codes = {
        "LOW_ENGLISH_RATIO",
        "HIGH_NOISE_RATIO",
        "UNSUPPORTED_TEXT_TYPE",
    }
    has_informational_only = (
        len(existing_warnings) > 0
        and all(w.code in informational_codes for w in existing_warnings)
    ) if existing_warnings else False

    if has_heavy_failure and has_no_entries:
        render_scene["user_facing_state"] = "degraded_heavy"
    elif len(existing_warnings) > 0 and not has_informational_only:
        render_scene["user_facing_state"] = "degraded_light"
    else:
        render_scene["user_facing_state"] = "normal"

    return {"render_scene": render_scene}
