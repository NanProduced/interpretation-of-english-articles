/**
 * Cloud API: Vocabulary Book
 *
 * 对应后端 GET/POST/PATCH/DELETE /vocabulary
 * 需要认证，自动附带 Authorization header
 */

import { request } from './client'
import type { VocabEntry, SourceRef } from '../../types/view/vocabulary.vm'

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
