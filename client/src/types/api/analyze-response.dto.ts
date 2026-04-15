/**
 * 后端响应 DTO
 *
 * 严格对齐后端 RenderSceneModel schema (snake_case)
 * 禁止在此文件引入 UI concerns
 *
 * @see server/app/schemas/analysis.py::RenderSceneModel
 */

/** 后端 schema 版本 */
export const BACKEND_SCHEMA_VERSION = '3.0.0' as const

// ============ 基础类型 ============

export interface TextSpan {
  start: number
  end: number
}

// ============ 请求元信息 ============

export type SourceType = 'user_input' | 'daily_article' | 'ocr'
export type ReadingGoal = 'exam' | 'daily_reading' | 'academic'
export type ReadingVariant =
  | 'gaokao' | 'cet' | 'kaoyan' | 'tem' | 'ielts_toefl'
  | 'beginner_reading' | 'intermediate_reading' | 'intensive_reading'
  | 'academic_general'

export interface AnalyzeRequestMeta {
  request_id: string
  source_type: SourceType
  reading_goal: ReadingGoal
  reading_variant: ReadingVariant
  profile_id: string
}

// ============ 文章结构 ============

export interface ArticleSentence {
  sentence_id: string
  paragraph_id: string
  text: string
  sentence_span: TextSpan
}

export interface ArticleParagraph {
  paragraph_id: string
  text: string
  render_span: TextSpan
  sentence_ids: string[]
}

export interface ArticleStructure {
  source_type: SourceType
  source_text: string
  render_text: string
  paragraphs: ArticleParagraph[]
  sentences: ArticleSentence[]
}

// ============ 行内标注 ============

export type InlineMarkRenderType = 'background' | 'underline'
export type VisualTone = 'vocab' | 'phrase' | 'context' | 'grammar'
export type AnnotationType = 'vocab_highlight' | 'phrase_gloss' | 'context_gloss' | 'grammar_note'

export interface InlineGlossary {
  zh?: string
  gloss?: string
  reason?: string
  phrase_type?: 'collocation' | 'phrasal_verb' | 'idiom' | 'proper_noun' | 'compound'
}

export interface TextAnchor {
  kind: 'text'
  sentence_id: string
  anchor_text: string
  occurrence?: number
}

export interface SpanRefPart {
  anchor_text: string
  occurrence?: number
  role?: string
}

export interface MultiTextAnchor {
  kind: 'multi_text'
  sentence_id: string
  parts: SpanRefPart[]
}

export type InlineMarkAnchor = TextAnchor | MultiTextAnchor

export interface InlineMark {
  id: string
  annotation_type: AnnotationType
  anchor: InlineMarkAnchor
  render_type: InlineMarkRenderType
  visual_tone: VisualTone
  clickable: boolean
  lookup_text?: string
  lookup_kind?: 'word' | 'phrase'
  glossary?: InlineGlossary
}

// ============ 句尾入口 ============

export type SentenceEntryType = 'grammar_note' | 'sentence_analysis'

export interface SentenceEntry {
  id: string
  sentence_id: string
  entry_type: SentenceEntryType
  label: string
  title?: string
  content: string
}

// ============ 警告 ============

export type WarningLevel = 'info' | 'warning' | 'error'

export interface Warning {
  code: string
  level: WarningLevel
  message: string
  sentence_id?: string
  annotation_id?: string
}

// ============ 翻译 ============

export interface TranslationItem {
  sentence_id: string
  translation_zh: string
}

// ============ 页面状态 ============

export type UserFacingState = 'normal' | 'degraded_light' | 'degraded_heavy'

// ============ Academic 场景类型 ============

export type TermCategory =
  | 'technical_term'
  | 'abbreviation'
  | 'variable'
  | 'method_name'
  | 'concept'
  | 'concept_opposition'
  | 'proper_noun'

export type LogicRelation =
  | 'contrast'
  | 'concession'
  | 'qualification'
  | 'causation'
  | 'comparison'
  | 'hypothesis'
  | 'conclusion'
  | 'condition'
  | 'addition'
  | 'sequence'

export type ParagraphRoleType =
  | 'definition'
  | 'background'
  | 'problem_statement'
  | 'methodology'
  | 'evidence'
  | 'result'
  | 'limitation'
  | 'transition'
  | 'discussion'
  | 'conclusion'

export interface TermNoteDto {
  type: 'term_note'
  sentence_id: string
  text: string
  occurrence?: number
  category: TermCategory
  term_zh: string
  definition?: string
  context_hint?: string
}

export interface LogicNoteDto {
  type: 'logic_note'
  sentence_id: string
  spans: SpanRefPart[]
  relation: LogicRelation
  label: string
  explanation_zh: string
}

export interface InterpretationNoteDto {
  type: 'interpretation_note'
  sentence_id: string
  spans?: SpanRefPart[]
  literal_translation?: string
  intended_meaning_zh: string
  why_not_literal?: string
  rhetorical_purpose?: string
}

export interface ParagraphRoleDto {
  type: 'paragraph_role'
  paragraph_id: string
  role: ParagraphRoleType
  label: string
  summary_zh: string
  key_claim?: string
}

export interface DocumentSummaryDto {
  type: 'document_summary'
  research_problem_zh?: string
  methodology_zh?: string
  key_findings_zh?: string
  limitations_zh?: string
  overall_significance_zh?: string
}

// ============ 完整响应 ============

export interface AnalyzeResponseDto {
  schema_version: typeof BACKEND_SCHEMA_VERSION
  request: AnalyzeRequestMeta
  article: ArticleStructure
  user_facing_state: UserFacingState
  translations: TranslationItem[]
  inline_marks: InlineMark[]
  sentence_entries: SentenceEntry[]
  warnings: Warning[]
  term_notes?: TermNoteDto[]
  logic_notes?: LogicNoteDto[]
  interpretation_notes?: InterpretationNoteDto[]
  paragraph_roles?: ParagraphRoleDto[]
  document_summary?: DocumentSummaryDto
}
