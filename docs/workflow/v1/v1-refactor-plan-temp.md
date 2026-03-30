# V0 到 V1 代码重构计划（临时）

说明：

- 本文档用于指导 `v0 -> v1` 的代码改造过程
- 当 V1 稳定、评估通过且旧代码已清理完成后，本文件应删除
- 本文件不作为长期规范文档维护

## 1. 重构目标

本次重构的目标不是在 V0 代码上继续补丁式迭代，而是：

- 以 V1 设计为准重建 workflow 主链路
- 尽量避免保留会误导后续开发的 V0 历史实现
- 删除伪 fallback、过重 schema、冗余节点和命名不一致逻辑
- 保留 LangSmith 可用性与最小必要的回放能力

## 2. 总体策略

### 2.1 先立新，再删旧

按以下顺序推进：

1. 先建 V1 schema、rules、workflow 和 tracing
2. 跑通样本与评估
3. 再删除 V0 主链路和不再使用的文档/代码

### 2.2 逻辑迁移优先于兼容层

V1 不是对 V0 的兼容包装。

原则：

- 能重写就不保留旧接口拼接层
- 能删除就不保留“为了兼容而兼容”的桥接逻辑
- 只保留确实对过渡期有帮助、且不会污染长期结构的薄适配层

### 2.3 清理优先级

优先删除以下 V0 设计残留：

- 伪 fallback 标注
- 复杂 `SentenceComponent` 绝对位置结构
- `core + translation` 的重复重型链路
- 裸 `span` 坐标命名
- 带版本号的 node / schema / prompt 命名

## 3. 重构阶段

## 阶段 A：先定义新契约

输出：

- V1 schema
- V1 `user_config`
- V1 `user_rules`
- V1 render contract
- V1 trace metadata 方案

重点：

- 所有核心字段补 `Field(description=...)`
- 命名统一按 `server/README.md` 执行
- prompt 统一为中文

## 阶段 B：重建输入链路

目标：

- 重写 `prepare_input`
- 用本地逻辑替代 V0 的 LLM guardrails 主路径

实现项：

- 输入清洗
- 安全可渲染文本生成
- 段落与句子切分
- 粗粒度输入拒绝与失败状态

删除候选：

- V0 guardrails prompt
- V0 guardrails 伪 fallback 语义

保留项：

- LangSmith 可观测性
- 预处理结果的最小调试信息

## 阶段 C：重建配置层

目标：

- 建立 `user_config -> user_rules` 模块

实现项：

- `reading_goal`
- `reading_variant`
- `profile_id`
- prompt 注入规则
- 展示层策略
- few-shot 选择接口预留

删除候选：

- 只靠 `profile_key` 驱动全部行为的逻辑

## 阶段 D：重建主教学节点

目标：

- 建立单主节点 `generate_annotations`

实现项：

- 统一中文 prompt
- 精简结构化输出
- 仅返回句级锚点
- 包含逐句翻译

删除候选：

- `core_agent_v0`
- `translation_agent_v0`
- 关键短语翻译与词汇解释重复逻辑

## 阶段 E：重建组装层

目标：

- 建立 `assemble_result`

实现项：

- `anchor_text -> render_span`
- 去重与过滤
- `render_index`
- `render_marks`
- 失败显式化

删除候选：

- V0 `merge`
- V0 `enrich`
- V0 `validate`
- 所有教学伪 fallback 结果

## 阶段 F：重建 tracing 与评估

目标：

- 保持 LangSmith 可用
- 调整 metadata / tags，使其服务于 V1 评估

实现项：

- 新 workflow 名与 node 名
- 新 metadata 字段
- token、latency、drop_count 记录
- 关键样本回放入口

删除候选：

- 旧节点命名和旧 metadata 语义

## 阶段 G：删除 V0 历史代码

当满足以下条件后，删除 V0 主链路：

- V1 样本测试通过
- 结构化输出稳定
- 前端联调通过
- LangSmith trace 正常
- 无伪 fallback 残留

删除范围重点关注：

- V0 prompt
- V0 workflow 节点
- V0 fallback 逻辑
- V0 schema 草案引用
- 旧 user_config 文档和旧命名

## 4. 代码改造注意事项

### 4.1 注释

- 对核心逻辑补注释
- 不在简单 getter/setter 或显而易见的字段映射处堆注释

### 4.2 Prompt

- 全部改为中文
- 统一模板结构
- few-shot 走单独构造逻辑，不硬编码在函数体中

### 4.3 Schema

- 核心字段必须写 `Field(description=...)`
- 所有坐标字段显式命名
- 不再混用句内坐标和全文坐标

### 4.4 删除策略

- 不保留“也许以后还会用”的死代码
- 删除前先确认：
  - 是否还有调用
  - 是否还有文档引用
  - 是否还有 LangSmith 依赖

## 5. LangSmith 调整清单

V1 需要同步修改：

- workflow root `run_name`
- root metadata
- node metadata
- tags 语义
- usage metadata 回填字段

建议重点保留的 trace 信息：

- `workflow_name`
- `workflow_version`
- `profile_id`
- `reading_goal`
- `reading_variant`
- `model_profile`
- `prompt_template_id`
- `annotation_count`
- `drop_count`
- `failure_reason`

## 6. 完成标准

满足以下条件，说明可以进入“删除临时计划文档”阶段：

- V1 文档与代码一致
- V1 workflow 已替代主链路
- V0 主链路代码已删除或彻底下线
- LangSmith 可正常使用
- 样本评估无明显结构性错误
- 前端结果页渲染稳定
