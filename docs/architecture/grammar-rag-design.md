# Grammar RAG 设计文档

> 文档定位：用于指导 Claread 透读当前阶段 `grammar_agent` 的 RAG 能力建设。  
> 生效范围：本文只覆盖 `grammar_note` 与 `sentence_analysis` 两类 few-shot 检索增强，不展开词汇、翻译或阅读理解题生成。  
> 核心目标：在不显著拉长主链路时延的前提下，为 `grammar_agent` 提供更贴合句法结构、考试场景和讲解风格的动态 few-shot。

## 1. 背景

当前 V3 架构已经预留了 `example_strategy -> rag` 的扩展位，静态 few-shot 也已经按 variant 区分为 `grammar_note` 与 `sentence_analysis` 两类示例。

但当前静态方案仍有三个问题：

- 示例数量固定，难以覆盖不同句法结构。
- 同一 `reading_variant` 下，复杂句和局部语法点共用同一小组示例，命中率有限。
- 随着样本积累增加，静态 hardcode 的维护成本会持续上升。

因此需要把当前 `grammar_agent` 的示例注入，从“静态示例表”升级为“可检索、可回退、可评估”的 RAG 示例选择机制。

## 2. 设计目标

本阶段目标按优先级排序如下：

1. 只为 `grammar_agent` 引入 RAG，不扩散到 `vocabulary_agent` 和 `translation_agent`。
2. 只覆盖两类输出：
   - `grammar_note`
   - `sentence_analysis`
3. 根据句法结构、讲解目标和 `reading_variant` 动态召回更合适的 few-shot。
4. 保持强 fallback：检索或 rerank 失败时，自动退回 baseline few-shot。
5. 控制时延，避免“全文逐句全量检索”。

## 3. 非目标

本阶段明确不做以下内容：

- 不做通用知识库问答。
- 不做 `vocabulary` / `translation` 的 few-shot RAG。
- 不做阅读理解题生成或题库检索。
- 不做用户错题记忆、长期个性化推荐。
- 不把 RAG 结果直接暴露为前端产品能力。

## 4. 总体结论

本方案的核心判断只有一句话：

- 对 `grammar_agent` 来说，最有价值的示例不是“主题相似”，而是“结构相似 + variant 相似 + 讲解目标相似”。

因此，本方案不做“文章级语义 RAG”，而做“句法结构导向的 example retrieval”。

## 5. 总体架构

### 5.1 方案概述

`grammar_agent` 的 RAG 流程如下：

```mermaid
flowchart LR
  A["prepared_input"] --> B["grammar retrieval planner"]
  B --> C["build query_texts"]
  C --> D["Bailian Embedding"]
  D --> E["Zilliz ANN search"]
  E --> F["Bailian Rerank"]
  F --> G["example selector"]
  G --> H["example_strategy.examples"]
  H --> I["grammar_agent prompt"]
```

### 5.2 外部组件

- 向量数据库：Zilliz Cloud（托管 Milvus）
- Embedding：阿里云百炼 `text-embedding-v4` 或后续稳定版本
- Rerank：阿里云百炼 `qwen3-rerank` 或后续稳定版本

### 5.3 关键原则

- Zilliz 只负责 ANN 召回，不负责最终排序。
- Bailian rerank 只对小候选集做精排，不直接替代召回。
- 业务侧保留 metadata 过滤、预算控制和 fallback 策略。

## 6. 为什么拆成两个池

`grammar_note` 与 `sentence_analysis` 虽然都属于 grammar 维度，但它们的“相似性定义”不同：

- `grammar_note` 关注局部结构点。
- `sentence_analysis` 关注整句层次与拆解方式。

因此推荐拆成两个独立池或两个独立 schema：

- `grammar_note_examples`
- `sentence_analysis_examples`

拆分带来的收益：

- 召回目标更清晰。
- 查询粒度可以不同。
- rerank 的对齐标准可以不同。
- 注入预算更容易控制。

## 7. 数据模型设计

## 7.1 样本主结构

每条样本建议至少包含以下字段：

| 字段 | 说明 |
|------|------|
| `example_id` | 样本唯一 ID |
| `output_type` | `grammar_note` 或 `sentence_analysis` |
| `reading_variant` | `gaokao` / `cet` / `kaoyan` / `tem` / `ielts_toefl` / 其他 |
| `grammar_granularity` | 与当前 prompt policy 对应的讲解风格 |
| `source_sentence` | 原始英文句子 |
| `output_fragment` | few-shot 注入的结构化输出片段 |
| `label` | 语法点名称或句型概述 |
| `grammar_tags` | 结构标签列表 |
| `structure_signals` | 轻量结构信号列表 |
| `quality_score` | 人工或离线评估后的质量分 |
| `approved` | 是否可进入线上召回 |
| `retrieval_text` | 用于生成 embedding 的拼接文本 |

