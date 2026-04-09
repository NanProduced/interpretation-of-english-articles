/**
 * 前端渲染 VM
 *
 * 严格对齐 UI 需求，禁止引入后端 concerns
 * 这是前端唯一正式的渲染模型输入
 *
 * 基于 client/src/types/render-scene.ts 重构，明确 VM 边界
 */

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

export interface InlineGlossary {
  zh?: string
  gloss?: string
  reason?: string
}

export type AnnotationType =
  | 'vocab_highlight'
  | 'phrase_gloss'
  | 'context_gloss'
  | 'grammar_note'

export type VisualTone = 'vocab' | 'phrase' | 'context' | 'grammar'

export type RenderType = 'background' | 'underline'

export type PhraseKind = 
  | 'word' 
  | 'phrase' 
  | 'collocation' 
  | 'phrasal_verb' 
  | 'idiom' 
  | 'proper_noun' 
  | 'compound'

export interface InlineMarkModel {
  id: string
  annotationType: AnnotationType
  anchor: InlineMarkAnchor
  renderType: RenderType
  visualTone: VisualTone
  clickable: boolean
  lookupText?: string
  lookupKind?: PhraseKind
  glossary?: InlineGlossary
  parentId?: string
}

export type SentenceEntryType = 'grammar_note' | 'sentence_analysis'

export interface SentenceEntryModel {
  id: string
  sentenceId: string
  entryType: SentenceEntryType
  label: string
  title?: string
  content: string
}

export type WarningLevel = 'info' | 'warning' | 'error'

export interface WarningModel {
  code: string
  level: WarningLevel
  message: string
  sentenceId?: string
  annotationId?: string
}

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

export interface TranslationModel {
  sentenceId: string
  translationZh: string
}

export interface RequestMeta {
  requestId: string
  sourceType: 'user_input'
  readingGoal: string
  readingVariant: string
  profileId: string
}

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

export type RenderSceneVm = RenderSceneVmBase

export type ContentResultState = 'normal' | 'degraded_light' | 'degraded_heavy'

export type ResultPageState =
  | 'loading'
  | 'normal'
  | 'degraded_light'
  | 'degraded_heavy'
  | 'empty'
  | 'failed'
  | 'timeout'
  | 'network_fail'

export type PageMode = 'immersive' | 'intensive'

export interface DictionaryMeaning {
  partOfSpeech: string
  definitions: Array<{
    meaning: string
    example?: string
    exampleTranslation?: string
  }>
}

export interface DictionaryExample {
  example: string
  exampleTranslation?: string
}

export interface DictionaryPhrase {
  phrase: string
  meaning?: string
}

export interface DictionaryEntryPayload {
  id: number
  word: string
  baseWord?: string
  homographNo?: number
  phonetic?: string
  primaryPos?: string
  meanings: DictionaryMeaning[]
  examples: DictionaryExample[]
  phrases: DictionaryPhrase[]
  entryKind: 'entry' | 'fragment'
}

export interface DictionaryCandidate {
  entryId: number
  label: string
  partOfSpeech?: string
  preview?: string
  entryKind: 'entry' | 'fragment'
}

interface DictionaryResultBase {
  resultType: 'entry' | 'disambiguation'
  query: string
  provider?: string
  cached?: boolean
}

export interface DictionaryEntryResult extends DictionaryResultBase {
  resultType: 'entry'
  entry: DictionaryEntryPayload
}

export interface DictionaryDisambiguationResult extends DictionaryResultBase {
  resultType: 'disambiguation'
  candidates: DictionaryCandidate[]
}

export type DictionaryResult = DictionaryEntryResult | DictionaryDisambiguationResult
