export interface DailyReaderArticleDto {
  id: string
  title: string
  subtitle: string | null
  source: string
  source_url: string
  publish_date: string
  difficulty: string
  read_time_minutes: number
  tags: string[]
  cover_image_url: string | null
  cover_theme: string
  body: DailyReaderBodyDto
  highlights: DailyReaderHighlightDto[]
  footer_analysis: DailyReaderFooterAnalysisDto
}

export interface DailyReaderBodyDto {
  paragraphs: DailyReaderParagraphDto[]
}

export interface DailyReaderParagraphDto {
  id: string
  text: string
  highlights: DailyReaderHighlightDto[]
}

export interface DailyReaderHighlightDto {
  id: string
  type: 'vocab_highlight' | 'phrase_gloss' | 'context_gloss'
  text: string
  gloss: string
  paragraph_id: string
  start: number
  end: number
  detail?: {
    phonetic?: string
    pos?: string
    context_explanation?: string
  } | null
}

export interface DailyReaderFooterAnalysisDto {
  summary: string
  thesis_and_intent: {
    thesis: string
    author_intent: string
  }
  structure: DailyReaderStructurePartDto[]
  key_expressions: DailyReaderKeyExpressionDto[]
  misreading_points: DailyReaderMisreadingPointDto[]
  full_article_analysis: string
  discussion_questions: string[]
}

export interface DailyReaderStructurePartDto {
  label: string
  title: string
  summary: string
}

export interface DailyReaderKeyExpressionDto {
  expression: string
  gloss: string
  context_sentence: string
}

export interface DailyReaderMisreadingPointDto {
  point: string
  clarification: string
}

export interface DailyReaderTodayResponseDto {
  articles: DailyReaderArticleDto[]
}

export interface DailyReaderListItemDto {
  id: string
  title: string
  subtitle: string | null
  source: string
  publish_date: string
  difficulty: string
  read_time_minutes: number
  tags: string[]
  cover_image_url: string | null
  cover_theme: string
}

export interface DailyReaderListResponseDto {
  items: DailyReaderListItemDto[]
  cursor: string | null
  has_more: boolean
}
