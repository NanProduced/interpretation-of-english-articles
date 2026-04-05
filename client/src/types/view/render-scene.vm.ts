/**
 * 前端渲染 VM
 *
 * 严格对齐 UI 需求，禁止引入后端 concerns
 * 这是前端唯一正式的渲染模型输入
 *
 * 基于 client/src/types/render-scene.ts 重构，明确 VM 边界
 */

// ============ 基础组件 ============

export interface TextAnchor {
  kind: 'text'
  sentenceId: string
  anchorText: string
  occurrence?: number
}

export interface SpanRef {
  anchorText: string
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
  zh?: string
  gloss?: string
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
  /** 父标注 ID（用于 multi_text 拆分后的部分标注） */
  parentId?: string
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

/**
 * 请求元信息
 *
 * 注意：当前联调范围仅限 sourceType = 'user_input'
 * daily_article / ocr 不在本联调范围内
 */
export interface RequestMeta {
  requestId: string
  /** 当前联调范围: 仅限 user_input */
  sourceType: 'user_input'
  readingGoal: string
  readingVariant: string
  profileId: string
}

// ============ 统一渲染模型 ============

/** 仅字段映射，不含业务派生字段（由 adapter 使用） */
export interface RenderSceneVmBase {
  schemaVersion: '3.0.0'
  request: RequestMeta
  article: ArticleModel
  userFacingState: ContentResultState
  translations: TranslationModel[]
  inlineMarks: InlineMarkModel[]
  sentenceEntries: SentenceEntryModel[]
  warnings: WarningModel[]
}

/** 完整渲染模型 */
export type RenderSceneVm = RenderSceneVmBase

// ============ 用户可见状态 ============

/**
 * 内容质量状态（snake_case 语义映射）
 * 用于 success/empty 态，反映内容本身的质量
 */
export type ContentResultState = 'normal' | 'degraded_light' | 'degraded_heavy'

/**
 * 页面级状态（唯一的状态入口）
 * - loading: 初始/请求中
 * - ContentResultState: 内容结果（normal/degraded_light/degraded_heavy/empty）
 * - failed/timeout/network_fail: 错误态
 */
export type ResultPageState =
  | 'loading'
  | 'normal'
  | 'degraded_light'
  | 'degraded_heavy'
  | 'empty'
  | 'failed'
  | 'timeout'
  | 'network_fail'

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