## 7.2 `grammar_tags`

`grammar_tags` 是结构级标签，不是前端协议字段。它的作用是辅助过滤、rerank 和离线分析。

推荐示例：

- `relative_clause`
- `nonrestrictive_relative_clause`
- `object_clause`
- `appositive_clause`
- `participle_adverbial`
- `participle_attribute`
- `inversion`
- `passive_voice`
- `parallelism`
- `main_clause_interruption`
- `nested_clause`

## 7.3 `structure_signals`

`structure_signals` 是更轻、更容易从原句中提取的观察信号，用于查询构造和低成本筛选。

推荐示例：

- `leading_vbn`
- `leading_ving`
- `has_that_clause`
- `has_wh_clause`
- `has_comma_insertion`
- `has_long_subject_gap`
- `has_parallel_chain`
- `long_sentence`
- `nested_structure`

## 8. Embedding 策略

## 8.1 只对一个字段做 embedding

本方案不对多个字段分别做 embedding。  
每条样本只生成一个 `retrieval_text`，并对该字段整体做 embedding。

原因：

- 便于统一维度管理。
- 简化 Zilliz collection schema。
- 让 metadata 继续保留为结构化过滤字段。
- 避免多向量检索导致实现复杂度和时延增加。

## 8.2 `retrieval_text` 模板

### `grammar_note`

```text
output_type=grammar_note
variant=gaokao
grammar_tags=participle_adverbial, nonfinite
signals=leading_vbn, local_structure
teaching_goal=explicit_exam
sentence=Inspired by the speech, the students decided to start their own project.
label=过去分词作状语
```

### `sentence_analysis`

```text
output_type=sentence_analysis
variant=kaoyan
grammar_tags=object_clause, nonrestrictive_relative_clause, nested_clause
signals=long_sentence, has_comma_insertion, has_that_clause
teaching_goal=structural
sentence=The study suggests that the approach, which was initially designed for urban areas, has failed to address the needs of rural communities.
label=宾语从句 + 非限制性定语从句
```

## 8.3 设计原则

- `retrieval_text` 保留英文原句。
- 同时拼入少量结构标签和讲解风格字段。
- 不把完整中文 `note_zh` 或 `analysis_zh` 拼进去，避免检索偏向中文表述相似而非结构相似。

## 9. 在线查询策略

## 9.1 查询侧也构造 `query_text`

线上查询不直接用裸句子做 embedding，而是构造一个轻量 `query_text`，尽量与样本侧 `retrieval_text` 处于相同表示空间。

### `grammar_note` 查询模板

```text
output_type=grammar_note
variant=gaokao
sentence=Inspired by the speech, the students decided to start their own project.
possible_signals=leading_vbn, local_structure
teaching_goal=explicit_exam
```

### `sentence_analysis` 查询模板

```text
output_type=sentence_analysis
variant=kaoyan
focus_sentence=The study suggests that the approach, which was initially designed for urban areas, has failed to address the needs of rural communities.
paragraph=...
possible_signals=long_sentence, has_comma_insertion, has_that_clause, nested_structure
teaching_goal=structural
```

## 9.2 查询粒度

两个池采用不同查询粒度：

- `grammar_note`：句子级查询为主，可附少量上下文。
- `sentence_analysis`：长句级查询为主，必要时附所在段落。

原因：

- `grammar_note` 的价值主要取决于局部结构。
- `sentence_analysis` 的价值主要取决于整句复杂度与层次关系。

## 10. 查询预算与时延控制

## 10.1 不做全文逐句全量检索

本方案明确禁止：

- 对全文每一句都做 embedding、ANN 和 rerank。
- 对同一请求发起无预算上限的多次召回。

## 10.2 预算控制策略

建议的线上预算如下：

- `sentence_analysis`：1 到 2 个 query
- `grammar_note`：2 到 4 个 query

这里的 query 选择不要求绝对准确，只要求足够便宜且有较高覆盖率。

## 10.3 轻量候选句筛选

候选句筛选只承担“预算控制”作用，不承担最终价值判断。

可使用以下低成本信号：

- 句长
- 逗号数量
- `that / which / who / whose / where / when`
- 句首 `V-ed / V-ing`
- 倒装触发词
- 疑似从句数量

