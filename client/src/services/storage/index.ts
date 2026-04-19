/**
 * 存储服务
 *
 * 统一封装所有 Taro.setStorageSync/getStorageSync 调用
 * 禁止在其他地方直接调用 storage API
 *
 * 3 类 key 分离：
 * - article_draft:          输入草稿（高频读写，体积小）
 * - analysis_record_ids:     历史记录 ID 有序列表
 * - analysis_record_{id}:    单条分析快照（按需懒加载）
 * - user_preferences:       用户偏好、onboarding 状态
 */

import Taro from '@tarojs/taro'
import type { AnalysisRecord } from '../../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../../types/view/favorites.vm'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import type { AnalyzeRequest } from '../api'
import type { AnyRenderSceneVm, ResultPageState } from '../../types/view/render-scene.vm'

// ============ Key 定义 ============

const KEYS = {
  DRAFT: 'article_draft',
  RECORD_IDS: 'analysis_record_ids',
  RECORD: (id: string) => `analysis_record_${id}`,
  FAVORITES: 'favorite_records',
  VOCABULARY: 'vocabulary_book',
  USER_PREF: 'user_preferences',
  RECORD_IDENTITY_MAP: 'record_identity_map',
  SYNC_QUEUE: 'sync_queue',
} as const

// ============ Article Draft ============

export interface ArticleDraft {
  text: string
  reading_goal: AnalyzeRequest['reading_goal']
  reading_variant: AnalyzeRequest['reading_variant']
  savedAt: number
}

export function saveDraft(draft: ArticleDraft): void {
  try {
    Taro.setStorageSync(KEYS.DRAFT, draft)
  } catch (e) {
    console.error('[storage] saveDraft failed', e)
  }
}

export function getDraft(): ArticleDraft | null {
  try {
    const raw = Taro.getStorageSync(KEYS.DRAFT)
    return raw || null
  } catch (e) {
    console.error('[storage] getDraft failed', e)
    return null
  }
}

export function clearDraft(): void {
  try {
    Taro.removeStorageSync(KEYS.DRAFT)
  } catch (e) {
    console.error('[storage] clearDraft failed', e)
  }
}

// ============ Analysis Records ============

/**
 * 生成唯一 ID
 */
export function generateRecordId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

/**
 * 获取所有历史记录 ID（按时间倒序）
 */
export function getRecordIds(): string[] {
  try {
    const raw = Taro.getStorageSync<string[]>(KEYS.RECORD_IDS)
    return raw || []
  } catch (e) {
    console.error('[storage] getRecordIds failed', e)
    return []
  }
}

/**
 * 获取单条分析记录
 */
export function getRecord(id: string): AnalysisRecord | null {
  try {
    const raw = Taro.getStorageSync<AnalysisRecord>(KEYS.RECORD(id))
    return raw || null
  } catch (e) {
    console.error('[storage] getRecord failed', e)
    return null
  }
}

/**
 * 保存分析记录（追加到列表头部）
 */
export function saveRecord(record: AnalysisRecord): void {
  try {
    // 保存记录本身
    Taro.setStorageSync(KEYS.RECORD(record.recordId), record)

    // 更新 ID 列表（去重 + 头部插入）
    const ids = getRecordIds()
    const filtered = ids.filter((id) => id !== record.recordId)
    Taro.setStorageSync(KEYS.RECORD_IDS, [record.recordId, ...filtered])
  } catch (e) {
    console.error('[storage] saveRecord failed', e)
  }
}

/**
 * 更新已有记录（如收藏状态变化）
 */
export function updateRecord(id: string, patch: Partial<AnalysisRecord>): void {
  try {
    const record = getRecord(id)
    if (!record) return
    const updated = { ...record, ...patch, updatedAt: Date.now() }
    Taro.setStorageSync(KEYS.RECORD(id), updated)
  } catch (e) {
    console.error('[storage] updateRecord failed', e)
  }
}

/**
 * 删除记录
 */
export function deleteRecord(id: string): void {
  try {
    Taro.removeStorageSync(KEYS.RECORD(id))
    const ids = getRecordIds().filter((recordId) => recordId !== id)
    Taro.setStorageSync(KEYS.RECORD_IDS, ids)
  } catch (e) {
    console.error('[storage] deleteRecord failed', e)
  }
}

/**
 * 获取所有记录（按时间倒序）
 * 注意：大列表场景建议用 getRecordIds + 按需加载单条
 */
export function getAllRecords(): AnalysisRecord[] {
  const ids = getRecordIds()
  const records: AnalysisRecord[] = []
  for (const id of ids) {
    const record = getRecord(id)
    if (record) records.push(record)
  }
  return records
}

// ============ Favorites ============

export function getFavorites(): FavoriteRecord[] {
  try {
    const raw = Taro.getStorageSync<FavoriteRecord[]>(KEYS.FAVORITES)
    return raw || []
  } catch (e) {
    console.error('[storage] getFavorites failed', e)
    return []
  }
}

export function saveFavorite(favorite: FavoriteRecord): void {
  try {
    const favorites = getFavorites()
    const exists = favorites.some((f) => f.recordId === favorite.recordId)
    if (exists) return
    Taro.setStorageSync(KEYS.FAVORITES, [favorite, ...favorites])
  } catch (e) {
    console.error('[storage] saveFavorite failed', e)
  }
}

export function removeFavorite(recordId: string): void {
  try {
    const favorites = getFavorites().filter((f) => f.recordId !== recordId)
    Taro.setStorageSync(KEYS.FAVORITES, favorites)
  } catch (e) {
    console.error('[storage] removeFavorite failed', e)
  }
}

