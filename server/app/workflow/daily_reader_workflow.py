"""Daily Reader Workflow - LangGraph StateGraph with 8 nodes.

Nodes: light_normalize → vocab_highlight → phrase_context_gloss → footer_analysis
       → full_interpretation → quality_review → (conditional) refinement → daily_projection

Model routes:
- daily_annotation: vocab_highlight, phrase_context_gloss
- daily_analysis: footer_analysis, full_interpretation
- daily_review: quality_review, refinement
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import get_current_run_tree, traceable

from app.agents.daily_footer_agent import (
    DailyFooterAgentDeps,
    build_daily_footer_prompt,
    get_daily_footer_agent,
)
from app.agents.daily_interpretation_agent import (
    DailyInterpretationAgentDeps,
    build_daily_interpretation_prompt,
    get_daily_interpretation_agent,
)
from app.agents.daily_refinement_agent import (
    DailyRefinementAgentDeps,
    build_daily_refinement_prompt,
    get_daily_refinement_agent,
)
from app.agents.daily_review_agent import (
    DailyReviewAgentDeps,
    build_daily_review_prompt,
    get_daily_review_agent,
)
from app.agents.daily_vocab_agent import (
    DailyVocabAgentDeps,
    build_daily_vocab_prompt,
    get_daily_vocab_agent,
)
from app.llm.agent_runner import extract_run_usage, run_agent_with_route
from app.llm.routes import (
    MODEL_ROUTE_DAILY_ANALYSIS,
    MODEL_ROUTE_DAILY_ANNOTATION,
    MODEL_ROUTE_DAILY_REVIEW,
)

logger = logging.getLogger(__name__)

WORKFLOW_NAME = "daily_reader"
WORKFLOW_VERSION = "1.0.0"


class DailyReaderState(TypedDict, total=False):
    original_text: str
    title: str
    subtitle: str
    source: str
    source_url: str
    cover_image_url: str | None
    tags: list[str]
    difficulty: str
    read_time_minutes: int
    pipeline_source: str
    pipeline_meta: dict

    normalized_paragraphs: list[dict]
    vocab_draft: dict | None
    highlights_json: list[dict]
    footer_analysis_json: dict
    full_interpretation: str
    review_result: dict | None
    refinement_result: dict | None
    abort: bool

    body_json: dict
    content_sec_check: dict

    usage_summary: dict | None


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


def _aggregate_usage(state: DailyReaderState) -> dict[str, Any]:
    per_agent: dict[str, dict[str, object]] = {}
    for key in (
        "vocab_usage", "phrase_gloss_usage", "footer_usage",
        "interpretation_usage", "review_usage", "refinement_usage",
    ):
        usage = state.get(key)
        if usage and isinstance(usage, dict):
            per_agent[key.replace("_usage", "")] = usage

    if not per_agent:
        return {
            "available": False,
            "per_agent": {},
            "aggregate": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

    def _sum(field: str) -> int:
        return sum(int(u.get(field, 0) or 0) for u in per_agent.values())

    return {
        "available": True,
        "per_agent": per_agent,
        "aggregate": {
            "input_tokens": _sum("input_tokens"),
            "output_tokens": _sum("output_tokens"),
            "total_tokens": _sum("total_tokens"),
        },
    }


def light_normalize_node(state: DailyReaderState) -> dict:
    text = state.get("original_text", "")
    paragraphs = _split_into_paragraphs(text)
    normalized = []
    for i, para in enumerate(paragraphs):
        cleaned = _clean_paragraph(para)
        if cleaned:
            normalized.append({"paragraph_id": f"p_{i}", "text": cleaned})
    return {"normalized_paragraphs": normalized}


@traceable(name="vocab_highlight_llm_call", run_type="llm")
async def _vocab_highlight_llm_span(
    *, agent: Any, prompt: str, deps: Any, route: str, metadata: dict[str, object],
) -> dict[str, Any]:
    result = await run_agent_with_route(agent=agent, prompt=prompt, deps=deps, route=route)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        draft = result.output if hasattr(result, "output") else None
        hl_count = len(_extract_highlights_from_vocab_draft(draft)) if draft else 0
        _set_current_run(
            run_tree=current_run,
            metadata={**metadata, "highlight_count": hl_count},
            usage_metadata=usage,
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def vocab_highlight_node(state: DailyReaderState) -> dict:
    paragraphs = state.get("normalized_paragraphs", [])
    if not paragraphs:
        return {"vocab_draft": None, "highlights_json": []}

    try:
        deps = DailyVocabAgentDeps(paragraphs=paragraphs)
        agent = get_daily_vocab_agent()
        prompt = build_daily_vocab_prompt(deps)
        metadata = {"workflow": WORKFLOW_NAME, "node": "vocab_highlight", "model_route": MODEL_ROUTE_DAILY_ANNOTATION}

        span_result = await _vocab_highlight_llm_span(
            agent=agent, prompt=prompt, deps=deps,
            route=MODEL_ROUTE_DAILY_ANNOTATION, metadata=metadata,
        )
        draft = span_result["output"]
        usage = span_result.get("usage")

        vocab_dict = draft.model_dump() if draft else {}
        highlights = _extract_highlights_from_vocab_draft(draft)

        updates: dict[str, Any] = {"vocab_draft": vocab_dict, "highlights_json": highlights}
        if usage:
            updates["vocab_usage"] = usage
        return updates
    except Exception as e:
        logger.error("vocab_highlight_node failed: %s", e, exc_info=True)
        return {"vocab_draft": None, "highlights_json": []}


@traceable(name="phrase_gloss_llm_call", run_type="llm")
async def _phrase_gloss_llm_span(
    *, agent: Any, prompt: str, deps: Any, route: str, metadata: dict[str, object],
) -> dict[str, Any]:
    result = await run_agent_with_route(agent=agent, prompt=prompt, deps=deps, route=route)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        draft = result.output if hasattr(result, "output") else None
        hl_count = len(_extract_highlights_from_vocab_draft(draft)) if draft else 0
        _set_current_run(
            run_tree=current_run,
            metadata={**metadata, "highlight_count": hl_count},
            usage_metadata=usage,
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def phrase_context_gloss_node(state: DailyReaderState) -> dict:
    paragraphs = state.get("normalized_paragraphs", [])
    existing_highlights = state.get("highlights_json", [])

    if not paragraphs:
        return {"highlights_json": existing_highlights}

    try:
        from app.services.analysis.prompting.daily_prompt_strategy import build_phrase_gloss_strategy

        deps = DailyVocabAgentDeps(
            paragraphs=paragraphs,
            prompt_strategy=build_phrase_gloss_strategy(),
        )
        agent = get_daily_vocab_agent()
        prompt = build_daily_vocab_prompt(deps)
        metadata = {"workflow": WORKFLOW_NAME, "node": "phrase_context_gloss", "model_route": MODEL_ROUTE_DAILY_ANNOTATION}

        span_result = await _phrase_gloss_llm_span(
            agent=agent, prompt=prompt, deps=deps,
            route=MODEL_ROUTE_DAILY_ANNOTATION, metadata=metadata,
        )
        draft = span_result["output"]
        usage = span_result.get("usage")

        new_highlights = _extract_highlights_from_vocab_draft(draft)
        merged = existing_highlights + new_highlights

        updates: dict[str, Any] = {"highlights_json": merged}
        if usage:
            updates["phrase_gloss_usage"] = usage
        return updates
    except Exception as e:
        logger.error("phrase_context_gloss_node failed: %s", e, exc_info=True)
        return {"highlights_json": existing_highlights}


@traceable(name="footer_analysis_llm_call", run_type="llm")
async def _footer_analysis_llm_span(
    *, agent: Any, prompt: str, deps: Any, route: str, metadata: dict[str, object],
) -> dict[str, Any]:
    result = await run_agent_with_route(agent=agent, prompt=prompt, deps=deps, route=route)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        footer = result.output if hasattr(result, "output") else None
        _set_current_run(
            run_tree=current_run,
            metadata={**metadata, "has_footer": footer is not None},
            usage_metadata=usage,
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def footer_analysis_node(state: DailyReaderState) -> dict:
    full_text = state.get("original_text", "")
    title = state.get("title", "")
    highlights = state.get("highlights_json", [])

    try:
        highlights_summary = ""
        if highlights:
            hl_texts = [h.get("text", "") for h in highlights[:10]]
            highlights_summary = f"已标注的关键词：{', '.join(hl_texts)}"

        deps = DailyFooterAgentDeps(
            full_text=full_text,
            title=title,
            highlights_summary=highlights_summary,
        )
        agent = get_daily_footer_agent()
        prompt = build_daily_footer_prompt(deps)
        metadata = {"workflow": WORKFLOW_NAME, "node": "footer_analysis", "model_route": MODEL_ROUTE_DAILY_ANALYSIS}

        span_result = await _footer_analysis_llm_span(
            agent=agent, prompt=prompt, deps=deps,
            route=MODEL_ROUTE_DAILY_ANALYSIS, metadata=metadata,
        )
        footer = span_result["output"]
        usage = span_result.get("usage")

        footer_dict = footer.model_dump() if footer else {}

        updates: dict[str, Any] = {"footer_analysis_json": footer_dict}
        if usage:
            updates["footer_usage"] = usage
        return updates
    except Exception as e:
        logger.error("footer_analysis_node failed: %s", e, exc_info=True)
        return {"footer_analysis_json": {}}


@traceable(name="full_interpretation_llm_call", run_type="llm")
async def _full_interpretation_llm_span(
    *, agent: Any, prompt: str, deps: Any, route: str, metadata: dict[str, object],
) -> dict[str, Any]:
    result = await run_agent_with_route(agent=agent, prompt=prompt, deps=deps, route=route)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        interp = result.output if hasattr(result, "output") else None
        text_len = len(getattr(interp, "full_article_analysis", "")) if interp else 0
        _set_current_run(
            run_tree=current_run,
            metadata={**metadata, "interpretation_length": text_len},
            usage_metadata=usage,
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def full_interpretation_node(state: DailyReaderState) -> dict:
    full_text = state.get("original_text", "")
    title = state.get("title", "")
    footer = state.get("footer_analysis_json", {})

    try:
        footer_summary = ""
        if footer:
            footer_summary = json.dumps(footer, ensure_ascii=False)[:1000]

        deps = DailyInterpretationAgentDeps(
            full_text=full_text,
            title=title,
            footer_summary=footer_summary,
        )
        agent = get_daily_interpretation_agent()
        prompt = build_daily_interpretation_prompt(deps)
        metadata = {"workflow": WORKFLOW_NAME, "node": "full_interpretation", "model_route": MODEL_ROUTE_DAILY_ANALYSIS}

        span_result = await _full_interpretation_llm_span(
            agent=agent, prompt=prompt, deps=deps,
            route=MODEL_ROUTE_DAILY_ANALYSIS, metadata=metadata,
        )
        interpretation = span_result["output"]
        usage = span_result.get("usage")

        updates: dict[str, Any] = {
            "full_interpretation": interpretation.full_article_analysis if interpretation else "",
        }
        if usage:
            updates["interpretation_usage"] = usage
        return updates
    except Exception as e:
        logger.error("full_interpretation_node failed: %s", e, exc_info=True)
        return {"full_interpretation": ""}


@traceable(name="quality_review_llm_call", run_type="llm")
async def _quality_review_llm_span(
    *, agent: Any, prompt: str, deps: Any, route: str, metadata: dict[str, object],
) -> dict[str, Any]:
    result = await run_agent_with_route(agent=agent, prompt=prompt, deps=deps, route=route)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        review = result.output if hasattr(result, "output") else None
        passed = getattr(review, "passed", True) if review else True
        _set_current_run(
            run_tree=current_run,
            metadata={**metadata, "review_passed": passed},
            usage_metadata=usage,
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def quality_review_node(state: DailyReaderState) -> dict:
    original_text = state.get("original_text", "")
    highlights = state.get("highlights_json", [])
    footer = state.get("footer_analysis_json", {})
    interpretation = state.get("full_interpretation", "")

    try:
        deps = DailyReviewAgentDeps(
            original_text=original_text,
            highlights_json=json.dumps(highlights, ensure_ascii=False),
            footer_analysis_json=json.dumps(footer, ensure_ascii=False),
            full_interpretation=interpretation,
        )
        agent = get_daily_review_agent()
        prompt = build_daily_review_prompt(deps)
        metadata = {"workflow": WORKFLOW_NAME, "node": "quality_review", "model_route": MODEL_ROUTE_DAILY_REVIEW}

        span_result = await _quality_review_llm_span(
            agent=agent, prompt=prompt, deps=deps,
            route=MODEL_ROUTE_DAILY_REVIEW, metadata=metadata,
        )
        review = span_result["output"]
        usage = span_result.get("usage")

        review_dict = review.model_dump() if review else {}
        updates: dict[str, Any] = {"review_result": review_dict}
        if usage:
            updates["review_usage"] = usage
        return updates
    except Exception as e:
        logger.error("quality_review_node failed: %s", e, exc_info=True)
        return {"review_result": {"passed": True}}


@traceable(name="refinement_llm_call", run_type="llm")
async def _refinement_llm_span(
    *, agent: Any, prompt: str, deps: Any, route: str, metadata: dict[str, object],
) -> dict[str, Any]:
    result = await run_agent_with_route(agent=agent, prompt=prompt, deps=deps, route=route)
    usage = extract_run_usage(result)
    current_run = get_current_run_tree()
    if current_run is not None:
        refinement = result.output if hasattr(result, "output") else None
        aborted = getattr(refinement, "abort", False) if refinement else False
        _set_current_run(
            run_tree=current_run,
            metadata={**metadata, "refinement_aborted": aborted},
            usage_metadata=usage,
        )
    return {"output": result.output if hasattr(result, "output") else result, "usage": usage}


async def refinement_node(state: DailyReaderState) -> dict:
    original_text = state.get("original_text", "")
    review = state.get("review_result", {})
    highlights = state.get("highlights_json", [])
    footer = state.get("footer_analysis_json", {})
    interpretation = state.get("full_interpretation", "")

    try:
        issues_text = json.dumps(review.get("issues", []), ensure_ascii=False)

        deps = DailyRefinementAgentDeps(
            original_text=original_text,
            review_issues=issues_text,
            current_highlights=json.dumps(highlights, ensure_ascii=False),
            current_footer=json.dumps(footer, ensure_ascii=False),
            current_interpretation=interpretation,
        )
        agent = get_daily_refinement_agent()
        prompt = build_daily_refinement_prompt(deps)
        metadata = {"workflow": WORKFLOW_NAME, "node": "refinement", "model_route": MODEL_ROUTE_DAILY_REVIEW}

        span_result = await _refinement_llm_span(
            agent=agent, prompt=prompt, deps=deps,
            route=MODEL_ROUTE_DAILY_REVIEW, metadata=metadata,
        )
        refinement = span_result["output"]
        usage = span_result.get("usage")

        refinement_dict = refinement.model_dump() if refinement else {}

        updates: dict[str, Any] = {"refinement_result": refinement_dict}

        if refinement and refinement.abort:
            updates["abort"] = True
            if usage:
                updates["refinement_usage"] = usage
            return updates

        if refinement:
            if refinement.refined_highlights is not None:
                updates["highlights_json"] = [h.model_dump() for h in refinement.refined_highlights]
            if refinement.refined_footer is not None:
                updates["footer_analysis_json"] = refinement.refined_footer.model_dump()
            if refinement.refined_interpretation is not None:
                updates["full_interpretation"] = refinement.refined_interpretation

        if usage:
            updates["refinement_usage"] = usage
        return updates
    except Exception as e:
        logger.error("refinement_node failed: %s", e, exc_info=True)
        return {"refinement_result": {}}


def daily_projection_node(state: DailyReaderState) -> dict:
    paragraphs = state.get("normalized_paragraphs", [])
    highlights = state.get("highlights_json", [])

    body_paragraphs = []
    for para in paragraphs:
        pid = para.get("paragraph_id", "")
        text = para.get("text", "")
        para_highlights = [h for h in highlights if h.get("paragraph_id") == pid]
        body_paragraphs.append({
            "id": pid,
            "text": text,
            "highlights": para_highlights,
        })

    usage_summary = _aggregate_usage(state)
    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(outputs={"usage_summary": usage_summary})

    return {"body_json": {"paragraphs": body_paragraphs}, "usage_summary": usage_summary}


def _should_refine(state: DailyReaderState) -> bool:
    review = state.get("review_result")
    if review is None:
        return False
    return not review.get("passed", True)


def build_daily_reader_graph() -> Any:
    graph = StateGraph(DailyReaderState)

    graph.add_node("light_normalize", light_normalize_node)
    graph.add_node("vocab_highlight", vocab_highlight_node)
    graph.add_node("phrase_context_gloss", phrase_context_gloss_node)
    graph.add_node("footer_analysis", footer_analysis_node)
    graph.add_node("full_interpretation", full_interpretation_node)
    graph.add_node("quality_review", quality_review_node)
    graph.add_node("refinement", refinement_node)
    graph.add_node("daily_projection", daily_projection_node)

    graph.add_edge(START, "light_normalize")
    graph.add_edge("light_normalize", "vocab_highlight")
    graph.add_edge("vocab_highlight", "phrase_context_gloss")
    graph.add_edge("phrase_context_gloss", "footer_analysis")
    graph.add_edge("footer_analysis", "full_interpretation")
    graph.add_edge("full_interpretation", "quality_review")
    graph.add_conditional_edges(
        "quality_review",
        _should_refine,
        {True: "refinement", False: "daily_projection"},
    )
    graph.add_edge("refinement", "daily_projection")
    graph.add_edge("daily_projection", END)

    return graph.compile()


def _split_into_paragraphs(text: str) -> list[str]:
    if re.search(r"\n\s*\n", text):
        parts = re.split(r"\n\s*\n", text)
    elif "\n" in text:
        parts = re.split(r"\n", text)
    else:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        parts: list[str] = []
        chunk: list[str] = []
        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 3 or len(" ".join(chunk)) > 300:
                parts.append(" ".join(chunk))
                chunk = []
        if chunk:
            parts.append(" ".join(chunk))
    return [p.strip() for p in parts if p.strip()]


def _clean_paragraph(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_highlights_from_vocab_draft(draft: Any) -> list[dict]:
    if draft is None:
        return []
    highlights = []
    hl_counter = 0
    for para in getattr(draft, "paragraphs", []):
        pid = getattr(para, "paragraph_id", "")
        for hl in getattr(para, "highlights", []):
            hl_counter += 1
            highlights.append({
                "id": f"hl_{hl_counter:03d}",
                "type": getattr(hl, "type", "vocab_highlight"),
                "text": getattr(hl, "anchor", ""),
                "gloss": getattr(hl, "gloss", ""),
                "paragraph_id": pid,
                "start": getattr(hl, "start", 0),
                "end": getattr(hl, "end", 0),
            })
    return highlights
