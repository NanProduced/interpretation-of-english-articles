# `/dict` 查询策略优化设计（phrase-first + placeholder-aware）

> 文档定位：为当前 `/dict` 查询链路提供一份可直接实施的后端设计，重点覆盖短语优先、批量召回、`sb./sth.` 模板短语命中、缓存与验收标准。  
> 依赖文档：[TECD3 本地词典接入与查询策略](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/docs/architecture/tecd3-local-dictionary-integration.md)。  
> 当前结论：继续沿用“Python 后端 + PostgreSQL 词典真源”的架构，不拆独立 dict service；本次优化只调整 `/dict` 运行时查询策略与 phrase 索引补齐方式，不改词典内容真源。

## 1. 目标与边界

本次文档只定义“查询策略”这一层，目标是把 `/dict` 从当前的“单字符串查表”升级为“请求建模 + 批量召回 + 规则排序”。

本次明确要解决：

1. 让 `type=phrase` 真正生效。
2. 让“短语嗅探 + 最长优先”成为正式运行时规则。
3. 让库里带 `sb.` / `sth.` 的模板短语可以命中真实句子里的 `you / him / it / something` 等变体。
4. 保持现有返回结构兼容 `WordPopup`。
5. 修正缓存 key，使不同查询意图不再串缓存。

本次明确不做：

- 重构成独立 dict service
- 改动词典内容真源
- 把运行时猜测结果写回 `dict_entries`
- 基于 `exam_tags` 的过滤、排序或索引设计

## 2. 非本次范围但需要统一的约定

### 2.1 `exam_tags` 暂不参与查询

当前约定应写死在设计里，避免后端 agent 误实现：

- `dict_entries.exam_tags` 暂时不用于查询过滤
- `dict_entries.exam_tags` 暂时不用于查询排序
- `dict_entries.exam_tags` 暂时不需要为查询单独建索引
- `exam_tags` 只保留给后续“单词卡片展示”使用
- 即使未来展示使用，也只在 `reading_goal=exam` 时考虑

因此，本次 `/dict` 查询优化应完全忽略 `exam_tags`。

### 2.2 `reading_variant` 命名统一

与考试相关的运行时命名需要统一成下面的目标值：

- `gaokao`
- `cet`
- `gre_tem`
- `ielts_toefl`

其中：

- `gre_tem` 里的 `gre` 指中国研究生考试，不是国外 `GRE`
- `tem` 指中国专业英语等级考试 `TEM4/TEM8`

说明：

- 这个命名统一本身不是本次查询策略的核心内容
- 但后端如果顺手调整相关 schema 或枚举，应以 `gre_tem` 为目标值，不再使用旧的 `gre`

## 3. 当前实现审计

### 3.1 路由层

[dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py) 当前接口：

- `GET /dict?q=&type=`
- `GET /dict/entry?id=`

其中 `/dict` 虽然接受 `type`，但实际只做：

- `q.strip()`
- `_service.lookup(word)`

也就是说，`type` 当前是无效输入。

### 3.2 服务层

[service.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/service.py) 当前逻辑只有：

1. 对输入做 `_normalize()`
2. 把归一化后的字符串传给 provider

当前服务层不感知：

- 查询类型是 `word` 还是 `phrase`
- 当前句子上下文
- 点击词在句中的第几次出现

### 3.3 Provider 层

[tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py) 当前策略：

1. 只按 `query` 构造缓存 key
2. `lookup_candidates(query)`
3. 若未命中且 `query` 不含空格，则执行 lemma fallback
4. 单候选返回 `entry`
5. 多候选返回 `disambiguation`

当前缺失：

- `type` 感知
- `context_sentence` 感知
- phrase 的专门召回和排序
- 模板短语的 placeholder 归一化

### 3.4 DB 查询层

[db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py) 当前 `lookup_candidates()`：

- 只支持单个 `normalized_form`
- 只查 `dict_lookup_targets.normalized_form = $2`
- 无法支持“一个请求带多个候选 form”的批量召回

这意味着：

- 无法高效支持“最长优先”的短语召回
- 无法把 literal phrase 和 placeholder-normalized phrase 一起送入同一次查询

