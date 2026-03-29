from fastapi import APIRouter

from app.schemas.preprocess import PreprocessAnalyzeRequest, PreprocessResult
from app.workflow.preprocess import run_preprocess_v0


router = APIRouter(prefix="/preprocess", tags=["preprocess"])


@router.post("", response_model=PreprocessResult)
async def preprocess(payload: PreprocessAnalyzeRequest) -> PreprocessResult:
    # 这里是当前 workflow 的统一执行入口，先跑 preprocess_v0。
    return await run_preprocess_v0(payload)
