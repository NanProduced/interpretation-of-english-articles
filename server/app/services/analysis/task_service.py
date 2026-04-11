"""
Analysis Task Service.

Handles task creation (with single-active-task control),
status queries, and record+task lifecycle management.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.database import connection as db_connection

logger = logging.getLogger(__name__)


def compute_source_text_hash(text: str) -> str:
    """Simple hash used for analysis_records.source_text_hash."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


class TaskSubmitResult:
    """Result of submit_task."""

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


class TaskExecutionPayload:
    """Claimed task payload needed by the worker to execute analysis."""

    __slots__ = (
        "task_id",
        "record_id",
        "user_id",
        "text",
        "reading_goal",
        "reading_variant",
        "source_type",
        "extended",
        "worker_token",
    )

    def __init__(
        self,
        *,
        task_id: UUID,
        record_id: UUID,
        user_id: UUID,
        text: str,
        reading_goal: str,
        reading_variant: str,
        source_type: str,
        extended: bool,
        worker_token: str,
    ) -> None:
        self.task_id = task_id
        self.record_id = record_id
        self.user_id = user_id
        self.text = text
        self.reading_goal = reading_goal
        self.reading_variant = reading_variant
        self.source_type = source_type
        self.extended = extended
        self.worker_token = worker_token


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
) -> TaskSubmitResult:
    """
    Submit an analysis task with single-active-task control.

    Steps (in one transaction):
    1. Check if user has active task (queued/running/finalizing) — if so, raise ActiveTaskConflict
    2. Create analysis_record (status=queued)
    3. Create analysis_task (status=queued)
    4. Insert task_submitted event

    Returns:
        TaskSubmitResult with task_id, record_id, status, created

    Raises:
        ActiveTaskConflict if user already has a running task
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    source_text_hash = compute_source_text_hash(text)
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Single active task check
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

            # 2. Create analysis_record
            client_record_id = f"task-{uuid4()}"
            record_row = await conn.fetchrow(
                """
                INSERT INTO analysis_records (
                    user_id, client_record_id, source_type,
                    source_text, source_text_hash,
                    request_payload_json, reading_goal, reading_variant,
                    analysis_status, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, 'queued', $9, $9)
                RETURNING id
                """,
                user_id,
                client_record_id,
                source_type,
                text,
                source_text_hash,
                json.dumps({
                    "reading_goal": reading_goal,
                    "reading_variant": reading_variant,
                    "source_type": source_type,
                    "extended": extended,
                }),
                reading_goal,
                reading_variant,
                now,
            )
            record_id = record_row["id"]

            # 3. Create analysis_task
            task_row = await conn.fetchrow(
                """
                INSERT INTO analysis_tasks (
                    user_id, analysis_record_id, status, queued_at,
                    created_at, updated_at
                )
                VALUES ($1, $2, 'queued', $3, $3, $3)
                RETURNING id
                """,
                user_id,
                record_id,
                now,
            )
            task_id = task_row["id"]

            # 4. Insert task_submitted event
            await conn.execute(
                """
                INSERT INTO analysis_task_events (task_id, event_type, event_payload_json, created_at)
                VALUES ($1, 'task_submitted', $2, $3)
                """,
                task_id,
                json.dumps({}),
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
    worker_token: str | None = None,
) -> None:
    """Update task status and optional fields."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    sets = ["status = $2", "updated_at = $3"]
    params: list[Any] = [task_id, status, datetime.now(timezone.utc)]
    idx = 4

    _JSONB_FIELDS = {"usage_summary_json"}

    for field_name, value in [
        ("started_at", started_at),
        ("finished_at", finished_at),
        ("failure_code", failure_code),
        ("failure_message", failure_message),
        ("usage_summary_json", usage_summary_json),
        ("quota_cost_points", quota_cost_points),
        ("worker_token", worker_token),
    ]:
        if value is not None:
            if field_name in _JSONB_FIELDS and isinstance(value, dict):
                sets.append(f"{field_name} = ${idx}::jsonb")
                params.append(json.dumps(value, ensure_ascii=False))
            else:
                sets.append(f"{field_name} = ${idx}")
                params.append(value)
            idx += 1

    sql = f"UPDATE analysis_tasks SET {', '.join(sets)} WHERE id = $1"

    async with pool.acquire() as conn:
        await conn.execute(sql, *params)


