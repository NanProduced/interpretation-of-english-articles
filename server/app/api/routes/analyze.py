from fastapi import APIRouter, HTTPException

from app.llm.router import ModelSelectionError
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.workflow.analyze import run_article_analysis

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AnalysisResult)
async def analyze(payload: AnalyzeRequest) -> AnalysisResult:
    try:
        return await run_article_analysis(payload)
    except ModelSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