这些规则不需要完全准确，因为真正的精排发生在 rerank 阶段。

## 11. ANN 召回策略

## 11.1 硬过滤

进入 ANN 前，先做 metadata 过滤：

- `approved = true`
- `output_type` 必须匹配当前池
- `reading_variant` 优先 exact match

必要时允许分级 fallback：

1. exact `reading_variant`
2. same `grammar_granularity`
3. generic grammar pool

## 11.2 TopK

建议的初始参数：

- `grammar_note` ANN topK：8
- `sentence_analysis` ANN topK：12

原因：

- 当前数据量不大，不需要过高 topK。
- 候选太多只会增加 rerank token 成本和时延。

## 12. Rerank 策略

## 12.1 Rerank 的作用

ANN 负责“找得到”，rerank 负责“排得准”。

本方案中的 rerank 重点解决三个问题：

- 原句结构相似但讲解目标不匹配。
- 主题词相似但句法形态不匹配。
- variant 不同导致讲解风格偏差。

## 12.2 输入内容

rerank 的文档输入建议为候选样本的简化文本，而不是全部 metadata dump。

推荐格式：

```text
variant=gaokao
output_type=grammar_note
grammar_tags=participle_adverbial, nonfinite
sentence=Inspired by the speech, the students decided to start their own project.
label=过去分词作状语
```

## 12.3 精排后选择

建议：

- `grammar_note` rerank 后保留 top 3 到 5
- `sentence_analysis` rerank 后保留 top 2 到 4

随后再进入业务侧的多样性筛选。

## 13. 最终 few-shot 选择

## 13.1 注入数量

建议的 prompt 注入上限：

- `grammar_note`：2 条
- `sentence_analysis`：1 条

特殊复杂场景可放宽到：

- `grammar_note`：3 条
- `sentence_analysis`：2 条

但不建议默认放宽，避免 prompt 过重。

## 13.2 多样性约束

最终注入时要避免：

- 三条都讲同一种定语从句。
- 两条结构完全等价、只是句面不同。

因此在最终选择阶段，需要按以下维度去重：

- `grammar_tags`
- `label`
- `source_sentence` 近重复

## 14. 回退策略

RAG 必须是增强层，不得成为主链路硬依赖。

以下情况统一回退到 baseline few-shot：

- Embedding 调用失败
- Zilliz 查询失败
- Rerank 调用失败
- 候选结果为空
- 候选分数低于阈值

回退后：

- `selection_mode` 仍可记录为 `rag_fallback`
- 但注入内容使用当前静态 baseline 示例

## 15. 与现有代码的接入点

当前推荐接入位置：

- `server/app/services/analysis/prompting/example_strategy.py`
- `server/app/services/analysis/prompting/strategy_builder.py`
- `server/app/workflow/analyze_nodes.py`

建议新增职责：

- `grammar_rag_service.py`
  - 构造 query
  - 调 embedding
  - 调 Zilliz
  - 调 rerank
  - 输出最终 `ExampleEntry`
- `grammar_retrieval_hints.py`
  - 从句子和段落中提取低成本结构信号

`example_strategy.py` 的角色改为：

- baseline 示例定义
- 当 `few_shot_mode=rag` 时，委托 `grammar_rag_service`
- 当 RAG 失败时，回退 baseline

## 16. Zilliz schema 建议

每个池可单独建 collection，字段建议如下：

- `example_id`：主键
- `vector`：dense vector
- `reading_variant`
- `grammar_granularity`
- `grammar_tags`
- `structure_signals`
- `label`
- `source_sentence`
- `output_fragment`
- `quality_score`
- `approved`

向量维度取决于最终选定的 Bailian embedding 模型维度，collection 创建后不应频繁变更。

## 17. 可观测性

最少记录以下指标：

- `rag_enabled`
- `pool_name`
- `query_count`
- `ann_topk`
- `rerank_topn`
- `selected_example_ids`
- `fallback_reason`
- `embedding_latency_ms`
- `ann_latency_ms`
- `rerank_latency_ms`

建议同时记录：

- 最终注入的 `label`
- `reading_variant`
- 请求的句子数量

## 18. 质量评估建议

当前阶段至少做两类评估：

### 18.1 离线评估

- 同一批 regression 输入，对比：
  - baseline
  - rag
- 观察：
  - `grammar_note` 命中率
  - `sentence_analysis` 质量
  - variant 风格一致性

### 18.2 在线观测

- 请求总时延变化
- RAG 使用率
- fallback 率
- 召回样本分布

## 19. 实施顺序

推荐按以下顺序推进：

