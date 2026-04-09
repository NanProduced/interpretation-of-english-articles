from app.agents.grammar_agent import GrammarAgentDeps, build_grammar_prompt
from app.agents.vocabulary_agent import (
    VocabularyAgentDeps,
    build_vocabulary_prompt,
)
from app.services.analysis.prompt_composer import PromptSection, merge_prompt_sections
from app.services.analysis.prompt_strategy import (
    build_grammar_prompt_strategy,
    build_prompt_sections,
    build_repair_prompt_strategy,
    build_vocabulary_prompt_strategy,
)
from app.services.analysis.user_rules import derive_user_rules


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
    user_rules = derive_user_rules("daily_reading", "intermediate_reading")
    deps = VocabularyAgentDeps(
        sentences=[{"sentence_id": "s1", "text": "Hello, world!"}],
        prompt_strategy=build_vocabulary_prompt_strategy(user_rules),
        examples=[],
    )

    prompt = build_vocabulary_prompt(deps)

    assert "<profile>" in prompt
    assert "<policy>" in prompt
    assert "<input_sentences>" in prompt
    assert "profile_id: daily_intermediate" in prompt
    assert "当前 profile=daily_intermediate，按 baseline 调试" in prompt
    assert "只标最影响理解的高价值词" in prompt


def test_grammar_prompt_uses_balanced_policy_lines() -> None:
    user_rules = derive_user_rules("daily_reading", "intermediate_reading")
    deps = GrammarAgentDeps(
        sentences=[{"sentence_id": "s1", "text": "Higher gas prices result in higher costs."}],
        prompt_strategy=build_grammar_prompt_strategy(user_rules),
        examples=[],
    )

    prompt = build_grammar_prompt(deps)

    assert "<policy>" in prompt
    assert "grammar_granularity: balanced" in prompt
    assert "复杂句仍优先，但允许少量高价值局部 grammar_note" in prompt


def test_repair_prompt_strategy_adds_runtime_constraints_section() -> None:
    strategy = build_repair_prompt_strategy("只修复 grounding 错误，不要重写整份草稿。")

    sections = build_prompt_sections(strategy)

    tags = [section.tag for section in sections]
    assert tags == ["profile", "runtime_constraints"]
    assert sections[1].lines == ("只修复 grounding 错误，不要重写整份草稿。",)
