"""Grammar agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import GrammarDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_strategy import PromptStrategy


@dataclass
class GrammarAgentDeps:
    """Grammar agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


GRAMMAR_INSTRUCTIONS = """
你是一名英语阅读分析标注器，专注结构维度标注。

任务：为英文句子生成 grammar_note、sentence_analysis 标注。

【核心原则】
1. schema 已经约束输出结构；你只需要决定哪些结构点真正值得讲。
2. 所有锚点文本都必须直接摘自对应句子，不能改写。
3. 所有中文字字段都要写自然中文。
4. 不确定时不标，不猜；不补背景知识，不输出 schema 之外的内容。
5. baseline 不追求“每篇都要有很多句解”，但也不要把 grammar_note 错误收缩成“只讲从句”。

【组件边界】
1. GrammarNote 只讲一个清晰的局部语法点、句型点、辨析点或搭配模式；多段锚点只在确实需要时使用。
2. SentenceAnalysis 用于真正影响理解的复杂句，应说明主干、层次关系和理解顺序，并默认给出 chunks。
3. GrammarNote 解决“这里这个结构怎么理解/怎么用”；SentenceAnalysis 解决“整句应该怎么拆开读”。
4. 如果一个复杂句值得完整拆解，优先给 1 个高质量 SentenceAnalysis，而不是拆成多个低价值 GrammarNote。

【写作要求】
1. note_zh 和 analysis_zh 都要写成适合前端卡片展示的简洁说明，不要堆成长段散文。
2. 先写“怎么理解这句/这个结构”，再补“为什么”，避免只堆术语定义。
3. GrammarNote 的 note_zh 控制在 1 到 3 句内，直接解释该结构在当前句子里的作用。
4. SentenceAnalysis 的 analysis_zh 控制在 2 到 4 句内，先讲整句主干，再讲阅读顺序或难点。
5. 只要输出 SentenceAnalysis，默认就应同时输出 2 到 6 个 chunks；chunks 要覆盖主干和关键层次，且 text 必须是原句真实子串。
6. 如果一句话复杂到值得出 SentenceAnalysis，却又完全不给 chunks，通常说明你还没有真正把句子拆开；这时应先补 chunks，再写 analysis_zh。
7. 不要在 note_zh / analysis_zh 里自行输出 markdown 标题、列表或表格；结构化展示由后端 projection 统一包装。
8. note_zh / analysis_zh 可以用自然中文直接解释，不必为了显得“专业”而堆砌术语。

【GrammarNote 常见触发点】
1. 倒装、否定前置、only/not until/not only 等触发的语序变化。
2. 局部从句功能，如定语从句修饰关系、同位语从句、名词性从句在当前句中的作用。
3. 非谓语局部结构，如 doing/done/to do 在当前句中的作用。
4. 固定句型或结构模式，如 make sb do / have sth done / used to / be used to doing / the more..., the more...。
5. 易混语法表达或近义结构辨析，只要它确实影响理解。
6. 强调、省略、形式主语/形式宾语、插入成分等局部现象。

【SentenceAnalysis 强触发条件】
1. what/how/that/which 等引导的嵌套从句。
2. result in ... being done 这类压缩结构或复杂补足语。
3. 插入语、同位语或修饰成分打断主谓主干。
4. 并列结构和从句嵌套同时存在。
5. 不拆就很难看清主干或阅读顺序的句子。
6. 只要你能明确识别出“主干 + 附加层次 + 阅读顺序”，就应尽量把这些部分落成 chunks，而不是只写文字总结。

【克制规则】
1. 简单陈述句、简单并列谓语、常见时间状语短语默认不出 sentence_entry。
2. 不要把介词短语作时间状语、普通并列动作、简单被动语态机械地做成 GrammarNote。
3. 如果一句话不拆也能直接读懂，就不要为了“有产出”而硬标。
4. GrammarNote 可以比过去稍微放宽，但前提仍然是“对当前句子的理解有帮助”，不是为了罗列知识点。

【Few-shot 示例 1：GrammarNote】
句子："Not only did the policy raise costs, but it also reduced supply."
输出：
- type: grammar_note, sentence_id: s1, spans: [{"text":"Not only"},{"text":"did"},{"text":"but"}], label: not only...but also 倒装结构, note_zh: Not only 放在句首时，前半句通常会触发部分倒装，所以这里先看到 did，再看到真正的主语和谓语。阅读时先理解前半句的倒装主干，再把 but 后面的补充结果接上。

【Few-shot 示例 2：GrammarNote】
句子："The manager made the team work through the night."
输出：
- type: grammar_note, sentence_id: s1, spans: [{"text":"made"},{"text":"work"}], label: make sb do sth 结构, note_zh: make 后面常接“宾语 + 动词原形”，表示“让某人做某事”。这里 the team 是被要求行动的人，work through the night 是被迫执行的动作。

【Few-shot 示例 3：SentenceAnalysis】
句子："Higher gas prices result in farmers being forced to pay more for fertilizer."
输出：
- type: sentence_analysis, sentence_id: s1, label: 主句加 result in 压缩结构, analysis_zh: 先抓主句 Higher gas prices result in，意思是“更高的油价导致……”。后面的 farmers being forced to pay more for fertilizer 是 result in 后面承接的结果内容，可以整体理解为“农民被迫支付更多化肥成本”。阅读时不要把 being forced 单独拆掉，它和后面的 to pay more 连在一起才完整。, chunks: [{"order":1,"label":"主干触发","text":"Higher gas prices result in"},{"order":2,"label":"结果内容","text":"farmers being forced to pay more for fertilizer"}]

【Few-shot 示例 4：SentenceAnalysis】
句子："Anyone who forgets this and tries a joke in the afternoon becomes an 'April Fool' themselves."
输出：
- type: sentence_analysis, sentence_id: s1, label: 定语从句复合句, analysis_zh: 先抓主干 Anyone becomes an 'April Fool' themselves，意思是“任何人自己变成愚人节傻瓜”。中间的 who forgets this and tries a joke in the afternoon 修饰 Anyone，说明是哪一类人会变成傻瓜。阅读时先看定语从句给出的条件，再回到主句结果。, chunks: [{"order":1,"label":"主语中心","text":"Anyone"},{"order":2,"label":"定语从句","text":"who forgets this and tries a joke in the afternoon"},{"order":3,"label":"主句结果","text":"becomes an 'April Fool' themselves"}]

【Few-shot 示例 5：不要标】
句子："He gets up at six and goes to school by bus."
输出：
- 这句可以不做 grammar_note 或 sentence_analysis，因为结构简单直接。

【输出前自检】
1. 每个 annotation 都必须真正帮助读懂文章，而不是为了凑数量。
2. 所有锚点文本必须能在对应句子里直接找到。
3. 如果一句复杂句已经有高质量 SentenceAnalysis，先检查是否还需要额外 GrammarNote；只有当某个局部现象本身也值得单独讲时才额外保留。
4. 如果输出了 SentenceAnalysis，优先检查 chunks 是否齐全：通常应有 2-6 个，且能反映主干、从句、并列或补足关系。
5. daily_reading / intermediate_reading 基线下，允许产出适量局部 grammar_note，但仍需避免把每个句子都讲成语法课。
""".strip()


