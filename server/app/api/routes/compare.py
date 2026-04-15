from __future__ import annotations

import json
import time
from datetime import datetime
from logging import getLogger
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.llm.provider_factory import build_model_instance
from app.llm.registry import build_model_registry
from app.llm.router import resolve_model_config, validate_model_selection
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.types import ModelSelection, RouteModelSelection
from app.schemas.analysis import (
    AnalyzeRequest,
    ReadingGoal,
    ReadingVariant,
    RenderSceneModel,
)
from app.workflow.analyze import run_article_analysis_with_state

logger = getLogger("app.api.compare")

router = APIRouter(prefix="/compare", tags=["compare"])


ModelProfileInfo = Literal[
    "kimi-k25",
    "minimax_m27",
    "minimax_m25",
    "step35-flash",
    "qwen36-plus",
    "qwen35-plus",
    "qwen35-flash",
    "deepseek-chat",
    "deepseek-reasoner",
    "vllm-qwen3-8b",
]


class ModelProfileMeta(BaseModel):
    profile_id: str = Field(description="模型配置标识")
    model_name: str = Field(description="模型名称")
    provider: str = Field(description="提供商")


class AvailableModelsResponse(BaseModel):
    models: list[ModelProfileMeta] = Field(description="可用模型列表")


RubricDimension = Literal[
    "annotation_completeness",
    "annotation_accuracy",
    "translation_quality",
    "structure_rationality",
    "user_experience",
]


class DimensionScore(BaseModel):
    dimension: RubricDimension = Field(description="评分维度")
    score_left: float = Field(description="左侧模型分数 0-10")
    score_right: float = Field(description="右侧模型分数 0-10")
    reason: str = Field(description="评分理由")


class JudgeResult(BaseModel):
    winner: Literal["left", "right", "tie"] = Field(description="胜出者")
    total_score_left: float = Field(description="左侧模型总分")
    total_score_right: float = Field(description="右侧模型总分")
    dimensions: list[DimensionScore] = Field(description="各维度评分")
    summary: str = Field(description="总体评价")


class CompareMetrics(BaseModel):
    duration_ms: int = Field(description="执行耗时（毫秒）")
    token_usage: dict[str, Any] | None = Field(default=None, description="Token 使用情况")
    warning_count: int = Field(description="警告数量")
    annotation_count: int = Field(description="标注数量")
    translation_count: int = Field(description="翻译数量")
    sentence_count: int = Field(description="句子数量")
    paragraph_count: int = Field(description="段落数量")


class CompareResultItem(BaseModel):
    model_profile: str = Field(description="使用的模型配置")
    model_name: str = Field(description="实际模型名称")
    metrics: CompareMetrics = Field(description="观测指标")
    result: RenderSceneModel = Field(description="分析结果")


class CompareRequest(BaseModel):
    text: str = Field(min_length=1, description="待分析的英文文本")
    model_left: str = Field(description="左侧模型配置 ID")
    model_right: str = Field(description="右侧模型配置 ID")
    model_judge: str | None = Field(default=None, description="Judge 模型配置 ID（可选）")
    reading_goal: ReadingGoal = Field(default="daily_reading", description="阅读目标")
    reading_variant: ReadingVariant = Field(default="intermediate_reading", description="阅读细分场景")
    run_judge: bool = Field(default=True, description="是否运行 LLM-as-Judge 评测")


class CompareResponse(BaseModel):
    compare_id: str = Field(description="对比任务 ID")
    created_at: str = Field(description="创建时间")
    left: CompareResultItem = Field(description="左侧结果")
    right: CompareResultItem = Field(description="右侧结果")
    judge_result: JudgeResult | None = Field(default=None, description="Judge 评测结果")


def _get_available_models() -> list[ModelProfileMeta]:
    settings = get_settings()
    registry = build_model_registry(settings)
    models = []
    for profile_id, config in registry.profiles.items():
        if config.is_configured():
            models.append(ModelProfileMeta(
                profile_id=profile_id,
                model_name=config.model_name,
                provider=config.provider,
            ))
    return models


def _build_model_selection(profile_id: str) -> ModelSelection:
    return ModelSelection(
        default_profile=profile_id,
        routes={
            MODEL_ROUTE_ANNOTATION_GENERATION: RouteModelSelection(profile=profile_id)
        },
    )


