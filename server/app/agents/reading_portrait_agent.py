"""
Reading Portrait Agent.

Generates user-readable reading portrait based on accumulated reading signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.services.analysis.prompting.prompt_loader import load_agent_instructions


class ReadingPortraitOutput(BaseModel):
    """Generated reading portrait output."""

    common_content: str = Field(
        description="用户常读内容类型的总结，比如：'常读考试类文章，以四六级和考研为主'"
    )
    current_challenges: str = Field(
        description="当前阅读难点分析，比如：'词汇量有待提升，特别是学术类专业术语；长难句理解有困难'"
    )
    next_steps: str = Field(
        description="建议下一步行动，比如：'建议增加学术类文章阅读，重点积累专业词汇；可尝试做一些长难句分析练习'"
    )


@dataclass
class ReadingPortraitAgentDeps:
    """Dependencies for reading portrait agent."""

    signals_json: str
    prompt_context: dict[str, Any] = field(default_factory=dict)


def build_reading_portrait_prompt(deps: ReadingPortraitAgentDeps) -> str:
    """Build the prompt for reading portrait generation."""
    return f"""以下是用户最近的阅读行为统计数据：

{deps.signals_json}

请基于这些数据，生成一份用户可读的阅读画像。注意：
1. 不要透露原始JSON数据的细节
2. 用自然、友好的语言总结
3. 结合阅读目标、变体、词数、标注数量等信息给出有价值的洞察
4. 建议要具体、可执行"""


@lru_cache(maxsize=1)
def get_reading_portrait_agent() -> Agent[ReadingPortraitAgentDeps, ReadingPortraitOutput]:
    """Get the cached reading portrait agent."""
    return Agent[ReadingPortraitAgentDeps, ReadingPortraitOutput](
        model=None,
        output_type=ReadingPortraitOutput,
        deps_type=ReadingPortraitAgentDeps,
        instructions=load_agent_instructions("reading_portrait"),
        name="reading_portrait_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )
