# V2 前端渲染组件设计文档

## 1. 文档目标

本文档用于指导 V2 前端实验场的设计与开发，目标不是直接定义最终的 LLM 输出协议，而是先回答：

1. 微信小程序环境下，哪些标注渲染方式能稳定实现？
2. 哪些交互不会与基础词典查词动作冲突？
3. 哪些组件形态值得保留进最终的结构化输出协议？
4. 如何先在本地用 mock 页面验证效果，再把稳定 schema 交给后端升级到 V2 版本联调？

这份文档是 V2 的**前端先行设计稿**。  
最终 schema 应以后续前端实验结果为准，而不是反过来让前端被 schema 牵着走。

---

## 2. 设计前提

### 2.1 已确认的项目结论

以下结论已经在 [v2-generative-ui-vision.md](./v2-generative-ui-vision.md) 中确定：

*   保留 `sentence_id` 作为锚点定位的硬边界。
*   不再把绝对 `start-end` 偏移作为 LLM 输出目标。
*   对 `so ... that`、`not only ... but also` 这类不连续模式，必须支持 **span 列表 / 锚点列表**。
*   翻译层是页面固定能力，不是 AI 自由选择组件。
*   “点击单词查词”是系统级基础交互，优先级高于 AI 标注点击。
*   第一阶段优先验证静态稳定渲染，不把 streaming 作为主目标。

### 2.2 当前代码现状

*   结果页目前仍以 mock 数据探索表现为主，见 [result/index.tsx](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/pages/result/index.tsx)。
*   前端类型定义仍停留在旧 draft，见 [schema.d.ts](C:/Users/nanpr/miniprogram/interpretation-of-english-articles/client/src/types/schema.d.ts)。
*   V1 版本已经被证明不可用，不值得继续为其编写前端适配层。
*   V2 前端实验应直接面向新渲染模型和新 schema 设计，不再为旧接口兼容投入额外成本。

---

## 3. 设计原则

### 3.1 前端优先定义“渲染能力”，而不是“教学分类”

前端组件不以“词汇组件 / 语法组件 / 长难句组件”命名和划分，而以“渲染能力”来定义。

换句话说，前端先回答的是：

*   能否高亮？
*   能否下划线？
*   能否弹出词级气泡？
*   能否挂句级卡片？
*   能否打开底部详情面板？

至于某个知识点到底是“词汇”“语法”还是“语境特殊义”，应在后续 schema 中作为内容语义，而不是直接决定组件名称。

### 3.2 翻译层固定

翻译不参与组件自由选择。

页面固定为三层：

1. 英文正文主层
2. 中文翻译副层
3. 标注叠加层

### 3.3 词典点击是基础交互

词级点击默认进入查词流程。  
AI 的词级补充说明只能复用这个入口，不能再定义第二套词级点击行为。

### 3.4 解析与渲染分离

前端实验场不直接消费生的 LLM 输出，而是消费一个统一的 `RenderSceneModel`。

页面组件层只关心最终可渲染模型，不关心它后续由哪个后端节点生成。

---

## 4. 小程序环境约束

### 4.1 关键限制

*   `rich-text` 不适合承载复杂点击交互。
*   长文章大量节点容易造成渲染卡顿。
*   绝对定位气泡需要精心控制遮挡和滚动偏移。
*   小屏设备不适合复杂双栏布局。
*   复杂图形组件（句法树、箭头连线、多段覆盖）风险高，第一阶段不应作为核心依赖。

### 4.2 第一阶段明确不做

*   逐词 interlinear 行间对照
*   复杂句法树
*   自由漂浮边注
*   多层浮窗叠加
*   高密度实时 streaming 注入

---

## 5. 页面信息架构

## 5.1 结果页结构

```text
ResultPage
├── ReaderToolbar
├── ArticleScrollView
│   ├── ParagraphBlock[]
│   │   ├── SentenceRow[]
│   │   │   ├── EnglishLine
│   │   │   ├── TranslationLine
│   │   │   ├── SentenceTailEntry[]
│   │   ├── BetweenSentenceCard[]
├── WordPopup
├── BottomSheetDetail
```

