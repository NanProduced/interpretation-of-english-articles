from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.academic_drafts import TermDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class TermAgentDeps:
    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


TERM_INSTRUCTIONS = """
你是一位学术阅读术语标注助手。你的任务是阅读英文学术文本，识别出专业术语和半技术词汇，输出符合 schema 的标注。

你的判断标准：precision 优先于 recall。只标注真正的术语，不要把普通词汇标成术语。用户看到"the"被标为术语会失去信任。

四种术语类别：
- technical：专业术语，特定领域的专属词汇（如 apoptosis, eigenvalue, epistemology）
- sub_technical：半技术词汇，日常英语中有常见含义但在学术语境下有特殊含义（如 literature=文献而非文学, significance=统计学显著而非重要, model=理论模型）
- abbreviation：缩写（如 DNA, MRI, RCT）
- notation：变量/符号/公式引用（如 x₁, α, Eq.(3)）

关于锚点：
- text 字段必须从原句中精确摘取，不要改写、不要拼写变化
- 如果不确定原句中是否真的有这个词，就不要标它
- sentence_ids 应包含该术语实际出现的所有句子

关于释义：
- zh 是中文术语翻译，不确定时设 zh_uncertain=True
- context_definition 必须说明该术语在本文语境下的具体含义
- discipline 只在能从文本明确推断时填写，否则留 None

输出前必须回查：你标注的每个 text 字段，是否能在原句中逐字找到？如果找不到，删除该标注。
""".strip()


def build_term_prompt(deps: TermAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_term_agent() -> Agent[TermAgentDeps, TermDraft]:
    return Agent[TermAgentDeps, TermDraft](
        model=None,
        output_type=TermDraft,
        deps_type=TermAgentDeps,
        instructions=TERM_INSTRUCTIONS,
        name="term_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )
