import { RenderSceneModel, RequestMeta } from '../../types/v2-render'

/**
 * SCENARIO_FULL: 全功能场景
 * 覆盖所有标注类型与交互场景，对齐 v2.1 规范
 */
const requestMeta: RequestMeta = {
  requestId: 'req_v2_1_full_demo',
  sourceType: 'user_input',
  readingGoal: 'Academic Reading',
  readingVariant: 'Intensive',
  profileId: 'user_01'
}

export const SCENARIO_FULL: RenderSceneModel = {
  schemaVersion: '2.1.0',
  request: requestMeta,
  article: {
    paragraphs: [
      { paragraphId: 'p1', sentenceIds: ['s1', 's2'] },
      { paragraphId: 'p2', sentenceIds: ['s3', 's4', 's5'] },
    ],
    sentences: [
      { sentenceId: 's1', paragraphId: 'p1', text: 'This paradigm shift represents a comprehensive transformation in how organizations leverage emerging opportunities.' },
      { sentenceId: 's2', paragraphId: 'p1', text: 'The shift is so profound that it fundamentally alters our understanding of competitive advantage.' },
      { sentenceId: 's3', paragraphId: 'p2', text: 'Leading firms are already leveraging these insights to drive meaningful change across their operations.' },
      { sentenceId: 's4', paragraphId: 'p2', text: 'Those who fail to adapt will find themselves increasingly marginalized in the global marketplace.' },
      { sentenceId: 's5', paragraphId: 'p2', text: 'However, the challenge lies not only in adopting new technologies but also in fostering a culture of continuous learning.' },
    ],
  },
  translations: [
    { sentenceId: 's1', translationZh: '这种范式转变代表了组织利用新兴机会方式的全面变革。' },
    { sentenceId: 's2', translationZh: '这种转变如此深刻，以至于从根本上改变了我们对竞争优势的理解。' },
    { sentenceId: 's3', translationZh: '领先的企业已经开始利用这些见解，在整个运营过程中推动有意义的变革。' },
    { sentenceId: 's4', translationZh: '那些未能适应的人将发现自己在全球市场中日益被边缘化。' },
    { sentenceId: 's5', translationZh: '然而，挑战不仅在于采用新技术，还在于培养一种持续学习的文化。' },
  ],
  inlineMarks: [
    // --- s1 ---
    // 1. VocabHighlight (vocab, background, examTags)
    {
      id: 'm1',
      annotationType: 'vocab_highlight',
      visualTone: 'vocab',
      renderType: 'background',
      clickable: true,
      lookupText: 'paradigm',
      lookupKind: 'word',
      examTags: ['CET-6', 'IELTS'],
      anchor: { kind: 'text', sentenceId: 's1', anchorText: 'paradigm', occurrence: 1 },
    },
    // 1.5 GrammarNote - Single Anchor
    {
      id: 'm1_5',
      annotationType: 'grammar_note',
      visualTone: 'grammar',
      renderType: 'underline',
      clickable: false,
      anchor: { kind: 'text', sentenceId: 's1', anchorText: 'represents', occurrence: 1 },
    },
    // 2. PhraseGloss (phrase, background, glossary.zh)
    {
      id: 'm2',
      annotationType: 'phrase_gloss',
      visualTone: 'phrase',
      renderType: 'background',
      clickable: true,
      lookupText: 'leverage emerging opportunities',
      lookupKind: 'phrase',
      glossary: { zh: '利用新兴机会' },
      anchor: { kind: 'text', sentenceId: 's1', anchorText: 'leverage emerging opportunities', occurrence: 1 },
    },

    // --- s2 ---
    // 3. ContextGloss (context, underline, glossary.gloss/reason)
    {
      id: 'm3',
      annotationType: 'context_gloss',
      visualTone: 'context',
      renderType: 'underline',
      clickable: true,
      lookupText: 'profound',
      lookupKind: 'word',
      glossary: { 
        gloss: '深远而根本的', 
        reason: '在此语境下不仅指深度（deep），更强调这种转变对未来战略产生的本质性影响。' 
      },
      anchor: { kind: 'text', sentenceId: 's2', anchorText: 'profound', occurrence: 1 },
    },
    // 4. GrammarNote - Multi Anchor (so...that)
    {
      id: 'm5',
      annotationType: 'grammar_note',
      visualTone: 'grammar',
      renderType: 'underline',
      clickable: false,
      anchor: {
        kind: 'multi_text',
        sentenceId: 's2',
        parts: [
          { text: 'so', occurrence: 1, role: 'trigger' },
          { text: 'that', occurrence: 1, role: 'result' },
        ],
      },
    },

    // --- s3 ---
    // 5. VocabHighlight
    {
      id: 'm6',
      annotationType: 'vocab_highlight',
      visualTone: 'vocab',
      renderType: 'background',
      clickable: true,
      lookupText: 'insights',
      lookupKind: 'word',
      examTags: ['TOEFL'],
      anchor: { kind: 'text', sentenceId: 's3', anchorText: 'insights', occurrence: 1 },
    },

    // --- s5 ---
    // 6. GrammarNote - Multi Anchor (not only...but also)
    {
      id: 'm7',
      annotationType: 'grammar_note',
      visualTone: 'grammar',
      renderType: 'underline',
      clickable: false,
      anchor: {
        kind: 'multi_text',
        sentenceId: 's5',
        parts: [
          { text: 'not only', occurrence: 1, role: 'part1' },
          { text: 'but also', occurrence: 1, role: 'part2' },
        ],
      },
    },
  ],
  sentenceEntries: [
    // s2: Grammar Note
    {
      id: 'e1',
      sentenceId: 's2',
      entryType: 'grammar_note',
      label: '语法',
      title: 'So...That 结果状语从句',
      content: `本句使用了典型的 **so + adj. + that** 结构。

- **so profound**: 如此深刻
- **that...**: 引导结果状语从句，说明程度带来的结果。

> 在学术阅读中，这类结构常用于建立强因果逻辑关系，强调前者对后者的直接推动作用。`
    },
    // s4: Sentence Analysis
    {
      id: 'e2',
      sentenceId: 's4',
      entryType: 'sentence_analysis',
      label: '句解',
      title: '长难句逻辑拆解',
      content: `## 结构拆解

1. **Those (who fail to adapt)** [主语 + 定语从句]
   - *Those*: 代词，指代上文提到的“不能适应的人”。
   - *who fail to adapt*: 限制性定语从句，修饰 Those。
2. **will find themselves** [谓语 + 宾语]
   - *find themselves*: 发现自己处于某种状态。
3. **increasingly marginalized** [宾语补足语]
   - *marginalized*: 过去分词作补足语，表示“被边缘化”。
4. **in the global marketplace** [地点状语]

## 关键要点

*Those who...* 是一种常见的泛指结构。注意 *marginalized* 在此处的被动含义及渐进色彩（increasingly）。`
    },
    // s5: Grammar Note
    {
      id: 'e3',
      sentenceId: 's5',
      entryType: 'grammar_note',
      label: '语法',
      title: 'Not Only...But Also 并列结构',
      content: `本句使用了 **not only...but also** 并列结构连接两个动名词短语：

- **adopting new technologies**: 采用新技术
- **fostering a culture...**: 培养一种文化

### 注意事项
1. **平行结构**：not only 和 but also 后接的成分必须语法形式一致（本句均为 V-ing）。
2. **重心偏移**：语气上更强调 but also 之后的内容。`
    },
  ],
  warnings: []
}