1. 定义两个池的 schema 与 metadata。
2. 把现有静态示例迁移为结构化样本。
3. 实现离线 ingestion：
   - 生成 `retrieval_text`
   - 调 embedding
   - 写入 Zilliz
4. 实现 `grammar_rag_service`。
5. 接入 `example_strategy` 的 `few_shot_mode=rag`。
6. 加入 fallback 和可观测性。
7. 进行回归对比与参数调优。

## 20. 最终结论

当前阶段的 grammar RAG，不应理解为"给 grammar_agent 加一个通用知识库"，而应理解为：

- 为 `grammar_note` 与 `sentence_analysis` 建立两个结构化示例池；
- 用 `retrieval_text` 统一承载"原句 + 结构特征 + variant 风格"；
- 用"轻结构提示 + ANN + rerank + fallback baseline"的方式，动态选择 few-shot；
- 在保证主链路可回退的前提下，逐步提升 grammar 输出的结构命中率与讲解稳定性。

---

## 21. 实际实现状态

> 本节记录截至当前代码的实际实现情况，与上述设计章节一一对应。

### 21.1 外部依赖与配置（对应 §5.2）

| 组件 | 实际型号 | 配置项 | 默认值 |
|------|---------|--------|--------|
| 向量库 | Zilliz Cloud | `ZILLIZ_URI` / `ZILLIZ_TOKEN` | 空（未配置则跳过初始化） |
| Embedding | 百炼 `text-embedding-v4` | `BAILIAN_API_KEY` / `bailian_embedding_model` / `bailian_embedding_dimension` | 1024 维 |
| Rerank | 百炼 `qwen3-rerank` | `bailian_rerank_model` | — |

全部配置集中在 `server/app/config/settings.py`，RAG 开关为 `grammar_rag_enabled: bool = False`。

### 21.2 基础设施层（对应 §5.2、§16）

| 模块 | 文件 | 说明 |
|------|------|------|
| Zilliz 客户端 | `server/app/infra/zilliz_client.py` | 全局单例，`init/close/search/insert/query/create_collection`，所有方法在 `_client=None` 时返回空结果而非抛异常 |
| 百炼 Embedding | `server/app/infra/bailian_embedding.py` | `embed_texts`（批量，25 条/批自动分批）/ `embed_single`，`asyncio.to_thread` 包装 |
| 百炼 Rerank | `server/app/infra/bailian_rerank.py` | `rerank(query, documents, top_n)`，返回 `RerankResult(index, relevance_score, document)` |

Zilliz Schema 实际字段（12 个，对应 §16）：

| 字段 | Milvus 类型 | 说明 |
|------|------------|------|
| `example_id` | VARCHAR(128) PK | — |
| `vector` | FLOAT_VECTOR(1024) | COSINE + AUTOINDEX |
| `reading_variant` | VARCHAR(64) | — |
| `output_type` | VARCHAR(32) | — |
| `grammar_tags` | VARCHAR(512) | JSON 序列化 |
| `structure_signals` | VARCHAR(512) | JSON 序列化 |
| `label` | VARCHAR(256) | — |
| `source_sentence` | VARCHAR(2048) | — |
| `output_fragment` | VARCHAR(8192) | — |
| `grammar_granularity` | VARCHAR(64) | — |
| `quality_score` | FLOAT | — |
| `approved` | BOOL | — |

### 21.3 检索链路（对应 §5.1、§9-§13）

完整链路实现在 `server/app/services/analysis/prompting/rag/grammar_rag_service.py`：

```
输入句子 → select_candidate_sentences → build_query_text → embed_single → zilliz_search → rerank → _apply_confidence_filter → _diversity_dedup → 注入预算控制 → ExampleEntry 列表
```

各环节实际参数：

| 环节 | 设计章节 | 实际参数 | 配置项 |
|------|---------|---------|--------|
| 候选句筛选 | §10.3 | `budget=4`，按信号丰富度排序 | 硬编码 |
| query_text 构造 | §9.1 | `output_type + variant + possible_signals + sentence` | — |
| Embedding | §8 | `text-embedding-v4`, 1024d | `bailian_embedding_model` / `bailian_embedding_dimension` |
| ANN TopK | §11.2 | 8 | `grammar_rag_ann_topk` |
| ANN 过滤 | §11.1 | `approved == true AND output_type == "{type}" AND reading_variant == "{variant}"`，variant miss 时 fallback 到 `"default"` | — |
| Rerank TopN | §12.3 | 5 | `grammar_rag_rerank_topn` |
| Rerank 文档格式 | §12.2 | `variant=…\noutput_type=…\ngrammar_tags=…\nsentence=…\nlabel=…` | — |
| 置信度过滤 | §14 | `min_score=0.3` | `grammar_rag_confidence_threshold` |
| 多样性去重 | §13.2 | 按 `label` / `source_sentence` / `grammar_tags` 三维去重 | — |
| 注入预算 | §13.1 | `grammar_note` 最多 2 条，`sentence_analysis` 最多 1 条 | `_INJECTION_BUDGET` 硬编码 |