export function isFavorited(recordId: string): boolean {
  return getFavorites().some((f) => f.recordId === recordId)
}

// ============ Vocabulary ============

export function getVocabulary(): VocabEntry[] {
  try {
    const raw = Taro.getStorageSync<VocabEntry[]>(KEYS.VOCABULARY)
    return raw || []
  } catch (e) {
    console.error('[storage] getVocabulary failed', e)
    return []
  }
}

export function saveVocabEntry(entry: VocabEntry): void {
  try {
    const vocab = getVocabulary()
    /**
     * 去重策略：统一用 lemma（如果有）加 recordId 来判断，
     * 如果没有 lemma 则用 word（统一小写）加 recordId。
     * 确保同一篇文章中同一 lemma 的词不会重复。
     */
    const entryKey = (entry.lemma || entry.word).toLowerCase()
    const exists = vocab.some((v) => {
      const vKey = (v.lemma || v.word).toLowerCase()
      return vKey === entryKey && v.recordId === entry.recordId
    })
    if (exists) return
    Taro.setStorageSync(KEYS.VOCABULARY, [entry, ...vocab])
  } catch (e) {
    console.error('[storage] saveVocabEntry failed', e)
  }
}

export function removeVocabEntry(id: string): void {
  try {
    const vocab = getVocabulary().filter((v) => v.id !== id)
    Taro.setStorageSync(KEYS.VOCABULARY, vocab)
  } catch (e) {
    console.error('[storage] removeVocabEntry failed', e)
  }
}

export function updateVocabEntry(id: string, updates: Partial<VocabEntry>): void {
  try {
    const vocab = getVocabulary()
    const index = vocab.findIndex(v => v.id === id)
    if (index > -1) {
      vocab[index] = { ...vocab[index], ...updates }
      Taro.setStorageSync(KEYS.VOCABULARY, vocab)
    }
  } catch (e) {
    console.error('[storage] updateVocabEntry failed', e)
  }
}

// ============ User Preferences ============

export interface UserPreferences {
  purpose?: 'daily' | 'exam' | 'academic'
  level?: string
  configured?: boolean
}

export function getUserPreferences(): UserPreferences {
  try {
    const raw = Taro.getStorageSync<UserPreferences>(KEYS.USER_PREF)
    return raw || {}
  } catch (e) {
    console.error('[storage] getUserPreferences failed', e)
    return {}
  }
}

export function saveUserPreferences(pref: Partial<UserPreferences>): void {
  try {
    const current = getUserPreferences()
    Taro.setStorageSync(KEYS.USER_PREF, { ...current, ...pref })
  } catch (e) {
    console.error('[storage] saveUserPreferences failed', e)
  }
}

// ============ Record Identity Map ============

export interface RecordIdentityMap {
  [clientRecordId: string]: string
}

export function getRecordIdentityMap(): RecordIdentityMap {
  try {
    const raw = Taro.getStorageSync<RecordIdentityMap>(KEYS.RECORD_IDENTITY_MAP)
    return raw || {}
  } catch (e) {
    console.error('[storage] getRecordIdentityMap failed', e)
    return {}
  }
}

export function saveRecordIdentity(clientRecordId: string, cloudRecordId: string): void {
  try {
    const map = getRecordIdentityMap()
    map[clientRecordId] = cloudRecordId
    Taro.setStorageSync(KEYS.RECORD_IDENTITY_MAP, map)
  } catch (e) {
    console.error('[storage] saveRecordIdentity failed', e)
  }
}

export function resolveCloudIdFromMap(clientRecordId: string): string | null {
  const map = getRecordIdentityMap()
  return map[clientRecordId] || null
}

export function resolveClientIdFromMap(cloudRecordId: string): string | null {
  const map = getRecordIdentityMap()
  for (const [clientId, cloudId] of Object.entries(map)) {
    if (cloudId === cloudRecordId) return clientId
  }
  return null
}

// ============ Sync Queue ============

export interface SyncQueueItem {
  opId: string
  entityType: 'record' | 'favorite' | 'vocab'
  entityId: string
  action: string
  payload: Record<string, unknown>
  dependsOn?: string[]
  status: 'pending' | 'running' | 'failed' | 'done'
  retryCount: number
  nextRetryAt?: number
  lastError?: string | null
  createdAt: number
  updatedAt: number
}

export function getSyncQueue(): SyncQueueItem[] {
  try {
    const raw = Taro.getStorageSync<SyncQueueItem[]>(KEYS.SYNC_QUEUE)
    return raw || []
  } catch (e) {
    console.error('[storage] getSyncQueue failed', e)
    return []
  }
}

export function saveSyncQueue(queue: SyncQueueItem[]): void {
  try {
    Taro.setStorageSync(KEYS.SYNC_QUEUE, queue)
  } catch (e) {
    console.error('[storage] saveSyncQueue failed', e)
  }
}

export function enqueueSyncItem(item: SyncQueueItem): void {
  const queue = getSyncQueue()
  queue.push(item)
  saveSyncQueue(queue)
}

export function updateSyncQueueItem(opId: string, updates: Partial<SyncQueueItem>): void {
  const queue = getSyncQueue()
  const idx = queue.findIndex(item => item.opId === opId)
  if (idx > -1) {
    queue[idx] = { ...queue[idx], ...updates, updatedAt: Date.now() }
    saveSyncQueue(queue)
  }
}

export function removeSyncQueueItem(opId: string): void {
  const queue = getSyncQueue().filter(item => item.opId !== opId)
  saveSyncQueue(queue)
}

export function getPendingSyncItems(): SyncQueueItem[] {
  return getSyncQueue().filter(item => item.status === 'pending')
}
