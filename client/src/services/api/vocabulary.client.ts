/**
 * Cloud API: Vocabulary Book
 *
 * 对应后端 GET/POST/PATCH/DELETE /vocabulary
 * 需要认证，自动附带 Authorization header
 */

import { request } from './client'
import type { VocabEntry } from '../../types/view/vocabulary.vm'

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
  meanings_json: Array<Record<string, unknown>>
  tags: string[]
  exchange: string[]
  source_provider: string
  analysis_record_id: string | null
  client_record_id: string | null
  source_sentence: string | null
  source_context: string | null
  mastery_status: string
  review_count: number
  last_reviewed_at: string | null
  payload_json: Record<string, unknown>
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

function dtoToVm(dto: VocabularyResponseDto): VocabEntry {
  const detailMeanings = Array.isArray(dto.meanings_json) 
    ? dto.meanings_json.map((m: any) => ({
        pos: m.partOfSpeech || m.part_of_speech || '',
        definitions: Array.isArray(m.definitions) 
          ? m.definitions.map((d: any) => d.meaning || d) 
          : []
      })).filter(m => m.definitions.length > 0)
    : undefined;

  return {
    id: dto.id,
    recordId: dto.client_record_id || dto.analysis_record_id || '', 
    cloudRecordId: dto.analysis_record_id || undefined,
    word: dto.display_word,
    lemma: dto.lemma,
    phonetic: dto.phonetic || undefined,
    partOfSpeech: dto.part_of_speech || '',
    meaning: dto.short_meaning,
    addedAt: new Date(dto.created_at).getTime(),
    mastered: dto.mastery_status === 'mastered',
    detailMeanings,
    tags: dto.tags,
    exchange: dto.exchange,
    provider: dto.source_provider,
    sentence: dto.source_sentence || undefined,
    context: dto.source_context || undefined,
  }
}

// ---------------------------------------------------------------------------
// API 调用
// ---------------------------------------------------------------------------

/**
 * 获取云端生词本列表
 */
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

/**
 * 添加生词到云端
 */
export async function addVocabToCloud(
  entry: VocabEntry
): Promise<{ id: string; created: boolean }> {
  const res = await request<VocabularyUpsertDto>({
    url: '/vocabulary',
    method: 'POST',
    data: {
      analysis_record_id: entry.cloudRecordId || null,
      lemma: entry.lemma || entry.word,
      display_word: entry.word,
      phonetic: entry.phonetic || null,
      part_of_speech: entry.partOfSpeech || null,
      short_meaning: entry.meaning,
      meanings_json: entry.detailMeanings 
        ? entry.detailMeanings.map(m => ({ partOfSpeech: m.pos, definitions: m.definitions.map(d => ({ meaning: d })) }))
        : [],
      tags: entry.tags || [],
      exchange: entry.exchange || [],
      source_provider: entry.provider || 'tecd3',
      source_sentence: entry.sentence || null,
      source_context: entry.context || null,
      payload_json: {},
    },
  })
  return { id: res.id, created: res.created }
}

/**
 * 更新生词状态（如标记为已掌握）
 */
export async function updateCloudVocabulary(
  vocabId: string,
  patch: {
    mastery_status?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
    short_meaning?: string
  }
): Promise<void> {
  await request<VocabularyResponseDto>({
    url: `/vocabulary/${vocabId}`,
    method: 'PATCH',
    data: patch,
  })
}

/**
 * 删除云端生词
 */
export async function deleteCloudVocabulary(vocabId: string): Promise<void> {
  await request<{ deleted: boolean }>({
    url: `/vocabulary/${vocabId}`,
    method: 'DELETE',
  })
}
