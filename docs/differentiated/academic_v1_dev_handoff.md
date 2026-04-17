# academic v1 开发对照文档

> 用途：给开发 agent 直接执行的实现说明。  
> 权威来源：以 [academic_reading_differentiation.md](./academic_reading_differentiation.md) 第 12 节为准；本文件只做开发收口，不重复展开研究背景。

## 1. 结论

`academic v1` 可以开始开发，但**不建议直接按主文档逐段开发**。

原因不是方向不清楚，而是主文档仍然承担了研究记录、历史探索、产品论证三种角色；开发 agent 更适合按这份 handoff 文档执行，避免把背景章节误当成实现规范。

## 2. 开发目标

本期目标：做出 `academic` 的最小可联调闭环，让用户在 academic 模式下拿到稳定的“内容理解优先”输出。

v1 用户价值：
- 有稳定逐句翻译
- 有高 precision 的术语标注
- 有低噪声的逻辑标注
- 对少量确实难懂的句子给解释性改写

v1 不追求：
- 论文结构导航
- 首屏全文摘要
- 强制每段都有角色标签
- 完整学术性检测框架

## 3. 唯一规范

开发时只遵守下面这些规则：

1. academic v1 是“专业内容理解模式”，不是“英语教学模式”。
2. academic v1 首屏解决“逐句读懂当前段落”，不是“快速把握全文结构”。
3. workflow 采用两阶段：
   `term_agent + translation_agent` 并行，之后进入 `understanding_agent`。
4. v1 的正式 draft 只有三个：
   `TermDraft`、`TranslationDraft`、`UnderstandingDraft`。
5. `UnderstandingDraft` 内含：
   `logic_notes`、`interpretation_notes`、`paragraph_roles`、`content_summary`。
6. `paragraph_roles` 和 `content_summary` 是 `P2`：
   schema 支持，但 Phase 1 不强求产出，缺失不报错。

## 4. 正式对象

Phase 1 必须落地这些对象：

- `TermNote`
- `TermDraft`
- `AcademicSentenceTranslation`
- `TranslationDraft`
- `LogicNote`
- `InterpretationNote`
- `ParagraphRole`
- `ContentSummary`
- `UnderstandingDraft`
- `AcademicGoalPolicy`
- `AcademicNormalizedResult`
- `AcademicInlineGlossary`
- `AcademicInlineMark`
- `AcademicSentenceEntry`
- `AcademicRenderSceneModel`

约束：
- `TermNote.text`、`LogicNote.anchor_text` 必须可做精确子串校验
- `TermNote.context_definition`、`LogicNote.explanation`、`InterpretationNote.interpretation` 只要求句级可追溯
- `AcademicTranslation.translation_zh` 和 `ContentSummary` 属于解释层，不要求精确 span

## 5. 输出优先级

按重要性排序：

1. `P0`：逐句翻译
2. `P0`：术语标注
3. `P1`：逻辑标注
4. `P1`：解释性改写
5. `P2`：段落角色
6. `P2`：内容概要

实现约束：
- `InterpretationNote` 允许为空，不是每句都需要解释
- `ParagraphRole` 允许为空
- `ContentSummary` 允许为空

## 6. Normalize 规则

不要用“P0/P1 任意为空就降级”这种粗规则。

Phase 1 推荐判定：
- `translations` 缺失：必降级
- `term_annotations` 全空且文本明显存在术语密度：降级
- `logic_notes` 全空：不自动降级，需结合文本复杂度判断
- `interpretation_notes` 全空：不自动降级，这是合法结果
- `paragraph_roles` / `content_summary` 为空：不降级

因此 normalize 至少要保留两个能力：
- 基于文本复杂度做轻量 coverage 判定
- 区分“合法为空”和“异常缺失”

## 7. Projection 规则

Projection 目标统一是 `AcademicRenderSceneModel`。

v1 只渲染：
- `translations`
- `inline_marks`
- `sentence_entries`
- `content_summary`（若有）
- `warnings`

v1 不渲染：
- `paragraph_role_marks`
- 结构导航条
- 摘要卡片
- 行内 interpretation mark

映射规则：
- `TermNote` -> `AcademicInlineMark(annotation_type="term_note")`
- `LogicNote` -> `AcademicInlineMark(annotation_type="logic_note")`
- `InterpretationNote` -> `AcademicSentenceEntry(entry_type="interpretation_note")`

## 8. Agent 职责

`term_agent`
- 只做术语识别与释义
- precision 优先于 recall
- 不做逻辑和解释

`translation_agent`
- 只做逐句翻译
- 必须保留 hedging、限定条件、不确定性
- 不做术语解释和逻辑分析

`understanding_agent`
- 产出 `logic_notes`
- 产出 `interpretation_notes`
- 可选产出 `paragraph_roles`
- 可选产出 `content_summary`

特别要求：
- `understanding_agent` 读取 `TermDraft` 但只能把它当参考
- 如 `TermDraft` 与原文矛盾，以原文为准

## 9. 代码实施顺序

建议 agent 严格按这个顺序开发：

1. 补 academic schema 定义
2. 补 academic workflow state
3. 实现 `term_agent`
4. 实现 `translation_agent`
5. 实现 `understanding_agent`
6. 实现 academic normalize
7. 实现 academic projection
8. 接通 `/analyze`
9. 接通 `/analysis-tasks`
10. 补最小测试集

不要先做：
- 前端大改
- FragmentHint
- AcademicTextScore
- 引用标记高级处理
- 结构导航与段落标签展示

## 10. 最小测试要求

至少覆盖：

1. `academic` 请求不再走 `501/422` 占位失败
2. `term_agent + translation_agent` 并行链路可跑通
3. `understanding_agent` 可产出空的 `interpretation_notes` 且不视为错误
4. `paragraph_roles` / `content_summary` 为空时，normalize 与 projection 不报错
5. `AcademicRenderSceneModel` 能成功校验
6. `logic_density` 和 `interpretation_density` 会生效

## 11. 评审重点

我后续会重点看这些点：

1. 有没有把 `InterpretationNote` 做成“万能解释框”
2. 有没有把 `translation` 润色得过头，丢掉 hedging
3. 有没有误把普通词汇标成术语
4. 有没有把 `P2` 字段当成必填
5. 有没有让 normalize 因“合法空结果”误判 degraded
6. 有没有让 projection 偷偷回退到 learning 语义

## 12. 给开发 agent 的一句话说明

按 `academic_reading_differentiation.md` 第 12 节和本 handoff 文档开发 `academic v1`。先做后端最小闭环：`TermDraft + TranslationDraft + UnderstandingDraft -> AcademicNormalizedResult -> AcademicRenderSceneModel`，不要扩 UI，不要做检测框架，不要把 P2 字段当成必填。
