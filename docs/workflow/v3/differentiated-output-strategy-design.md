# 差异化输出策略设计文档

> 文档定位：用于指导 Claread 透读在 Workflow V3 上实现“按阅读目标差异化输出”的配置架构、prompt 分层和 few-shot 注入机制。  
> 生效范围：本稿是 [Workflow V3 设计与重构文档](./workflow-v3-design.md) 的补充细化稿，聚焦 `reading_goal` / `reading_variant` 的策略设计，不展开模型路由、前端页面改造和 exam_tag 数据建设细节。  
> 当前阶段结论：先以 `daily_reading + intermediate_reading` 作为唯一 baseline，对 prompt 做“非风格化、仅基础输出控制”的收敛；其余场景先完成设计，不立即落代码。

## 1. 背景

当前 V3 主链路已经具备以下基础能力：

- 请求层可传入 `reading_goal` 与 `reading_variant`
- 后端可把它们映射为 `UserRules`
- 三个 agent 已拆分为 `vocabulary_agent`、`grammar_agent`、`translation_agent`
- prompt 运行时部分已经支持 section 化组装
- example 注入已经预留 `ExampleStrategy`

但当前实现仍有一个明显问题：

- “用户场景差异”
- “教学策略差异”
- “prompt 注入差异”
- “few-shot 来源差异”
- “后处理密度控制差异”

还没有被拆成稳定、可独立演进的层次。

结果是：

1. baseline 不够纯，当前 prompt 中仍混有风格性规则和内联示例。
2. `profile_id` 同时承担 prompt 语义与后处理密度控制，不利于精细扩展。
3. 后续要做 exam / academic 时，很容易继续把 prompt 写成越来越大的条件分支。

因此本稿先解决两个问题：

1. 差异化能力的设计边界是什么。
2. 代码架构应该如何分层，才能允许后续仅通过 prompt / few-shot / policy 调整场景输出。

## 2. 目标

本阶段目标：

1. 明确三类 `reading_goal` 的产品意图与输出策略差异。
2. 设计一套可扩展的配置架构，把 baseline、风格化 overlay、few-shot、RAG 注入彼此解耦。
3. 确定第一阶段只落地 `daily_reading`，且只调 prompt，不先改 agent topology。

非目标：

1. 当前不实现 exam_tag 数据库改造。
2. 当前不实现 RAG few-shot 检索。
3. 当前不立刻重写 academic 的完整 agent 逻辑。
4. 当前不引入新的 workflow node。

## 3. 设计原则

### 3.1 baseline 必须是“无额外风格”的对照组

baseline 不是“默认风格”，而是“最小教学约束 + 最小格式约束 + 最小 few-shot”。

它应满足：

- 不提前模拟考试讲解口吻
- 不提前模拟论文导读口吻
- 不额外注入发散举例、术语扩展、考试技巧
- 只要求模型在既定 schema 下，产出稳定、克制、可解释的结果

这意味着：

- 基础任务定义要保留
- 输出格式要求要保留
- 与特定场景绑定的风格性规则应移出 baseline

### 3.2 差异化优先作用在“讲解选择与表达方式”，而不是 schema

V3 第一阶段不建议为每种 `reading_goal` 设计完全不同的返回协议。

推荐原则：

- 前端 contract 尽量统一
- 内部 agent draft schema 尽量统一
- 差异化主要体现在：
  - prompt overlay
  - few-shot selection
  - annotation density
  - 解释角度
  - 翻译风格
  - 句子解析侧重点

只有当某个场景的任务目标与当前 schema 产生根本冲突时，才考虑分叉 agent 或分叉输出层。

### 3.3 先保证 daily_reading 收敛，再扩展其他场景

`daily_reading` 是最适合做 baseline 的场景，原因是：

- 用户目标最接近“辅助理解 + 温和学习”
- 不强依赖考试知识体系
- 不强依赖学科术语体系
- 仅通过 prompt 收敛就能得到较高价值

所以第一阶段建议：

1. 明确 `daily_reading` baseline
2. 清理现有 prompt 中不属于 baseline 的规则
3. 建立 overlay 机制
4. 再讨论 `exam` 与 `academic`

## 4. 用户场景建模

## 4.1 `daily_reading`

