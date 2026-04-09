"""
Analysis Task Service.

Handles task creation (with idempotency + single-active-task control),
status queries, and record+task lifecycle management.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection

logger = logging.getLogger(__name__)


def compute_request_fingerprint(
    text: str,
    reading_goal: str,
    reading_variant: str,
    source_type: str,
    extended: bool,
) -> str:
    """Deterministic fingerprint for request content dedup / analytics."""
    payload = json.dumps(
        {
            "text": text.strip(),
            "reading_goal": reading_goal,
            "reading_variant": reading_variant,
            "source_type": source_type,
            "extended": extended,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_source_text_hash(text: str) -> str:
    """Simple hash used for analysis_records.source_text_hash."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


class TaskSubmitResult:
    """Result of submit_task — holds IDs and whether the task was newly created."""

    __slots__ = ("task_id", "record_id", "status", "created")

    def __init__(
        self,
        task_id: UUID,
        record_id: UUID,
        status: str,
        created: bool,
    ) -> None:
        self.task_id = task_id
        self.record_id = record_id
        self.status = status
        self.created = created


class ActiveTaskConflict(Exception):
    """Raised when user already has an active task."""

    def __init__(self, task_id: UUID, record_id: UUID, status: str) -> None:
        self.task_id = task_id
        self.record_id = record_id
        self.status = status
        super().__init__(f"Active task exists: {task_id} ({status})")


async def submit_task(
    *,
    user_id: UUID,
    text: str,
    reading_goal: str,
    reading_variant: str,
    source_type: str,
    extended: bool,
    idempotency_key: str,
) -> TaskSubmitResult:
    """
    Submit an analysis task with idempotency + single-active-task control.

    Steps (in one transaction):
    1. Check (user_id, idempotency_key) — if exists, return existing task (dedup)
    2. Check if user has active task (queued/running/finalizing) — if so, raise ActiveTaskConflict
    3. Create analysis_record (status=queued)
    4. Create analysis_task (status=queued)
    5. Insert task_submitted event

    Returns:
        TaskSubmitResult with task_id, record_id, status, created

    Raises:
        ActiveTaskConflict if user already has a running task
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    request_fingerprint = compute_request_fingerprint(
        text, reading_goal, reading_variant, source_type, extended
    )
    source_text_hash = compute_source_text_hash(text)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Idempotency check
            existing = await conn.fetchrow(
                """
                SELECT t.id AS task_id, t.analysis_record_id AS record_id, t.status
                FROM analysis_tasks t
                WHERE t.user_id = $1 AND t.idempotency_key = $2
                """,
                user_id,
                idempotency_key,
            )
            if existing is not None:
                return TaskSubmitResult(
                    task_id=existing["task_id"],
                    record_id=existing["record_id"],
                    status=existing["status"],
                    created=False,
                )

            # 2. Single active task check
            active = await conn.fetchrow(
                """
                SELECT t.id AS task_id, t.analysis_record_id AS record_id, t.status
                FROM analysis_tasks t
                WHERE t.user_id = $1
                  AND t.status IN ('queued', 'running', 'finalizing')
                """,
                user_id,
            )
            if active is not None:
                raise ActiveTaskConflict(
                    task_id=active["task_id"],
                    record_id=active["record_id"],
                    status=active["status"],
                )

            # 3. Create analysis_record
            client_record_id = f"task-{idempotency_key}"
            record_row = await conn.fetchrow(
                """
                INSERT INTO analysis_records (
                    user_id, client_record_id, source_type,
                    source_text, source_text_hash,
                    request_payload_json, reading_goal, reading_variant,
                    analysis_status, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'queued', $9, $9)
                RETURNING id
                """,
                user_id,
                client_record_id,
                source_type,
                text,
                source_text_hash,
                json.dumps(
                    {
                        "reading_goal": reading_goal,
                        "reading_variant": reading_variant,
                        "source_type": source_type,
                        "extended": extended,
                    }
                ),
                reading_goal,
                reading_variant,
                now,
            )
            record_id = record_row["id"]

            # 4. Create analysis_task
            task_row = await conn.fetchrow(
                """
                INSERT INTO analysis_tasks (
                    user_id, analysis_record_id, idempotency_key,
                    request_fingerprint, status, queued_at,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, 'queued', $5, $5, $5)
                RETURNING id
                """,
                user_id,
                record_id,
                idempotency_key,
                request_fingerprint,
                now,
            )
            task_id = task_row["id"]

            # 5. Insert task_submitted event
            await conn.execute(
                """
                INSERT INTO analysis_task_events (task_id, event_type, event_payload_json, created_at)
                VALUES ($1, 'task_submitted', $2, $3)
                """,
                task_id,
                json.dumps({"idempotency_key": idempotency_key}),
                now,
            )

            return TaskSubmitResult(
                task_id=task_id,
                record_id=record_id,
                status="queued",
                created=True,
            )


async def cancel_new_task(task_id: UUID, record_id: UUID) -> None:
    """
    Cancel a just-created task (e.g. when quota check fails after submission).

    Marks both the task and the associated record as cancelled.
    This is safe to call only on tasks in 'queued' state.
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE analysis_tasks
                SET status = 'cancelled',
                    failure_code = 'insufficient_credits',
                    failure_message = 'Task cancelled: daily credits exhausted.',
                    finished_at = $2,
                    updated_at = $2
                WHERE id = $1 AND status = 'queued'
                """,
                task_id,
                now,
            )
            await conn.execute(
                """
                UPDATE analysis_records
                SET analysis_status = 'cancelled', updated_at = $2
                WHERE id = $1
                """,
                record_id,
                now,
            )
            await conn.execute(
                """
                INSERT INTO analysis_task_events
                    (task_id, event_type, event_payload_json, created_at)
                VALUES ($1, 'task_cancelled', '{"reason": "insufficient_credits"}', $2)
                """,
                task_id,
                now,
            )

async def get_task_status(
    user_id: UUID,
    task_id: UUID,
) -> dict[str, Any] | None:
    """Get task status, ensuring it belongs to the user."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                id AS task_id,
                analysis_record_id AS record_id,
                status,
                failure_code,
                failure_message,
                quota_cost_points,
                queued_at,
                started_at,
                finished_at,
                created_at,
                updated_at
            FROM analysis_tasks
            WHERE id = $1 AND user_id = $2
            """,
            task_id,
            user_id,
        )
        return dict(row) if row else None


async def get_active_task(user_id: UUID) -> dict[str, Any] | None:
    """Get the currently active task for the user (queued/running/finalizing)."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                id AS task_id,
                analysis_record_id AS record_id,
                status,
                failure_code,
                failure_message,
                quota_cost_points,
                queued_at,
                started_at,
                finished_at,
                created_at,
                updated_at
            FROM analysis_tasks
            WHERE user_id = $1
              AND status IN ('queued', 'running', 'finalizing')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )
        return dict(row) if row else None