/**
 * SCENARIO_WARNINGS: 异常与警告场景
 */
export const SCENARIO_WARNINGS: RenderSceneModel = {
  ...SCENARIO_FULL,
  request: { ...requestMeta, requestId: 'req_warnings_demo' },
  warnings: [
    {
      code: 'anchor_resolve_failed',
      level: 'warning',
      message: '无法在句子 s1 中精确定位锚点 "paradigm shift"，已回退到模糊匹配。',
      sentenceId: 's1'
    },
    {
      code: 'overlap_conflict',
      level: 'info',
      message: '检测到 "paradigm" 与更长标注 "paradigm shift" 存在重叠，已优先展示长标注。',
      sentenceId: 's1'
    }
  ]
}

/**
 * SCENARIO_BASIC: 极简场景 (仅正文与翻译)
 */
export const SCENARIO_BASIC: RenderSceneModel = {
  schemaVersion: '2.1.0',
  request: { ...requestMeta, requestId: 'req_basic_demo' },
  article: {
    paragraphs: [{ paragraphId: 'p1', sentenceIds: ['s1'] }],
    sentences: [{ sentenceId: 's1', paragraphId: 'p1', text: 'Education is the most powerful weapon which you can use to change the world.' }],
  },
  translations: [{ sentenceId: 's1', translationZh: '教育是你可以用来改变世界的最强大的武器。' }],
  inlineMarks: [],
  sentenceEntries: [],
  warnings: []
}

// 导出默认场景
export const mockSceneData = SCENARIO_FULL

// 导出所有可用场景供切换
export const ALL_SCENARIOS = {
  '全功能演示': SCENARIO_FULL,
  '警告与异常': SCENARIO_WARNINGS,
  '纯净模式': SCENARIO_BASIC,
}

// 文章元数据
export const articleMeta = {
  title: 'Digital Transformation in Modern Era',
  source: 'Harvard Business Review',
  date: '2026-04-01',
  level: 'CET-6 / GRE',
}

// 页面模式配置
export const PAGE_MODE_OPTIONS = [
  { value: 'immersive', label: '沉浸', description: '专注阅读，极简标注' },
  { value: 'bilingual', label: '双语', description: '对照阅读，标准标注' },
  { value: 'intensive', label: '精读', description: '深度解析，全量标注' },
] as const
