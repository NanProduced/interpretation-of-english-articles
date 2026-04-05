/**
 * RenderScene Adapter
 *
 * 唯一转换点: AnalyzeResponseDto (snake_case) -> RenderSceneVm (camelCase)
 *
 * 约束:
 * - 只做字段映射 + 轻量结构适配
 * - 禁止在此文件引入业务逻辑
 * - 禁止在其他任何位置做字段转换
 */

import type {
  AnalyzeResponseDto,
  InlineMark as DtoInlineMark,
  TextAnchor as DtoTextAnchor,
  MultiTextAnchor as DtoMultiTextAnchor,
  SpanRefPart,
  ArticleSentence,
  ArticleParagraph,
  ArticleStructure,
  TranslationItem,
  SentenceEntry,
  Warning,
  AnalyzeRequestMeta,
} from '@/types/api/analyze-response.dto'

import type {
  RenderSceneVmBase,
  InlineMarkModel,
  TextAnchor as VmTextAnchor,
  MultiTextAnchor as VmMultiTextAnchor,
  SpanRef,
  SentenceModel,
  ParagraphModel,
  ArticleModel,
  TranslationModel,
  SentenceEntryModel,
  WarningModel,
  RequestMeta,
} from '@/types/view/render-scene.vm'

/**
 * 转换 InlineMarkAnchor (dto -> vm)
 */
function transformAnchor(dtoAnchor: DtoTextAnchor | DtoMultiTextAnchor): VmTextAnchor | VmMultiTextAnchor {
  if (dtoAnchor.kind === 'text') {
    const a = dtoAnchor as DtoTextAnchor
    return {
      kind: 'text',
      sentenceId: a.sentence_id,
      anchorText: a.anchor_text,
      occurrence: a.occurrence,
    }
  } else {
    const a = dtoAnchor as DtoMultiTextAnchor
    return {
      kind: 'multi_text',
      sentenceId: a.sentence_id,
      parts: a.parts.map((p: SpanRefPart) => ({
        anchorText: p.anchor_text,
        occurrence: p.occurrence,
        role: p.role,
      })),
    }
  }
}

/**
 * 转换 InlineMark
 */
function transformInlineMark(mark: DtoInlineMark): InlineMarkModel {
  return {
    id: mark.id,
    annotationType: mark.annotation_type,
    anchor: transformAnchor(mark.anchor),
    renderType: mark.render_type,
    visualTone: mark.visual_tone,
    clickable: mark.clickable,
    lookupText: mark.lookup_text,
    lookupKind: mark.lookup_kind,
    glossary: mark.glossary
      ? {
          zh: mark.glossary.zh,
          gloss: mark.glossary.gloss,
          reason: mark.glossary.reason,
        }
      : undefined,
  }
}

/**
 * 转换 SentenceEntry
 */
function transformSentenceEntry(entry: SentenceEntry): SentenceEntryModel {
  return {
    id: entry.id,
    sentenceId: entry.sentence_id,
    entryType: entry.entry_type,
    label: entry.label,
    title: entry.title,
    content: entry.content,
  }
}

/**
 * 转换 Warning
 */
function transformWarning(warning: Warning): WarningModel {
  return {
    code: warning.code,
    level: warning.level,
    message: warning.message,
    sentenceId: warning.sentence_id,
    annotationId: warning.annotation_id,
  }
}

/**
 * 转换 TranslationItem
 */
function transformTranslation(item: TranslationItem): TranslationModel {
  return {
    sentenceId: item.sentence_id,
    translationZh: item.translation_zh,
  }
}

/**
 * 转换 ArticleSentence
 */
function transformSentence(sentence: ArticleSentence): SentenceModel {
  return {
    sentenceId: sentence.sentence_id,
    paragraphId: sentence.paragraph_id,
    text: sentence.text,
  }
}

/**
 * 转换 ArticleParagraph
 */
function transformParagraph(paragraph: ArticleParagraph): ParagraphModel {
  return {
    paragraphId: paragraph.paragraph_id,
    sentenceIds: paragraph.sentence_ids,
  }
}

/**
 * 转换 ArticleStructure
 */
function transformArticle(article: ArticleStructure): ArticleModel {
  return {
    paragraphs: article.paragraphs.map(transformParagraph),
    sentences: article.sentences.map(transformSentence),
  }
}

/**
 * 转换 AnalyzeRequestMeta
 */
function transformRequestMeta(meta: AnalyzeRequestMeta): RequestMeta {
  return {
    requestId: meta.request_id,
    sourceType: meta.source_type as 'user_input',
    readingGoal: meta.reading_goal,
    readingVariant: meta.reading_variant,
    profileId: meta.profile_id,
  }
}

/**
 * 转换完整响应
 * 唯一转换点，snake_case -> camelCase
 * 返回 RenderSceneVmBase
 */
export function analyzeResponseDtoToVm(dto: AnalyzeResponseDto): RenderSceneVmBase {
  return {
    schemaVersion: dto.schema_version as RenderSceneVmBase['schemaVersion'],
    request: transformRequestMeta(dto.request),
    article: transformArticle(dto.article),
    userFacingState: dto.user_facing_state,
    translations: dto.translations.map(transformTranslation),
    inlineMarks: dto.inline_marks.map(transformInlineMark),
    sentenceEntries: dto.sentence_entries.map(transformSentenceEntry),
    warnings: dto.warnings.map(transformWarning),
  }
}
