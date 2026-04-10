# `/dict` 接口字段与前端词典渲染分析

> 文档定位：给前端和后端一起确认当前 `/dict` 接口的真实使用情况。\
> 目标：先判断当前卡片与详情渲染是否合理、哪些漏掉的字段会影响释义效果，再决定是否对接口做瘦身。\
> 当前结论：现在的前端词典渲染已经形成最小闭环，但详情页对词典内容的承载还不够完整；在决定瘦身前，至少要先评估 `phrases`、`examples` 这类字段的展示价值。

## 1. 当前接口形态

当前词典接口有两个：

- `GET /dict?q=...&type=word|phrase`
- `GET /dict/entry?id=...`

路由定义见：

- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py)

`/dict` 的响应分为两类：

- `entry`
- `disambiguation`

字段定义见：

- [schemas.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/schemas.py)

### 1.1 `entry` 响应

当前 `entry` payload 包含：

- `id`
- `word`
- `base_word`
- `homograph_no`
- `phonetic`
- `meanings`
- `examples`
- `phrases`
- `entry_kind`

这些字段由 `TECD3` provider 从 PostgreSQL 词典记录组装，见：

- [tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py)

### 1.2 `disambiguation` 响应

当前候选项包含：

- `entry_id`
- `label`
- `part_of_speech`
- `preview`
- `entry_kind`

## 2. 哪些数据库字段没有透出到 `/dict`

数据库里的 `dict_entries` 比 `/dict` 暴露的字段更多，但下面这些字段当前没有直接返回给前端：

- `source_entry_key`
- `sections_json`
- `raw_html`
- `parse_version`

其中：

- `source_entry_key` 是词典源内部唯一键，主要用于导入、跳转和 disambiguation 关联。
- `sections_json`、`raw_html`、`parse_version` 都是内部运行和导入质量字段，不属于前端当前需要直接消费的字段。

结论：

- `source_entry_key` 不是前端展示字段。
- 它不应该进入词卡或详情页。
- 前端看到的标题应始终以 `word` 为准。

## 3. 前端当前实际消费了哪些字段

前端接口 DTO 和 VM 映射定义见：

- [dict-response.dto.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/types/api/dict-response.dto.ts)
- [render-scene.vm.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/types/view/render-scene.vm.ts)
- [dict.adapter.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/services/api/adapters/dict.adapter.ts)

虽然 adapter 会把后端公开字段都映射出来，但“被映射”不等于“被 UI 真正使用”。

### 3.1 单词卡片使用的字段

当前 mini 卡片在 [WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx) 中渲染，实际使用的是：

- `entry.word`
- `entry.phonetic`
- `entry.meanings[].definitions[0].meaning`

具体位置：

- 标题： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:182)
- 音标： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:183)
- 摘要释义： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:23)

mini 卡片当前没有直接使用：

- `baseWord`
- `homographNo`
- `examples`
- `phrases`
- `entryKind`

### 3.2 详情页使用的字段

当前 full detail 也在 [WordPopup/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx) 中渲染，实际使用的是：

- `entry.word`
- `entry.phonetic`
- `entry.meanings[]`
- `meaning.partOfSpeech`
- `definition.meaning`
- `definition.example`
- `definition.exampleTranslation`

对应位置：

- 标题： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:234)
- 音标： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:244)
- 候选列表： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:293)
- 义项和例句： [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:312)

歧义候选列表使用：

- `candidate.entryId`
- `candidate.label`
- `candidate.partOfSpeech`
- `candidate.preview`

### 3.3 生词本快照使用的字段

结果页在“加入生词本”时，会从 `/dict` 结果里取这些字段：

<br />

<br />

- `detailMeanings[0]?.partOfSpeech`
- `detailEntry.baseWord ?? detailEntry.word`
- `detailEntry.phonetic`
- `dictResult.provider`

位置见：

- [result/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/result/index.tsx:423)

结论：

- `base_word` 当前有真实业务用途，不能轻易删除。
- `phonetic` 当前有真实业务用途，不能轻易删除。
- `provider` 当前也已经进入生词本快照逻辑。

## 4. 当前渲染是否合理

整体判断：合理，但只做到了“最小可用”，还没有把词典内容承载完整。

### 4.1 mini 卡片

当前 mini 卡片的策略是合理的：

- 标题显示当前词头
- 音标单独展示
- 释义只取最短摘要

这适合“点一下先看一眼”的交互目标。

### 4.2 full detail

当前 full detail 可以展示：

- 多词性
- 多释义
- 释义下的例句和中文

这已经比只有一行释义强很多，足够支撑当前版本上线使用。

但它还没有把词典里已有的一些重要内容展示出来，所以“词典信息量”仍然偏保守。