### 3.5 数据层缺口

[import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py) 当前会把短语解析进 `dict_entries.phrases_json`，但没有把 phrase 系统性补成可检索索引。

这会导致两个问题：

1. phrase-first 只停留在设计层，没有数据基础
2. 带 `sb.` / `sth.` 的模板短语即使在详情里存在，运行时也无从命中

## 4. 推荐接口契约

### 4.1 外部 API

保持现有 `GET /dict`，但扩展为可表达查询意图的输入：

- `q`: 用户点击的词或短语
- `type`: `word | phrase`
- `context_sentence`: 可选，点击词所在句子的原始文本
- `occurrence`: 可选，`q` 在 `context_sentence` 中的第几次出现，从 `1` 开始
- `reading_goal`: 可选，保留透传，但本次查询逻辑不使用
- `reading_variant`: 可选，保留透传，但本次查询逻辑不使用

兼容策略：

- 旧客户端只传 `q` 和 `type` 时，接口继续可用
- `context_sentence` 和 `occurrence` 缺失时，退化为当前精确匹配逻辑
- `reading_goal` / `reading_variant` 先保留接口兼容，但本次 provider 不读取

### 4.2 内部请求模型

后端内部建议新增显式请求模型，例如：

```python
class DictionaryLookupRequest(BaseModel):
    query: str
    query_type: Literal["word", "phrase"]
    context_sentence: str | None = None
    occurrence: int | None = None
    reading_goal: str | None = None
    reading_variant: str | None = None
```

说明：

- 服务层统一负责归一化、请求建模和 fallback 决策
- provider 不再只接收裸字符串

## 5. 数据模型与索引改动

### 5.1 继续复用 `dict_lookup_targets`

短语索引不建议单独新建表，优先增强现有 `dict_lookup_targets`。

推荐新增列：

- `lookup_type text not null default 'word'`

允许值：

- `word`
- `phrase`

推荐迁移：

```sql
ALTER TABLE dict_lookup_targets
ADD COLUMN lookup_type text NOT NULL DEFAULT 'word';

ALTER TABLE dict_lookup_targets
ADD CONSTRAINT dict_lookup_targets_lookup_type_chk
CHECK (lookup_type IN ('word', 'phrase'));
```

保留现有 `match_kind`，但新增可选值：

- `phrase`
- `phrase_template`

分工建议：

- `lookup_type`：区分“单词索引”还是“短语索引”
- `match_kind`：描述命中来源，例如 `headword / redirect / nlp / phrase / phrase_template`

### 5.2 phrase 回填要求

[import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py) 需要在导入阶段把 `phrases_json` 中可检索的短语补写进 `dict_lookup_targets`。

推荐每条 phrase 至少写入一条 literal row：

- `normalized_form`: phrase 文本的归一化结果
- `lookup_label`: phrase 原文
- `target_label`: phrase 原文
- `match_kind`: `phrase`
- `lookup_type`: `phrase`
- `preview_text`: phrase 的首条中文释义或可展示摘要
- `entry_id`: 指向所属 `dict_entries.id`

### 5.3 模板短语回填要求

对于包含 placeholder 的词典短语，导入阶段还要额外补一条 template row。

典型例子：

- `be there for sb.`
- `give sth. to sb.`
- `take sb.'s advice`

推荐规则：

1. phrase 原文先保留 literal row
2. 再生成一条 template-normalized row
3. template row 仍写进 `dict_lookup_targets`
4. template row 仍指向原 `entry_id`

推荐 placeholder 规范化：

- `sb.` / `somebody` / `someone` -> `sb`
- `sb.'s` / `somebody's` / `someone's` -> `sb's`
- `sth.` / `something` -> `sth`

示例：

- 原 phrase：`be there for sb.`
- literal row：`be there for sb`
- template row：`be there for sb`

说明：

- 对这个例子，literal 和 template 可能归一化后相同，这没问题
- 关键在于导入与运行时必须共用同一套 placeholder canonicalization

## 6. Placeholder 归一化设计

### 6.1 为什么要单独设计

