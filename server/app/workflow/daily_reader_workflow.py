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
from app.llm.agent_runner import run_agent_with_route
from app.llm.routes import (
    MODEL_ROUTE_DAILY_ANALYSIS,
    MODEL_ROUTE_DAILY_ANNOTATION,
    MODEL_ROUTE_DAILY_REVIEW,
)

logger = logging.getLogger(__name__)


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


def light_normalize_node(state: DailyReaderState) -> dict:
    text = state.get("original_text", "")
    paragraphs = _split_into_paragraphs(text)
    normalized = []
    for i, para in enumerate(paragraphs):
        cleaned = _clean_paragraph(para)
        if cleaned:
            normalized.append({"paragraph_id": f"p_{i}", "text": cleaned})
    return {"normalized_paragraphs": normalized}


async def vocab_highlight_node(state: DailyReaderState) -> dict:
    paragraphs = state.get("normalized_paragraphs", [])
    if not paragraphs:
        return {"vocab_draft": None, "highlights_json": []}

    try:
        deps = DailyVocabAgentDeps(paragraphs=paragraphs)
        agent = get_daily_vocab_agent()
        prompt = build_daily_vocab_prompt(deps)

        result = await run_agent_with_route(
            agent=agent,
            prompt=prompt,
            deps=deps,
            route=MODEL_ROUTE_DAILY_ANNOTATION,
        )

        draft = result.output
        vocab_dict = draft.model_dump() if draft else {}
        highlights = _extract_highlights_from_vocab_draft(draft)

        return {"vocab_draft": vocab_dict, "highlights_json": highlights}
    except Exception as e:
        logger.error("vocab_highlight_node failed: %s", e, exc_info=True)
        return {"vocab_draft": None, "highlights_json": []}


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

        result = await run_agent_with_route(
            agent=agent,
            prompt=prompt,
            deps=deps,
            route=MODEL_ROUTE_DAILY_ANNOTATION,
        )

        draft = result.output
        new_highlights = _extract_highlights_from_vocab_draft(draft)
        merged = existing_highlights + new_highlights

        return {"highlights_json": merged}
    except Exception as e:
        logger.error("phrase_context_gloss_node failed: %s", e, exc_info=True)
        return {"highlights_json": existing_highlights}


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

        result = await run_agent_with_route(
            agent=agent,
            prompt=prompt,
            deps=deps,
            route=MODEL_ROUTE_DAILY_ANALYSIS,
        )

        footer = result.output
        footer_dict = footer.model_dump() if footer else {}

        return {"footer_analysis_json": footer_dict}
    except Exception as e:
        logger.error("footer_analysis_node failed: %s", e, exc_info=True)
        return {"footer_analysis_json": {}}


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

        result = await run_agent_with_route(
            agent=agent,
            prompt=prompt,
            deps=deps,
            route=MODEL_ROUTE_DAILY_ANALYSIS,
        )

        interpretation = result.output
        return {"full_interpretation": interpretation.full_article_analysis if interpretation else ""}
    except Exception as e:
        logger.error("full_interpretation_node failed: %s", e, exc_info=True)
        return {"full_interpretation": ""}


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

        result = await run_agent_with_route(
            agent=agent,
            prompt=prompt,
            deps=deps,
            route=MODEL_ROUTE_DAILY_REVIEW,
        )

        review = result.output
        review_dict = review.model_dump() if review else {}
        return {"review_result": review_dict}
    except Exception as e:
        logger.error("quality_review_node failed: %s", e, exc_info=True)
        return {"review_result": {"passed": True}}


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

        result = await run_agent_with_route(
            agent=agent,
            prompt=prompt,
            deps=deps,
            route=MODEL_ROUTE_DAILY_REVIEW,
        )

        refinement = result.output
        refinement_dict = refinement.model_dump() if refinement else {}

        updates: dict[str, Any] = {"refinement_result": refinement_dict}

        if refinement and refinement.abort:
            updates["abort"] = True
            return updates

        if refinement:
            if refinement.refined_highlights is not None:
                updates["highlights_json"] = [h.model_dump() for h in refinement.refined_highlights]
            if refinement.refined_footer is not None:
                updates["footer_analysis_json"] = refinement.refined_footer.model_dump()
            if refinement.refined_interpretation is not None:
                updates["full_interpretation"] = refinement.refined_interpretation

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

    return {"body_json": {"paragraphs": body_paragraphs}}


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
    parts = re.split(r"\n\s*\n|\r\n\s*\r\n", text)
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
