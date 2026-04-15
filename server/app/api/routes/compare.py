from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from logging import getLogger
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.config.settings import get_settings
from app.llm.agent_runner import extract_run_usage
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


class TokenUsage(BaseModel):
    input_tokens: int | None = Field(default=None, description="输入 token 数")
    output_tokens: int | None = Field(default=None, description="输出 token 数")
    total_tokens: int | None = Field(default=None, description="总 token 数")
    per_agent: dict[str, dict[str, Any] | None] | None = Field(default=None, description="各 agent 的 token 使用")


class CompareMetrics(BaseModel):
    duration_ms: int = Field(description="执行耗时（毫秒）")
    token_usage: TokenUsage | None = Field(default=None, description="Token 使用情况")
    warning_count: int = Field(description="警告数量")
    annotation_count: int = Field(description="标注数量")
    translation_count: int = Field(description="翻译数量")
    sentence_count: int = Field(description="句子数量")
    paragraph_count: int = Field(description="段落数量")


class ModelProfileMeta(BaseModel):
    profile_id: str = Field(description="模型配置标识")
    model_name: str = Field(description="模型名称")
    provider: str = Field(description="提供商")


class AvailableModelsResponse(BaseModel):
    models: list[ModelProfileMeta] = Field(description="可用模型列表")


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


@dataclass
class JudgeAgentDeps:
    left_result: dict[str, Any]
    right_result: dict[str, Any]
    original_text: str


JUDGE_INSTRUCTIONS = """你是一位专业的英语阅读批注质量评测专家。你的任务是对比两个不同模型在英语文章分析任务中的输出质量，并根据 Rubric 进行公平、客观的评分。

## Rubric 评分维度（每个维度 0-10 分）

### 1. 标注完整性 (annotation_completeness)
评估模型是否覆盖了文章中所有值得标注的重点词汇、短语、语法点。
- 10分：覆盖所有重点，无明显遗漏，关键难点都有解释
- 7-9分：覆盖大部分重点，少数非关键内容遗漏
- 4-6分：部分覆盖，有较多重要内容遗漏
- 0-3分：严重遗漏，无法满足基本阅读需求

### 2. 标注准确性 (annotation_accuracy)
评估模型给出的释义、解释是否准确、符合语境。
- 10分：所有释义完全准确，符合上下文，解释清晰
- 7-9分：基本准确，个别细节有误但不影响理解
- 4-6分：存在较多错误，部分解释误导读者
- 0-3分：大量错误，严重影响理解

### 3. 翻译质量 (translation_quality)
评估模型生成的中文翻译质量。
- 10分：翻译准确、流畅、自然，符合中文表达习惯，术语统一
- 7-9分：翻译基本准确，少数表达略显生硬
- 4-6分：翻译存在偏差，部分句子理解有误
- 0-3分：翻译错误较多，难以理解

### 4. 结构合理性 (structure_rationality)
评估句子分割、段落划分、锚点定位是否合理。
- 10分：句子分割合理，锚点定位精准，没有错位
- 7-9分：结构基本合理，个别边界处理略欠准确
- 4-6分：结构存在问题，部分句子/段落划分不当
- 0-3分：结构混乱，无法正常阅读

### 5. 用户体验 (user_experience)
综合评估标注密度、警告数量、整体阅读体验。
- 10分：标注分布合理，不过度也不遗漏，无警告或极少
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
            "reason": "<详细评分理由，对比两个模型在该维度的表现>"
        },
        {
            "dimension": "annotation_accuracy",
            "score_left": <float 0-10>,
            "score_right": <float 0-10>,
            "reason": "<详细评分理由>"
        },
        {
            "dimension": "translation_quality",
            "score_left": <float 0-10>,
            "score_right": <float 0-10>,
            "reason": "<详细评分理由>"
        },
        {
            "dimension": "structure_rationality",
            "score_left": <float 0-10>,
            "score_right": <float 0-10>,
            "reason": "<详细评分理由>"
        },
        {
            "dimension": "user_experience",
            "score_left": <float 0-10>,
            "score_right": <float 0-10>,
            "reason": "<详细评分理由>"
        }
    ],
    "summary": "<200字以内的总体评价，说明为什么某个模型更优或平局，给出具体的优缺点对比>"
}

## 评测原则
1. 公平客观：基于事实，不偏袒任何模型
2. 具体详细：每个评分都要有具体的理由和依据，对比两个模型的实际输出
3. 独立判断：每个维度独立评分，不受其他维度影响
4. 综合考量：winner 基于总分，但也要考虑各维度的均衡性

## 提示
- 仔细对比两个模型的实际标注内容，不要只看数量
- 注意标注的质量：一个准确的标注比多个不准确的标注更有价值
- 考虑阅读场景：不同的 reading_goal 可能有不同的标注重点
- 警告信息很重要：大量警告可能意味着模型处理有问题"""