词典里的短语经常写成“词典模板语法”，而用户句子里出现的是自然语言实例。

例如：

- 词典：`be there for sb.`
- 句子：`I will always be there for you.`

如果运行时只做 literal n-gram 匹配：

- 查询 form 会是 `be there for you`
- 词典索引是 `be there for sb`
- 两者不会命中

因此，运行时必须支持“自然句子 -> 词典模板”的 placeholder 归一化。

### 6.2 运行时 placeholder 归一化范围

第一版建议只做低风险映射，不做复杂 NER 或语义判断。

建议映射集合：

- 人称宾格或泛指人：
  - `me`
  - `you`
  - `him`
  - `her`
  - `us`
  - `them`
  - `someone`
  - `somebody`
  - `anyone`
  - `anybody`
  -> `sb`

- 所有格：
  - `my`
  - `your`
  - `his`
  - `her`
  - `our`
  - `their`
  - `someone's`
  - `somebody's`
  -> `sb's`

- 泛指物：
  - `it`
  - `something`
  - `anything`
  - `everything`
  -> `sth`

本阶段明确不做：

- 把任意普通名词自动归一成 `sth`
- 把任意专有名词自动归一成 `sb`
- 复杂 NER

也就是说，第一版优先解决最常见的英文代词场景。

### 6.3 共享实现要求

必须保证下面两端共用同一套规则：

1. 导入阶段生成 template row
2. 运行时生成 template query form

否则会出现“导入写的是一种模板，查询时算的是另一种模板”的错配。

建议做法：

- 在词典模块内新增独立 helper，例如 `phrase_template.py`
- 同时供 [import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py) 和运行时 service/provider 复用

## 7. 查询管线设计

### 7.1 总体原则

新的 `/dict` 查询不再是“单次查询 + 单个排序”，而是四段式管线：

1. 请求建模
2. 候选 form 生成
3. 批量数据库召回
4. 规则化排序与返回

### 7.2 候选 form 生成

#### A. 直接查询 form

所有请求都必须包含：

- `normalized_query`

如果 `type=phrase`：

- 直接把 `q` 当成 phrase exact 查询
- 同时生成一份 placeholder-normalized phrase form

#### B. 上下文短语 form

当满足下面条件时，生成 anchored n-gram：

- `query_type == "word"`
- `context_sentence` 非空
- `occurrence` 可解析，或 `query` 在句中仅出现一次

生成规则：

1. 以点击词为锚点，只生成“包含该锚点”的窗口
2. 推荐窗口长度 `2..5`
3. 候选按 token 数倒序排列
4. 每个 literal n-gram 再派生一份 template-normalized form
5. 去重后送入批量召回

例子：

- 点击 `there`
- 上下文：`I will always be there for you`
- 候选顺序应接近：
  - `be there for you`
  - `be there for sb`
  - `there for you`
  - `there for sb`
  - `there`

说明：

- literal phrase 和 template phrase 要一起进批量召回
- 排序时 literal 不应无条件压过 template，因为 `sb.` 类短语本来就依赖模板命中

#### C. lemma form

只有当直接查询和上下文短语都未命中时，才进入 lemma fallback。

lemma 阶段规则：

1. 只对 `query_type == "word"` 启用
2. 先对点击词做 lemma 还原
3. 用 lemma 重新执行：
   - 上下文短语 form 生成
   - 单词 exact 查询

这保持与主设计文档一致：

- 先精确
- 再降级
- 先上下文
- 后孤立单词

### 7.3 锚点无法可靠定位时的降级

如果发生下面任一情况：

- `query` 在句中出现多次，且 `occurrence` 缺失
- 句子清洗后无法稳定定位点击词

则不做上下文短语嗅探，直接退化为：

1. exact query
2. placeholder-normalized query
3. lemma fallback

要求：

- 不要猜测
- 不要在定位不可靠时做高风险 phrase 合成

## 8. 批量召回接口

[db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py) 推荐新增：

```python
async def lookup_candidates_batch(
    normalized_forms: list[str],
    source: str = "tecd3",
) -> list[CandidateRow]:
    ...
```

`CandidateRow` 推荐扩展字段：