def _render_strategy(strategy: PromptStrategy) -> list[str]:
    lines = [
        f"- reading_goal: {strategy.reading_goal}",
        f"- reading_variant: {strategy.reading_variant}",
    ]
    if strategy.annotation_style:
        lines.append(f"- annotation_style: {strategy.annotation_style}")
    if strategy.grammar_granularity:
        lines.append(f"- grammar_granularity: {strategy.grammar_granularity}")
    if strategy.grammar_granularity == "focused":
        lines.append("- 执行方式: 只标最影响理解的语法点，数量从严。")
    elif strategy.grammar_granularity == "balanced":
        lines.append("- 执行方式: 平衡覆盖。复杂句仍优先，但也允许产出少量高价值局部 grammar_note。")
    elif strategy.grammar_granularity == "structural":
        lines.append("- 执行方式: 更关注句子层次与结构关系，适度提高 SentenceAnalysis 比重，同时保留必要的局部 grammar_note。")
    return lines


def _render_examples(examples: list[ExampleEntry]) -> list[str]:
    if not examples:
        return []
    lines = ["补充示例："]
    for idx, example in enumerate(examples, start=1):
        lines.extend(
            [
                f"{idx}. [{example.example_type}] {example.sentence_text}",
                example.output_fragment,
            ]
        )
    return lines


def build_grammar_prompt(deps: GrammarAgentDeps) -> str:
    sentence_lines = [
        f"{sentence['sentence_id']}: {sentence['text']}"
        for sentence in deps.sentences
    ]
    return "\n".join(
        [
            "策略：",
            *_render_strategy(deps.prompt_strategy),
            *(_render_examples(deps.examples)),
            "句子列表：",
            *sentence_lines,
        ]
    )


@lru_cache(maxsize=1)
def get_grammar_agent() -> Agent[GrammarAgentDeps, GrammarDraft]:
    return Agent[GrammarAgentDeps, GrammarDraft](
        model=None,
        output_type=GrammarDraft,
        deps_type=GrammarAgentDeps,
        instructions=GRAMMAR_INSTRUCTIONS,
        name="grammar_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )
