"""
Analysis Tasks API.

Provides endpoints for submitting, querying, and managing analysis tasks.
"""

from __future__ import annotations

import asyncio
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

logger = getLogger("app.api")

from app.schemas.analysis import RenderSceneModel
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
from app.services.analysis.task_service import (
    ActiveTaskConflict,
    get_active_task,
    get_task_status,
    submit_task,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.user_assets import records as records_svc

router = APIRouter(prefix="/analysis-tasks", tags=["tasks"])
_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "expired"}


async def _wait_task_until_terminal(
    *,
    user_id: UUID,
    task_id: UUID,
    timeout_seconds: float,
) -> dict | None:
    """
    Wait task status until terminal or timeout.

    Returns latest status snapshot (may still be queued/running/finalizing on timeout).
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    latest: dict | None = None

    while True:
        latest = await get_task_status(user_id=user_id, task_id=task_id)
        if latest is None:
            return None
        if latest["status"] in _TERMINAL_STATUSES:
            return latest
        if loop.time() >= deadline:
            return latest
        await asyncio.sleep(1.0)


def _parse_render_scene(record: dict | None) -> RenderSceneModel | None:
    if not record:
        return None
    raw_scene = record.get("render_scene_json")
    if not isinstance(raw_scene, dict) or not raw_scene:
        return None
    try:
        # 兼容性处理：如果后端返回的是旧版本或结构略有差异，尝试容错处理
        if "schema_version" not in raw_scene:
            raw_scene["schema_version"] = "3.0.0"
        return RenderSceneModel.model_validate(raw_scene)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"RenderScene validation failed: {e}")
        return None


@router.post("", response_model=TaskSubmitResponse, status_code=202)
async def submit_analysis_task(
    current_user: AuthUserDep,
    body: TaskSubmitRequest,
) -> JSONResponse:
    """
    Submit an analysis task.

    - 402 if user has insufficient credits
    - 409 if user already has an active task (queued/running/finalizing)
    - Returns 202 Accepted with task_id and record_id by default
    - If wait_for_result=true and task finishes in time, returns 200 + render_scene
    """
    user_id = UUID(current_user.user_id)

    try:
        await ensure_credit_account(user_id)

        active = await get_active_task(user_id)
        if active is not None:
            raise ActiveTaskConflict(
                task_id=active["task_id"],
                record_id=active["record_id"],
                status=active["status"],
            )

        remaining = await check_quota(user_id)
        if remaining <= 0:
            raise InsufficientCredits(
                remaining=remaining,
                required=1,
            )

        result = await submit_task(
            user_id=user_id,
            text=body.text,
            reading_goal=body.reading_goal,
            reading_variant=body.reading_variant,
            source_type=body.source_type,
            extended=body.extended,
        )

        response_status = 202
        response_task_status = result.status
        render_scene = None

        if body.wait_for_result:
            latest = await _wait_task_until_terminal(
                user_id=user_id,
                task_id=result.task_id,
                timeout_seconds=body.wait_timeout_seconds,
            )
            if latest is None:
                raise HTTPException(status_code=404, detail="Task not found")

            response_task_status = latest["status"]
            if latest["status"] == "succeeded":
                record = await records_svc.get_record_by_id(
                    user_id=user_id,
                    record_id=latest["record_id"],
                )
                render_scene = _parse_render_scene(record)
                if render_scene is not None:
                    response_status = 200
            elif latest["status"] in {"failed", "cancelled", "expired"}:
                return JSONResponse(
                    status_code=422,
                    content={
                        "error": "TASK_TERMINATED",
                        "detail": latest.get("failure_message") or "Analysis task failed.",
                        "task_id": str(result.task_id),
                        "record_id": str(result.record_id),
                        "status": latest["status"],
                        "failure_code": latest.get("failure_code"),
                    },
                )

        response = TaskSubmitResponse(
            task_id=result.task_id,
            record_id=result.record_id,
            status=response_task_status,
            created=result.created,
            render_scene=render_scene,
        )
        return JSONResponse(
            status_code=response_status,
            content=response.model_dump(mode="json", exclude_none=True),
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("submit_analysis_task failed: %s", e, exc_info=True)
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
        logger.error("get_current_task failed: %s", e, exc_info=True)
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
        logger.error("get_task failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
