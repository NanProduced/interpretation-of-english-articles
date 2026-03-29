from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, RunContext

from app.config.settings import get_settings
from app.agents.model_factory import build_guardrails_model
from app.schemas.preprocess import GuardrailsAssessment


@dataclass
class GuardrailsDeps:
    # 这一层只保留 guardrails 判定真正依赖的上下文，避免把整份复杂状态直接塞进 Prompt。
    profile_key: str
    paragraph_count: int
    sentence_count: int
    english_ratio: float
    non_english_ratio: float
    noise_ratio: float
    has_html: bool
    has_code_like_content: bool
    appears_truncated: bool


def _build_model():
    settings = get_settings()
    return build_guardrails_model(settings)


def _instructions(ctx: RunContext[GuardrailsDeps]) -> str:
    deps = ctx.deps
    return f"""
你是英文文章解读工作流中的 guardrails / preprocess agent。

你的任务不是做完整解读，而是基于输入文本的预处理上下文，判断文本是否适合进入后续完整标注流程，并输出严格的结构化结果。

用户档案:
- profile_key: {deps.profile_key}

预处理上下文:
- paragraph_count: {deps.paragraph_count}
- sentence_count: {deps.sentence_count}
- english_ratio: {deps.english_ratio:.2f}
- non_english_ratio: {deps.non_english_ratio:.2f}
- noise_ratio: {deps.noise_ratio:.2f}
- has_html: {deps.has_html}
- has_code_like_content: {deps.has_code_like_content}
- appears_truncated: {deps.appears_truncated}

输出要求:
1. 只输出 GuardrailsAssessment 对应的结构化字段。
2. text_type 只能是: article, list, subtitle, code, email, other
3. issues.type 只能是:
   - possible_grammar_issue
   - possible_spelling_issue
   - non_english_content
   - noise_content
   - truncated_text
   - unsupported_text_type
4. severity 只能是: low, medium, high
5. quality.grade 只能是: good, acceptable, poor
6. routing.decision 只能是: full, degraded, reject
7. 如果文本整体可用于正常解读, routing.decision 应优先使用 full。
8. 只有在文本类型明显不适合文章解读，或非英文/噪音严重影响理解时，才使用 reject。
9. warning 与 summary 使用简洁中文。
10. 不要输出 markdown，不要附加解释，不要输出模型思考过程。
""".strip()


@lru_cache(maxsize=1)
def get_guardrails_agent() -> Agent[GuardrailsDeps, GuardrailsAssessment] | None:
    model = _build_model()
    if model is None:
        return None

    # Agent 本身只负责“判断是否适合进入后续流程”，不负责完整文章解读。
    return Agent[GuardrailsDeps, GuardrailsAssessment](
        model=model,
        output_type=GuardrailsAssessment,
        deps_type=GuardrailsDeps,
        instructions=_instructions,
        name="preprocess_guardrails_v0",
        retries=2,
        output_retries=2,
        instrument=True,
    )