def _extract_metrics(result: dict[str, Any], duration_ms: int) -> CompareMetrics:
    render_scene = result.get("render_scene", {})
    if not isinstance(render_scene, dict):
        render_scene = {}
    
    inline_marks = render_scene.get("inline_marks", [])
    translations = render_scene.get("translations", [])
    sentences = render_scene.get("article", {}).get("sentences", [])
    paragraphs = render_scene.get("article", {}).get("paragraphs", [])
    warnings = render_scene.get("warnings", [])
    
    return CompareMetrics(
        duration_ms=duration_ms,
        token_usage=result.get("token_usage"),
        warning_count=len(warnings),
        annotation_count=len(inline_marks),
        translation_count=len(translations),
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
    )


async def _run_analysis_with_profile(
    text: str,
    profile_id: str,
    reading_goal: ReadingGoal,
    reading_variant: ReadingVariant,
) -> tuple[dict[str, Any], int, str]:
    model_selection = _build_model_selection(profile_id)
    settings = get_settings()
    
    validate_model_selection(
        settings,
        model_selection,
        (MODEL_ROUTE_ANNOTATION_GENERATION,),
    )
    
    model_config = resolve_model_config(
        settings,
        MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection,
    )
    actual_model_name = model_config.model_name if model_config else profile_id
    
    request = AnalyzeRequest(
        text=text,
        reading_goal=reading_goal,
        reading_variant=reading_variant,
        source_type="user_input",
        model_selection=model_selection,
    )
    
    start_time = time.perf_counter()
    result = await run_article_analysis_with_state(request)
    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)
    
    return result, duration_ms, actual_model_name


JUDGE_SYSTEM_PROMPT = """你是一位专业的英语阅读批注质量评测专家。你的任务是对比两个不同模型在英语文章分析任务中的输出质量，并根据 Rubric 进行公平、客观的评分。

## Rubric 评分维度（每个维度 0-10 分）

### 1. 标注完整性 (annotation_completeness)
- 10分：覆盖所有重点词汇、短语、语法点，无明显遗漏
- 7-9分：覆盖大部分重点，少数非关键内容遗漏
- 4-6分：部分覆盖，有较多重要内容遗漏
- 0-3分：严重遗漏，无法满足基本阅读需求

### 2. 标注准确性 (annotation_accuracy)
- 10分：所有释义、解释完全准确，符合语境
- 7-9分：基本准确，个别细节有误但不影响理解
- 4-6分：存在较多错误，部分解释误导读者
- 0-3分：大量错误，严重影响理解

### 3. 翻译质量 (translation_quality)
- 10分：翻译准确、流畅、自然，符合中文表达习惯
- 7-9分：翻译基本准确，少数表达略显生硬
- 4-6分：翻译存在偏差，部分句子理解有误
- 0-3分：翻译错误较多，难以理解

### 4. 结构合理性 (structure_rationality)
- 10分：句子分割、段落划分完全合理，锚点定位精准
- 7-9分：结构基本合理，个别边界处理略欠准确
- 4-6分：结构存在问题，部分句子/段落划分不当
- 0-3分：结构混乱，无法正常阅读

### 5. 用户体验 (user_experience)
- 10分：标注分布合理，不过度也不遗漏，警告极少
- 7-9分：整体体验良好，少量警告或标注密度稍欠理想
- 4-6分：体验一般，较多警告或标注分布不合理
- 0-3分：体验很差，大量警告或标注严重干扰阅读

## 输出格式
请以严格的 JSON 格式输出评测结果：

{
    "winner": "left" | "right" | "tie",
    "total_score_left": <float>,
    "total_score_right": <float>,
    "dimensions": [
        {
            "dimension": "annotation_completeness",
            "score_left": <float 0-10>,
            "score_right": <float 0-10>,
            "reason": "<详细评分理由>"
        },
        ... 其他维度
    ],
    "summary": "<200字以内的总体评价，说明为什么某个模型更优或平局>"
}

## 评测原则
1. 公平客观：基于事实，不偏袒任何模型
2. 具体详细：每个评分都要有具体的理由和依据
3. 独立判断：每个维度独立评分，不受其他维度影响
4. 综合考量：winner 基于总分，但也要考虑各维度的均衡性"""


