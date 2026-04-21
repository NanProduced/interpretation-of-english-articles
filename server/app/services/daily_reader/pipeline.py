"""Daily Reader Pipeline orchestrator.

Coordinates the four-layer pipeline: Discovery → Extraction → Content Security → Scoring,
then selects diverse candidates and runs the Daily Reader Workflow.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime

import orjson

from app.database import connection as db_connection
from app.services.daily_reader.discovery import DiscoveredArticle, discover_guardian, discover_rss_sources
from app.services.daily_reader.extraction import apply_extraction_to_article, extract_with_trafilatura
from app.services.daily_reader.content_security import check_content_security, is_content_safe
from app.services.daily_reader.scoring import (
    ArticleScore,
    deduplicate,
    filter_by_word_count,
    score_article,
    SCORE_THRESHOLD,
)

logger = logging.getLogger(__name__)

SOURCE_ROTATION_POLICY = {
    "max_same_source_per_day": 2,
    "topic_diversity": True,
}


@dataclass
class PipelineResult:
    articles: list[dict] = field(default_factory=list)
    candidates_found: int = 0
    candidates_extracted: int = 0
    candidates_safe: int = 0
    candidates_scored: int = 0
    candidates_selected: int = 0
    errors: list[str] = field(default_factory=list)


async def run_daily_pipeline(
    max_count: int = 3,
    force: bool = False,
) -> PipelineResult:
    result = PipelineResult()

    # Layer 1: Discovery (concurrent)
    guardian_articles, rss_articles = await asyncio.gather(
        discover_guardian(),
        discover_rss_sources(),
    )
    candidates = guardian_articles + rss_articles
    result.candidates_found = len(candidates)
    logger.info("Pipeline discovery: %d candidates", len(candidates))

    # Layer 2: Extraction (concurrent for RSS-sourced articles)
    async def _extract_one(article: DiscoveredArticle) -> None:
        if article.needs_extraction:
            extraction = await extract_with_trafilatura(article.url)
            if extraction:
                apply_extraction_to_article(article, extraction)
            else:
                article.text = ""

    await asyncio.gather(*[_extract_one(a) for a in candidates])

    candidates = [a for a in candidates if a.text]
    result.candidates_extracted = len(candidates)
    logger.info("Pipeline extraction: %d articles with text", len(candidates))

    # Deduplication
    existing_hashes = await _get_existing_text_hashes()
    candidates = deduplicate(candidates, existing_hashes=existing_hashes)

    # Length filter
    candidates = filter_by_word_count(candidates)
    logger.info("Pipeline word count filter: %d articles in range", len(candidates))

    # Layer 2.5: Content Security Check (concurrent)
    async def _check_security(article: DiscoveredArticle) -> tuple[DiscoveredArticle, dict]:
        sec_result = await check_content_security(article.title, article.text)
        return article, sec_result

    sec_results = await asyncio.gather(*[_check_security(a) for a in candidates])

    safe_candidates: list[tuple[DiscoveredArticle, dict]] = []
    for article, sec_result in sec_results:
        if is_content_safe(sec_result):
            safe_candidates.append((article, sec_result))
        else:
            logger.info(
                "Content security rejected: %s (suggest=%s)",
                article.title[:50],
                sec_result.get("suggest"),
            )

    result.candidates_safe = len(safe_candidates)
    logger.info("Pipeline content security: %d safe articles", len(safe_candidates))

    # Layer 3: AI Scoring (concurrent)
    async def _score_one(
        article: DiscoveredArticle, sec_result: dict
    ) -> tuple[DiscoveredArticle, ArticleScore | None, dict]:
        score = await score_article(article)
        return article, score, sec_result

    score_results = await asyncio.gather(
        *[_score_one(a, s) for a, s in safe_candidates]
    )

    scored: list[tuple[DiscoveredArticle, ArticleScore, dict]] = []
    for article, score, sec_result in score_results:
        if score and score.score >= SCORE_THRESHOLD:
            scored.append((article, score, sec_result))

    scored.sort(key=lambda x: (x[0].cover_image_url is not None, x[1].score), reverse=True)
    result.candidates_scored = len(scored)
    logger.info("Pipeline scoring: %d articles passed threshold", len(scored))

    # Select diverse candidates (oversample to allow for workflow failures)
    selected = select_diverse_candidates(scored, max_count=max_count + 2)
    result.candidates_selected = len(selected)
    logger.info("Pipeline selection: %d candidates selected (target: %d)", len(selected), max_count)

    # Execute workflow for each candidate until we have enough
    success_count = 0
    for article, score, sec_result in selected:
        if success_count >= max_count:
            break
        try:
            payload = await _run_workflow_and_store(article, score, sec_result)
            if payload is not None:
                result.articles.append(payload)
                success_count += 1
        except Exception as e:
            error_msg = f"Workflow failed for '{article.title[:30]}': {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

    if success_count < max_count and len(scored) > len(selected):
        remaining = [s for s in scored if s not in selected]
        for article, score, sec_result in remaining:
            if success_count >= max_count:
                break
            try:
                payload = await _run_workflow_and_store(article, score, sec_result)
                if payload is not None:
                    result.articles.append(payload)
                    success_count += 1
            except Exception as e:
                error_msg = f"Workflow failed for '{article.title[:30]}': {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

    return result


def select_diverse_candidates(
    scored: list[tuple[DiscoveredArticle, ArticleScore, dict]],
    max_count: int = 3,
    max_same_source: int = 2,
) -> list[tuple[DiscoveredArticle, ArticleScore, dict]]:
    selected: list[tuple[DiscoveredArticle, ArticleScore, dict]] = []
    source_counts: Counter[str] = Counter()
    selected_topics: list[str] = []

    for article, score in scored:
        if len(selected) >= max_count:
            break

        source = article.source
        if source_counts[source] >= max_same_source:
            continue

        if SOURCE_ROTATION_POLICY["topic_diversity"] and selected_topics:
            article_topics = set(article.tags)
            overlap = sum(1 for t in selected_topics if t in article_topics)
            if overlap >= len(selected_topics) and len(selected) >= 2:
                continue

        selected.append((article, score))
        source_counts[source] += 1
        selected_topics.extend(article.tags)

    return selected


async def _run_workflow_and_store(
    article: DiscoveredArticle, score: ArticleScore, sec_check_result: dict
) -> dict | None:
    from app.workflow.daily_reader_workflow import build_daily_reader_graph

    graph = build_daily_reader_graph()

    input_state = {
        "original_text": article.text,
        "title": article.title,
        "subtitle": article.description,
        "source": article.source,
        "source_url": article.url,
        "cover_image_url": article.cover_image_url,
        "tags": article.tags,
        "difficulty": score.difficulty,
        "read_time_minutes": max(1, article.word_count // 200),
        "pipeline_source": article.source,
        "pipeline_meta": {
            "score": score.score,
            "score_details": {
                "language_richness": score.language_richness,
                "topic_interest": score.topic_interest,
                "structure_clarity": score.structure_clarity,
                "cultural_value": score.cultural_value,
            },
        },
    }

    try:
        final_state = await graph.ainvoke(input_state)
    except Exception as e:
        logger.error("Daily Reader Workflow execution failed: %s", e)
        return None

    if final_state.get("abort"):
        logger.info("Workflow aborted for: %s", article.title[:50])
        return None

    payload = _assemble_payload(article, score, sec_check_result, final_state)
    await _store_daily_reader(payload)
    return payload


async def _assemble_payload(
    article: DiscoveredArticle, score: ArticleScore, sec_check_result: dict, state: dict
) -> dict:
    today = date.today()
    nnn = await _next_sequence_number(today)
    return {
        "id": f"daily_{today.strftime('%Y')}_{today.strftime('%m')}_{today.strftime('%d')}_{nnn:03d}",
        "title": article.title,
        "subtitle": article.description,
        "source": article.source,
        "source_url": article.url,
        "publish_date": today.isoformat(),
        "difficulty": score.difficulty,
        "read_time_minutes": max(1, article.word_count // 200),
        "tags": score.tags or article.tags,
        "cover_image_url": article.cover_image_url,
        "cover_theme": "editorial_warm",
        "body_json": state.get("body_json", {"paragraphs": []}),
        "highlights_json": state.get("highlights_json", []),
        "footer_analysis_json": state.get("footer_analysis_json", {}),
        "status": "draft",
        "score": score.score,
        "content_sec_check": sec_check_result,
        "original_text_hash": hashlib.sha256(article.text.encode()).hexdigest(),
        "pipeline_source": article.source,
        "pipeline_meta": state.get("pipeline_meta", {}),
    }


async def _get_existing_text_hashes() -> set[str]:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT original_text_hash FROM daily_readers WHERE original_text_hash IS NOT NULL"
            )
            return {row["original_text_hash"] for row in rows}
    except Exception as e:
        logger.warning("Failed to fetch existing text hashes: %s", e)
        return set()


async def _next_sequence_number(publish_date: date) -> int:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM daily_readers WHERE publish_date = $1",
                publish_date,
            )
            count = row["cnt"] if row else 0
            return count + 1
    except Exception as e:
        logger.warning("Failed to query sequence number for %s: %s", publish_date, e)
        return 1


async def _store_daily_reader(payload: dict) -> None:
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO daily_readers (
                id, title, subtitle, source, source_url, publish_date,
                difficulty, read_time_minutes, tags, cover_image_url, cover_theme,
                body_json, highlights_json, footer_analysis_json,
                status, score, content_sec_check, original_text_hash,
                pipeline_source, pipeline_meta
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                      $12, $13, $14, $15, $16, $17, $18, $19, $20)
            """,
            payload["id"],
            payload["title"],
            payload["subtitle"],
            payload["source"],
            payload["source_url"],
            payload["publish_date"],
            payload["difficulty"],
            payload["read_time_minutes"],
            orjson.dumps(payload["tags"]),
            payload["cover_image_url"],
            payload["cover_theme"],
            orjson.dumps(payload["body_json"]),
            orjson.dumps(payload["highlights_json"]),
            orjson.dumps(payload["footer_analysis_json"]),
            payload["status"],
            payload["score"],
            orjson.dumps(payload["content_sec_check"]),
            payload["original_text_hash"],
            payload["pipeline_source"],
            orjson.dumps(payload["pipeline_meta"]),
        )
