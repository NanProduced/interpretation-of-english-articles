import { RenderSceneModel } from '../../types/v2-render'

/**
 * V2 实验页 Mock 数据
 * 包含丰富的标注类型演示
 */

// 文章元数据
export const articleMeta = {
  title: 'The New Science of Sleep and Dreams',
  source: 'Why We Sleep',
  date: '2024-03-15',
  level: 'CET-6',
}

export const mockSceneData: RenderSceneModel = {
  article: {
    paragraphs: [
      { paragraphId: 'p1', sentenceIds: ['s1', 's2', 's3'] },
      { paragraphId: 'p2', sentenceIds: ['s4', 's5', 's6'] },
      { paragraphId: 'p3', sentenceIds: ['s7', 's8', 's9'] },
    ],
    sentences: [
      // Paragraph 1
      { sentenceId: 's1', paragraphId: 'p1', text: 'This paradigm shift represents a comprehensive transformation in how organizations leverage emerging opportunities.' },
      { sentenceId: 's2', paragraphId: 'p1', text: 'Not only does it challenge traditional assumptions, but it also opens new avenues for innovation and growth.' },
      { sentenceId: 's3', paragraphId: 'p1', text: 'The shift is so profound that it fundamentally alters our understanding of competitive advantage.' },

      // Paragraph 2
      { sentenceId: 's4', paragraphId: 'p2', text: 'Leading firms are already leveraging these insights to drive meaningful change across their operations.' },
      { sentenceId: 's5', paragraphId: 'p2', text: 'They recognize that sustainable success requires a fundamental rethinking of core business models.' },
      { sentenceId: 's6', paragraphId: 'p2', text: 'Those who fail to adapt will find themselves increasingly marginalized in the marketplace.' },

      // Paragraph 3
      { sentenceId: 's7', paragraphId: 'p3', text: 'The implications extend far beyond individual organizations to encompass entire industries.' },
      { sentenceId: 's8', paragraphId: 'p3', text: 'Indeed, we are witnessing a fundamental restructuring of the global economic landscape.' },
      { sentenceId: 's9', paragraphId: 'p3', text: 'This transformation, while challenging, presents unprecedented opportunities for those prepared to embrace it.' },
    ],
  },

  translations: [
    { sentenceId: 's1', translationZh: '这种范式转变代表了组织利用新兴机会方式的全面变革。' },
    { sentenceId: 's2', translationZh: '它不仅挑战了传统假设，还为创新和增长开辟了新的途径。' },
    { sentenceId: 's3', translationZh: '这种转变如此深刻，以至于从根本上改变了我们对竞争优势的理解。' },
    { sentenceId: 's4', translationZh: '领先的企业已经开始利用这些见解推动其运营的有意义的变革。' },
    { sentenceId: 's5', translationZh: '他们认识到，持续的成功需要对核心业务模式进行根本性的重新思考。' },
    { sentenceId: 's6', translationZh: '那些未能适应的人将发现自己在市场上越来越被边缘化。' },
    { sentenceId: 's7', translationZh: '其影响远远超出了单个组织，涵盖了整个行业。' },
    { sentenceId: 's8', translationZh: '事实上，我们正在目睹全球经济格局的根本性重构。' },
    { sentenceId: 's9', translationZh: '这种转变虽然充满挑战，但为那些准备接受它的人带来了前所未有的机遇。' },
  ],

  inlineMarks: [
    // s1 - 词汇标注（exam 重点词）
    {
      id: 'm1',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's1', anchorText: 'paradigm', occurrence: 1 },
      tone: 'exam',
      clickable: true,
      aiNote: 'paradigm 是学术写作中的高频词汇，表示"范式"或"典范"，源自希腊语 paradeigma。',
    },
    {
      id: 'm2',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's1', anchorText: 'comprehensive', occurrence: 1 },
      tone: 'exam',
      clickable: true,
    },
    {
      id: 'm3',
      renderType: 'underline',
      anchor: { kind: 'text', sentenceId: 's1', anchorText: 'leverage', occurrence: 1 },
      tone: 'phrase',
      clickable: true,
      aiNote: 'leverage 在商业语境中表示"利用"，比喻巧妙地使用资源或优势达到目的。',
    },

    // s2 - 多段锚点示例（not only...but also）
    {
      id: 'm4',
      renderType: 'background',
      anchor: {
        kind: 'multi_text',
        sentenceId: 's2',
        parts: [
          { anchorText: 'Not only', role: 'part1' },
          { anchorText: 'but also', role: 'part2' },
        ],
      },
      tone: 'grammar',
      clickable: false,
    },

    // s3 - 语法标注 + 多段锚点（so...that）
    {
      id: 'm5',
      renderType: 'underline',
      anchor: {
        kind: 'multi_text',
        sentenceId: 's3',
        parts: [
          { anchorText: 'so', role: 'part1' },
          { anchorText: 'that', role: 'part2' },
        ],
      },
      tone: 'grammar',
      clickable: false,
    },
    {
      id: 'm6',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's3', anchorText: 'profound', occurrence: 1 },
      tone: 'focus',
      clickable: true,
    },

    // s4 - 短语搭配
    {
      id: 'm7',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's4', anchorText: 'leading', occurrence: 1 },
      tone: 'info',
      clickable: true,
    },
    {
      id: 'm8',
      renderType: 'underline',
      anchor: { kind: 'text', sentenceId: 's4', anchorText: 'insights', occurrence: 1 },
      tone: 'phrase',
      clickable: true,
    },

    // s5 - 词汇标注
    {
      id: 'm9',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's5', anchorText: 'sustainable', occurrence: 1 },
      tone: 'exam',
      clickable: true,
      aiNote: 'sustainable 是 CET/考研高频词，表示"可持续的"，常用于环保、商业可持续发展等话题。',
    },
    {
      id: 'm10',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's5', anchorText: 'fundamental', occurrence: 1 },
      tone: 'exam',
      clickable: true,
    },
    {
      id: 'm11',
      renderType: 'underline',
      anchor: { kind: 'text', sentenceId: 's5', anchorText: 'core', occurrence: 1 },
      tone: 'info',
      clickable: true,
    },

    // s6 - 词汇标注
    {
      id: 'm12',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's6', anchorText: 'marginalized', occurrence: 1 },
      tone: 'focus',
      clickable: true,
    },

    // s7 - 短语
    {
      id: 'm13',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's7', anchorText: 'implications', occurrence: 1 },
      tone: 'exam',
      clickable: true,
    },
    {
      id: 'm14',
      renderType: 'underline',
      anchor: { kind: 'text', sentenceId: 's7', anchorText: 'beyond', occurrence: 1 },
      tone: 'phrase',
      clickable: true,
    },

    // s8 - 词汇标注
    {
      id: 'm15',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's8', anchorText: 'witnessing', occurrence: 1 },
      tone: 'info',
      clickable: true,
    },
    {
      id: 'm16',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's8', anchorText: 'restructuring', occurrence: 1 },
      tone: 'focus',
      clickable: true,
    },
    {
      id: 'm17',
      renderType: 'underline',
      anchor: { kind: 'text', sentenceId: 's8', anchorText: 'Indeed', occurrence: 1 },
      tone: 'grammar',
      clickable: false,
    },

    // s9 - 词汇标注
    {
      id: 'm18',
      renderType: 'background',
      anchor: { kind: 'text', sentenceId: 's9', anchorText: 'unprecedented', occurrence: 1 },
      tone: 'exam',
      clickable: true,
    },
    {
      id: 'm19',
      renderType: 'underline',
      anchor: { kind: 'text', sentenceId: 's9', anchorText: 'prepared', occurrence: 1 },
      tone: 'phrase',
      clickable: true,
    },
  ],

  sentenceEntries: [    // s1 句尾入口 - 演示 title !== label
    {
      id: 'e1',
      label: '语法',
      title: '语法分析：定语从句与后置定语', // title 比 label 更详细
      anchor: { kind: 'sentence', sentenceId: 's1' },
      type: 'grammar',
      content: `本句包含以下语法现象：

- **主语 + 谓语 + 宾语结构**
- **that 引导的定语从句**：修饰 "a paradigm shift"
- **现在分词短语作后置定语**："leveraging emerging opportunities" 修饰 "organizations"

### that 作关系代词

在定语从句中作主语，指代先行词 "a paradigm shift"。

\`\`\`
This paradigm shift (that) represents...
                    ________that作为主语
\`\`\`

### 学习要点

- 区分 that/which 在定语从句中的用法
- 掌握现在分词短语作后置定语的用法`,
    },
    {
      id: 'e2',
      label: '句解',
      anchor: { kind: 'sentence', sentenceId: 's1' },
      type: 'sentence_analysis',
      content: `## 句子解析

**句子主干**：

\`\`\`
This represents a paradigm shift.
主语      谓语        宾语（名词短语）
\`\`\`

**成分划分**：

- 主语：This
- 谓语：represents
- 宾语：a paradigm shift
- 定语从句：that organizations leverage emerging opportunities（修饰 paradigm shift）
- 后置定语：in how organizations leverage emerging opportunities（修饰方式）

**阅读技巧**：

遇到长难句时，先找到主谓宾结构，再逐层分析修饰成分。本句关键在于理解 *paradigm shift* 的含义以及 that 从句的修饰关系。`,
    },

    // s2 句尾入口
    {
      id: 'e3',
      label: '语法',
      anchor: { kind: 'sentence', sentenceId: 's2' },
      type: 'grammar',
      content: `## 语法分析：Not Only...But Also 结构

**结构解析**：

\`\`\`
Not only (does it challenge...)  but it also (opens...)
__________________A_______________  _________________B_______________
              并列分句A                              并列分句B
\`\`\`

**倒装用法**：

"Not only" 放在句首时，主谓要部分倒装。

\`\`\`
Not only does it challenge traditional assumptions,
Not only did it challenge...
(如果是一般过去时)
\`\`\`

**语义功能**：

- *Not only* 引出第一个观点（递进起点）
- *but also* 引出第二个观点（递进升级）
- 强调两点都正确，且后者更重要

### 学习要点

- 掌握 Not only...but also 的平行结构
- 了解句首倒装的规则`,
    },
    {
      id: 'e4',
      label: '语境',
      anchor: { kind: 'sentence', sentenceId: 's2' },
      type: 'context',
      content: `## 语境解读

**文章背景**：

本文讨论的是组织和个人如何通过理解和使用"范式"来改善思维和行动方式。

**关键词汇**：

- *paradigm*: 范式，源自希腊语 paradeigma，意为"模型"或"典范"
- *leverage*: 利用，原意为"杠杆作用"，比喻善于利用资源
- *avenues*: 途径，源自法语 avenue（林荫道），比喻通向目标的路

**写作目的**：

作者通过引入"范式"这一概念，为后文讨论组织和个人的改进奠定理论基础。这种引入概念的方式在学术写作中常见。

**与上下文的联系**：

本句承接上文对传统方法的批评，引出"范式转变"作为新的解决思路。`,
    },

    // s3 句尾入口
    {
      id: 'e5',
      label: '语法',
      anchor: { kind: 'sentence', sentenceId: 's3' },
      type: 'grammar',
      content: `## 语法分析：So...that 结果从句

**结构解析**：

\`\`\`
The shift is so profound [状语]
                    ________that it fundamentally alters... [结果状语从句]
\`\`\`

**核心语法**：

\`\`\`
so + adj./adv. + that + 从句
"如此...以至于..."
\`\`\`

- *so* 修饰形容词 *profound*
- *that* 引导结果状语从句
- 从句说明前面动作或状态的结果

**与 Not only...but also 的对比**：

| 结构 | 语义关系 | 例子 |
|------|---------|------|
| so...that | 因果关系 | so profound that... (如此深刻以至于) |
| not only...but also | 递进关系 | not only...but also (不仅...而且) |`,
    },
    {
      id: 'e6',
      label: '句解',
      anchor: { kind: 'sentence', sentenceId: 's3' },
      type: 'sentence_analysis',
      content: `## 句子解析

**句子主干**：

\`\`\`
The shift is so profound that it fundamentally alters our understanding.
主语     系动词      表语（so...that结构）              结果状语从句
\`\`\`

**成分划分**：

- 主语：The shift
- 系动词：is
- 表语：so profound
- 结果状语从句：that it fundamentally alters our understanding of competitive advantage

**翻译技巧**：

原句：*"This shift is so profound that it fundamentally alters..."*
译文：*"这种转变如此深刻，以至于从根本上改变了..."*

**关键理解**：

*fundamentally* = in a fundamental way = 根本地，彻底地

本句用 *so...that* 结构强调变化的深度和影响力。`,
    },

    // s4 句尾入口
    {
      id: 'e7',
      label: '语境',
      anchor: { kind: 'sentence', sentenceId: 's4' },
      type: 'context',
      content: `## 语境解读

**论点推进**：

本句开始从理论转向实践，引用"领先企业"的例子说明范式转变的实际应用。

**关键词汇**：

- *leading firms*: 领先企业，行业领头羊
- *insights*: 洞察力，源自动词 *see inside*，比喻深刻理解
- *drive meaningful change*: 推动实质性变革

**写作手法**：

从一般性论述（Organizations）到具体案例（Leading firms），这是典型的从抽象到具体的论证路径。

**行业视角**：

这里的 "leading firms" 通常指行业中具有创新精神、愿意尝试新方法的企业，如科技行业的创新者。`,
    },

    // s5 句尾入口
    {
      id: 'e8',
      label: '语法',
      anchor: { kind: 'sentence', sentenceId: 's5' },
      type: 'grammar',
      content: `## 语法分析

**结构**：宾语从句 + 不定式作状语

**that 引导的宾语从句**：

\`\`\`
They recognize [that sustainable success requires...]
          _________________that 引导的宾语从句________________
\`\`\`

**不定式短语作状语**：

\`\`\`
...requires a fundamental rethinking [of core business models]
                                  ____________不定式短语作后置定语____________
\`\`\`

**核心词汇**：

- *require*: 需要，后接名词或动名词
- *fundamental*: 基础的，根本的
- *rethinking*: 重新思考，re- 前缀 + thinking

### 学习要点

- 区分 require 后接名词 vs 动名词的区别
- 掌握 re- 前缀表示"重新"的用法`,
    },

    // s6 句尾入口
    {
      id: 'e9',
      label: '句解',
      anchor: { kind: 'sentence', sentenceId: 's6' },
      type: 'sentence_analysis',
      content: `## 句子解析

**句子主干**：

\`\`\`
Those (who fail to adapt) will find themselves marginalized.
主语（定语从句修饰）            谓语        宾语    主语补足语
\`\`\`

**成分划分**：

- 主语：Those who fail to adapt（定语从句修饰）
- 谓语：will find
- 宾语：themselves
- 宾语补足语：marginalized（形容词作补足语）

**词汇辨析**：

| 词汇 | 含义 | 语气 |
|------|------|------|
| marginalized | 边缘化 | 渐进过程 |
| excluded | 排斥 | 直接行为 |
| sidelined | 被边缘化/冷落 | 被动地位 |

**本句语境**：

用 *marginalized* 而非 *excluded*，暗示这是一个渐进过程，而非一蹴而就的排斥。`,
    },

    // s7 句尾入口
    {
      id: 'e10',
      label: '语境',
      anchor: { kind: 'sentence', sentenceId: 's7' },
      type: 'context',
      content: `## 语境解读

**宏观视角**：

本句将讨论范围从单个组织扩展到整个行业，体现典型的逐层递进写作手法。

**关键词汇**：

- *implications*: 影响，结果
- *extend beyond*: 超出，延伸到
- *encompass*: 包含，涵盖

**写作逻辑**：

\`\`\`
单个组织 (organizations)
    ↓
整个行业 (entire industries)
    ↓
全球层面 (global economic landscape - 下文)
\`\`\`

**预测下文**：

基于这个递进结构，下文很可能讨论全球经济层面的影响或变革。`,
    },

    // s8 句尾入口
    {
      id: 'e11',
      label: '语法',
      anchor: { kind: 'sentence', sentenceId: 's8' },
      type: 'grammar',
      content: `## 语法分析

**结构**：现在进行时 + 宾语从句

**核心时态**：

\`\`\`
We are witnessing [a fundamental restructuring...]
_________________现在进行时________________
\`\`\`

**witness 的用法**：

- 及物动词：见证，目睹
- 主动语态表示"见证"客观发生的事件
- 比 *see/observe* 更正式

**词汇特征**：

*restructuring* = re- (重新) + structure (结构) + -ing (进行时态)

\`\`\`
re- + structure + -ing = 正在重新构建
\`\`\`

### 学习要点

- 掌握 *witness* 作为及物动词的用法
- 了解 *re-* 前缀表示"重新"的构词法`,
    },

    // s9 句尾入口
    {
      id: 'e12',
      label: '句解',
      anchor: { kind: 'sentence', sentenceId: 's9' },
      type: 'sentence_analysis',
      content: `## 句子解析

**句子主干**：

\`\`\`
This transformation presents opportunities [for those prepared...]
主语              谓语          宾语                    定语从句
\`\`\`

**转折对比**：

| Part | Structure | Meaning |
|------|-----------|---------|
| This transformation | 主语 | 这一转变 |
| while challenging | 让步状语（现在分词） | 虽然充满挑战 |
| presents unprecedented opportunities | 谓语 + 宾语 | 带来了前所未有的机遇 |
| for those prepared to embrace it | 目的状语 | 对于准备好接受它的人 |

**核心词汇**：

- *transformation*: 彻底改变，transform + -ation
- *unprecedented*: 前所未有的，un- + precedent + -ed
- *prepared*: 准备好的，be prepared to = 愿意/准备好做某事`,
    },
    {
      id: 'e13',
      label: '语境',
      anchor: { kind: 'sentence', sentenceId: 's9' },
      type: 'context',
      content: `## 语境解读

**文章总结**：

本文从多个角度论证了范式转变的重要性和影响，本句作为结尾具有总结和展望的双重功能。

**关键词汇**：

- *transformation*: 转变，彻头彻尾的改变
- *unprecedented*: 前所未有的
- *prepared to embrace*: 准备好接受/拥抱

**写作目的**：

作者在结尾处给出积极正面的信息：虽然变革充满挑战，但也带来了前所未有的机遇。这种写法符合"提出问题-分析问题-给出希望"的经典结构。

**读者启示**：

作为读者，我们应该：
1. 认识到变革的必然性
2. 理解变革带来的挑战
3. 积极准备，抓住机遇`,
    },
  ],

  cards: [
    // s1 和 s2 之间 - 验证"任意句后插卡"规则
    {
      id: 'c0',
      anchor: { kind: 'after_sentence', afterSentenceId: 's1' },
      title: '语法提示：本文的复合句结构',
      content: `本段包含 **3 个复合句**，涉及多种从句类型：

**连接词一览**：

- *that* 引导定语从句
- *not only...but also* 并列结构
- *so...that* 结果状语从句

**阅读建议**：

遇到包含多个从句的长句时，先识别主句的核心主谓宾结构，再逐层分析修饰成分。`,
    },

    // s2 和 s3 之间 - 长难句分析
    {
      id: 'c1',
      anchor: { kind: 'after_sentence', afterSentenceId: 's3' },
      title: '长难句解析：So...that 结构',
      content: `本句包含 so...that 结果状语从句结构：

**结构分析**：
The shift is so profound [状] that it fundamentally alters... [结果状语从句]

**语法要点**：
- so + adj./adv. + that 引导结果状语从句
- 表示"如此...以至于"
- that 从句说明前面动作或状态的结果

**与 not only...but also 的对比**：
前一句使用 not only...but also 并列结构，表示递进关系；
本句使用 so...that 结构，表示因果关系。

**翻译技巧**：
"这种转变如此深刻，以至于..." = This shift is SO profound THAT...`,
    },

    // s5 和 s6 之间 - 词汇辨析
    {
      id: 'c2',
      anchor: { kind: 'after_sentence', afterSentenceId: 's5' },
      title: '词汇辨析：fundamental vs. essential',
      content: `**fundamental（基础的）** vs **essential（本质的）**

两者都有"根本"之意，但使用场景不同：

**fundamental**：
- 更强调"最基础的、不可分割的"
- 常用于描述原则、理论、问题
- *fundamental change* = 根本性变革

**essential**：
- 更强调"不可或缺的、本质的"
- 常用于描述必需品、要素
- *essential skills* = 必备技能

**本句语境**：
...requires a *fundamental* rethinking of core business models

这里用 fundamental，强调需要对核心业务模式进行"最根本"的重新思考，暗示现有模式可能已经过时。`,
    },

    // s6 和 s7 之间 - 对比说明
    {
      id: 'c3',
      anchor: { kind: 'after_sentence', afterSentenceId: 's6' },
      title: '词汇辨析：marginalized vs. excluded',
      content: `**marginalized（边缘化）** vs **excluded（排斥）**

两者都表示被排除在外，但含义有细微差别：

**marginalized**：
- 强调逐渐被推到社会或组织的边缘
- 暗示过程是渐进的，非立即的
- 带有社会政策、结构性不平等含义

**excluded**：
- 强调被故意排斥在外
- 更直接、立即的行动
- 可用于任何排斥行为

**本句语境**：
Those who fail to adapt will find themselves increasingly marginalized...

这里用 marginalized 暗示那些不适应的人会"逐渐"被边缘化，是一个渐进过程，而非一蹴而就的排斥。`,
    },
  ],
}

// 页面模式配置
export const PAGE_MODE_OPTIONS = [
  { value: 'immersive', label: '沉浸', description: '仅显示英文，低密度标注' },
  { value: 'bilingual', label: '双语', description: '英文+中文，适合阅读' },
  { value: 'intensive', label: '精读', description: '显示全部标注和入口' },
] as const
