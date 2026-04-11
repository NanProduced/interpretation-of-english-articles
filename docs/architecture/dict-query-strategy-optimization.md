# `/dict` 查询策略优化设计（已落地实现）

> 文档状态：**已完成实施 (2026-04-12)**  
> 实施成果：成功引入 `spaCy` 句法解析、短语索引补齐及多维重排算法，显著提升了点按查词命中率。
> 依赖文档：[TECD3 本地词典接入与查询策略](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/docs/architecture/tecd3-local-dictionary-integration.md)。  

## 0. 实施总结 (Post-Implementation Summary)

该方案已于 2026-04-12 全量上线，主要交付物包括：
1. **数据层**：执行了 `backfill_phrases.py`，为 7 万+ fragment 补齐了 `lookup_type='phrase'`，并从 4700+ 主词条中提取了隐藏短语，同时生成了 `sb/sth` 规范化模板索引。
2. **NLP 层**：建立了词典专用 `en_core_web_sm` 单例，实现了基于依存树的短语嗅探与“去代词化”模板生成。
3. **策略层**：重构了 `DictionaryService` 与 `Tecd3Provider`，实现了 7 层维度的 Python 权重重排算法。
4. **前端层**：`WordPopup` 与 `ParagraphBlock` 已联动，实现了点击位置上下文句子的全量自动透传。

---

## 1. 目标与边界

本次文档只定义“查询策略”这一层，目标是把 `/dict` 从当前的“单字符串查表”升级为“请求建模 + 批量召回 + 规则排序”。

本次明确要解决：

1. 让 `type=phrase` 真正生效。
2. 让“短语嗅探 + 最长优先”成为正式运行时规则。
3. 让库里带 `sb.` / `sth.` 的模板短语可以通过 `spaCy` 的 lemma / POS / DEP 能力命中真实句子里的实例化变体。
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

## 3. 最终实施架构 (Final Implementation)

### 3.1 路由层 (`dict.py`)
- 已支持全量参数：`q`, `type`, `context_sentence`, `occurrence`, `reading_goal`, `reading_variant`。
- 内部自动封装为 `DictionaryLookupRequest` Pydantic 模型。

### 3.2 服务调度层 (`service.py` & `nlp.py`)
- 实现了 `DictionaryService.lookup(request)` 统一入口。
- 新增 `nlp.py` 管理专用 `en_core_web_sm` 模型，带懒加载与可用性检查（`check_dict_spacy_model`）。

### 3.3 候选生成层 (`phrase_candidates.py` & `phrase_templates.py`)
- 实现了 `generate_candidates`：基于 `spaCy` 依存树，向上寻找动词/名词 Head，生成 `literal/lemma/template` 候选。
- 模板化逻辑：能将代词或名词块智能识别为 `sb`, `sth`, `sb's`。

### 3.4 Provider 与 DB 层 (`tecd3.py` & `db_pg.py`)
- **批量召回**：`lookup_candidates_batch` 支持通过 `ANY()` 数组语法一次性回查所有 NLP 生成的候选词。
- **多维重排**：按照 `(phase, query_type, -token_count, match_kind, entry_kind, rank)` 元组在 Python 层进行精准排序。
- **缓存隔离**：缓存 Key 已加入 `context_sentence` 的 MD5 哈希值，确保语境隔离。

### 3.5 数据索引补齐
- 执行了 `server/scripts/backfill_phrases.py` 增量脚本：
  - 更新 `dict_lookup_targets` 增加 `lookup_type` 字段。
  - 提取并入库了 2 万+ 句型与短语索引。

---

## 4. 推荐接口契约 (已对齐)

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

## 5. 数据模型与索引改动 (已落地)

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

### 5.2 phrase 回填要求 (已完成)

[import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py) 及补填脚本已完成 phrase 补写进 `dict_lookup_targets`。

推荐每条 phrase 至少写入一条 literal row：

- `normalized_form`: phrase 文本的归一化结果
- `lookup_label`: phrase 原文
- `target_label`: phrase 原文
- `match_kind`: `phrase`
- `lookup_type`: `phrase`
- `preview_text`: phrase 的首条中文释义或可展示摘要
- `entry_id`: 指向所属 `dict_entries.id`

### 5.3 模板短语回填要求 (已完成)

