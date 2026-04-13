from logging import getLogger

from fastapi import APIRouter, HTTPException

from app.llm.router import ModelSelectionError
from app.schemas.analysis import AnalyzeRequest, RenderSceneModel
from app.workflow.analyze import run_article_analysis
from app.workflow.academic_workflow import AcademicWorkflowNotImplementedError

logger = getLogger("app.api")

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=RenderSceneModel)
async def analyze(payload: AnalyzeRequest) -> RenderSceneModel:
    try:
        return await run_article_analysis(payload)
    except ModelSelectionError as exc:
        logger.error("analyze ModelSelectionError: %s", exc, exc_info=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AcademicWorkflowNotImplementedError as exc:
        logger.error("analyze AcademicWorkflowNotImplementedError: %s", exc, exc_info=True)
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("analyze unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
