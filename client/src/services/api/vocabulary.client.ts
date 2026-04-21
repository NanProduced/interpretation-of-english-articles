/**
 * Cloud API: Vocabulary Book
 *
 * 对应后端 GET/POST/PATCH/DELETE /vocabulary
 * 需要认证，自动附带 Authorization header
 *
 * 扩展：艾宾浩斯遗忘曲线复习系统
 * - /vocabulary/review-stats: 复习统计
 * - /vocabulary/due: 待复习单词列表
 * - /vocabulary/review: 提交复习结果
 */

import { request } from './client'
import type {
  VocabEntry,
  SourceRef,
  VocabHighlightMatch,
  ReviewStats,
  DueVocabItem,
  ReviewSubmitResult,
} from '../../types/view/vocabulary.vm'

// ---------------------------------------------------------------------------
// 后端 DTO（snake_case）
// ---------------------------------------------------------------------------

interface VocabularyResponseDto {
  id: string
  user_id: string
  lemma: string
  display_word: string
  phonetic: string | null
  part_of_speech: string | null
  short_meaning: string
  meanings_json?: Array<Record<string, unknown>>
  tags: string[]
  exchange: string[]
  source_provider: string
  dict_entry_id: number | null
  source_sentence?: string | null
  source_context?: string | null
  mastery_status: string
  review_count: number
  last_reviewed_at: string | null
  next_review_at: string | null
  ease_factor: number
  repetitions: number
  review_interval: number
  payload_json?: Record<string, unknown>
  created_at: string
  updated_at: string
}

interface VocabularyListDto {
  items: VocabularyResponseDto[]
  total: number
  page: number
  limit: number
}

interface VocabularyUpsertDto {
  id: string
  lemma: string
  created: boolean
  updated_at: string
}

function parseSourceRefs(payload: Record<string, unknown> | undefined): SourceRef[] {
  if (!payload?.source_refs || !Array.isArray(payload.source_refs)) return []
  return payload.source_refs.map((ref: any) => ({
    clientRecordId: ref.client_record_id || '',
    cloudRecordId: ref.cloud_record_id || undefined,
    sourceSentence: ref.source_sentence || undefined,
    sourceContext: ref.source_context || undefined,
    sourceSentenceId: ref.source_sentence_id || undefined,
    sourceAnchorText: ref.source_anchor_text || undefined,
    sourceOccurrence: ref.source_occurrence || undefined,
    collectedAt: ref.collected_at || undefined,
  }))
}

function dtoToVm(dto: VocabularyResponseDto): VocabEntry {
  const detailMeanings = Array.isArray(dto.meanings_json)
    ? dto.meanings_json.map((m: any) => ({
        pos: m.partOfSpeech || m.part_of_speech || '',
        definitions: Array.isArray(m.definitions)
          ? m.definitions.map((d: any) => d.meaning || d)
          : [],
      })).filter(m => m.definitions.length > 0)
    : undefined

  const payload = dto.payload_json || {}
  const sourceRefs = parseSourceRefs(payload as Record<string, unknown>)
  const collectedForms = Array.isArray(payload.collected_forms)
    ? payload.collected_forms as string[]
    : []
  const audioUrl = (payload as Record<string, unknown>).audio_url as string | undefined

  return {
    id: dto.id,
    word: dto.display_word,
    lemma: dto.lemma,
    phonetic: dto.phonetic || undefined,
    partOfSpeech: dto.part_of_speech || '',
    meaning: dto.short_meaning,
    addedAt: new Date(dto.created_at).getTime(),
    mastered: dto.mastery_status === 'mastered',
    dictEntryId: dto.dict_entry_id ?? undefined,
    detailMeanings,
    tags: dto.tags,
    exchange: dto.exchange,
    provider: dto.source_provider,
    sentence: dto.source_sentence || undefined,
    context: dto.source_context || undefined,
    sourceRefs,
    collectedForms,
    audioUrl,
    masteryStatus: dto.mastery_status as VocabEntry['masteryStatus'],
    reviewCount: dto.review_count,
    lastReviewedAt: dto.last_reviewed_at ? new Date(dto.last_reviewed_at).getTime() : undefined,
    nextReviewAt: dto.next_review_at ? new Date(dto.next_review_at).getTime() : undefined,
    easeFactor: dto.ease_factor,
    repetitions: dto.repetitions,
    reviewInterval: dto.review_interval,
  }
}

// ---------------------------------------------------------------------------
// API 调用
// ---------------------------------------------------------------------------