目标用户：

- 在日常阅读中提升英语能力的普通学习者
- 重点不是应试，而是“读懂 + 顺手学到东西”

核心诉求：

- 遇到不熟的词、短语时能快速看懂
- 遇到一般长句时能被拆清楚
- 语法解释尽量直白，不要被英语语言学术语压住
- 有需要时可以补少量例子或换种说法帮助理解

策略特点：

- 以理解与支持型讲解为主
- 允许少量教学型扩展，但不做考试导向表达
- 语法可以讲，但优先说“怎么理解”，再说“它叫什么”

按 `reading_variant` 细分：

### `beginner_reading`

- 词汇与短语帮助优先级最高
- 长句拆解要更积极
- 语法点数量可以适当少而清晰
- 更强调“看懂这句”的直接帮助

### `intermediate_reading`

- 词汇、短语、结构说明保持均衡
- 仍以自然解释为主，不提前转向考试风格
- 推荐作为 baseline 主对照组

### `intensive_reading`

- 可以提高结构分析密度
- 可以允许少量术语，但术语不应主导说明
- 强调“精读式理解”，但仍不是考试解析

## 4.2 `exam`

目标用户：

- 以考试提分为核心目的的学习者

核心诉求：

- 解释要围绕该考试真正关心的点
- 同样的句子，不同考试的讲解重点应不同
- 词汇优先级、长难句拆法、语法强调程度都应体现考试差异

本场景的关键不是“统一 exam prompt”，而是“按考试类型建子策略”。

当前建议的 `reading_variant` 方向：

- `gaokao`
- `cet`
- `kaoyan`
- `gre_tem`（建议后续替代当前 `gre`）
- `ielts_toefl`

说明：

- `gre_tem` 是暂定设计名，不代表本轮必须改代码。
- exam_tag 的数据库建设在下一轮专题讨论，不在本稿展开。

各子场景策略摘要：

### `gaokao`

- 重点偏显性语法、基础词汇和阅读理解支撑
- 解释应直接、清晰、显性
- 术语可用，但要尽量贴近中学英语教学语言

### `cet`

- 不主打显性语法讲解
- 更强调理解辅助、固定搭配、阅读中的隐含结构
- 语法解释应弱化“考点感”，强化“帮助理解”

### `kaoyan`

- 高度依赖长难句、从句嵌套、主从关系拆解
- 句子结构分析权重显著提升
- 翻译与结构说明要更紧密配合

### `gre_tem`

- 允许更高密度、更精细的语法与结构分析
- 可以适当使用更专业的术语
- 但术语必须服务于理解，不能沦为标签堆叠

### `ielts_toefl`

- 语法不是显性考点
- 更强调它作为理解与表达工具的价值
- 讲解中应弱化“这是什么语法题”，强化“这会如何影响阅读理解与表达准确性”

设计注意：

- exam 不是一个 overlay，而是一族 overlay profile。
- 后续需要单独补一份“考试场景知识来源与校验方案”，避免只凭经验写 prompt。

## 4.3 `academic`

目标用户：

- 阅读英文论文、学术文献的研究生、研究者、从业者

核心诉求：

- 快速理解论文在说什么
- 术语准确
- 长句拆清楚
- 句子分析以“理解论证与信息结构”为目标，而不是“学英语”

与 `daily_reading` 的根本区别：

- 用户主要不是来学英语
- 用户主要不是来学语法
- 用户要的是“准确理解文本内容”

因此 academic 不应简单视为“更高级的 daily_reading”。

推荐策略：

- vocabulary 重点转向术语、学术表达、领域搭配
- grammar_note 大幅弱化，只有在结构确实阻碍理解时才出现
- sentence_analysis 转为“信息结构与逻辑层次拆解”
- translation 风格应强调准确、术语一致、论证关系清晰

这意味着：

- academic 很可能需要独立 prompt overlay
- 长期看甚至可能需要独立的 grammar / sentence analysis 任务定义

但在第一阶段，仍建议先保持现有 agent topology，只改 prompt 和 policy。

## 5. 推荐的配置分层

为避免继续把所有逻辑塞进 `UserRules`，建议把配置拆成 5 层。

### 5.1 `RequestConfig`