## 5.2 页面模式

### 沉浸模式

*   默认只显示英文正文
*   保留低密度高亮
*   中文默认隐藏

### 双语模式

*   每句英文下方显示中文
*   仍保留低密度标注
*   适合作为第一阶段主测试模式

### 精读模式

*   开启更多语法标记和句级入口
*   展示句尾入口、卡片和详情面板
*   仍然避免在正文上叠加太多点击目标

---

## 6. 前端渲染原语

V2 前端第一阶段只定义 6 类稳定渲染原语。

### 6.1 `InlineBackground`

用于词级或短语级背景高亮。

适合：

*   考试词
*   难词
*   短语搭配

不适合：

*   同时承载复杂语法关系

### 6.2 `InlineUnderline`

用于轻量语法提示或特殊表达标记。

适合：

*   单段语法现象
*   特殊语境词提示

限制：

*   同一区域不与 `InlineBackground` 同时叠加

### 6.3 `WordPopup`

词级统一点击容器。

内容分区：

*   词典结果
*   AI 补充说明

这是唯一允许挂在单词点击上的弹层。

### 6.4 `TranslationLine`

逐句中文翻译行。

特点：

*   固定渲染层
*   由页面模式控制显示/隐藏
*   不属于 annotation 组件

### 6.5 `SentenceTailEntry`

句尾或句旁的小入口，用于打开更重的句级/语法级解释。

适合：

*   语法说明
*   句级分析
*   语境说明入口

优势：

*   不和词典点击冲突
*   正文可保持清爽

### 6.6 `BetweenSentenceCard`

插入在句子之间或段落内部的分析卡片。

适合：

*   长难句分析
*   对比说明
*   精读提示

限制：

*   每段数量必须受限
*   需要折叠能力

---

## 7. 第一阶段组件清单

以下是建议前端先实现并测试的实验组件。

## 7.1 `SentenceRow`

职责：

*   承载英文句子和对应中文
*   承载词级高亮和句级入口

最小 props：

```ts
type SentenceRowProps = {
  sentenceId: string
  englishText: string
  translationZh?: string
  showTranslation: boolean
  inlineMarks: InlineMarkModel[]
  tailEntries: SentenceTailEntryModel[]
}
```

## 7.2 `InlineMark`

职责：

*   在句内渲染背景高亮或下划线
*   可选绑定词级点击行为

最小 props：

```ts
type InlineMarkModel = {
  id: string
  renderType: 'background' | 'underline'
  anchor: TextAnchorModel | MultiTextAnchorModel
  tone: 'info' | 'focus' | 'exam' | 'phrase' | 'grammar'
  clickable: boolean
}
```

说明：

*   `clickable=true` 仅用于词级统一弹层
*   多段 anchor 第一阶段只验证解析，不强求复杂连线视觉

## 7.3 `WordPopup`

职责：

*   统一承载单词点击后的查询结果

结构建议：

*   顶部：词形、音标、发音
*   中部 Tab A：词典结果
*   中部 Tab B：AI 补充
*   底部：收藏、加入生词本

## 7.4 `SentenceActionChip`

职责：

*   作为句尾入口，打开句级或语法级详情

适合承载：

*   “语法”
*   “句解”
*   “语境”

## 7.5 `BottomSheetDetail`

职责：

*   统一承载较重解释内容

支持内容：

*   句级分析
*   语法详细说明
*   对比说明

## 7.6 `AnalysisCard`

职责：

*   在句子之间插入可展开卡片

第一阶段用途：

*   验证段间卡片在长文中的视觉节奏
*   验证收起 / 展开对阅读流的影响

---

## 8. 锚点模型

前端实验场使用统一锚点模型，不直接依赖绝对偏移。

## 8.1 单段锚点