export async function fetchCloudVocabulary(
  page = 1,
  limit = 50,
  masteryStatus?: string
): Promise<{ items: VocabEntry[]; total: number }> {
  let url = `/vocabulary?page=${page}&limit=${limit}`
  if (masteryStatus) url += `&mastery_status=${masteryStatus}`
  const res = await request<VocabularyListDto>({ url })
  return {
    items: res.items.map(dtoToVm),
    total: res.total,
  }
}

export async function addVocabToCloud(
  entry: VocabEntry
): Promise<{ id: string; created: boolean }> {
  const sourceRefs = (entry.sourceRefs || []).map(ref => ({
    client_record_id: ref.clientRecordId,
    cloud_record_id: ref.cloudRecordId || null,
    source_sentence: ref.sourceSentence || null,
    source_context: ref.sourceContext || null,
    source_sentence_id: ref.sourceSentenceId || null,
    source_anchor_text: ref.sourceAnchorText || null,
    source_occurrence: ref.sourceOccurrence || null,
    collected_at: ref.collectedAt || null,
  }))

  const payloadJson: Record<string, unknown> = {
    source_refs: sourceRefs,
    collected_forms: entry.collectedForms || [entry.word],
  }
  if (entry.audioUrl) {
    payloadJson.audio_url = entry.audioUrl
  }

  const res = await request<VocabularyUpsertDto>({
    url: '/vocabulary',
    method: 'POST',
    data: {
      lemma: entry.lemma || entry.word,
      display_word: entry.word,
      phonetic: entry.phonetic || null,
      part_of_speech: entry.partOfSpeech || null,
      short_meaning: entry.meaning,
      meanings_json: entry.detailMeanings
        ? entry.detailMeanings.map(m => ({
            partOfSpeech: m.pos,
            definitions: m.definitions.map(d => ({ meaning: d })),
          }))
        : [],
      tags: entry.tags || [],
      exchange: entry.exchange || [],
      source_provider: entry.provider || 'tecd3',
      dict_entry_id: entry.dictEntryId || null,
      source_sentence: entry.sentence || null,
      source_context: entry.context || null,
      payload_json: payloadJson,
      mastery_status: entry.masteryStatus || 'new',
      next_review_at: entry.nextReviewAt ? new Date(entry.nextReviewAt).toISOString() : null,
      ease_factor: entry.easeFactor || null,
      repetitions: entry.repetitions || null,
      review_interval: entry.reviewInterval || null,
      review_count: entry.reviewCount || null,
      last_reviewed_at: entry.lastReviewedAt ? new Date(entry.lastReviewedAt).toISOString() : null,
    },
  })
  return { id: res.id, created: res.created }
}

export async function updateCloudVocabulary(
  vocabId: string,
  patch: {
    mastery_status?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
    short_meaning?: string
    payload_json?: Record<string, unknown>
    next_review_at?: string
    ease_factor?: number
    repetitions?: number
    review_interval?: number
    review_count?: number
    last_reviewed_at?: string
  }
): Promise<void> {
  await request<VocabularyResponseDto>({
    url: `/vocabulary/${vocabId}`,
    method: 'PATCH',
    data: patch,
  })
}

export async function deleteCloudVocabulary(vocabId: string): Promise<void> {
  await request<{ deleted: boolean }>({
    url: `/vocabulary/${vocabId}`,
    method: 'DELETE',
  })
}

interface HighlightsResponseDto {
  matches: Array<{
    vocab_id: string
    lemma: string
    sentence_id: string
    anchor_text: string
    occurrence: number
    mastery_status: string
  }>
}

export async function fetchVocabHighlights(
  sentences: Array<{ sentenceId: string; tokens: string[] }>
): Promise<VocabHighlightMatch[]> {
  const res = await request<HighlightsResponseDto>({
    url: '/vocabulary/highlights',
    method: 'POST',
    data: {
      sentences: sentences.map(s => ({
        sentence_id: s.sentenceId,
        tokens: s.tokens,
      })),
    },
  })
  return res.matches.map(m => ({
    vocabId: m.vocab_id,
    lemma: m.lemma,
    sentenceId: m.sentence_id,
    anchorText: m.anchor_text,
    occurrence: m.occurrence,
    masteryStatus: m.mastery_status,
  }))
}

// ---------------------------------------------------------------------------
// 艾宾浩斯复习系统 API
// ---------------------------------------------------------------------------

