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
 * - sync_queue:             同步队列（离线优先架构）
 * - sync_metadata:          同步元数据（网络状态、最后同步时间等）
 */

import Taro from '@tarojs/taro'
import type { AnalysisRecord } from '../../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../../types/view/favorites.vm'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import type { AnalyzeRequest } from '../api'
import type { RenderSceneVm, ResultPageState } from '../../types/view/render-scene.vm'
import type { SyncQueueItem, NetworkStatus } from '../../types/sync-queue.vm'

// ============ Key 定义 ============

const KEYS = {
  DRAFT: 'article_draft',
  RECORD_IDS: 'analysis_record_ids',
  RECORD: (id: string) => `analysis_record_${id}`,
  FAVORITES: 'favorite_records',
  VOCABULARY: 'vocabulary_book',
  USER_PREF: 'user_preferences',
  SYNC_QUEUE: 'sync_queue',
  SYNC_METADATA: 'sync_metadata',
} as const

// ============ Sync Queue Metadata ============

export interface SyncMetadata {
  /** 网络状态 */
  networkStatus: NetworkStatus
  /** 最后一次成功同步的时间戳 */
  lastSyncedAt?: number
  /** 队列是否正在处理中 */
  isProcessing: boolean
  /** 当前处理中的操作 ID */
  currentProcessingId?: string
  /** 同步配置（覆盖默认配置） */
  config?: {
    maxRetries?: number
    initialRetryDelay?: number
    maxRetryDelay?: number
    backoffFactor?: number
    batchSize?: number
  }
}

export function getSyncMetadata(): SyncMetadata {
  try {
    const raw = Taro.getStorageSync<SyncMetadata>(KEYS.SYNC_METADATA)
    return raw || {
      networkStatus: 'unknown',
      isProcessing: false,
    }
  } catch (e) {
    console.error('[storage] getSyncMetadata failed', e)
    return {
      networkStatus: 'unknown',
      isProcessing: false,
    }
  }
}

export function saveSyncMetadata(metadata: Partial<SyncMetadata>): void {
  try {
    const current = getSyncMetadata()
    const updated = { ...current, ...metadata }
    Taro.setStorageSync(KEYS.SYNC_METADATA, updated)
  } catch (e) {
    console.error('[storage] saveSyncMetadata failed', e)
  }
}

// ============ Sync Queue ============

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

export function addToSyncQueue(item: SyncQueueItem): void {
  try {
    const queue = getSyncQueue()
    queue.push(item)
    saveSyncQueue(queue)
  } catch (e) {
    console.error('[storage] addToSyncQueue failed', e)
  }
}

export function removeFromSyncQueue(operationId: string): void {
  try {
    const queue = getSyncQueue()
    const filtered = queue.filter((item) => item.operationId !== operationId)
    saveSyncQueue(filtered)
  } catch (e) {
    console.error('[storage] removeFromSyncQueue failed', e)
  }
}

export function updateSyncQueueItem(operationId: string, patch: Partial<SyncQueueItem>): void {
  try {
    const queue = getSyncQueue()
    const index = queue.findIndex((item) => item.operationId === operationId)
    if (index === -1) return
    queue[index] = { ...queue[index], ...patch }
    saveSyncQueue(queue)
  } catch (e) {
    console.error('[storage] updateSyncQueueItem failed', e)
  }
}

export function getSyncQueueItem(operationId: string): SyncQueueItem | null {
  try {
    const queue = getSyncQueue()
    return queue.find((item) => item.operationId === operationId) || null
  } catch (e) {
    console.error('[storage] getSyncQueueItem failed', e)
    return null
  }
}

export function clearCompletedSyncQueue(): void {
  try {
    const queue = getSyncQueue()
    const filtered = queue.filter((item) => item.status !== 'completed')
    saveSyncQueue(filtered)
  } catch (e) {
    console.error('[storage] clearCompletedSyncQueue failed', e)
  }
}

export function getPendingSyncQueue(): SyncQueueItem[] {
  try {
    const queue = getSyncQueue()
    const now = Date.now()
    return queue.filter((item) => {
      if (item.status === 'completed' || item.status === 'cancelled') return false
      if (item.retryAt && item.retryAt > now) return false
      return true
    }).sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority
      return a.timestamp - b.timestamp
    })
  } catch (e) {
    console.error('[storage] getPendingSyncQueue failed', e)
    return []
  }
}

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