对于包含 `sb.` / `sth.` 槽位的词典短语，导入阶段还要额外补一条 template row。

典型例子：

- `be there for sb.`
- `give sth. to sb.`
- `take sb.'s advice`

推荐规则：

1. phrase 原文先保留 literal row
2. 再生成一条 canonical template row
3. template row 仍写进 `dict_lookup_targets`
4. template row 仍指向原 `entry_id`

canonical template 只做最小词典规范化：

- `sb.` / `somebody` / `someone` -> `sb`
- `sb.'s` / `somebody's` / `someone's` -> `sb's`
- `sth.` / `something` -> `sth`

示例：

- 原 phrase：`be there for sb.`
- literal row：`be there for sb`
- template row：`be there for sb`

说明：

- 对这个例子，literal 和 template 可能归一化后相同，这没问题
- 关键在于词典侧必须有 canonical template 可查，运行时再用 `spaCy` 把自然句子映射到这个 template

## 6. `spaCy` 驱动的模板短语命中设计 (核心逻辑)

### 6.1 为什么不能继续走“硬规则替换”

如果继续用“`you -> sb`、`it -> sth`、`my -> sb's`”这类字符串替换去做模板匹配，会有三个问题：

1. 命中率差  
   `you / him / her / them / your / his / her / it` 只是最小集合，真实句子里还会出现 noun chunk、专有名词、并列结构、所有格结构。
2. 误伤高  
   仅靠 token 字符串很难区分 `sb` 和 `sth`，尤其碰到 `it`、名词短语、专有名词时容易错。
3. 效率差  
   如果靠字符串替换去枚举所有窗口和变体，候选 form 会指数膨胀。

更合理的方式是：

- 词典侧只存 canonical template
- 运行时先用 `spaCy` 解析句子
- 再基于 lemma / POS / DEP / noun chunk 把真实句子投影成少量“语法上合理”的 template candidate

### 6.2 `spaCy` 应该怎么在 `/dict` 里用

根据 `spaCy` 官方文档：

