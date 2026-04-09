"""
Analysis Tasks API.

Provides endpoints for submitting, querying, and managing analysis tasks.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from app.schemas.tasks import (
    ActiveTaskResponse,
    TaskStatusResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
)
from app.services.analysis.credit_service import (
    InsufficientCredits,
    check_quota,
    ensure_credit_account,
)
from app.services.analysis.task_executor import launch_task
from app.services.analysis.task_service import (
    ActiveTaskConflict,
    cancel_new_task,
    get_active_task,
    get_task_status,
    submit_task,
)
from app.services.auth.dependencies import AuthUserDep

router = APIRouter(prefix="/analysis-tasks", tags=["tasks"])


@router.post("", response_model=TaskSubmitResponse, status_code=202)
async def submit_analysis_task(
    current_user: AuthUserDep,
    body: TaskSubmitRequest,
) -> JSONResponse:
    """
    Submit an analysis task.

    - Idempotent: same (user_id, idempotency_key) returns existing task (bypasses quota)
    - 402 if user has insufficient credits (new tasks only)
    - 409 if user already has an active task (queued/running/finalizing)
    - Returns 202 Accepted with task_id and record_id
    """
    user_id = UUID(current_user.user_id)

    try:
        # Ensure credit account exists (idempotent, cheap)
        await ensure_credit_account(user_id)

        # Step 1: submit_task handles idempotency + single-active-task check.
        # If this is a duplicate idempotency_key, it returns the existing task
        # without any quota check — preserving idempotency semantics.
        result = await submit_task(
            user_id=user_id,
            text=body.text,
            reading_goal=body.reading_goal,
            reading_variant=body.reading_variant,
            source_type=body.source_type,
            extended=body.extended,
            idempotency_key=body.idempotency_key,
        )

        # Step 2: For NEW tasks only, check quota before launching execution.
        if result.created:
            remaining = await check_quota(user_id)
            if remaining <= 0:
                # Quota exhausted — cancel the just-created task + record
                await cancel_new_task(result.task_id, result.record_id)
                raise InsufficientCredits(remaining=remaining)

            # Step 3: Launch background execution
            launch_task(
                task_id=result.task_id,
                record_id=result.record_id,
                user_id=user_id,
                text=body.text,
                reading_goal=body.reading_goal,
                reading_variant=body.reading_variant,
                source_type=body.source_type,
                extended=body.extended,
            )

        response = TaskSubmitResponse(
            task_id=result.task_id,
            record_id=result.record_id,
            status=result.status,
            created=result.created,
        )

        return JSONResponse(
            status_code=202,
            content=response.model_dump(mode="json"),
        )

    except InsufficientCredits as exc:
        return JSONResponse(
            status_code=402,
            content={
                "error": "INSUFFICIENT_CREDITS",
                "detail": "Your daily credits are exhausted.",
                "remaining_points": exc.remaining,
            },
        )
    except ActiveTaskConflict as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "ACTIVE_TASK_EXISTS",
                "detail": "You already have an active analysis task.",
                "task_id": str(exc.task_id),
                "record_id": str(exc.record_id),
                "status": exc.status,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/current", response_model=ActiveTaskResponse)
async def get_current_task(
    current_user: AuthUserDep,
) -> ActiveTaskResponse:
    """
    Get the user's current active task (queued/running/finalizing).

    Returns has_active=false if no active task exists.
    """
    try:
        task = await get_active_task(UUID(current_user.user_id))
        if task is None:
            return ActiveTaskResponse(has_active=False)
        return ActiveTaskResponse(
            has_active=True,
            task=TaskStatusResponse(**task),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(
    current_user: AuthUserDep,
    task_id: UUID,
) -> TaskStatusResponse:
    """Get the status of a specific task."""
    try:
        task = await get_task_status(
            user_id=UUID(current_user.user_id),
            task_id=task_id,
        )
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskStatusResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