interface ReviewStatsDto {
  total_vocab: number
  due_today: number
  overdue: number
  new_words: number
  learning: number
  mastered: number
}

interface DueVocabItemDto {
  id: string
  lemma: string
  display_word: string
  phonetic: string | null
  part_of_speech: string | null
  short_meaning: string
  mastery_status: string
  repetitions: number
  ease_factor: number
  review_interval: number
  next_review_at: string | null
  source_sentence: string | null
  source_refs?: Array<Record<string, unknown>>
  meanings_json?: Array<Record<string, unknown>>
  payload_json?: Record<string, unknown>
}

interface DueVocabListDto {
  items: DueVocabItemDto[]
  total: number
  due_type: string
}

interface ReviewSubmitResponseDto {
  vocab_id: string
  success: boolean
  next_review_at: string | null
  new_ease_factor: number
  new_interval: number
  new_repetitions: number
  new_mastery_status: string
  quality: number
  message: string
}

function dueVocabDtoToVm(dto: DueVocabItemDto): DueVocabItem {
  return {
    id: dto.id,
    lemma: dto.lemma,
    displayWord: dto.display_word,
    phonetic: dto.phonetic || undefined,
    partOfSpeech: dto.part_of_speech || undefined,
    shortMeaning: dto.short_meaning,
    masteryStatus: dto.mastery_status as DueVocabItem['masteryStatus'],
    repetitions: dto.repetitions,
    easeFactor: dto.ease_factor,
    reviewInterval: dto.review_interval,
    nextReviewAt: dto.next_review_at ? new Date(dto.next_review_at).getTime() : undefined,
    sourceSentence: dto.source_sentence || undefined,
    sourceRefs: dto.source_refs?.map((ref: any) => ({
      clientRecordId: ref.client_record_id || '',
      cloudRecordId: ref.cloud_record_id || undefined,
      sourceSentence: ref.source_sentence || undefined,
      sourceContext: ref.source_context || undefined,
      sourceSentenceId: ref.source_sentence_id || undefined,
      sourceAnchorText: ref.source_anchor_text || undefined,
      sourceOccurrence: ref.source_occurrence || undefined,
      collectedAt: ref.collected_at || undefined,
    })),
    meaningsJson: dto.meanings_json,
    payloadJson: dto.payload_json,
  }
}

/**
 * 获取复习统计数据
 */
export async function fetchReviewStats(): Promise<ReviewStats> {
  const res = await request<ReviewStatsDto>({
    url: '/vocabulary/review-stats',
    method: 'GET',
  })
  return {
    totalVocab: res.total_vocab,
    dueToday: res.due_today,
    overdue: res.overdue,
    newWords: res.new_words,
    learning: res.learning,
    mastered: res.mastered,
  }
}

/**
 * 获取待复习单词列表
 * @param dueType 'today' | 'overdue' | 'new'
 * @param limit 返回数量限制
 */
export async function fetchDueVocabulary(
  dueType: 'today' | 'overdue' | 'new' = 'today',
  limit = 100
): Promise<{ items: DueVocabItem[]; total: number; dueType: string }> {
  const res = await request<DueVocabListDto>({
    url: `/vocabulary/due?due_type=${dueType}&limit=${limit}`,
    method: 'GET',
  })
  return {
    items: res.items.map(dueVocabDtoToVm),
    total: res.total,
    dueType: res.due_type,
  }
}

/**
 * 提交复习结果
 * @param vocabId 生词记录ID
 * @param quality 复习质量评分 (0-5)
 *   - 0: 完全忘记
 *   - 1: 几乎忘记
 *   - 2: 模糊记得
 *   - 3: 记住了
 *   - 4: 熟练掌握
 *   - 5: 完全掌握
 */
export async function submitReview(
  vocabId: string,
  quality: 0 | 1 | 2 | 3 | 4 | 5
): Promise<ReviewSubmitResult> {
  const res = await request<ReviewSubmitResponseDto>({
    url: '/vocabulary/review',
    method: 'POST',
    data: {
      vocab_id: vocabId,
      quality,
    },
  })
  return {
    vocabId: res.vocab_id,
    success: res.success,
    nextReviewAt: res.next_review_at ? new Date(res.next_review_at).getTime() : undefined,
    newEaseFactor: res.new_ease_factor,
    newInterval: res.new_interval,
    newRepetitions: res.new_repetitions,
    newMasteryStatus: res.new_mastery_status,
    quality: res.quality as 0 | 1 | 2 | 3 | 4 | 5,
    message: res.message,
  }
}
