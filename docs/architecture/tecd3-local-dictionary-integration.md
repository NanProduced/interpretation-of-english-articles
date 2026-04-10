# TECD3 本地词典接入与查询策略

> 文档定位：定义 Claread 透读当前 TECD3 本地词典的有效设计。  
> 生效范围：覆盖词典数据真源、离线导入、数据库落地、`/dict` 运行时查询策略，以及后续词量扩充时需要遵守的约束。  
> 当前结论：词典能力暂不拆独立服务，继续以 PostgreSQL 为运行时真源；同时必须同时维护好“数据库里的词库数据”和“运行时查询策略”，二者缺一不可。

## 1. 当前决策

- 词典内容真源仍然是 `TECD3` 的 `.mdx/.mdd` 资源。
- 运行时不直接读取 `.mdx/.mdd`，而是读取离线解析后导入 `PostgreSQL` 的结构化数据。
- `/dict` 仍由现有 Python 后端提供，不在本阶段拆分成独立 dict service。
- 词典优化分为两条并行主线：
  - 数据质量：把 TECD3 内容正确转换进数据库。
  - 查询质量：让用户点击时尽量命中“真正需要的词或短语”。

这意味着：

- 只补充词量，不优化查询策略，命中率仍然会差。
- 只优化查询策略，不修导入和结构化质量，结果仍然会脏。

## 2. 目标

当前词典能力的直接目标不是做完整词典浏览器，而是稳定服务下面三类场景：

- 结果页点词查词
- 结果页点短语查词
- 生词本词条快照

其中最重要的产品要求是：

1. 普通单词点击后，尽量能命中正确词条。
2. 短语点击后，优先命中完整短语，而不是被错误拆成单生词。
3. 变形词点击后，尽量能回退到基础词形。
4. 返回结构稳定，可直接被 `WordPopup`、详情弹层和生词本复用。

## 3. 词典数据真源与运行时边界

### 3.1 真源

当前本地词典资源：

- [英汉大词典（第三版）.mdx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/.dict/Mdict/TECD3/英汉大词典（第三版）.mdx)
- [英汉大词典（第三版）.mdd](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/.dict/Mdict/TECD3/英汉大词典（第三版）.mdd)
- [tecd3.css](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/.dict/Mdict/TECD3/tecd3.css)

### 3.2 运行时边界

运行时统一遵守下面的边界：

- 不直接在 `/dict` 里读取 `.mdx/.mdd`
- 不在运行时即时解析 HTML
- 不把词典 provider 建在前端
- 不让小程序直接操作词典文件

运行时唯一真源是：

- `PostgreSQL`
- `/dict`

## 4. 离线导入链路

```mermaid
flowchart LR
  A["TECD3.mdx / TECD3.mdd"] --> B["mdict-utils 解包"]
  B --> C["unpacked_mdx/*.txt"]
  C --> D["import_tecd3.py"]
  D --> E["dict_entries / dict_lookup_targets / dict_redirects"]
  E --> F["/dict runtime lookup"]
```

当前链路约束：

- `mdict-utils` 只参与离线解包。
- [import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py) 负责结构化解析与数据库写入。
- 数据重建时，以重新导入为准，不手工修库。

## 5. 数据库职责

当前词典相关表的职责如下：

### `dict_entries`

保存词条详情真源，至少包含：

- 词头
- 基础词头
- 同形词编号
- 主词性
- 音标
- 义项
- 例句
- 短语
- 原始 HTML

### `dict_lookup_targets`

保存“可查形式 -> 词条”的检索索引，供运行时快速命中。

### `dict_redirects`

保存 MDX 跳转、归一化别名等重定向关系。

设计原则：

- `dict_entries` 负责内容质量。
- `dict_lookup_targets` 负责召回质量。
- 两者都要持续维护。

## 6. 当前已知数据质量问题

截至当前版本，TECD3 导入已经确认过以下问题类型：

### 6.1 词性归一化不稳定

典型问题：

- `ABBREVIATION 缩略词` 没有统一转成 `abbr.`
- `COMBINING FORM 组合语素` 与 `comb.` / `comb. form` 混用
- `DEMONSTRATIVE PRONOUN 指示代词` 这类低频标签未规范化
- 导航标签存在 `n. 2`、`suf. 2` 这类带尾号的变体

当前修复要求：

- 导入阶段必须做 POS canonicalization
- 无论标签来自正文块还是导航块，都走同一套归一化逻辑

### 6.2 多例句块被截断

典型问题：

- 同一个 `egBlock` 里存在多个 `.ex`
- 旧逻辑只保留第一个例句，导致示例信息丢失

当前修复要求：

- 导入阶段保留同一例句块中的多个 example
- 合并为稳定可读的结构化文本

### 6.3 fragment 与弱结构词条较多

当前 TECD3 中存在大量：

- `fragment`
- 无稳定词性块的词条
- 纯跳转或片段化入口

这类数据不是单纯“脏数据”，而是词典源本身的结构现实。处理原则：