## 5. 漏掉的字段是否影响释义效果

结论：会。影响最大的不是内部字段，而是前端没有展示的内容字段。

### 5.1 `phrases` 是当前最大缺口

后端已经返回了 `entry.phrases`，并且 adapter 也映射了它，但 `WordPopup` 没有渲染。

这意味着：

- 词条本身携带的习语、固定搭配、短语释义，目前在详情页里是不可见的。
- 像 `A` 这种条目，即使数据库里有 `A to Z`、`from A to B`、`not know from A to B`，前端也完全看不到。

这会直接削弱：

- 短语解释效果
- 习语理解效果
- 对“这个词常见搭配是什么”的帮助

判断：

- `phrases` 不是冗余字段。
- 在决定瘦身前，不应该把它视为可删字段。
- 更合理的做法是优先考虑是否在详情页加一个“短语/搭配”区块。

### 5.2 顶层 `examples` 暂时没有被发挥价值

当前详情页使用的是 definition 内联 example。

这意味着：

- 如果例句已经很好挂在每个 definition 下，UI 主体验不受影响。
- 但顶层 `examples[]` 目前没有直接展示，会导致“例句总览”能力缺失。

判断：

- `examples` 的优先级低于 `phrases`
- 但它不是没有意义
- 如果后续想做“更多例句”或“统一例句区”，它会很有价值

### 5.3 `homograph_no` 目前不是主要问题

当前前端没有展示 `homographNo`。

影响是：

- 同形词场景下，用户的辨识信息少一点
- 但由于现在已经有 disambiguation 列表，这个问题并不严重

判断：

- `homograph_no` 属于次要字段
- 当前不展示不会显著影响释义质量

### 5.4 `entry_kind` 主要是交互元数据

当前 `entry_kind` 几乎没有被 UI 真正使用。

它的潜在用途是：

- 区分 `entry` 和 `fragment`
- 对 fragment 做不同样式或文案

但它不属于释义本身的核心内容。

## 6. 当前前端渲染中的一个小问题

full detail 里词性标签现在是直接渲染的：

- [index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/components/WordPopup/index.tsx:314)

如果某个 `meaning.partOfSpeech` 为空，UI 会出现一个空的词性标签占位。

这不会让数据错误，但会影响细节质量。前端最好改成：

- 只有当 `meaning.partOfSpeech` 有值时才渲染词性标签

## 7. `/dict?type=word|phrase` 当前有什么区别

结论：当前后端几乎没有区别。

虽然 `/dict` 路由收了 `type` 参数，见：

- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py:21)

但它并没有继续向 service / provider 透传。当前实际调用是：

- [dict.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/api/routes/dict.py:25)

即：

- 前端传了 `type`
- 后端没有真正用 `type`

当前真正影响查询分支的不是 `type`，而是 query 本身是否包含空格：

- [tecd3.py](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/server/app/services/dictionary/providers/tecd3.py:50)

现状是：

- 查询里没有空格，才会尝试 lemma fallback
- 查询里有空格，就不会走 lemma fallback

所以现在的 `type=word|phrase` 更像一个“前端意图参数”，不是一个真正生效的后端查询策略参数。

## 8. 当前结论

### 8.1 当前前端渲染是否合理

合理，能用，但还不够完整。

当前已经覆盖了：

- 词头
- 音标
- 义项
- 义项级例句
- 多义项候选切换

这足以支撑当前的点词查词和详情弹层。

### 8.2 当前最值得优先补的字段

优先级最高的是：

- `phrases`

其次是：

- `examples`

因为这两类字段都会直接影响“释义是否完整”和“短语是否真正可见”。

### 8.3 在决定瘦身前的建议

在瘦身之前，建议先把字段分成三类：

必须保留：

- `id`
- `word`
- `base_word`
- `phonetic`
- `meanings`
- `phrases`

建议保留：

- `examples`
- `provider`

可后续评估：

- `homograph_no`
- `entry_kind`
- `cached`
- `query`

### 8.4 当前不建议删除的字段

当前不建议因为“前端暂时没展示”就删除：

- `phrases`
- `examples`
- `base_word`
- `phonetic`
- `provider`

原因：

- `phrases`、`examples` 是释义增强字段
- `base_word`、`phonetic`、`provider` 已经有真实业务用途

## 9. 后续动作建议

如果下一步继续优化，建议顺序如下：

1. 先让详情页真正渲染 `phrases`
2. 再评估是否增加独立 `examples` 区块
3. 再决定 `/dict` 响应字段是否需要瘦身
4. 最后再把 `type=word|phrase` 接回真正的查询策略分支

这样可以避免先把字段删瘦，再发现前端需要回头补字段。
