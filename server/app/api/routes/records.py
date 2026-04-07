"""
Analysis Records API.

Provides endpoints for saving, retrieving, and managing analysis records.
"""

from __future__ import annotations

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

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordUpsertResponse)
async def create_record(
    current_user: AuthUserDep,
    body: RecordCreateRequest,
) -> RecordUpsertResponse:
    """Save an analysis record (upsert by client_record_id)."""
    try:
        record_id, created, updated_at = await records_svc.upsert_record(
            user_id=UUID(current_user.user_id),
            client_record_id=body.client_record_id,
            source_type=body.source_type,
            title=body.title,
            source_text=body.source_text,
            source_text_hash=body.source_text_hash,
            request_payload_json=body.request_payload_json,
            render_scene_json=body.render_scene_json,
            page_state_json=body.page_state_json,
            reading_goal=body.reading_goal,
            reading_variant=body.reading_variant,
            user_facing_state=body.user_facing_state,
            workflow_version=body.workflow_version,
            schema_version=body.schema_version,
            analysis_status=body.analysis_status,
        )
        return RecordUpsertResponse(
            id=record_id,
            client_record_id=body.client_record_id,
            created=created,
            updated_at=updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=RecordListResponse)
async def list_records(
    current_user: AuthUserDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> RecordListResponse:
    """List analysis records for the current user."""
    try:
        items, total = await records_svc.list_records(
            user_id=UUID(current_user.user_id),
            page=page,
            limit=limit,
        )
        return RecordListResponse(
            items=[RecordResponse(**row) for row in items],
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{record_id}")
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
        raise HTTPException(status_code=500, detail=str(e)) from e