```ts
type TextAnchorModel = {
  kind: 'text'
  sentenceId: string
  anchorText: string
  occurrence?: number
}
```

## 8.2 多段锚点

```ts
type MultiTextAnchorModel = {
  kind: 'multi_text'
  sentenceId: string
  parts: Array<{
    anchorText: string
    occurrence?: number
    role?: string
  }>
}
```

适用场景：

*   `so ... that`
*   `not only ... but also`
*   其他不连续结构

## 8.3 句级锚点

```ts
type SentenceAnchorModel = {
  kind: 'sentence'
  sentenceId: string
}
```

## 8.4 段间插入锚点

```ts
type BetweenSentenceAnchorModel = {
  kind: 'after_sentence'
  afterSentenceId: string
}
```

---

## 9. 统一渲染模型

前端不直接吃后端原始 schema，而是统一适配为 `RenderSceneModel`。

```ts
type RenderSceneModel = {
  article: {
    paragraphs: Array<{
      paragraphId: string
      sentenceIds: string[]
    }>
    sentences: Array<{
      sentenceId: string
      paragraphId: string
      text: string
    }>
  }
  translations: Array<{
    sentenceId: string
    translationZh: string
  }>
  inlineMarks: InlineMarkModel[]
  sentenceEntries: SentenceTailEntryModel[]
  cards: AnalysisCardModel[]
}
```

这个模型是前端实验阶段的唯一输入。

第一阶段来源只有一种：

1. mock 构造

后续在 schema 冻结后，再由后端 V2 接口原生生成相同结构。

---

## 10. 本地开发与联调路径

推荐按以下顺序打通：

1. 前端新建实验结果页，优先消费 `RenderSceneModel`
2. 先用 mock 数据开发并验证组件
3. 基于实验结果收敛出稳定 schema
4. 把 schema 交给后端，使用 LLM 做 V2 structured output 测试
5. 后端升级到 V2 接口
6. 前端再接入 V2 真接口进行联调
7. 记录真实数据下的渲染失败、定位失败和交互冲突

---

## 11. 第一阶段验收标准

前端实验场至少回答以下问题：

*   长文场景下 `SentenceRow` 是否足够稳定？
*   双语逐句模式是否阅读负担可接受？
*   `WordPopup` 是否能统一承载词典和 AI 两类信息？
*   句级入口是否比正文内多点击目标更自然？
*   `InlineBackground` 与 `InlineUnderline` 哪种更适合作为默认 L0 样式？
*   多段锚点能否稳定定位，但不引入复杂视觉负担？
*   段间卡片在小程序里是否会显著打断阅读节奏？

如果这些问题没有通过，V2 schema 不能冻结，也不进入后端实现阶段。

---

## 12. 暂定实施顺序

### Phase A：实验页与组件

*   新建实验结果页
*   实现 `SentenceRow`
*   实现 `InlineMark`
*   实现 `TranslationLine`
*   实现 `WordPopup`
*   实现 `SentenceActionChip`
*   实现 `BottomSheetDetail`

### Phase B：冻结前端 schema

*   基于组件实验收敛字段
*   输出前端可消费的 `RenderSceneModel`
*   明确锚点模型、点击优先级和降级规则

### Phase C：后端 V2 输出测试

*   后端基于前端 schema 定义 V2 接口
*   用 LLM 做 structured output 测试
*   修正 schema 中不利于模型稳定输出的字段

### Phase D：前后端联调

*   记录渲染失败场景
*   记录点击冲突场景
*   记录密度失控场景
*   记录性能瓶颈

---

## 13. 文档结论

V2 的正确顺序不是“先定义最终 schema，再逼前端适配”，也不是“继续为 V1 写兼容层”，而是：

**先做前端 V2 mock 实验页验证渲染能力与交互约束 -> 再冻结前端可消费的统一渲染模型 -> 再让后端和 LLM 一起适配这份 schema -> 最后进行 V2 真接口联调。**

V1 已被验证不可用，因此不再为旧接口设计前端适配层。