- 能保留详情就保留
- 提不出稳定词性时，允许只在 `meanings_json[].part_of_speech` 中保留可识别信息
- 不在导入阶段做高风险猜测

## 7. 查询策略必须同步优化

仅修数据库里的词条数据还不够。运行时查询策略必须同步增强，否则点词体验仍然会差。

当前要解决的两个核心问题：

### 7.1 短语优先

问题：

- 用户点击 `take place` 里的 `take`
- 如果系统只先查单生词，会返回 `take = 拿`
- 但用户实际需要的是 `take place = 发生`

结论：

- 运行时必须优先做短语匹配
- 查询原则必须是“最长优先”，不能先查单词再考虑短语

### 7.2 变形词回退

问题：

- 库里只有 `study`
- 用户点的是 `studies`
- 如果系统只按表面词形查，会直接返回空

结论：

- 运行时必须做形态学还原
- 短语和单词都未命中后，再对点击词做 Lemmatization，再重试

## 8. 推荐查询流程

最终查询输入：

- `clicked_word`
- `context_sentence`

运行时流程分两阶段。

### 第一阶段：短语嗅探

目标：

- 不要急着查单词
- 先利用上下文判断是否存在“更长、更合理”的短语候选

推荐流程：

1. 以 `clicked_word` 为中心，在 `context_sentence` 中生成滑动窗口 N-gram。
2. 候选按长度倒序排列，执行数据库匹配。
3. 采用“最长优先”原则，一旦命中更长短语，就优先返回。

例子：

- `take place`
- `in charge of`
- `as well as`
- `look forward to`

优化点：

- 如果 N-gram 中只是在外围拼进了 `a`、`the`、`of` 这类极高频功能词，可跳过明显无效的候选，以减少数据库查询次数。

### 第二阶段：词形降级

触发条件：

- 第一阶段短语未命中
- 单词表面形式也未命中

推荐流程：

1. 对 `clicked_word` 做 Lemmatization。
2. 例如：
   - `took -> take`
   - `studies -> study`
   - `happening -> happen`
3. 用还原后的 lemma 重新执行第一阶段。
4. 重新寻找：
   - 包含该 lemma 的短语
   - 对应 lemma 的单词词条

当前建议实现：

- 使用 `spaCy` 做运行时 Lemmatization。
- 如果后续实践发现 `spaCy` 对某些边界词不稳定，再补轻量规则和别名表。

## 9. 查询策略设计原则

### 9.1 最长优先

短语一旦存在，优先返回短语，不先拆成单生词。

### 9.2 先上下文，后孤立单词

词典查询不是纯“字符串查表”，而是“结合点击位置和上下文理解用户要查什么”。

### 9.3 先精确，后降级

推荐优先级：

1. 上下文短语精确命中
2. 单词表面形式命中
3. lemma 后重试短语
4. lemma 后命中单词
5. 未命中

### 9.4 查询增强不能污染词典真源

查询策略可以增强，但不要把运行时猜测结果直接写回 `dict_entries`。

区分清楚：

- `dict_entries`：词典内容真源
- `query pipeline`：召回与排序逻辑

## 10. 后续数据库扩充原则

你后续会继续找资源扩充词量，这部分需要遵守以下原则：

- 新资源进入库前，先明确来源、版权和格式边界
- 继续坚持“离线导入 -> PostgreSQL 真源 -> 运行时查询”
- 新词量进入时，同时补索引，不只补 `dict_entries`
- 对短语、习语、固定搭配，要优先考虑可检索性，而不是只存为详情字段

## 11. 当前实现要求

接下来与词典相关的开发，默认按以下要求推进：

### 数据层

- 持续修复 `import_tecd3.py` 的结构化质量
- 重导后检查 `examples_json`、`phrases_json`
- 用数据库抽检验证导入效果，不靠个别样例判断

### 查询层

- 在现有 `/dict` 基础上加入“短语嗅探 + 最长优先”
- 加入 Lemmatization fallback
- 将 `clicked_word + context_sentence` 作为查询策略输入，而不是只传孤立单词

### 文档层

- 本文档只保留当前有效设计
- 旧方案对比、已失效路线和过细 UI 描述不再保留

## 12. 当前不做

本阶段明确不做：

- 独立 dict service
- 前端直连词典真源
- 运行时直接读取 MDX/MDD
- 为了查询策略优化而重构整套业务后端

## 13. 直接相关文件

- [import_tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/scripts/import_tecd3.py)
- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py)
- [service.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/service.py)
- [tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py)
- [lemma.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/lemma.py)
- [0001_initial_schema.sql](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/db/migrations/0001_initial_schema.sql)

## 14. 下一步建议

推荐按下面顺序推进：

1. 用修复后的导入脚本全量重导 TECD3。
2. 重导后做数据库抽检，确认 `examples_json` 的质量。
3. 在 `/dict` 查询链路中加入“短语嗅探 + 最长优先”。
4. 在未命中时加入 `spaCy` Lemmatization fallback。
5. 再评估是否需要把短语索引单独落表或增强到 `dict_lookup_targets`。
