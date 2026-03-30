from fastapi import APIRouter, HTTPException

from app.llm.router import ModelSelectionError
from app.schemas.analysis import AnalyzeRequest, AnalysisResult
from app.workflow.analyze import run_analyze_v0


router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AnalysisResult)
async def analyze(payload: AnalyzeRequest) -> AnalysisResult:
    # 当前统一走 analyze_v0，后续扩版本时优先在 workflow 层扩展，而不是在路由层堆逻辑。
    try:
        return await run_analyze_v0(payload)
    except ModelSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