async def touch_task_heartbeat(task_id: UUID, worker_token: str) -> None:
    """Refresh updated_at for a running/finalizing task owned by the worker."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE analysis_tasks
            SET updated_at = $3
            WHERE id = $1
              AND worker_token = $2
              AND status IN ('running', 'finalizing')
            """,
            task_id,
            worker_token,
            datetime.now(timezone.utc),
        )


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
            VALUES ($1, $2, $3::jsonb, $4)
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
    title: str | None = None,
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

    _JSONB_FIELDS = {"render_scene_json", "page_state_json"}

    for field_name, value in [
        ("title", title),
        ("render_scene_json", render_scene_json),
        ("page_state_json", page_state_json),
        ("user_facing_state", user_facing_state),
        ("workflow_version", workflow_version),
        ("schema_version", schema_version),
    ]:
        if value is not None:
            if field_name in _JSONB_FIELDS and isinstance(value, dict):
                sets.append(f"{field_name} = ${idx}::jsonb")
                params.append(json.dumps(value, ensure_ascii=False))
            else:
                sets.append(f"{field_name} = ${idx}")
                params.append(value)
            idx += 1

    sql = f"UPDATE analysis_records SET {', '.join(sets)} WHERE id = $1"

    async with pool.acquire() as conn:
        await conn.execute(sql, *params)


async def claim_next_queued_task(worker_token: str) -> TaskExecutionPayload | None:
    """Atomically claim the next queued task for a worker."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            next_row = await conn.fetchrow(
                """
                SELECT id
                FROM analysis_tasks
                WHERE status = 'queued'
                ORDER BY queued_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
            if next_row is None:
                return None

            row = await conn.fetchrow(
                """
                UPDATE analysis_tasks t
                SET status = 'running',
                    started_at = COALESCE(t.started_at, $3),
                    worker_token = $1,
                    updated_at = $3
                FROM analysis_records r
                WHERE t.id = $2
                  AND t.analysis_record_id = r.id
                  AND t.status = 'queued'
                RETURNING
                    t.id AS task_id,
                    t.analysis_record_id AS record_id,
                    t.user_id AS user_id,
                    r.source_text AS text,
                    r.reading_goal AS reading_goal,
                    r.reading_variant AS reading_variant,
                    r.source_type AS source_type,
                    COALESCE((r.request_payload_json->>'extended')::boolean, false) AS extended
                """,
                worker_token,
                next_row["id"],
                now,
            )
        if row is None:
            return None

        return TaskExecutionPayload(
            task_id=row["task_id"],
            record_id=row["record_id"],
            user_id=row["user_id"],
            text=row["text"],
            reading_goal=row["reading_goal"],
            reading_variant=row["reading_variant"],
            source_type=row["source_type"],
            extended=row["extended"],
            worker_token=worker_token,
        )


async def requeue_stale_tasks(
    *,
    queued_before: datetime,
    active_before: datetime,
) -> int:
    """Requeue stale queued/running/finalizing tasks so the worker can retry them."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                """
                SELECT id AS task_id, analysis_record_id AS record_id, status
                FROM analysis_tasks
                WHERE (status = 'queued' AND queued_at < $1)
                   OR (status IN ('running', 'finalizing') AND updated_at < $2)
                FOR UPDATE
                """,
                queued_before,
                active_before,
            )

            if not rows:
                return 0

            task_ids = [row["task_id"] for row in rows]
            record_ids = [row["record_id"] for row in rows]

            await conn.execute(
                """
                UPDATE analysis_tasks
                SET status = 'queued',
                    worker_token = NULL,
                    queued_at = $2,
                    started_at = NULL,
                    finished_at = NULL,
                    failure_code = NULL,
                    failure_message = NULL,
                    updated_at = $2
                WHERE id = ANY($1::uuid[])
                """,
                task_ids,
                now,
            )
            await conn.execute(
                """
                UPDATE analysis_records
                SET analysis_status = 'queued',
                    updated_at = $2
                WHERE id = ANY($1::uuid[])
                """,
                record_ids,
                now,
            )

            for row in rows:
                await conn.execute(
                    """
                    INSERT INTO analysis_task_events
                        (task_id, event_type, event_payload_json, created_at)
                    VALUES ($1, 'task_requeued', $2, $3)
                    """,
                    row["task_id"],
                    json.dumps(
                        {
                            "reason": "server_restart",
                            "previous_status": row["status"],
                        }
                    ),
                    now,
                )

            return len(rows)