@lru_cache(maxsize=1)
def get_judge_agent() -> Agent[JudgeAgentDeps, JudgeResult]:
    return Agent[JudgeAgentDeps, JudgeResult](
        model=None,
        output_type=JudgeResult,
        deps_type=JudgeAgentDeps,
        instructions=JUDGE_INSTRUCTIONS,
        name="judge_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )


def _build_judge_prompt(deps: JudgeAgentDeps) -> str:
    left = deps.left_result
    right = deps.right_result
    
    left_annotations_sample = _sample_annotations(left.get("inline_marks", []), 15)
    right_annotations_sample = _sample_annotations(right.get("inline_marks", []), 15)
    
    left_translations_sample = _sample_translations(left.get("translations", []), left.get("article", {}), 10)
    right_translations_sample = _sample_translations(right.get("translations", []), right.get("article", {}), 10)
    
    left_entries_sample = _sample_entries(left.get("sentence_entries", []), 8)
    right_entries_sample = _sample_entries(right.get("sentence_entries", []), 8)
    
    left_warnings = left.get("warnings", [])
    right_warnings = right.get("warnings", [])
    
    return f"""请对比以下两个模型的英语文章分析输出，根据 Rubric 进行评测。

## 原始文本
{deps.original_text}

============================================================================
## 左侧模型 (Left) 完整结果概览
============================================================================

### 基础统计
- 标注总数: {len(left.get("inline_marks", []))}
- 翻译总数: {len(left.get("translations", []))}
- 句尾入口: {len(left.get("sentence_entries", []))}
- 句子数量: {len(left.get("article", {}).get("sentences", []))}
- 段落数量: {len(left.get("article", {}).get("paragraphs", []))}
- 警告数量: {len(left_warnings)}

### 标注详情 (抽样)
{left_annotations_sample}

### 翻译详情 (抽样)
{left_translations_sample}

### 句尾入口 (抽样)
{left_entries_sample}

### 警告信息
{_format_warnings(left_warnings)}

============================================================================
## 右侧模型 (Right) 完整结果概览
============================================================================

### 基础统计
- 标注总数: {len(right.get("inline_marks", []))}
- 翻译总数: {len(right.get("translations", []))}
- 句尾入口: {len(right.get("sentence_entries", []))}
- 句子数量: {len(right.get("article", {}).get("sentences", []))}
- 段落数量: {len(right.get("article", {}).get("paragraphs", []))}
- 警告数量: {len(right_warnings)}

### 标注详情 (抽样)
{right_annotations_sample}

### 翻译详情 (抽样)
{right_translations_sample}

### 句尾入口 (抽样)
{right_entries_sample}

### 警告信息
{_format_warnings(right_warnings)}

============================================================================
## 评测任务
============================================================================

请根据以上两个模型的完整输出（包括抽样的详细数据），按照 Rubric 的五个维度进行评分。

评分要求：
1. 每个维度 0-10 分
2. 为每个维度提供详细的评分理由，对比两个模型的实际表现
3. 确定 winner（left/right/tie）
4. 提供总体评价

请输出严格的 JSON 格式。"""


def _sample_annotations(annotations: list[dict[str, Any]], max_count: int) -> str:
    if not annotations:
        return "（无标注）"
    
    sample = annotations[:max_count]
    lines = []
    for i, ann in enumerate(sample, 1):
        anchor_text = ann.get("anchor", {}).get("anchor_text", "")
        if not anchor_text:
            parts = ann.get("anchor", {}).get("parts", [])
            anchor_text = " + ".join(p.get("anchor_text", "") for p in parts)
        
        ann_type = ann.get("annotation_type", "unknown")
        glossary = ann.get("glossary", {}) or {}
        zh = glossary.get("zh", "")
        gloss = glossary.get("gloss", "")
        reason = glossary.get("reason", "")
        
        gloss_text = zh or gloss or ""
        if reason:
            gloss_text = f"{gloss_text} ({reason})" if gloss_text else reason
        
        lines.append(f"  {i}. [{ann_type}] {anchor_text!r}")
        if gloss_text:
            lines.append(f"     释义: {gloss_text}")
        lines.append("")
    
    if len(annotations) > max_count:
        lines.append(f"  ... 还有 {len(annotations) - max_count} 个标注未显示")
    
    return "\n".join(lines)


def _sample_translations(
    translations: list[dict[str, Any]],
    article: dict[str, Any],
    max_count: int
) -> str:
    if not translations:
        return "（无翻译）"
    
    sentences: dict[str, str] = {}
    for s in article.get("sentences", []):
        sentences[s.get("sentence_id", "")] = s.get("text", "")
    
    sample = translations[:max_count]
    lines = []
    for i, t in enumerate(sample, 1):
        sent_id = t.get("sentence_id", "")
        original = sentences.get(sent_id, sent_id)
        translated = t.get("translation_zh", "")
        
        lines.append(f"  {i}. 原文: {original}")
        lines.append(f"     译文: {translated}")
        lines.append("")
    
    if len(translations) > max_count:
        lines.append(f"  ... 还有 {len(translations) - max_count} 个翻译未显示")
    
    return "\n".join(lines)


def _sample_entries(entries: list[dict[str, Any]], max_count: int) -> str:
    if not entries:
        return "（无句尾入口）"
    
    sample = entries[:max_count]
    lines = []
    for i, e in enumerate(sample, 1):
        entry_type = e.get("entry_type", "unknown")
        label = e.get("label", "")
        title = e.get("title", "")
        content = e.get("content", "")
        
        lines.append(f"  {i}. [{entry_type}] {label}")
        if title:
            lines.append(f"     标题: {title}")
        if content:
            content_preview = content[:150] + ("..." if len(content) > 150 else "")
            lines.append(f"     内容: {content_preview}")
        lines.append("")
    
    if len(entries) > max_count:
        lines.append(f"  ... 还有 {len(entries) - max_count} 个入口未显示")
    
    return "\n".join(lines)


def _format_warnings(warnings: list[dict[str, Any]]) -> str:
    if not warnings:
        return "（无警告）"
    
    lines = []
    for w in warnings:
        code = w.get("code", "unknown")
        level = w.get("level", "warning")
        message = w.get("message", "")
        sent_id = w.get("sentence_id", "")
        
        line = f"  [{level}] {code}: {message}"
        if sent_id:
            line += f" (句子: {sent_id})"
        lines.append(line)
    
    return "\n".join(lines)


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


def _extract_metrics(
    state: dict[str, Any],
    duration_ms: int
) -> CompareMetrics:
    render_scene = state.get("render_scene")
    usage_summary = state.get("usage_summary")
    
    inline_marks: list[Any] = []
    translations: list[Any] = []
    sentences: list[Any] = []
    paragraphs: list[Any] = []
    warnings: list[Any] = []
    
    if render_scene:
        if hasattr(render_scene, "inline_marks"):
            inline_marks = render_scene.inline_marks
        elif isinstance(render_scene, dict):
            inline_marks = render_scene.get("inline_marks", [])
        
        if hasattr(render_scene, "translations"):
            translations = render_scene.translations
        elif isinstance(render_scene, dict):
            translations = render_scene.get("translations", [])
        
        if hasattr(render_scene, "article"):
            article = render_scene.article
            if hasattr(article, "sentences"):
                sentences = article.sentences
            if hasattr(article, "paragraphs"):
                paragraphs = article.paragraphs
        elif isinstance(render_scene, dict):
            article = render_scene.get("article", {})
            sentences = article.get("sentences", []) if isinstance(article, dict) else []
            paragraphs = article.get("paragraphs", []) if isinstance(article, dict) else []
        
        if hasattr(render_scene, "warnings"):
            warnings = render_scene.warnings
        elif isinstance(render_scene, dict):
            warnings = render_scene.get("warnings", [])
    
    token_usage: TokenUsage | None = None
    if usage_summary and isinstance(usage_summary, dict):
        aggregate = usage_summary.get("aggregate", {})
        if aggregate:
            token_usage = TokenUsage(
                input_tokens=aggregate.get("input_tokens"),
                output_tokens=aggregate.get("output_tokens"),
                total_tokens=aggregate.get("total_tokens"),
                per_agent=usage_summary.get("per_agent"),
            )
    
    return CompareMetrics(
        duration_ms=duration_ms,
        token_usage=token_usage,
        warning_count=len(warnings),
        annotation_count=len(inline_marks),
        translation_count=len(translations),
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
    )


def _render_scene_to_dict(scene: Any) -> dict[str, Any]:
    if hasattr(scene, "model_dump"):
        return scene.model_dump(mode="json")
    if isinstance(scene, dict):
        return scene
    return {}


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
    state = await run_article_analysis_with_state(request)
    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)
    
    return state, duration_ms, actual_model_name