- `matched_form: str`
- `lookup_type: str`

推荐 SQL：

```sql
SELECT
  t.normalized_form AS matched_form,
  t.lookup_label,
  t.lookup_type,
  t.entry_id,
  t.target_label,
  t.target_pos,
  t.preview_text,
  t.rank,
  t.match_kind,
  e.entry_kind
FROM dict_lookup_targets t
JOIN dict_entries e
  ON e.id = t.entry_id
 AND e.source = t.source
WHERE t.source = $1
  AND t.normalized_form = ANY($2::text[])
ORDER BY array_position($2::text[], t.normalized_form), t.rank ASC, t.id ASC;
```

设计要点：

- `array_position()` 用来保留输入 form 顺序，便于“最长优先”
- 召回后仍需在 Python 层去重和重排，不把复杂规则塞进 SQL

## 9. 排序规则设计

### 9.1 排序必须在 Python 层完成

原因：

- 规则依赖 `query_type`、form 来源、token 长度、`lookup_type`、`entry_kind`
- 这些因素塞进 SQL 会让实现脆弱且难调试
- 批量召回后的候选数量通常不大，Python 排序成本可接受

### 9.2 推荐排序桶

推荐采用“显式分桶 + 稳定 tie-breaker”，而不是简单加权分数。

排序维度从高到低如下：

1. `phase_priority`
   - `0`: 上下文短语 exact/template 命中
   - `1`: 直接 phrase/query exact 命中
   - `2`: lemma 后的上下文短语命中
   - `3`: lemma 后的 exact 命中

2. `query_type_priority`
   - 请求是 `phrase` 时：`lookup_type == "phrase"` 优先
   - 请求是 `word` 时：如果候选来自上下文 phrase 命中，phrase 仍可优先于孤立单词

3. `token_length_priority`
   - 同阶段下，token 数更多的 phrase 优先
   - 这就是“最长优先”

4. `match_kind_priority`
   - `phrase_template` 与 `phrase` 视为同一优先层
   - `headword / base_headword` 次之
   - `redirect` 次之
   - `nlp` 最后

5. `entry_kind_priority`
   - `entry` 优先于 `fragment`

6. `rank`
   - 保留数据库现有排序信息作为最终 tie-breaker

7. `entry_id`
   - 保证排序稳定

### 9.3 伪代码

```python
sort_key = (
    phase_priority,
    query_type_priority,
    -token_count,
    match_kind_priority,
    0 if entry_kind == "entry" else 1,
    rank,
    entry_id,
)
```

### 9.4 返回策略

本次不改变结果类型语义：

- 只有一个唯一 `entry_id` 时，返回 `entry`
- 多个唯一 `entry_id` 时，返回 `disambiguation`

也就是说：

- 本次只优化召回和候选顺序
- 不改变前端对单候选 / 多候选的处理方式

## 10. 缓存设计

### 10.1 当前问题

[tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py) 当前缓存 key 只包含 `query`，这在新策略下会造成串缓存：

- 同一 `query`
- 不同 `query_type`
- 不同 `context_sentence`
- 不同 `occurrence`

都可能错误复用一份结果。

### 10.2 新缓存 key

推荐按“请求意图”生成缓存 key：

```text
{source}:{cache_version}:lookup:
q={normalized_query}:
type={query_type}:
ctx={context_hash}:
occ={occurrence or 0}:
strategy=v1
```

说明：

- `context_sentence` 不要原文直接进 key，改用短 hash
- `/dict/entry` 的 entry cache 可以保持现状
- 本次缓存 key 不要带 `reading_goal` 或 `reading_variant`，因为查询逻辑不读取它们

## 11. 分阶段实施建议

### Phase 0：请求建模与缓存修正

目标：

- 让 `type` 真正生效
- 接口允许接收 `context_sentence` 和 `occurrence`
- provider 缓存 key 正确分桶

改动范围：

- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py)
- [service.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/service.py)
- [tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py)

### Phase 1：phrase 索引补齐

目标：

- 让 phrase 真正进入 `dict_lookup_targets`
- 为“最长优先”提供可命中的数据基础

改动范围：

