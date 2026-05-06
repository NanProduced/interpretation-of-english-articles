import type {
  DailyReaderArticleDto,
  DailyReaderTodayResponseDto,
  DailyReaderListItemDto,
  DailyReaderListResponseDto,
} from '../../../types/api/daily-reader.dto'
import type {
  DailyReaderArticle,
  DailyReaderHighlight,
  DailyReaderListItem,
  DailyReaderFooterAnalysis,
} from '../../../types/view/daily-reader.vm'

function stripHtml(value: string | null): string | null {
  if (!value) return value
  return value.replace(/<[^>]+>/g, '').trim()
}

export function dtoToDailyReaderArticle(dto: DailyReaderArticleDto): DailyReaderArticle {
  return {
    id: dto.id,
    title: dto.title,
    subtitle: stripHtml(dto.subtitle),
    source: dto.source,
    sourceUrl: dto.source_url,
    publishDate: dto.publish_date,
    difficulty: dto.difficulty,
    readTimeMinutes: dto.read_time_minutes,
    tags: Array.isArray(dto.tags) ? dto.tags : [],
    coverImageUrl: dto.cover_image_url,
    coverTheme: dto.cover_theme,
    body: {
      paragraphs: Array.isArray(dto.body?.paragraphs)
        ? dto.body.paragraphs.map((p) => ({
            id: p.id,
            text: p.text,
            highlights: Array.isArray(p.highlights) ? p.highlights.map(dtoToHighlight) : [],
          }))
        : [],
    },
    highlights: Array.isArray(dto.highlights) ? dto.highlights.map(dtoToHighlight) : [],
    footerAnalysis: dtoToFooterAnalysis(dto.footer_analysis),
  }
}

export function dtoToDailyReaderListItem(dto: DailyReaderListItemDto): DailyReaderListItem {
  return {
    id: dto.id,
    title: dto.title,
    subtitle: stripHtml(dto.subtitle),
    source: dto.source,
    publishDate: dto.publish_date,
    difficulty: dto.difficulty,
    readTimeMinutes: dto.read_time_minutes,
    tags: dto.tags,
    coverImageUrl: dto.cover_image_url,
    coverTheme: dto.cover_theme,
  }
}

function dtoToHighlight(dto: DailyReaderArticleDto['highlights'][0]): DailyReaderHighlight {
  return {
    id: dto.id,
    type: dto.type,
    text: dto.text,
    gloss: dto.gloss,
    paragraphId: dto.paragraph_id,
    start: dto.start,
    end: dto.end,
    detail: dto.detail
      ? {
          phonetic: dto.detail.phonetic,
          pos: dto.detail.pos,
          contextExplanation: dto.detail.context_explanation,
        }
      : null,
  }
}

function dtoToFooterAnalysis(dto: DailyReaderArticleDto['footer_analysis']): DailyReaderFooterAnalysis {
  const thesisAndIntent = dto?.thesis_and_intent
  return {
    summary: dto?.summary ?? '',
    thesisAndIntent: {
      thesis: thesisAndIntent?.thesis ?? '',
      authorIntent: thesisAndIntent?.author_intent ?? '',
    },
    structure: Array.isArray(dto?.structure) ? dto.structure.map((s) => ({
      label: s.label,
      title: s.title,
      summary: s.summary,
    })) : [],
    keyExpressions: Array.isArray(dto?.key_expressions) ? dto.key_expressions.map((e) => ({
      expression: e.expression,
      gloss: e.gloss,
      contextSentence: e.context_sentence,
    })) : [],
    misreadingPoints: Array.isArray(dto?.misreading_points) ? dto.misreading_points.map((m) => ({
      point: m.point,
      clarification: m.clarification,
    })) : [],
    fullArticleAnalysis: dto?.full_article_analysis ?? '',
    discussionQuestions: Array.isArray(dto?.discussion_questions) ? dto.discussion_questions : [],
  }
}
