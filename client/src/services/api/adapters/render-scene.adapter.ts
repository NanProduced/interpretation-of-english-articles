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
  TermNoteDto,
  LogicNoteDto,
  InterpretationNoteDto,
  ParagraphRoleDto,
  DocumentSummaryDto,
} from '@/types/api/analyze-response.dto'

import type {
  RenderSceneVmBase,
  AcademicRenderSceneVm,
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
  TermNoteModel,
  LogicNoteModel,
  InterpretationNoteModel,
  ParagraphRoleModel,
  DocumentSummaryModel,
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
          phraseType: mark.glossary.phrase_type,
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
    paragraphs: (article.paragraphs ?? []).map(transformParagraph),
    sentences: (article.sentences ?? []).map(transformSentence),
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
 * 转换 TermNote
 */
function transformTermNote(note: TermNoteDto): TermNoteModel {
  return {
    type: note.type,
    sentenceId: note.sentence_id,
    text: note.text,
    occurrence: note.occurrence,
    category: note.category,
    termZh: note.term_zh,
    definition: note.definition,
    contextHint: note.context_hint,
  }
}

/**
 * 转换 LogicNote
 */
function transformLogicNote(note: LogicNoteDto): LogicNoteModel {
  return {
    type: note.type,
    sentenceId: note.sentence_id,
    spans: note.spans.map((s: SpanRefPart) => ({
      anchorText: s.anchor_text,
      occurrence: s.occurrence,
      role: s.role,
    })),
    relation: note.relation,
    label: note.label,
    explanationZh: note.explanation_zh,
  }
}

/**
 * 转换 InterpretationNote
 */
function transformInterpretationNote(note: InterpretationNoteDto): InterpretationNoteModel {
  return {
    type: note.type,
    sentenceId: note.sentence_id,
    spans: note.spans?.map((s: SpanRefPart) => ({
      anchorText: s.anchor_text,
      occurrence: s.occurrence,
      role: s.role,
    })),
    literalTranslation: note.literal_translation,
    intendedMeaningZh: note.intended_meaning_zh,
    whyNotLiteral: note.why_not_literal,
    rhetoricalPurpose: note.rhetorical_purpose,
  }
}

/**
 * 转换 ParagraphRole
 */
function transformParagraphRole(role: ParagraphRoleDto): ParagraphRoleModel {
  return {
    type: role.type,
    paragraphId: role.paragraph_id,
    role: role.role,
    label: role.label,
    summaryZh: role.summary_zh,
    keyClaim: role.key_claim,
  }
}

/**
 * 转换 DocumentSummary
 */
function transformDocumentSummary(summary: DocumentSummaryDto | undefined): DocumentSummaryModel | undefined {
  if (!summary) return undefined
  return {
    type: summary.type,
    researchProblemZh: summary.research_problem_zh,
    methodologyZh: summary.methodology_zh,
    keyFindingsZh: summary.key_findings_zh,
    limitationsZh: summary.limitations_zh,
    overallSignificanceZh: summary.overall_significance_zh,
  }
}

/**
 * 转换完整响应
 * 唯一转换点，snake_case -> camelCase
 * 返回 RenderSceneVm 或 AcademicRenderSceneVm
 */
export function analyzeResponseDtoToVm(dto: AnalyzeResponseDto): RenderSceneVmBase | AcademicRenderSceneVm {
  const base = {
    schemaVersion: dto.schema_version as RenderSceneVmBase['schemaVersion'],
    request: transformRequestMeta(dto.request),
    article: transformArticle(dto.article),
    userFacingState: dto.user_facing_state,
    translations: (dto.translations ?? []).map(transformTranslation),
    inlineMarks: (dto.inline_marks ?? []).map(transformInlineMark),
    sentenceEntries: (dto.sentence_entries ?? []).map(transformSentenceEntry),
    warnings: (dto.warnings ?? []).map(transformWarning),
  }

  const hasAcademicFields = 
    (dto.term_notes && dto.term_notes.length > 0) ||
    (dto.logic_notes && dto.logic_notes.length > 0) ||
    (dto.interpretation_notes && dto.interpretation_notes.length > 0) ||
    (dto.paragraph_roles && dto.paragraph_roles.length > 0) ||
    dto.document_summary

  if (hasAcademicFields) {
    return {
      ...base,
      termNotes: (dto.term_notes ?? []).map(transformTermNote),
      logicNotes: (dto.logic_notes ?? []).map(transformLogicNote),
      interpretationNotes: (dto.interpretation_notes ?? []).map(transformInterpretationNote),
      paragraphRoles: (dto.paragraph_roles ?? []).map(transformParagraphRole),
      documentSummary: transformDocumentSummary(dto.document_summary),
    }
  }

  return base
}

/**
 * 反向转换 InlineMarkAnchor (vm -> dto)
 */
function reverseAnchor(vmAnchor: VmTextAnchor | VmMultiTextAnchor): DtoTextAnchor | DtoMultiTextAnchor {
  if (vmAnchor.kind === 'text') {
    const a = vmAnchor as VmTextAnchor
    return {
      kind: 'text',
      sentence_id: a.sentenceId,
      anchor_text: a.anchorText,
      occurrence: a.occurrence,
    }
  } else {
    const a = vmAnchor as VmMultiTextAnchor
    return {
      kind: 'multi_text',
      sentence_id: a.sentenceId,
      parts: a.parts.map((p: SpanRef) => ({
        anchor_text: p.anchorText,
        occurrence: p.occurrence,
        role: p.role,
      })),
    }
  }
}

/**
 * 反向转换 InlineMark (vm -> dto)
 */
function reverseInlineMark(mark: InlineMarkModel): DtoInlineMark {
  return {
    id: mark.id,
    annotation_type: mark.annotationType,
    anchor: reverseAnchor(mark.anchor),
    render_type: mark.renderType,
    visual_tone: mark.visualTone,
    clickable: mark.clickable,
    lookup_text: mark.lookupText,
    lookup_kind: mark.lookupKind as 'word' | 'phrase' | undefined,
    glossary: mark.glossary
      ? {
          zh: mark.glossary.zh,
          gloss: mark.glossary.gloss,
          reason: mark.glossary.reason,
          phrase_type: mark.glossary.phraseType,
        }
      : undefined,
  }
}

/**
 * 反向转换 SentenceEntry (vm -> dto)
 */
function reverseSentenceEntry(entry: SentenceEntryModel): SentenceEntry {
  return {
    id: entry.id,
    sentence_id: entry.sentenceId,
    entry_type: entry.entryType,
    label: entry.label,
    title: entry.title,
    content: entry.content,
  }
}

/**
 * 反向转换 Warning (vm -> dto)
 */
function reverseWarning(warning: WarningModel): Warning {
  return {
    code: warning.code,
    level: warning.level,
    message: warning.message,
    sentence_id: warning.sentenceId,
    annotation_id: warning.annotationId,
  }
}

/**
 * 反向转换 TranslationItem (vm -> dto)
 */
function reverseTranslation(item: TranslationModel): TranslationItem {
  return {
    sentence_id: item.sentenceId,
    translation_zh: item.translationZh,
  }
}

/**
 * 反向转换 ArticleSentence (vm -> dto)
 */
function reverseSentence(sentence: SentenceModel): ArticleSentence {
  return {
    sentence_id: sentence.sentenceId,
    paragraph_id: sentence.paragraphId,
    text: sentence.text,
    sentence_span: { start: 0, end: 0 },
  }
}

/**
 * 反向转换 ArticleParagraph (vm -> dto)
 */
function reverseParagraph(paragraph: ParagraphModel): ArticleParagraph {
  return {
    paragraph_id: paragraph.paragraphId,
    text: '',
    render_span: { start: 0, end: 0 },
    sentence_ids: paragraph.sentenceIds,
  }
}

/**
 * 反向转换 RequestMeta (vm -> dto)
 */
function reverseRequestMeta(meta: RequestMeta): AnalyzeRequestMeta {
  return {
    request_id: meta.requestId,
    source_type: meta.sourceType,
    reading_goal: meta.readingGoal as AnalyzeRequestMeta['reading_goal'],
    reading_variant: meta.readingVariant as AnalyzeRequestMeta['reading_variant'],
    profile_id: meta.profileId,
  }
}

/**
 * 反向转换完整响应
 * camelCase VM -> snake_case DTO
 * 用于前端保存记录到云端时，确保 render_scene_json 与后端输出格式一致
 */
export function vmToAnalyzeResponseDto(vm: RenderSceneVmBase): AnalyzeResponseDto {
  return {
    schema_version: vm.schemaVersion,
    request: reverseRequestMeta(vm.request),
    article: {
      source_type: vm.request.sourceType,
      source_text: '',
      render_text: '',
      paragraphs: (vm.article.paragraphs ?? []).map(reverseParagraph),
      sentences: (vm.article.sentences ?? []).map(reverseSentence),
    },
    user_facing_state: vm.userFacingState,
    translations: (vm.translations ?? []).map(reverseTranslation),
    inline_marks: (vm.inlineMarks ?? []).map(reverseInlineMark),
    sentence_entries: (vm.sentenceEntries ?? []).map(reverseSentenceEntry),
    warnings: (vm.warnings ?? []).map(reverseWarning),
  }
}