### 21.4 结构信号提取（对应 §7.3、§10.3）

实现在 `server/app/services/analysis/prompting/rag/grammar_retrieval_hints.py`：

| 信号 | 检测方式 | 对应设计 |
|------|---------|---------|
| `long_sentence` | `word_count > 20` | §7.3 |
| `has_that_clause` | `\bthat\b` 正则 | §7.3 |
| `has_wh_clause` | `which/who/whose` | §7.3 |
| `leading_vbn` | 句首 `V-ed` | §7.3 |
| `leading_ving` | 句首 `V-ing` | §7.3 |
| `has_inversion` | 句首 `Never/Rarely/Not only/Had…` | §7.3 |
| `has_comma_insertion` | 逗号≥2 或逗号+which/who 等 | §7.3 |
| `nested_structure` | 从句数≥2 或逗号≥2+从句≥1 | §7.3 |

`select_candidate_sentences` 按信号丰富度排序，对 `grammar_note` 额外加权 `leading_vbn` 和 `has_inversion_trigger`，对 `sentence_analysis` 额外加权 `long_sentence` 和 `nested_structure`。

### 21.5 策略层接入（对应 §15）

| 文件 | 职责 |
|------|------|
| `example_strategy.py` | `get_grammar_example_strategy`（同步，RAG 时 fallback）/ `get_grammar_example_strategy_async`（异步，真正调用 RAG） |
| `strategy_builder.py` | `build_grammar_bundle_async` 构建含 `rag_debug` 的 `StrategyBundle` |

实际行为：

- `GRAMMAR_RAG_ENABLED=true` 时，`build_grammar_bundle_async` 同时查询 `grammar_note` 和 `sentence_analysis` 两个池，合并结果
- vocabulary / translation 始终走 baseline，即使 `few_shot_mode=rag` 也回退
- `selection_mode` 取值：`baseline` / `rag` / `rag_fallback`

### 21.6 回退策略（对应 §14）

`grammar_rag_service.query_grammar_rag` 在以下情况自动 fallback：

| 情况 | `fallback_reason` |
|------|-------------------|
| 输入句子为空 | `no_input_sentences` |
| 任何外部调用异常 | `retrieval_error: {Exception}` |
| ANN 返回空结果 | `empty_candidates` |
| 所有候选低于置信度阈值 | `low_confidence` |

fallback 时 `selection_mode="rag_fallback"`，`example_strategy` 加载 baseline 静态示例。

### 21.7 可观测性（对应 §17）

`RAGQueryResult` 携带完整诊断字段，通过 `build_rag_debug_info()` 序列化为 dict，注入 `StrategyBundle.rag_debug`，最终出现在 `prompt_debug` 输出中：

- `selection_mode` / `fallback_reason` / `is_fallback`
- `example_count` / `selected_example_ids` / `query_count`
- `ann_topk` / `rerank_topn`
- `embedding_latency_ms` / `ann_latency_ms` / `rerank_latency_ms`

### 21.8 健康检查

`GET /health` 在 `GRAMMAR_RAG_ENABLED=true` 时返回 `zilliz` 字段（`bool | null`），调用 `is_zilliz_ready()` 检查连接状态。

### 21.9 数据 Ingestion（对应 §19 步骤 3）

`server/scripts/ingest_grammar_seed.py`：

- 从 `server/data/seed/grammar_seed_v1.jsonl` 读取 seed 数据
- 按 `output_type` 分组写入对应 collection
- 调用百炼 Embedding 生成向量
- 支持增量写入（跳过已有 `example_id`）
- 支持 `--dry-run` 模式预览
- 支持 `--batch-size` 控制嵌入批次大小

### 21.10 应用启动集成

`server/app/main.py` 在 `lifespan` 中：

- `GRAMMAR_RAG_ENABLED=true` 时调用 `init_zilliz(uri, token)`
- 初始化后调用 `is_zilliz_ready()` 验证连接
- 连接失败不阻塞启动，仅 warning 日志，RAG 运行时自动 fallback
