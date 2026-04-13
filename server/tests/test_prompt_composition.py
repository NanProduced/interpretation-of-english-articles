from app.agents.grammar_agent import GrammarAgentDeps, build_grammar_prompt
from app.agents.vocabulary_agent import (
    VocabularyAgentDeps,
    build_vocabulary_prompt,
)
from app.services.analysis.prompting.prompt_composer import PromptSection, merge_prompt_sections
from app.services.analysis.prompting.prompt_strategy import (
    build_grammar_prompt_strategy,
    build_prompt_sections,
    build_repair_prompt_strategy,
    build_vocabulary_prompt_strategy,
)
from app.services.analysis.planning.goal_planner import build_goal_execution_plan


def test_merge_prompt_sections_replaces_by_tag_and_preserves_order() -> None:
    merged = merge_prompt_sections(
        (
            PromptSection("profile", ("profile_id: daily_intermediate",)),
            PromptSection("policy", ("old policy",)),
        ),
        (
            PromptSection("policy", ("new policy",)),
            PromptSection("input_sentences", ("s1: hello",)),
        ),
    )

    assert [section.tag for section in merged] == [
        "profile",
        "policy",
        "input_sentences",
    ]
    assert merged[1].lines == ("new policy",)


def test_vocabulary_prompt_uses_tagged_sections_for_daily_intermediate() -> None:
    plan = build_goal_execution_plan("daily_reading", "intermediate_reading")
    deps = VocabularyAgentDeps(
        sentences=[{"sentence_id": "s1", "text": "Hello, world!"}],
        prompt_strategy=build_vocabulary_prompt_strategy(plan),
        examples=[],
    )

    prompt = build_vocabulary_prompt(deps)

    assert "<profile>" in prompt
    assert "<policy>" in prompt
    assert "<input_sentences>" in prompt
    assert "profile_id: daily_intermediate" in prompt
    assert "本次任务是基础阅读辅助，不做考试解析，也不做学术导读" in prompt
    assert "优先标注真正影响理解的语境义、固定搭配、短语动词" in prompt

def test_grammar_prompt_uses_balanced_policy_lines() -> None:
    plan = build_goal_execution_plan("daily_reading", "intermediate_reading")
    deps = GrammarAgentDeps(
        sentences=[{"sentence_id": "s1", "text": "Higher gas prices result in higher costs."}],
        prompt_strategy=build_grammar_prompt_strategy(plan),
        examples=[],
    )

    prompt = build_grammar_prompt(deps)

    assert "<policy>" in prompt
    assert "grammar_granularity: balanced" in prompt
    assert "只处理真正影响理解的结构" in prompt
    assert "复杂句优先解释主干、从句关系和阅读顺序" in prompt


def test_repair_prompt_strategy_adds_runtime_constraints_section() -> None:
    strategy = build_repair_prompt_strategy("只修复 grounding 错误，不要重写整份草稿。")

    sections = build_prompt_sections(strategy)

    tags = [section.tag for section in sections]
    assert tags == ["profile", "runtime_constraints"]
    assert sections[1].lines == ("只修复 grounding 错误，不要重写整份草稿。",)
