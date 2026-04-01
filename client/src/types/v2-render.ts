/**
 * V2 统一渲染模型类型定义
 * 基于 docs/workflow/v2/v2-unified-design.md
 */

// ============ 锚点模型 ============

/** 单段文本锚点 */
export type TextAnchorModel = {
  kind: 'text'
  sentenceId: string
  anchorText: string
  occurrence?: number
}

/** 多段文本锚点（用于 so...that, not only...but also 等不连续结构） */
export type MultiTextAnchorModel = {
  kind: 'multi_text'
  sentenceId: string
  parts: Array<{
    anchorText: string
    occurrence?: number
    role?: string
  }>
}

/** 句级锚点 */
export type SentenceAnchorModel = {
  kind: 'sentence'
  sentenceId: string
}

/** 段间插入锚点 */
export type BetweenSentenceAnchorModel = {
  kind: 'after_sentence'
  afterSentenceId: string
}

export type AnchorModel =
  | TextAnchorModel
  | MultiTextAnchorModel
  | SentenceAnchorModel
  | BetweenSentenceAnchorModel

// ============ 标注原语 ============

export type InlineMarkTone = 'info' | 'focus' | 'exam' | 'phrase' | 'grammar'
export type InlineMarkRenderType = 'background' | 'underline'

export type InlineMarkModel = {
  id: string
  renderType: InlineMarkRenderType
  anchor: TextAnchorModel | MultiTextAnchorModel
  tone: InlineMarkTone
  /** clickable=true 时点击进入 WordPopup */
  clickable: boolean
  /** AI 补充说明（可选）- 点击 popup 后显示在 AI Tab */
  aiNote?: string
  /** _lookupText: 要查询的文本（可选，默认使用 anchorText） */
  lookupText?: string
  /** 查询类型（可选） */
  lookupKind?: 'word' | 'phrase'
  /** AI 补充标题（可选） */
  aiTitle?: string
  /** AI 补充正文（可选） */
  aiBody?: string
}

// ============ 句尾入口 ============

export type SentenceEntryType = 'grammar' | 'sentence_analysis' | 'context'

export type SentenceTailEntryModel = {
  id: string
  /** Chip 显示文案 */
  label: string
  /** 详情面板标题（可选，默认使用 label） */
  title?: string
  anchor: SentenceAnchorModel
  type: SentenceEntryType
  /** 详情内容，支持 Markdown 格式（必填） */
  content: string
}

// ============ 段间卡片 ============

export type AnalysisCardModel = {
  id: string
  anchor: BetweenSentenceAnchorModel
  title: string
  content: string
  /** 展开状态 */
  expanded?: boolean
}

// ============ 文章结构 ============

export type SentenceModel = {
  sentenceId: string
  paragraphId: string
  text: string
}

export type ParagraphModel = {
  paragraphId: string
  sentenceIds: string[]
}

export type ArticleModel = {
  paragraphs: ParagraphModel[]
  sentences: SentenceModel[]
}

// ============ 翻译 ============

export type TranslationModel = {
  sentenceId: string
  translationZh: string
}

// ============ 统一渲染模型 ============

export type RenderSceneModel = {
  article: ArticleModel
  translations: TranslationModel[]
  inlineMarks: InlineMarkModel[]
  sentenceEntries: SentenceTailEntryModel[]
  cards: AnalysisCardModel[]
}

// ============ 页面模式 ============

export type PageMode = 'immersive' | 'bilingual' | 'intensive'

// ============ 词典结果 ============

export type DictionaryResult = {
  word: string
  phonetic?: string
  audioUrl?: string
  meanings: Array<{
    partOfSpeech: string
    definitions: Array<{
      meaning: string
      example?: string
      exampleTranslation?: string
    }>
  }>
}
