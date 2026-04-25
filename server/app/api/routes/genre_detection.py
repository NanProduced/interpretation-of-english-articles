from logging import getLogger

from fastapi import APIRouter

from app.schemas.genre_detection import (
    GenreDetectionRequest,
    GenreDetectionResponse,
)
from app.services.genre_detection import detect_text_genre

logger = getLogger("app.api")

router = APIRouter(prefix="/genre-detection", tags=["genre-detection"])


@router.post("", response_model=GenreDetectionResponse, summary="文体检测")
async def detect_genre(payload: GenreDetectionRequest) -> GenreDetectionResponse:
    """
    检测英文文本的文体类别，判断是否适合使用 academic 模式。

    该接口会分析文本特征：
    - 专业术语密度
    - 学术词汇使用
    - 被动语态频率
    - 引用标记
    - 名词化结构
    - IMRAD 结构指示词

    返回检测结果，包括置信度和建议的 reading_goal。
    """
    return await detect_text_genre(payload)