async def _run_llm_judge(
    profile_id: str,
    left_result: CompareResultItem,
    right_result: CompareResultItem,
    original_text: str,
) -> JudgeResult:
    from app.llm.router import build_model_for_route
    from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
    
    settings = get_settings()
    model_selection = _build_model_selection(profile_id)
    
    model, _ = build_model_for_route(settings, MODEL_ROUTE_ANNOTATION_GENERATION, model_selection)
    if model is None:
        raise HTTPException(status_code=500, detail=f"Judge model {profile_id} not available")
    
    left_dict = _render_scene_to_dict(left_result.result)
    right_dict = _render_scene_to_dict(right_result.result)
    
    deps = JudgeAgentDeps(
        left_result=left_dict,
        right_result=right_dict,
        original_text=original_text,
    )
    
    prompt = _build_judge_prompt(deps)
    
    try:
        agent = get_judge_agent()
        result = await agent.run(prompt, deps=deps, model=model)
        
        usage = extract_run_usage(result)
        if usage:
            logger.info("Judge agent usage: %s", usage)
        
        return result.output
        
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
    
    left_state, left_duration, left_model_name = await _run_analysis_with_profile(
        text=payload.text,
        profile_id=payload.model_left,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
    )
    
    right_state, right_duration, right_model_name = await _run_analysis_with_profile(
        text=payload.text,
        profile_id=payload.model_right,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
    )
    
    left_render_scene = left_state.get("render_scene")
    right_render_scene = right_state.get("render_scene")
    
    if left_render_scene is None:
        raise HTTPException(status_code=500, detail="Left model analysis returned no result")
    if right_render_scene is None:
        raise HTTPException(status_code=500, detail="Right model analysis returned no result")
    
    left_result = CompareResultItem(
        model_profile=payload.model_left,
        model_name=left_model_name,
        metrics=_extract_metrics(left_state, left_duration),
        result=left_render_scene,
    )
    
    right_result = CompareResultItem(
        model_profile=payload.model_right,
        model_name=right_model_name,
        metrics=_extract_metrics(right_state, right_duration),
        result=right_render_scene,
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