对应用户原始请求：

- `reading_goal`
- `reading_variant`
- `source_type`

职责：

- 保留用户输入事实
- 不携带推导后的教学语义

### 5.2 `ScenarioConfig`

对应标准化场景定义：

- `scenario_id`
- `goal_family`
- `variant_family`
- `difficulty_level`
- `domain_mode`

职责：

- 把请求配置映射为统一场景标识
- 供 tracing、实验分桶、overlay 选择使用

### 5.3 `TaskPolicy`

对应确定性产品策略：

- `vocabulary_policy`
- `grammar_policy`
- `translation_policy`
- `annotation_density`
- `term_precision_level`
- `expansion_level`

职责：

- 控制“该讲什么、讲多少、哪类优先”
- 供 prompt 与 normalize_and_ground 同时消费

注意：

- 这一层不应包含自然语言 prompt 文本
- 也不应绑定某个 agent 的具体话术

### 5.4 `PromptPlan`

对应 prompt 注入计划：

- `base_sections`
- `policy_sections`
- `style_sections`
- `overlay_sections`
- `runtime_sections`

职责：

- 明确 prompt 的来源与覆盖顺序
- 允许后续只替换局部 section，而不是拼接大字符串

### 5.5 `ExamplePlan`

对应 few-shot 计划：

- `provider = baseline | manual | rag`
- `selection_mode`
- `example_ids`
- `resolved_examples`

职责：

- 明确示例从哪里来
- 让 baseline、手工配置、RAG 检索共享同一注入口

## 6. 推荐的运行时装配结构

当前的 `UserRules -> PromptStrategy / ExampleStrategy` 可以继续保留思路，但建议升级为下述 bundle：

```text
AnalysisConfigBundle
├── scenario_config
├── task_policy
├── vocabulary_prompt_plan
├── grammar_prompt_plan
├── translation_prompt_plan
├── vocabulary_example_plan
├── grammar_example_plan
└── translation_example_plan
```

推荐职责：

- `derive_user_config_node`
  统一生成 `AnalysisConfigBundle`
- `parallel_agents_node`
  只消费 bundle，不再现场推导 prompt/example
- `normalize_and_ground`
  读取 `task_policy` 中与密度控制有关的确定性参数

这样做的收益：

1. 配置推导集中，便于调试与 tracing。
2. prompt 与后处理解耦，不再都绑在 `profile_id` 上。
3. 未来新增 `exam` / `academic` 不需要把逻辑散落到 node、agent、normalize 多处。

## 7. Prompt 分层建议

建议把 agent prompt 统一拆成以下层次：

1. `agent_core`
2. `output_contract`
3. `baseline_task`
4. `scenario_policy`
5. `style_overlay`
6. `few_shot_examples`
7. `input_sentences`

含义如下：

### `agent_core`

稳定定义 agent 的角色边界，例如：

- vocabulary agent 只负责哪些 annotation 类型
- grammar agent 只负责哪些结构说明
- translation agent 必须全覆盖逐句翻译

这部分应尽量长期稳定，不随场景频繁改。

### `output_contract`

只描述结构约束、禁止事项、锚点规则。

这部分应尽量是“纯格式控制”。

### `baseline_task`

只描述在无风格化前提下，这个 agent 的基础任务优先级。

例如：

- 少标但不能乱标
- 语法解释优先说怎么理解
- 翻译要忠实、自然、完整

### `scenario_policy`

从 `TaskPolicy` 翻译成自然语言约束。

例如：

- 本场景弱化语法术语
- 本场景提高长难句结构说明优先级
- 本场景优先术语准确性

### `style_overlay`

只用于“额外风格化”或“场景特殊表达方式”。

例如：

- exam 的考试导向表达
- academic 的论文导读表达

baseline 阶段可以为空。

### `few_shot_examples`

统一由 example plan 注入。

关键要求：

- agent 静态 instructions 里不再长期内嵌大量示例
- baseline 例子也应通过这一层进入

### `input_sentences`

保持现在的做法即可。

## 8. 三类 goal 的模块化实现建议

## 8.1 `daily_reading`

第一阶段建议仅通过以下方式实现：

