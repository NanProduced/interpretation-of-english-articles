"""
Analysis Task Executor.

Runs the analysis workflow in background (asyncio.create_task)
and writes results back to analysis_records + analysis_tasks.
Deducts credits on success; failed tasks are NOT charged.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.schemas.analysis import AnalyzeRequest
from app.services.analysis.credit_service import deduct_credits
from app.services.analysis.task_service import (
    insert_task_event,
    update_record_for_task,
    update_task_status,
)
from app.workflow.analyze import (
    ANALYZE_SCHEMA_VERSION,
    WORKFLOW_VERSION,
    run_article_analysis_with_state,
)

logger = logging.getLogger(__name__)

# Points conversion: 1 point = 1000 tokens (weighted)
# Weighted token formula: input_tokens * 1 + output_tokens * 5
# Cost in points: ceil(weighted_tokens / 1000)
MULTIPLIER_INPUT = 1
MULTIPLIER_OUTPUT = 5
TOKENS_PER_POINT = 1000


def compute_cost_points(usage_summary: dict[str, Any] | None) -> int:
    """
    Compute cost points from usage summary.

    Formula: ceil((input_tokens * 1 + output_tokens * 5) / 1000)
    1 point = 1000 weighted tokens. Daily quota = 1000 points.
    Returns 0 if usage data is unavailable.
    """
    if not usage_summary:
        return 0

    aggregate = usage_summary.get("aggregate")
    if not aggregate:
        return 0

    input_tokens = int(aggregate.get("input_tokens") or 0)
    output_tokens = int(aggregate.get("output_tokens") or 0)

    weighted = input_tokens * MULTIPLIER_INPUT + output_tokens * MULTIPLIER_OUTPUT
    return (weighted + TOKENS_PER_POINT - 1) // TOKENS_PER_POINT  # ceil division


def _build_deduction_metadata(usage_summary: dict[str, Any] | None) -> dict[str, Any]:
    """Build metadata dict for credit ledger entry."""
    if not usage_summary:
        return {}
    aggregate = usage_summary.get("aggregate", {})
    return {
        "input_tokens": aggregate.get("input_tokens", 0),
        "output_tokens": aggregate.get("output_tokens", 0),
        "total_tokens": aggregate.get("total_tokens", 0),
        "multiplier_input": MULTIPLIER_INPUT,
        "multiplier_output": MULTIPLIER_OUTPUT,
        "tokens_per_point": TOKENS_PER_POINT,
    }


async def execute_task(
    task_id: UUID,
    record_id: UUID,
    user_id: UUID,
    text: str,
    reading_goal: str,
    reading_variant: str,
    source_type: str,
    extended: bool,
) -> None:
    """
    Execute analysis task in background.

    This function is designed to be called via asyncio.create_task().
    It catches all exceptions to prevent unhandled errors in background tasks.

    On success: deducts credits from user account.
    On failure: does NOT deduct credits.
    """
    try:
        # 1. Mark as running
        now = datetime.now(timezone.utc)
        await update_task_status(task_id, status="running", started_at=now)
        await insert_task_event(task_id, "task_started")

        # 2. Build AnalyzeRequest and run workflow
        payload = AnalyzeRequest(
            text=text,
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            source_type=source_type,
            extended=extended,
        )

        result = await run_article_analysis_with_state(payload)

        # 3. Extract results
        render_scene = result.get("render_scene")
        usage_summary = result.get("usage_summary")

        if render_scene is None:
            raise RuntimeError("Workflow returned no render_scene")

        # Serialize render_scene to dict for storage
        render_scene_dict = (
            render_scene.model_dump(mode="json")
            if hasattr(render_scene, "model_dump")
            else render_scene
        )

        user_facing_state = getattr(render_scene, "user_facing_state", "normal")

        # 4. Compute cost points
        cost_points = compute_cost_points(usage_summary)

        # 5. Mark as finalizing
        await update_task_status(task_id, status="finalizing")
        await insert_task_event(task_id, "task_finalizing", {
            "cost_points": cost_points,
        })

        # 6. Write results back to analysis_record
        await update_record_for_task(
            record_id,
            analysis_status="ready",
            render_scene_json=render_scene_dict,
            page_state_json={"pageState": user_facing_state},
            user_facing_state=user_facing_state,
            workflow_version=WORKFLOW_VERSION,
            schema_version=ANALYZE_SCHEMA_VERSION,
        )

        # 7. Deduct credits (success only — failed tasks are NOT charged)
        actual_deducted = 0
        if cost_points > 0:
            metadata = _build_deduction_metadata(usage_summary)
            actual_deducted = await deduct_credits(
                user_id=user_id,
                task_id=task_id,
                cost_points=cost_points,
                metadata=metadata,
            )

        # 8. Mark task as succeeded (quota_cost_points = actual amount charged)
        finished_at = datetime.now(timezone.utc)
        await update_task_status(
            task_id,
            status="succeeded",
            finished_at=finished_at,
            usage_summary_json=usage_summary or {},
            quota_cost_points=actual_deducted,
        )
        await insert_task_event(task_id, "task_succeeded", {
            "cost_points": cost_points,
            "usage_summary": usage_summary or {},
        })

        logger.info(
            "Task %s succeeded (record=%s, cost=%d points)",
            task_id, record_id, cost_points,
        )

    except Exception as exc:
        # Handle failure — NO credit deduction
        logger.exception("Task %s failed: %s", task_id, exc)

        failure_code = type(exc).__name__
        failure_message = str(exc)[:500]

        try:
            await update_task_status(
                task_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                failure_code=failure_code,
                failure_message=failure_message,
            )
            await update_record_for_task(record_id, analysis_status="failed")
            await insert_task_event(task_id, "task_failed", {
                "failure_code": failure_code,
                "failure_message": failure_message,
            })
        except Exception as inner_exc:
            logger.exception(
                "Failed to update task %s status after failure: %s",
                task_id, inner_exc,
            )


def launch_task(
    task_id: UUID,
    record_id: UUID,
    user_id: UUID,
    text: str,
    reading_goal: str,
    reading_variant: str,
    source_type: str,
    extended: bool,
) -> asyncio.Task:
    """
    Launch the task executor as a background asyncio Task.

    Returns the asyncio.Task object for optional monitoring.
    """
    return asyncio.create_task(
        execute_task(
            task_id=task_id,
            record_id=record_id,
            user_id=user_id,
            text=text,
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            source_type=source_type,
            extended=extended,
        ),
        name=f"analysis-task-{task_id}",
    )


async def recover_stuck_tasks() -> int:
    """
    Recover tasks stuck in queued/running state (e.g. after server restart).

    Marks them as failed with failure_code='server_restart' so users can retry.
    Returns the number of recovered tasks.
    """
    from app.database import connection as db_connection

    pool = db_connection.DB_POOL
    if pool is None:
        logger.warning("Cannot recover stuck tasks: DB pool not initialized")
        return 0

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        # Find all tasks stuck in active states
        stuck_rows = await conn.fetch(
            """
            SELECT id AS task_id, analysis_record_id AS record_id, status
            FROM analysis_tasks
            WHERE status IN ('queued', 'running', 'finalizing')
            """
        )

        if not stuck_rows:
            return 0

        count = 0
        for row in stuck_rows:
            task_id = row["task_id"]
            record_id = row["record_id"]

            try:
                await conn.execute(
                    """
                    UPDATE analysis_tasks
                    SET status = 'failed',
                        failure_code = 'server_restart',
                        failure_message = 'Task interrupted by server restart. Please retry.',
                        finished_at = $2,
                        updated_at = $2
                    WHERE id = $1
                    """,
                    task_id,
                    now,
                )
                await conn.execute(
                    """
                    UPDATE analysis_records
                    SET analysis_status = 'failed', updated_at = $2
                    WHERE id = $1
                    """,
                    record_id,
                    now,
                )
                await conn.execute(
                    """
                    INSERT INTO analysis_task_events
                        (task_id, event_type, event_payload_json, created_at)
                    VALUES ($1, 'task_recovered', '{"reason": "server_restart"}', $2)
                    """,
                    task_id,
                    now,
                )
                count += 1
            except Exception as e:
                logger.exception("Failed to recover stuck task %s: %s", task_id, e)

        logger.info("Recovered %d stuck tasks (marked as failed)", count)
        return count