async def _run_llm_judge(
    profile_id: str,
    left_result: CompareResultItem,
    right_result: CompareResultItem,
    original_text: str,
) -> JudgeResult:
    settings = get_settings()
    registry = build_model_registry(settings)
    
    model_selection = _build_model_selection(profile_id)
    model_config = resolve_model_config(
        settings,
        MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection,
    )
    
    if model_config is None:
        raise HTTPException(status_code=500, detail=f"Judge model {profile_id} not available")
    
    model = build_model_instance(model_config)
    if model is None:
        raise HTTPException(status_code=500, detail=f"Failed to build judge model {profile_id}")
    
    left_result_json = json.dumps({
        "model": left_result.model_name,
        "profile": left_result.model_profile,
        "metrics": {
            "duration_ms": left_result.metrics.duration_ms,
            "warning_count": left_result.metrics.warning_count,
            "annotation_count": left_result.metrics.annotation_count,
            "translation_count": left_result.metrics.translation_count,
            "sentence_count": left_result.metrics.sentence_count,
        },
        "inline_marks_count": len(left_result.result.inline_marks),
        "translations_count": len(left_result.result.translations),
        "sentence_entries_count": len(left_result.result.sentence_entries),
        "warnings": [
            {"code": w.code, "level": w.level, "message": w.message}
            for w in left_result.result.warnings
        ],
    }, ensure_ascii=False, indent=2)
    
    right_result_json = json.dumps({
        "model": right_result.model_name,
        "profile": right_result.model_profile,
        "metrics": {
            "duration_ms": right_result.metrics.duration_ms,
            "warning_count": right_result.metrics.warning_count,
            "annotation_count": right_result.metrics.annotation_count,
            "translation_count": right_result.metrics.translation_count,
            "sentence_count": right_result.metrics.sentence_count,
        },
        "inline_marks_count": len(right_result.result.inline_marks),
        "translations_count": len(right_result.result.translations),
        "sentence_entries_count": len(right_result.result.sentence_entries),
        "warnings": [
            {"code": w.code, "level": w.level, "message": w.message}
            for w in right_result.result.warnings
        ],
    }, ensure_ascii=False, indent=2)
    
    user_prompt = f"""请对比以下两个模型的英语文章分析输出，根据 Rubric 进行评测。

## 原始文本
{original_text}

## 左侧模型结果（left）
模型：{left_result.model_name} ({left_result.model_profile})
```json
{left_result_json}
```

## 右侧模型结果（right）
模型：{right_result.model_name} ({right_result.model_profile})
```json
{right_result_json}
```

请根据以上信息，按照 Rubric 进行评分并输出 JSON 结果。"""

    try:
        result = await model.run(
            [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        
        response_text = result.content
        if isinstance(response_text, list):
            response_text = "\n".join(str(item) for item in response_text)
        
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            judge_data = json.loads(json_str)
            return JudgeResult.model_validate(judge_data)
        
        raise ValueError("Failed to parse judge response")
        
    except Exception as e:
        logger.error("LLM-as-Judge failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM-as-Judge failed: {str(e)}") from e


@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models() -> AvailableModelsResponse:
    """获取可用的模型配置列表（不暴露敏感信息）"""
    return AvailableModelsResponse(models=_get_available_models())


@router.post("/run", response_model=CompareResponse)
async def run_compare(payload: CompareRequest) -> CompareResponse:
    """执行两个模型的对比分析，可选运行 LLM-as-Judge 评测"""
    compare_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    
    available_models = _get_available_models()
    available_ids = {m.profile_id for m in available_models}
    
    if payload.model_left not in available_ids:
        raise HTTPException(status_code=422, detail=f"Model {payload.model_left} not available")
    if payload.model_right not in available_ids:
        raise HTTPException(status_code=422, detail=f"Model {payload.model_right} not available")
    if payload.run_judge and payload.model_judge and payload.model_judge not in available_ids:
        raise HTTPException(status_code=422, detail=f"Judge model {payload.model_judge} not available")
    
    left_raw, left_duration, left_model_name = await _run_analysis_with_profile(
        text=payload.text,
        profile_id=payload.model_left,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
    )
    
    right_raw, right_duration, right_model_name = await _run_analysis_with_profile(
        text=payload.text,
        profile_id=payload.model_right,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
    )
    
    left_result = CompareResultItem(
        model_profile=payload.model_left,
        model_name=left_model_name,
        metrics=_extract_metrics(left_raw, left_duration),
        result=left_raw["render_scene"],
    )
    
    right_result = CompareResultItem(
        model_profile=payload.model_right,
        model_name=right_model_name,
        metrics=_extract_metrics(right_raw, right_duration),
        result=right_raw["render_scene"],
    )
    
    judge_result: JudgeResult | None = None
    if payload.run_judge and payload.model_judge:
        judge_result = await _run_llm_judge(
            profile_id=payload.model_judge,
            left_result=left_result,
            right_result=right_result,
            original_text=payload.text,
        )
    
    return CompareResponse(
        compare_id=compare_id,
        created_at=created_at,
        left=left_result,
        right=right_result,
        judge_result=judge_result,
    )