- [import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py)
- 相关 migration
- 必要时补一个 backfill script

### Phase 2：placeholder-aware 命中

目标：

- 让 `be there for sb.` 这类模板短语可以命中 `be there for you`
- 让 literal phrase 和 template phrase 共享同一套归一化规则

改动范围：

- 新增 phrase template helper
- 导入链路和运行时查询共用该 helper
- [db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py) 增加批量召回接口

### Phase 3：前端透传上下文

目标：

- 把 `clicked_word + context_sentence + occurrence` 真正传给 `/dict`

直接相关文件：

- [WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx)
- [dict.adapter.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/api/adapters/dict.adapter.ts)
- [projection.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/analysis/projection.py)

## 12. 测试与验收标准

### 12.1 查询正确性

至少覆盖下面的 case：

1. phrase 优先
   - 输入：点击 `take`，上下文 `take place`
   - 预期：优先返回 `take place`

2. longest-first
   - 输入：点击 `charge`，上下文 `in charge of`
   - 预期：`in charge of` 优先于 `charge`

3. lemma fallback
   - 输入：`studies`
   - 预期：未命中表面词形时能回退到 `study`

4. phrase query
   - 输入：`q=as well as&type=phrase`
   - 预期：phrase 候选优先，不退化成 `as` / `well`

5. `sb.` 模板短语
   - 词典：`be there for sb.`
   - 输入句子：`I will always be there for you`
   - 预期：能够命中该 phrase

6. `sth.` 模板短语
   - 词典：`give sth. to sb.`
   - 输入句子：`give it to him`
   - 预期：能够命中该 phrase

7. 多次出现的锚点词
   - 同一句中同一 token 出现多次，且 `occurrence` 缺失
   - 预期：不做高风险短语猜测，安全退化为 exact 查询

8. cache isolation
   - 相同 `query` 在不同 `context_sentence` 或 `occurrence` 下，不应共享错误缓存

9. backward compatibility
   - 旧调用方只传 `q` 和 `type` 时，接口仍应正常返回

### 12.2 数据正确性

需要抽检：

- `dict_lookup_targets.lookup_type='phrase'` 的数量是否合理
- 带 placeholder 的 phrase 是否都能生成稳定的 template row
- template row 是否都能回到正确的 `entry_id`
- `preview_text` 是否足够支撑 disambiguation

### 12.3 可观测性

推荐新增最少量结构化日志字段：

- `query`
- `query_type`
- `context_used`
- `phase_hit`
- `matched_form`
- `lookup_type`
- `match_kind`
- `candidate_count`

这样后续可以快速回答：

- phrase sniff 到底有没有命中
- placeholder 归一化有没有发生
- 哪一阶段最常 miss

## 13. 最终建议

后端 agent 实施时，建议按下面顺序推进：

1. 先把 `/dict` 的输入升级成显式请求模型，并让 `type` 真正参与 provider 策略。
2. 新增 `lookup_candidates_batch()`，把排序主逻辑移到 Python 层。
3. 补 migration 和导入逻辑，把 phrase 正式写进 `dict_lookup_targets`。
4. 增加 placeholder-aware 归一化，让 `sb.` / `sth.` 模板短语可命中真实句子。
5. 最后再接前端上下文透传，让“短语嗅探 + 最长优先”真正工作。

如果只做其中一部分，优先级应该是：

1. 请求建模 + cache 修正
2. phrase 索引补齐
3. placeholder-aware 命中
4. 前端上下文透传

## 14. 直接相关文件

- [TECD3 本地词典接入与查询策略](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/docs/architecture/tecd3-local-dictionary-integration.md)
- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py)
- [service.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/service.py)
- [tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py)
- [db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py)
- [lemma.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/lemma.py)
- [analysis.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/schemas/internal/analysis.py)
- [0001_initial_schema.sql](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/db/migrations/0001_initial_schema.sql)
- [0002_add_exam_tag.sql](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/db/migrations/0002_add_exam_tag.sql)
- [import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py)
- [import_exam_vocabulary.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_exam_vocabulary.py)
- [WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx)
- [dict.adapter.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/api/adapters/dict.adapter.ts)
