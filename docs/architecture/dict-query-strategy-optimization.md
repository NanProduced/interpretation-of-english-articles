# `/dict` 查询策略优化设计（phrase-first + spaCy pattern matching）

> 文档定位：为当前 `/dict` 查询链路提供一份可直接实施的后端设计，重点覆盖短语优先、批量召回、`spaCy` 驱动的模板短语命中、缓存与验收标准。  
> 依赖文档：[TECD3 本地词典接入与查询策略](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/docs/architecture/tecd3-local-dictionary-integration.md)。  
> 当前结论：继续沿用“Python 后端 + PostgreSQL 词典真源”的架构，不拆独立 dict service；本次优化只调整 `/dict` 运行时查询策略与 phrase 索引补齐方式，不改词典内容真源。

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

### 2.3 公开资料可见的产品信号

没有查到有道词典或 Google Dictionary 对 `sb./sth.` 模板命中的公开工程实现说明，因此下面的结论应视为“基于公开资料与产品行为的工程推断”，不是官方实现披露。

当前能确认的公开信号有三类：

1. 搜索引擎里的 dictionary box 通常来自结构化词典数据  
   Oxford Languages 明确对外提供“给 search engines 用的 dictionary data”，并说明这些数据是“machine-readable dictionaries”的标准化数据模型，面向搜索引擎以 XML / JSON 形式接入。[来源](https://languages.oup.com/products/dictionary-data-for-search-engines/)
2. 主流词典数据本身就是结构化 lexical dataset  
   Oxford Languages 对外说明词典数据集不仅有 headword、sense、example，还包括 phrasal verbs、idioms 等结构化内容，并以 machine-readable format 交付。[来源 1](https://languages.oup.com/about-us/what-is-a-dictionary-dataset/) [来源 2](https://languages.oup.com/products/language-datasets/new-oxford-american-dictionary/)
3. 有道公开页面能直接检索 canonical template 表达  
   例如有道公开页面可直接出现 `induce sb to do sth`、`remind sb. of sth`、`offer sb. sth` 这类模板表达。[来源 1](https://dict.youdao.com/w/%E5%8A%9D%E8%AF%B1%E6%9F%90%E4%BA%BA%E5%81%9A%E6%9F%90%E4%BA%8B/) [来源 2](https://dict.youdao.com/w/%E4%BD%BF%E6%9F%90%E4%BA%BA%E6%83%B3%E8%B5%B7%E4%BA%8B/) [来源 3](https://dict.youdao.com/w/%E5%90%91%E6%9F%90%E4%BA%BA%E5%81%9A%E6%9F%90%E4%BA%8B/)

这三点共同说明：

- 词典产品并不是把自然句子当作纯字符串去 regex 查词
- 词典侧本来就有 canonical template 和结构化短语数据
- 更合理的实现方向是“结构化词典索引 + 句内语法匹配”，而不是继续堆全局字符串替换规则

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
- `spaCy` 的 lemma / POS / dependency 信息

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
- 基于 `spaCy` 的模板短语匹配

### 3.4 DB 查询层

[db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py) 当前 `lookup_candidates()`：

- 只支持单个 `normalized_form`
- 只查 `dict_lookup_targets.normalized_form = $2`
- 无法支持“一个请求带多个候选 form”的批量召回

这意味着：

- 无法高效支持“最长优先”的短语召回
- 无法把 literal phrase 和 canonical template phrase 一起送入同一次查询

### 3.5 数据层缺口

[import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py) 当前会把短语解析进 `dict_entries.phrases_json`，但没有把 phrase 系统性补成可检索索引。

这会导致两个问题：

1. phrase-first 只停留在设计层，没有数据基础
2. 带 `sb.` / `sth.` 的模板短语即使在详情里存在，运行时也无从命中

### 3.6 当前 `spaCy` 实际没有用在词典查询

仓库里虽然已经引入了 `spaCy`，但当前只在 [input_preparation.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/analysis/input_preparation.py) 里做断句，而且加载模型时明确禁掉了：

- `tagger`
- `lemmatizer`
- `ner`

这意味着当前项目里的 `spaCy` 并没有为 `/dict` 提供：

- `Token.lemma_`
- `Token.pos_`
- `Token.dep_`
- noun chunk / dependency tree 级别的模式判断

因此，词典查询链路现在实际上还停留在“字符串查表 + lemminflect fallback”阶段。

### 3.7 当前本地启动现状：`uvicorn` 启动不等于 `spaCy` 可用

截至 **2026-04-12**，当前本地调试方式 `uv run uvicorn app.main:app --reload` 的实际状态如下：

1. 服务启动时不会主动预热 `spaCy`  
   [main.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/main.py) 的 `lifespan()` 只初始化：
   - PostgreSQL
   - Redis
   - LangSmith
   - Analysis task worker

   启动阶段没有任何 `spaCy` model preload。

2. `spaCy` 只会在运行到 `prepare_input()` 时被懒检查  
   触发点在 [input_preparation.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/analysis/input_preparation.py:579) 和 [input_preparation.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/analysis/input_preparation.py:898)。

3. 当前本地 `uv` 环境里只有 `spaCy` 包，没有 `en_core_web_sm` 模型  
   已验证到：
   - `spacy_version=3.8.14`
   - `model_spec=missing`
   - `spacy.load("en_core_web_sm")` 报 `OSError: [E050] Can't find model 'en_core_web_sm'`

4. 因此当前本地运行实际上会退回 regex 路径  
   一旦走到 `prepare_input`，`_check_spacy_model()` 会把 `_spacy_available` 标记为 `False`，后续走：
   - `regex_sentence_split_no_spacy`
   - `fallback_reason="spacy_unavailable"`

这个现状对 `/dict` 方案的约束是：

- 不能假设“项目已经装了 `spaCy`，所以 `/dict` 直接可用句法匹配”
- `/dict` 新方案必须自带：
  - 模型可用性检查
  - 清晰的降级路径
  - 可观测日志

也就是说，“在 `/dict` 里真正用上 `spaCy`”不仅是代码问题，还包括运行时环境就绪问题。

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

## 6. `spaCy` 驱动的模板短语命中设计

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

## 7. `/dict` 专用 `spaCy` pipeline` 的可实施技术拆分

这一节不是新的产品方案，而是把上面的查询策略拆成后端 agent 可以直接落地的技术任务。

### 7.1 新增模块拆分

推荐按下面的文件职责拆：

1. `server/app/services/dictionary/nlp.py`
   - 负责词典查询专用 `spaCy` singleton
   - 提供：
     - `check_dict_spacy_model()`
     - `get_dict_nlp()`
     - `parse_context_sentence(text: str) -> ParsedContext`

2. `server/app/services/dictionary/phrase_templates.py`
   - 负责 canonical template 规则
   - 提供：
     - `canonicalize_dictionary_phrase(text: str) -> str`
     - `canonicalize_sentence_span(doc, span) -> str`
     - `classify_slot(token_or_span) -> Literal["sb", "sth", "sb's", None]`

3. `server/app/services/dictionary/phrase_candidates.py`
   - 负责围绕点击锚点生成候选 form
   - 输入：
     - `query`
     - `context_sentence`
     - `occurrence`
     - `ParsedContext`
   - 输出：
     - `literal forms`
     - `lemma forms`
     - `canonical template forms`

4. `server/app/services/dictionary/db_pg.py`
   - 新增 `lookup_candidates_batch()`
   - 承接多个候选 form 的一次性查询

5. `server/app/services/dictionary/service.py`
   - 从“裸字符串 normalize”升级成“请求建模 + 调度”
   - 决定：
     - 是否尝试 `spaCy`
     - 是否退化到 regex / n-gram
     - 是否进入 lemma fallback

6. `server/app/services/dictionary/providers/tecd3.py`
   - 不再自己拼查询流程
   - 只负责：
     - 批量候选召回
     - 排序
     - `entry` / `disambiguation` 组装

### 7.2 推荐调用顺序

新的 `/dict` 调用链应收敛成：

1. `dict.py`
   - 收集 `q / type / context_sentence / occurrence`

2. `service.py`
   - 归一化输入
   - 构造 `DictionaryLookupRequest`
   - 判断是否可以尝试 `spaCy`

3. `nlp.py`
   - 检查模型可用性
   - 若可用，则 parse `context_sentence`

4. `phrase_candidates.py`
   - 基于 parse tree 生成少量高质量 candidate forms

5. `db_pg.py`
   - 用 `lookup_candidates_batch()` 一次性查回候选

6. `tecd3.py`
   - 统一排序
   - 返回 `entry` 或 `disambiguation`

7. fallback
   - 任一步失败都必须回退到：
     - exact query
     - canonical template query
     - lemma fallback

### 7.3 运行时前置检查

既然当前本地环境里 `en_core_web_sm` 实际缺失，那么 `/dict` 专用 `spaCy` pipeline` 必须包含显式前置检查，而不是等报错后再猜。

建议在 `nlp.py` 里实现：

```python
def check_dict_spacy_model() -> bool:
    ...
```

要求：

- 结果缓存
- 首次检查失败时只打一次 warning
- warning 里给出明确安装指引

例如日志语义：

- `dict: spaCy model en_core_web_sm unavailable`
- `dict: falling back to exact/n-gram lookup`

### 7.4 本地调试要求

为了避免“代码写好了，但本地一直没真正跑到 `spaCy` 分支”，文档里应明确：

1. 仅执行 `uv run uvicorn app.main:app --reload` 不能证明 `spaCy` 可用
2. 只有同时满足下面两点，`/dict` 的 `spaCy` 分支才可能真正生效：
   - `en_core_web_sm` 已安装
   - 请求里带可用的 `context_sentence`
3. 本地调试需要至少覆盖两组场景：
   - 模型存在：验证 `spaCy` 分支
   - 模型缺失：验证 fallback 分支

### 7.5 测试拆分

推荐增加三组测试，而不是只写集成 case：

1. `nlp.py` 单测
   - 模型缺失时返回 `False`
   - 模型可用时能 parse 出 lemma / POS / DEP

2. `phrase_templates.py` 单测
   - dictionary phrase -> canonical template
   - parsed span -> canonical template
   - `sb / sth / sb's` 槽位分类

3. `phrase_candidates.py` 单测
   - 围绕锚点生成的 candidate 数量受控
   - `be there for you -> be there for sb`
   - `give it to him -> give sth to sb`

这样能把“环境问题”“模板 canonicalization 问题”“候选生成问题”拆开定位。

## 8. 查询管线设计

### 8.1 总体原则

新的 `/dict` 查询不再是“单次查询 + 单个排序”，而是四段式管线：

1. 请求建模
2. 候选 form 生成
3. 批量数据库召回
4. 规则化排序与返回

### 8.2 候选 form 生成

#### A. 直接查询 form

所有请求都必须包含：

- `normalized_query`

如果 `type=phrase`：

- 直接把 `q` 当成 phrase exact 查询
- 同时生成一份 canonical template form（如果 phrase 本身包含 slot）

#### B. 上下文短语 form

当满足下面条件时，生成 anchored n-gram：

- `query_type == "word"`
- `context_sentence` 非空
- `occurrence` 可解析，或 `query` 在句中仅出现一次

生成规则：

1. 先用 `spaCy` 定位点击锚点对应的 token / span
2. 优先沿 dependency 关系生成最小合理 phrase span
3. 再为每个 span 生成：
   - literal form
   - lemma form
   - canonical template form
4. 只有 parse-based span 不可靠时，才退化为有限长度 anchored n-gram
5. 去重后送入批量召回

例子：

- 点击 `there`
- 上下文：`I will always be there for you`
- 候选顺序应接近：
  - `be there for you`
  - `be there for sb`
  - `there`

说明：

- literal phrase 和 template phrase 要一起进批量召回
- `spaCy` 的作用不是替代 DB，而是把自然句子压缩成少量高质量 candidate

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

### 8.3 锚点无法可靠定位时的降级

如果发生下面任一情况：

- `query` 在句中出现多次，且 `occurrence` 缺失
- 句子清洗后无法稳定定位点击词

则不做上下文短语嗅探，直接退化为：

1. exact query
2. canonical template query
3. lemma fallback

要求：

- 不要猜测
- 不要在定位不可靠时做高风险 phrase 合成
- 只有在 `spaCy` 不可用或 parse 异常时，才退回简单 n-gram

## 9. 批量召回接口

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

## 10. 排序规则设计

### 10.1 排序必须在 Python 层完成

原因：

- 规则依赖 `query_type`、form 来源、token 长度、`lookup_type`、`entry_kind`
- 这些因素塞进 SQL 会让实现脆弱且难调试
- 批量召回后的候选数量通常不大，Python 排序成本可接受

### 10.2 推荐排序桶

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

### 10.3 伪代码

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

### 10.4 返回策略

本次不改变结果类型语义：

- 只有一个唯一 `entry_id` 时，返回 `entry`
- 多个唯一 `entry_id` 时，返回 `disambiguation`

也就是说：

- 本次只优化召回和候选顺序
- 不改变前端对单候选 / 多候选的处理方式

## 11. 缓存设计

### 11.1 当前问题

[tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py) 当前缓存 key 只包含 `query`，这在新策略下会造成串缓存：

- 同一 `query`
- 不同 `query_type`
- 不同 `context_sentence`
- 不同 `occurrence`

都可能错误复用一份结果。

### 11.2 新缓存 key

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

## 12. 分阶段实施建议

### Phase 0：请求建模与缓存修正

目标：

- 让 `type` 真正生效
- 接口允许接收 `context_sentence` 和 `occurrence`
- provider 缓存 key 正确分桶
- 明确记录当前环境下 `spaCy` 不可用时的降级日志

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

### Phase 2：`spaCy` 驱动的 template 命中

目标：

- 让 `be there for sb.` 这类模板短语可以命中 `be there for you`
- 让 literal phrase 和 template phrase 共享同一套 canonicalization 规则
- 让 `/dict` 真正用上 `spaCy` 的 lemma / POS / DEP 能力

改动范围：

- 新增词典查询专用 `spaCy` singleton
- 新增 phrase template helper
- 导入链路和运行时查询共用该 helper
- 新增 candidate builder
- [db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py) 增加批量召回接口

前置条件：

- 本地 / CI / 部署环境至少有一处真正安装 `en_core_web_sm`
- 测试中要覆盖“模型存在”和“模型缺失”两条路径

### Phase 3：前端透传上下文

目标：

- 把 `clicked_word + context_sentence + occurrence` 真正传给 `/dict`

直接相关文件：

- [WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx)
- [dict.adapter.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/api/adapters/dict.adapter.ts)
- [projection.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/analysis/projection.py)

## 13. 测试与验收标准

### 13.1 查询正确性

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

10. `spaCy` 异常兜底
   - `spaCy` 不可用或运行时报错
   - 预期：退回 exact + 有限 n-gram，不影响 `/dict` 可用性

11. 当前本地环境验证
   - 在未安装 `en_core_web_sm` 的本地 `uv` 环境下启动 `uv run uvicorn app.main:app --reload`
   - 预期：服务可启动，`/dict` 不崩溃，但会记录 `spaCy unavailable` 并走 fallback

### 13.2 数据正确性

需要抽检：

- `dict_lookup_targets.lookup_type='phrase'` 的数量是否合理
- 带 `sb.` / `sth.` 槽位的 phrase 是否都能生成稳定的 canonical template row
- template row 是否都能回到正确的 `entry_id`
- `preview_text` 是否足够支撑 disambiguation

### 13.3 可观测性

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
- `spaCy` template candidate 有没有生成
- 哪一阶段最常 miss

## 14. 最终建议

后端 agent 实施时，建议按下面顺序推进：

1. 先把 `/dict` 的输入升级成显式请求模型，并让 `type` 真正参与 provider 策略。
2. 新增 `lookup_candidates_batch()`，把排序主逻辑移到 Python 层。
3. 补 migration 和导入逻辑，把 phrase 正式写进 `dict_lookup_targets`。
4. 增加 `spaCy` 驱动的 template candidate 生成，让 `sb.` / `sth.` 模板短语可命中真实句子。
5. 最后再接前端上下文透传，让“短语嗅探 + 最长优先”真正工作。

如果只做其中一部分，优先级应该是：

1. 请求建模 + cache 修正
2. phrase 索引补齐
3. `spaCy` template 命中
4. 前端上下文透传

## 15. 直接相关文件

- [TECD3 本地词典接入与查询策略](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/docs/architecture/tecd3-local-dictionary-integration.md)
- [main.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/main.py)
- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py)
- [service.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/service.py)
- [tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py)
- [db_pg.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/db_pg.py)
- [lemma.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/lemma.py)
- [input_preparation.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/analysis/input_preparation.py)
- [analysis.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/schemas/internal/analysis.py)
- [0001_initial_schema.sql](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/db/migrations/0001_initial_schema.sql)
- [0002_add_exam_tag.sql](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/db/migrations/0002_add_exam_tag.sql)
- [import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py)
- [import_exam_vocabulary.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_exam_vocabulary.py)
- [WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx)
- [dict.adapter.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/api/adapters/dict.adapter.ts)