async def update_task_status(
    task_id: UUID,
    *,
    status: str,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    failure_code: str | None = None,
    failure_message: str | None = None,
    usage_summary_json: dict[str, Any] | None = None,
    quota_cost_points: int | None = None,
) -> None:
    """Update task status and optional fields."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    sets = ["status = $2", "updated_at = $3"]
    params: list[Any] = [task_id, status, datetime.now(timezone.utc)]
    idx = 4

    for field_name, value in [
        ("started_at", started_at),
        ("finished_at", finished_at),
        ("failure_code", failure_code),
        ("failure_message", failure_message),
        ("usage_summary_json", json.dumps(usage_summary_json) if usage_summary_json else None),
        ("quota_cost_points", quota_cost_points),
    ]:
        if value is not None:
            if field_name == "usage_summary_json":
                sets.append(f"{field_name} = ${idx}::jsonb")
            else:
                sets.append(f"{field_name} = ${idx}")
            params.append(value)
            idx += 1

    sql = f"UPDATE analysis_tasks SET {', '.join(sets)} WHERE id = $1"

    async with pool.acquire() as conn:
        await conn.execute(sql, *params)


async def insert_task_event(
    task_id: UUID,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Insert a task event for audit trail."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO analysis_task_events (task_id, event_type, event_payload_json, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            task_id,
            event_type,
            json.dumps(payload or {}),
            datetime.now(timezone.utc),
        )


async def update_record_for_task(
    record_id: UUID,
    *,
    analysis_status: str,
    render_scene_json: dict[str, Any] | None = None,
    page_state_json: dict[str, Any] | None = None,
    user_facing_state: str | None = None,
    workflow_version: str | None = None,
    schema_version: str | None = None,
) -> None:
    """Update the analysis_record associated with a completed task."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    sets = ["analysis_status = $2", "updated_at = $3"]
    params: list[Any] = [record_id, analysis_status, datetime.now(timezone.utc)]
    idx = 4

    for field_name, value in [
        ("render_scene_json", json.dumps(render_scene_json) if render_scene_json else None),
        ("page_state_json", json.dumps(page_state_json) if page_state_json else None),
        ("user_facing_state", user_facing_state),
        ("workflow_version", workflow_version),
        ("schema_version", schema_version),
    ]:
        if value is not None:
            if field_name in ("render_scene_json", "page_state_json"):
                sets.append(f"{field_name} = ${idx}::jsonb")
            else:
                sets.append(f"{field_name} = ${idx}")
            params.append(value)
            idx += 1

    sql = f"UPDATE analysis_records SET {', '.join(sets)} WHERE id = $1"

    async with pool.acquire() as conn:
        await conn.execute(sql, *params)
