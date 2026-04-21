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

export function dtoToDailyReaderArticle(dto: DailyReaderArticleDto): DailyReaderArticle {
  return {
    id: dto.id,
    title: dto.title,
    subtitle: dto.subtitle,
    source: dto.source,
    sourceUrl: dto.source_url,
    publishDate: dto.publish_date,
    difficulty: dto.difficulty,
    readTimeMinutes: dto.read_time_minutes,
    tags: dto.tags,
    coverImageUrl: dto.cover_image_url,
    coverTheme: dto.cover_theme,
    body: {
      paragraphs: dto.body.paragraphs.map((p) => ({
        id: p.id,
        text: p.text,
        highlights: p.highlights.map(dtoToHighlight),
      })),
    },
    highlights: dto.highlights.map(dtoToHighlight),
    footerAnalysis: dtoToFooterAnalysis(dto.footer_analysis),
  }
}

export function dtoToDailyReaderListItem(dto: DailyReaderListItemDto): DailyReaderListItem {
  return {
    id: dto.id,
    title: dto.title,
    subtitle: dto.subtitle,
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
  return {
    summary: dto.summary,
    thesisAndIntent: {
      thesis: dto.thesis_and_intent.thesis,
      authorIntent: dto.thesis_and_intent.author_intent,
    },
    structure: dto.structure.map((s) => ({
      label: s.label,
      title: s.title,
      summary: s.summary,
    })),
    keyExpressions: dto.key_expressions.map((e) => ({
      expression: e.expression,
      gloss: e.gloss,
      contextSentence: e.context_sentence,
    })),
    misreadingPoints: dto.misreading_points.map((m) => ({
      point: m.point,
      clarification: m.clarification,
    })),
    fullArticleAnalysis: dto.full_article_analysis,
    discussionQuestions: dto.discussion_questions,
  }
}