- 清理静态 instructions 中过强的风格性表述
- 补一层更纯的 baseline task section
- 通过 `scenario_policy` 区分 beginner / intermediate / intensive

不建议第一阶段做：

- 单独分叉 agent
- 单独分叉 schema
- 单独分叉 normalize 逻辑

## 8.2 `exam`

第二阶段建议实现为：

- 共用 agent topology
- 为每个 exam variant 准备独立的 prompt overlay
- 为每个 exam variant 准备可演进的 example provider
- 在 `TaskPolicy` 中增加 exam-specific priority

如果后续发现某些考试场景在输出类型上差异过大，再考虑分叉 agent。

## 8.3 `academic`

建议分两步：

第一步：

- 保持当前三 agent 架构
- 大幅调整 vocabulary / grammar / translation prompt overlay
- 压低 grammar_note 权重，提高 sentence_analysis 的信息结构分析属性

第二步：

- 评估是否需要把 `grammar_agent` 演化为 `structure_agent`
- 评估是否需要为 academic 增加术语一致性和论证关系专门约束

## 9. 第一阶段实施范围

当前建议只做以下内容：

1. 明确 `daily_reading + intermediate_reading` 的 baseline 定义。
2. 从三个 agent 的静态 instructions 中分离出：
   - 核心角色定义
   - 纯输出契约
   - 可迁移的示例
3. 把示例从静态 instructions 迁移到 `ExampleStrategy`。
4. 把与场景相关的 policy 改为通过 section 注入。
5. 把 normalize 中的密度控制从 `profile_id` 绑定改为 `TaskPolicy` 绑定。

这一阶段不做：

1. 新增 goal / variant 枚举
2. 接入 RAG
3. 接入 exam_tag
4. academic 特化 agent

## 10. 推荐代码改造方向

建议后续重构的目标目录职责如下：

- `app/services/analysis/scenario_config.py`
  负责 `reading_goal + reading_variant -> ScenarioConfig`
- `app/services/analysis/task_policy.py`
  负责场景到产品策略的确定性映射
- `app/services/analysis/prompt_plan.py`
  负责 section 组合计划
- `app/services/analysis/example_provider.py`
  负责 baseline/manual/rag 的示例解析
- `app/services/analysis/config_bundle.py`
  负责统一产出 `AnalysisConfigBundle`

现有文件可对应演化为：

- `user_rules.py`
  逐步收缩或被替代，不再承担全部策略职责
- `prompt_strategy.py`
  从“字段包”升级为“prompt plan builder”
- `example_strategy.py`
  从“静态 list 容器”升级为“example provider façade”
- `strategy_builder.py`
  升级为 bundle assembler，面向 agent 产出最终 plan

## 11. 决策摘要

本稿的关键决策如下：

1. baseline 必须定义为“非风格化、仅基础输出控制”的对照组。
2. `daily_reading` 先落地，`intermediate_reading` 作为主 baseline。
3. `exam` 是一组子策略，不是单一 prompt。
4. `academic` 不是更高级的 `daily_reading`，其任务目标本质不同。
5. 差异化优先通过 prompt overlay、few-shot provider、task policy 实现，而不是立即分叉 workflow。
6. 后处理策略应从 `profile_id` 解耦，改为消费显式 policy。

## 12. 待讨论问题

下一轮建议按以下顺序继续讨论：

1. `daily_reading` baseline 的三个 agent prompt 应保留什么，移出什么。
2. `daily_reading` 的 beginner / intermediate / intensive 应分别调整哪些 policy。
3. exam 维度的 `reading_variant` 是否正式改为 `gaokao / cet / kaoyan / gre_tem / ielts_toefl`。
4. academic 是否仍保留 `grammar_agent` 命名，还是中长期改为 `structure_agent`。
5. exam_tag 在数据库中的建模方式与 few-shot/RAG 的联动方式。

## 13. 最终结论

差异化输出的核心不是“给不同场景多加几句 prompt”，而是先把系统拆成稳定的层：

- 用户请求层
- 场景标准化层
- 产品策略层
- prompt overlay 层
- example provider 层

只有这样，`daily_reading`、`exam`、`academic` 才能在共享 workflow 主体的前提下，分别演进自己的输出策略，而不会把当前 baseline 再次污染成一个难以调试的大 prompt。
