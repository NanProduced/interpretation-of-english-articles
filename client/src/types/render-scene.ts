/**
 * V3 统一渲染模型类型定义
 *
 * 对齐 docs/workflow/v3/workflow-v3-design.md
 * 版本号不进入业务命名
 */

// ============ 基础组件 ============

export interface TextAnchor {
  kind: 'text'
  sentenceId: string
  anchorText: string
  occurrence?: number
}

export interface SpanRef {
  text: string
  occurrence?: number
  role?: string
}

export interface MultiTextAnchor {
  kind: 'multi_text'
  sentenceId: string
  parts: SpanRef[]
}

export type InlineMarkAnchor = TextAnchor | MultiTextAnchor

// ============ LLM 附加说明 ============

export interface InlineGlossary {
  /** 对应 PhraseGloss.zh */
  zh?: string
  /** 对应 ContextGloss.gloss */
  gloss?: string
  /** 对应 ContextGloss.reason */
  reason?: string
}

// ============ Annotation 类型 ============

export type AnnotationType =
  | 'vocab_highlight'
  | 'phrase_gloss'
  | 'context_gloss'
  | 'grammar_note'

/** 渲染语义 */
export type VisualTone = 'vocab' | 'phrase' | 'context' | 'grammar'

export type RenderType = 'background' | 'underline'

// ============ 行内标注 ============

export interface InlineMarkModel {
  id: string
  /** 语义来源，用于前端识别业务逻辑 */
  annotationType: AnnotationType
  anchor: InlineMarkAnchor
  renderType: RenderType
  visualTone: VisualTone
  clickable: boolean
  /** 词典查询文本 */
  lookupText?: string
  /** 词典查询类型 */
  lookupKind?: 'word' | 'phrase'
  /** LLM 附加说明（结构化） */
  glossary?: InlineGlossary
  /** 考试标签（针对 vocab_highlight） */
  examTags?: string[]
}

// ============ 句尾入口 ============

/** v3 只保留这两类句尾入口 */
export type SentenceEntryType = 'grammar_note' | 'sentence_analysis'

export interface SentenceEntryModel {
  id: string
  sentenceId: string
  entryType: SentenceEntryType
  label: string
  title?: string
  content: string
}

// ============ 警告 ============

export type WarningLevel = 'info' | 'warning' | 'error'

export interface WarningModel {
  code: string
  level: WarningLevel
  message: string
  sentenceId?: string
  annotationId?: string
}

// ============ 文章结构 ============

export interface SentenceModel {
  sentenceId: string
  paragraphId: string
  text: string
}

export interface ParagraphModel {
  paragraphId: string
  sentenceIds: string[]
}

export interface ArticleModel {
  paragraphs: ParagraphModel[]
  sentences: SentenceModel[]
}

// ============ 翻译 ============

export interface TranslationModel {
  sentenceId: string
  translationZh: string
}

// ============ 请求元信息 ============

export interface RequestMeta {
  requestId: string
  sourceType: 'user_input' | 'daily_article' | 'ocr'
  readingGoal: string
  readingVariant: string
  profileId: string
}

// ============ 统一渲染模型 ============

export interface RenderSceneModel {
  schemaVersion: '3.0.0'
  request: RequestMeta
  article: ArticleModel
  translations: TranslationModel[]
  inlineMarks: InlineMarkModel[]
  sentenceEntries: SentenceEntryModel[]
  warnings: WarningModel[]
}

// ============ 页面模式 ============

export type PageMode = 'immersive' | 'bilingual' | 'intensive'

// ============ 词典结果 ============

export interface DictionaryMeaning {
  partOfSpeech: string
  definitions: Array<{
    meaning: string
    example?: string
    exampleTranslation?: string
  }>
}

export interface DictionaryResult {
  word: string
  phonetic?: string
  audioUrl?: string
  meanings: DictionaryMeaning[]
}