- `PhraseMatcher` 适合大规模 terminology list 或 gazetteer 的精确短语匹配
- `Matcher` 适合基于 `LEMMA`、`POS`、`DEP` 等属性写抽象 token pattern
- `DependencyMatcher` 适合在 dependency tree 上做关系模式匹配  
  [来源 1](https://spacy.io/usage/rule-based-matching/) [来源 2](https://spacy.io/api/dependencymatcher/) [来源 3](https://spacy.io/api/lemmatizer/)

因此推荐把 `spaCy` 用在两个点上：

1. 句子解析  
   把 `context_sentence` 变成带 `lemma / POS / DEP / noun chunk` 的 `Doc`
2. 模板候选生成  
   不再做全局字符串替换，而是从 parse tree 中生成少量 template candidate

### 6.3 词典查询专用 `spaCy` pipeline

不要复用当前只负责断句的 pipeline。建议单独新增词典查询专用 `nlp_dict`：

- 基础模型：`en_core_web_sm`
- 必须保留：
  - `tagger` 或 `morphologizer`
  - `lemmatizer`
  - `parser`
- 可选保留：
  - `ner`

推荐原则：

- 断句链路可以继续轻量
- `/dict` 链路单独持有一个 lazy singleton
- 只在有 `context_sentence` 时调用
- 每次只处理一条句子，性能成本可控

同时必须定义清楚“模型不可用时怎么办”：

- 如果 `en_core_web_sm` 缺失，不阻塞 `/dict`
- 直接退回 exact + lemma + 有限 n-gram 兜底
- 记录结构化日志，例如：
  - `dict_spacy_unavailable`
  - `dict_spacy_runtime_error`

### 6.4 模板槽位不再靠词面硬编码，而靠句法抽象

推荐把 `sb / sth / sb's` 看成“槽位类型”，不是字面替换结果。

第一版建议支持三种槽位：

1. `sb`
   - 代词宾格或主格的人称代词 span
   - 或者被 `spaCy` 识别为 PERSON 的实体
   - 或者 noun chunk，其 head 在句法上是典型参与者位置，例如 `nsubj / dobj / iobj / pobj / dative`

2. `sth`
   - 非 PERSON 的 noun chunk
   - 或中性代词 / 物类代词
   - 或句法上充当 object / complement 的非人称成分

3. `sb's`
   - possessive pronoun
   - 或 dependency 上的 `poss` 结构，且 possessor 为 person-like span

注意：

- 这里的判断核心是 `lemma + POS + DEP + noun chunk / entity`
- 不是先维护一大坨 `you, him, her...` 的替换表再拼字符串

### 6.5 推荐实现形态：生成 candidate，而不是全量跑模板库

不建议在每次点击时把整个模板短语库全部编译成 `Matcher` / `DependencyMatcher` 规则去跑整句。

更推荐的实现是：

1. 词典侧把 phrase 存成 literal row + canonical template row
2. 运行时只对“点击词所在句子”做一次 `spaCy` 解析
3. 围绕点击锚点，从 parse tree 生成少量候选：
   - literal candidate
   - lemma candidate
   - template candidate
4. 用这些 candidate 去做一次批量 DB lookup

这样效率更高，因为：

- 句子只 parse 一次
- 候选数量通常是个位数到十几条
- 不需要把整库模板规则灌进 matcher

### 6.6 候选生成规则

围绕点击锚点，优先生成“语法上合理”的 phrase span，而不是盲目滑动窗口。

推荐顺序：

1. 锚点所在的最小连续短语 span
   - 例如 `be there for you`
2. 该 span 的 lemma form
   - 例如 `be there for you`
3. 该 span 的 template form
   - 例如 `be there for sb`
4. 必要时再退化到有限长度的 anchored n-gram
   - 只作为 parse-based span 生成失败时的兜底

例子：

- 句子：`I will always be there for you.`
- parse 后生成：
  - literal: `be there for you`
  - template: `be there for sb`

- 句子：`He gave it to Mary.`
- parse 后生成：
  - literal: `give it to mary`
  - lemma: `give it to mary`
  - template: `give sth to sb`

### 6.7 共享实现要求

必须保证下面两端共用同一套 canonicalization helper：

1. 导入阶段生成 canonical template row
2. 运行时从 `Doc` 生成 template candidate

否则会出现“库里 template 长这样，运行时生成的 template 又是另一种”的错配。

建议新增独立 helper，例如：

- `server/app/services/dictionary/phrase_templates.py`

该 helper 至少负责：

- dictionary phrase -> canonical template
- parsed sentence span -> canonical template
- slot type 判断

## 7. `/dict` 专用 `spaCy` pipeline` 的技术拆分 (已实现)

### 7.1 新增模块

1. `server/app/services/dictionary/nlp.py`
   - 负责词典查询专用 `spaCy` singleton
   - 包含可用性检查。

2. `server/app/services/dictionary/phrase_templates.py`
   - 负责 canonical template 规则。
   - 实现 `classify_slot` 与 `canonicalize_sentence_span`。

3. `server/app/services/dictionary/phrase_candidates.py`
   - 负责围绕点击锚点生成候选 form。

4. `server/app/services/dictionary/db_pg.py`
   - 已增加 `lookup_candidates_batch()`。

5. `server/app/services/dictionary/service.py`
   - 已升级为“请求建模 + 调度”。

6. `server/app/services/dictionary/providers/tecd3.py`
   - 整合批量召回与重排逻辑。

---

## 13. 测试与验收标准 (已通过)

### 13.1 查询正确性

已覆盖 case：

1. **phrase 优先**：点击 `take`，成功优先返回 `take place`。
2. **longest-first**：`take place` 优先于 `take`。
3. **lemma fallback**：`studies` 回退到 `study`。
4. **phrase query**：`type=phrase` 锁定短语索引。
5. **模板匹配**：`be there for you` 命中 `be there for sb`。
6. **cache isolation**：不同句子的点击不再发生串缓存。
7. **spaCy 兜底**：在模型未加载时平滑退回 exact 查询。

---

## 15. 直接相关文件 (已更新)

- [DictionaryService](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/service.py)
- [Tecd3Provider](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py)
- [NLP Singleton](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/nlp.py)
- [Phrase Candidates](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/phrase_candidates.py)
- [Phrase Templates](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/phrase_templates.py)
- [Batch DB Access](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py)
- [Backfill Script](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/backfill_phrases.py)
- [WordPopup Component](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx)
