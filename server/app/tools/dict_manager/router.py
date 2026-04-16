"""词典数据管理工具的 API 路由。"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from .schemas import (
    DashboardStats,
    DataQualityReport,
    EntryKind,
    EntryUpdateRequest,
    LookupTargetUpdateRequest,
    MeaningDefinition,
    MeaningGroup,
    PaginatedResult,
    RedirectUpdateRequest,
    json_to_examples,
    json_to_phrases,
)
from .service import DictManagerService

router = APIRouter(prefix="/tools/dict-manager", tags=["tools", "dict-manager"])

_service: DictManagerService | None = None


def get_service() -> DictManagerService:
    """获取词典管理服务实例。"""
    global _service
    if _service is None:
        _service = DictManagerService()
    return _service


STATIC_DIR = Path(__file__).parent / "static"


@router.on_event("startup")
async def on_startup() -> None:
    """启动时确保日志表存在。"""
    service = get_service()
    await service.ensure_operation_log_table()


@router.get("", response_class=HTMLResponse)
async def index_page() -> FileResponse:
    """返回词典管理工具主页。"""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Index page not found")
    return FileResponse(index_path, media_type="text/html")


@router.get("/api/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """获取仪表盘统计数据。"""
    service = get_service()
    return await service.get_dashboard_stats()


@router.get("/api/entries/missing-meanings", response_model=PaginatedResult)
async def get_entries_without_meanings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResult:
    """获取缺失 meanings_json 的词条列表。"""
    service = get_service()
    return await service.get_entries_without_meanings(page=page, page_size=page_size)


@router.get("/api/entries/search", response_model=PaginatedResult)
async def search_entries(
    q: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entry_kind: Literal["entry", "fragment", "all"] = Query("all", description="词条类型过滤"),
    has_meanings: Literal["yes", "no", "all"] = Query("all", description="是否有释义"),
) -> PaginatedResult:
    """搜索词条。"""
    service = get_service()
    kind_filter = entry_kind if entry_kind != "all" else None
    meanings_filter = True if has_meanings == "yes" else (False if has_meanings == "no" else None)
    return await service.search_entries(
        keyword=q,
        page=page,
        page_size=page_size,
        entry_kind=kind_filter,
        has_meanings=meanings_filter,
    )


@router.get("/api/entries/{entry_id}")
async def get_entry_detail(entry_id: int):
    """获取词条详情。"""
    service = get_service()
    entry = await service.get_entry_detail(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

    lookup_targets = await service.get_entry_lookup_targets(entry_id)
    redirects = await service.get_entry_redirects(entry_id)

    return {
        "entry": entry.model_dump(),
        "lookup_targets": [t.model_dump() for t in lookup_targets],
        "redirects": [r.model_dump() for r in redirects],
    }


@router.put("/api/entries/{entry_id}")
async def update_entry(entry_id: int, request: EntryUpdateRequest):
    """更新词条内容。"""
    service = get_service()
    entry = await service.get_entry_detail(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

    examples_dict = [e.model_dump() for e in request.examples] if request.examples else None
    phrases_dict = [p.model_dump() for p in request.phrases] if request.phrases else None

    success = await service.update_entry(
        entry_id=entry_id,
        meanings=request.meanings,
        examples=examples_dict,
        phrases=phrases_dict,
        phonetic=request.phonetic,
        base_headword=request.base_headword,
        homograph_no=request.homograph_no,
        entry_kind=request.entry_kind.value if request.entry_kind else None,
        update_note=request.update_note,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update entry")

    return {"success": True, "entry_id": entry_id}


@router.post("/api/entries/{entry_id}/lookup-targets")
async def add_lookup_target(entry_id: int, request: LookupTargetUpdateRequest):
    """添加查询目标关联。"""
    service = get_service()
    entry = await service.get_entry_detail(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

    target_id = await service.add_lookup_target(
        entry_id=entry_id,
        normalized_form=request.normalized_form,
        lookup_label=request.lookup_label,
        target_label=request.target_label,
        target_pos=request.target_pos,
        preview_text=request.preview_text,
        rank=request.rank,
        match_kind=request.match_kind.value,
    )

    if not target_id:
        raise HTTPException(status_code=500, detail="Failed to add lookup target")

    return {"success": True, "target_id": target_id}


@router.delete("/api/lookup-targets/{target_id}")
async def delete_lookup_target(target_id: int, note: str | None = Query(None)):
    """删除查询目标关联。"""
    service = get_service()
    success = await service.delete_lookup_target(target_id, update_note=note)
    if not success:
        raise HTTPException(status_code=404, detail=f"Lookup target not found: {target_id}")
    return {"success": True}


@router.post("/api/redirects")
async def add_redirect(request: RedirectUpdateRequest):
    """添加重定向记录。"""
    service = get_service()
    redirect_id = await service.add_redirect(
        redirect_key=request.redirect_key,
        target_entry_key=request.target_entry_key,
        redirect_kind=request.redirect_kind.value,
    )

    if not redirect_id:
        raise HTTPException(status_code=500, detail="Failed to add redirect")

    return {"success": True, "redirect_id": redirect_id}


@router.delete("/api/redirects/{redirect_id}")
async def delete_redirect(redirect_id: int, note: str | None = Query(None)):
    """删除重定向记录。"""
    service = get_service()
    success = await service.delete_redirect(redirect_id, update_note=note)
    if not success:
        raise HTTPException(status_code=404, detail=f"Redirect not found: {redirect_id}")
    return {"success": True}


@router.get("/api/entries/{entry_id}/logs", response_model=PaginatedResult)
async def get_entry_logs(
    entry_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResult:
    """获取词条的操作日志。"""
    service = get_service()
    return await service.get_operation_logs(entry_id=entry_id, page=page, page_size=page_size)


@router.get("/api/logs", response_model=PaginatedResult)
async def get_all_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResult:
    """获取所有操作日志。"""
    service = get_service()
    return await service.get_operation_logs(page=page, page_size=page_size)


@router.get("/api/quality", response_model=DataQualityReport)
async def check_data_quality() -> DataQualityReport:
    """检查数据质量问题。"""
    service = get_service()
    return await service.check_data_quality()


class QuickMeaningRequest(BaseModel):
    part_of_speech: str
    meaning: str
    example: str | None = None
    example_translation: str | None = None


@router.post("/api/entries/{entry_id}/quick-meaning")
async def add_quick_meaning(entry_id: int, request: QuickMeaningRequest):
    """快速添加单个释义（补录缺失释义的便捷方式）。"""
    service = get_service()
    entry = await service.get_entry_detail(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

    new_definition = MeaningDefinition(
        meaning=request.meaning,
        example=request.example,
        example_translation=request.example_translation,
    )

    existing_meanings = entry.meanings
    pos_found = False

    for meaning in existing_meanings:
        if meaning.part_of_speech == request.part_of_speech:
            meaning.definitions.append(new_definition)
            pos_found = True
            break

    if not pos_found:
        new_group = MeaningGroup(
            part_of_speech=request.part_of_speech,
            definitions=[new_definition],
        )
        existing_meanings.append(new_group)

    success = await service.update_entry(
        entry_id=entry_id,
        meanings=existing_meanings,
        examples=[e.model_dump() for e in entry.examples],
        phrases=[p.model_dump() for p in entry.phrases],
        update_note=f"快速补录释义: {request.part_of_speech} - {request.meaning[:50]}",
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to add meaning")

    return {"success": True, "entry_id": entry_id}
