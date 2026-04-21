"""
Analysis Records API.

Provides endpoints for saving, retrieving, and managing analysis records.
"""

from __future__ import annotations

from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.user_assets.records import (
    RecordCreateRequest,
    RecordListResponse,
    RecordResponse,
    RecordUpdateRequest,
    RecordUpsertResponse,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.user_assets import records as records_svc

logger = getLogger("app.api")

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordUpsertResponse)
async def create_record(
    current_user: AuthUserDep,
    body: RecordCreateRequest,
) -> RecordUpsertResponse:
    """Save an analysis record (upsert by client_record_id)."""
    try:
        # 兼容性处理：优先从根字段取，其次从 request_payload_json 提取
        reading_goal = body.reading_goal or body.request_payload_json.get("reading_goal")
        reading_variant = body.reading_variant or body.request_payload_json.get("reading_variant")
        extended = body.extended or body.request_payload_json.get("extended", False)

        record_id, created, updated_at = await records_svc.upsert_record(
            user_id=UUID(current_user.user_id),
            client_record_id=body.client_record_id,
            source_type=body.source_type,
            title=body.title,
            source_text=body.source_text,
            source_text_hash=body.source_text_hash,
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            extended=extended,
            user_facing_state=body.user_facing_state,
            analysis_status=body.analysis_status,
            render_scene_json=body.render_scene_json,
            page_state_json=body.page_state_json,
            workflow_version=body.workflow_version,
            schema_version=body.schema_version,
        )
        return RecordUpsertResponse(
            id=record_id,
            client_record_id=body.client_record_id,
            created=created,
            updated_at=updated_at,
        )
    except Exception as e:
        logger.error("create_record failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("", response_model=RecordListResponse)
async def list_records(
    current_user: AuthUserDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    include_render_scene: bool = Query(default=False),
) -> RecordListResponse:
    """List analysis records for the current user."""
    try:
        items, total = await records_svc.list_records(
            user_id=UUID(current_user.user_id),
            page=page,
            limit=limit,
            include_content=include_render_scene,
        )
        return RecordListResponse(
            items=[RecordResponse(**row) for row in items],
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("list_records failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/by-client-id/{client_record_id}", response_model=RecordResponse)
async def get_record_by_client_id(
    current_user: AuthUserDep,
    client_record_id: str,
) -> RecordResponse:
    """Get a single analysis record by client_record_id."""
    try:
        record = await records_svc.get_record_by_client_id(
            user_id=UUID(current_user.user_id),
            client_record_id=client_record_id,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return RecordResponse(**record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_record_by_client_id failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    current_user: AuthUserDep,
    record_id: UUID,
) -> RecordResponse:
    """Get a single analysis record by id."""
    try:
        record = await records_svc.get_record_by_id(
            user_id=UUID(current_user.user_id),
            record_id=record_id,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return RecordResponse(**record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_record failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{record_id}", response_model=RecordResponse)
async def update_record(
    current_user: AuthUserDep,
    record_id: UUID,
    body: RecordUpdateRequest,
) -> RecordResponse:
    """Partial update of an analysis record."""
    try:
        updated = await records_svc.update_record(
            user_id=UUID(current_user.user_id),
            record_id=record_id,
            **body.model_dump(exclude_none=True),
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return RecordResponse(**updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_record failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{record_id}", response_model=RecordDeleteResponse)
async def delete_record(
    current_user: AuthUserDep,
    record_id: UUID,
) -> dict:
    """Delete an analysis record."""
    try:
        deleted = await records_svc.delete_record(
            user_id=UUID(current_user.user_id),
            record_id=record_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_record failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
