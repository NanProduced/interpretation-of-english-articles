/**
 * 词典查询多级缓存服务
 * 
 * 缓存层级：
 * - L1: 内存缓存 - 同一会话内的极速二次触发
 * - L2: Taro.getStorage 本地持久化缓存 - 重新打开小程序后无需联网
 * - L3: 服务端 API 请求 - 前两级失效后才触发
 * 
 * 缓存 Key 设计：
 * - 单词查询: dict:lookup:{word}:{type}:{ctxHash}
 * - 词条查询: dict:entry:{entryId}
 * 
 * 注意：
 * - context_sentence 会影响缓存命中率，因为同一单词在不同上下文中可能触发不同的短语识别
 * - 为了提高缓存命中率，我们将 context_sentence 进行哈希处理作为 key 的一部分
 * - 对于常见高频词，建议用户直接在词汇本中查询（无 context_sentence）以获得更高缓存命中率
 */

import Taro from '@tarojs/taro'
import type { DictResponseDto, DictEntryResultDto } from '../../types/api/dict-response.dto'

// ============ 缓存配置 ============

const CACHE_CONFIG = {
  L1_MAX_SIZE: 200,
  L1_TTL_MS: 1000 * 60 * 60 * 24,
  L2_MAX_SIZE: 500,
  L2_TTL_MS: 1000 * 60 * 60 * 24 * 7,
  STORAGE_KEY: 'dict_cache_v2',
  STORAGE_META_KEY: 'dict_cache_meta_v2',
} as const

// ============ 缓存类型定义 ============

interface CacheEntry<T> {
  data: T
  createdAt: number
  accessedAt: number
  accessCount: number
}

interface CacheMeta {
  keys: string[]
  size: number
}

interface L1Cache {
  [key: string]: CacheEntry<DictResponseDto | DictEntryResultDto>
}

// ============ L1 内存缓存实现 ============

let _l1Cache: L1Cache = Object.create(null)
let _l1CacheKeys: string[] = []

function _l1Get(key: string): DictResponseDto | DictEntryResultDto | null {
  const entry = _l1Cache[key]
  if (!entry) return null

  const now = Date.now()
  if (now - entry.createdAt > CACHE_CONFIG.L1_TTL_MS) {
    delete _l1Cache[key]
    _l1CacheKeys = _l1CacheKeys.filter((k) => k !== key)
    return null
  }

  entry.accessedAt = now
  entry.accessCount++
  return entry.data
}

function _l1Set(key: string, data: DictResponseDto | DictEntryResultDto): void {
  const now = Date.now()

  if (_l1CacheKeys.length >= CACHE_CONFIG.L1_MAX_SIZE) {
    const sortedKeys = [..._l1CacheKeys].sort((a, b) => {
      const entryA = _l1Cache[a]
      const entryB = _l1Cache[b]
      if (!entryA || !entryB) return 0

      const scoreA = entryA.accessCount * 1000 + (now - entryA.accessedAt)
      const scoreB = entryB.accessCount * 1000 + (now - entryB.accessedAt)
      return scoreA - scoreB
    })

    const toRemove = sortedKeys.slice(0, Math.ceil(CACHE_CONFIG.L1_MAX_SIZE * 0.25))
    for (const k of toRemove) {
      delete _l1Cache[k]
    }
    _l1CacheKeys = _l1CacheKeys.filter((k) => !toRemove.includes(k))
  }

  _l1Cache[key] = {
    data,
    createdAt: now,
    accessedAt: now,
    accessCount: 1,
  }
  if (!_l1CacheKeys.includes(key)) {
    _l1CacheKeys.push(key)
  }
}

// ============ L2 本地存储缓存实现 ============

function _l2GetMeta(): CacheMeta {
  try {
    const raw = Taro.getStorageSync<string>(CACHE_CONFIG.STORAGE_META_KEY)
    return raw ? JSON.parse(raw) : { keys: [], size: 0 }
  } catch {
    return { keys: [], size: 0 }
  }
}

function _l2SetMeta(meta: CacheMeta): void {
  try {
    Taro.setStorageSync(CACHE_CONFIG.STORAGE_META_KEY, JSON.stringify(meta))
  } catch (e) {
    console.warn('[dictCache] L2 setMeta failed:', e)
  }
}

function _l2Get(key: string): DictResponseDto | DictEntryResultDto | null {
  try {
    const raw = Taro.getStorageSync<string>(`${CACHE_CONFIG.STORAGE_KEY}:${key}`)
    if (!raw) return null

    const entry: CacheEntry<DictResponseDto | DictEntryResultDto> = JSON.parse(raw)
    const now = Date.now()

    if (now - entry.createdAt > CACHE_CONFIG.L2_TTL_MS) {
      Taro.removeStorageSync(`${CACHE_CONFIG.STORAGE_KEY}:${key}`)
      const meta = _l2GetMeta()
      meta.keys = meta.keys.filter((k) => k !== key)
      meta.size = meta.keys.length
      _l2SetMeta(meta)
      return null
    }

    return entry.data
  } catch (e) {
    console.warn('[dictCache] L2 get failed:', e)
    return null
  }
}

function _l2Set(key: string, data: DictResponseDto | DictEntryResultDto): void {
  try {
    const now = Date.now()
    const meta = _l2GetMeta()

    if (meta.size >= CACHE_CONFIG.L2_MAX_SIZE) {
      const toRemove = meta.keys.slice(0, Math.ceil(CACHE_CONFIG.L2_MAX_SIZE * 0.25))
      for (const k of toRemove) {
        try {
          Taro.removeStorageSync(`${CACHE_CONFIG.STORAGE_KEY}:${k}`)
        } catch {
          // 忽略单个删除失败
        }
      }
      meta.keys = meta.keys.filter((k) => !toRemove.includes(k))
      meta.size = meta.keys.length
    }

    const entry: CacheEntry<typeof data> = {
      data,
      createdAt: now,
      accessedAt: now,
      accessCount: 1,
    }

    Taro.setStorageSync(`${CACHE_CONFIG.STORAGE_KEY}:${key}`, JSON.stringify(entry))

    if (!meta.keys.includes(key)) {
      meta.keys.push(key)
      meta.size++
    }

    _l2SetMeta(meta)
  } catch (e) {
    console.warn('[dictCache] L2 set failed:', e)
  }
}

// ============ 缓存 Key 生成 ============

function generateLookupCacheKey(
  word: string,
  type: 'word' | 'phrase',
  contextSentence?: string,
  occurrence?: number
): string {
  const normalizedWord = word.trim().toLowerCase()
  let ctxHash = 'none'

  if (contextSentence) {
    let hash = 0
    const str = contextSentence
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash
    }
    ctxHash = hash.toString(36)
  }

  const occ = occurrence ?? 0
  return `lookup:${normalizedWord}:${type}:${ctxHash}:${occ}`
}

function generateEntryCacheKey(entryId: number): string {
  return `entry:${entryId}`
}

// ============ 公共 API ============

/**
 * 从缓存中获取词典查询结果
 * 查询顺序：L1 → L2 → (未命中返回 null)
 */
export function getDictFromCache(
  word: string,
  type: 'word' | 'phrase' = 'word',
  contextSentence?: string,
  occurrence?: number
): DictResponseDto | null {
  const key = generateLookupCacheKey(word, type, contextSentence, occurrence)

  const l1Result = _l1Get(key)
  if (l1Result) {
    console.debug('[dictCache] L1 cache hit (lookup):', word)
    return { ...l1Result, cached: true } as DictResponseDto
  }

  const l2Result = _l2Get(key)
  if (l2Result) {
    console.debug('[dictCache] L2 cache hit (lookup):', word)
    _l1Set(key, l2Result)
    return { ...l2Result, cached: true } as DictResponseDto
  }

  console.debug('[dictCache] cache miss (lookup):', word)
  return null
}

/**
 * 从缓存中获取词条查询结果
 * 查询顺序：L1 → L2 → (未命中返回 null)
 */
export function getDictEntryFromCache(entryId: number): DictEntryResultDto | null {
  const key = generateEntryCacheKey(entryId)

  const l1Result = _l1Get(key)
  if (l1Result) {
    console.debug('[dictCache] L1 cache hit (entry):', entryId)
    return { ...l1Result, cached: true } as DictEntryResultDto
  }

  const l2Result = _l2Get(key)
  if (l2Result) {
    console.debug('[dictCache] L2 cache hit (entry):', entryId)
    _l1Set(key, l2Result)
    return { ...l2Result, cached: true } as DictEntryResultDto
  }

  console.debug('[dictCache] cache miss (entry):', entryId)
  return null
}

/**
 * 写入词典查询结果到缓存
 * 同时写入 L1 和 L2 缓存
 */
export function setDictToCache(
  word: string,
  type: 'word' | 'phrase',
  data: DictResponseDto,
  contextSentence?: string,
  occurrence?: number
): void {
  const key = generateLookupCacheKey(word, type, contextSentence, occurrence)
  const dataToCache = { ...data, cached: true }

  _l1Set(key, dataToCache)
  _l2Set(key, dataToCache)

  console.debug('[dictCache] cached (lookup):', word)
}

/**
 * 写入词条查询结果到缓存
 * 同时写入 L1 和 L2 缓存
 */
export function setDictEntryToCache(entryId: number, data: DictEntryResultDto): void {
  const key = generateEntryCacheKey(entryId)
  const dataToCache = { ...data, cached: true }

  _l1Set(key, dataToCache)
  _l2Set(key, dataToCache)

  console.debug('[dictCache] cached (entry):', entryId)
}

/**
 * 清空 L1 内存缓存（用于调试或内存紧张时）
 */
export function clearL1Cache(): void {
  _l1Cache = Object.create(null)
  _l1CacheKeys = []
  console.info('[dictCache] L1 cache cleared')
}

/**
 * 清空 L2 本地存储缓存（用于调试或用户手动清理）
 */
export function clearL2Cache(): void {
  try {
    const meta = _l2GetMeta()
    for (const key of meta.keys) {
      try {
        Taro.removeStorageSync(`${CACHE_CONFIG.STORAGE_KEY}:${key}`)
      } catch {
        // 忽略单个删除失败
      }
    }
    Taro.removeStorageSync(CACHE_CONFIG.STORAGE_META_KEY)
    console.info('[dictCache] L2 cache cleared')
  } catch (e) {
    console.warn('[dictCache] clear L2 failed:', e)
  }
}

/**
 * 获取缓存统计信息（用于调试）
 */
export function getCacheStats(): {
  l1: { size: number; maxSize: number }
  l2: { size: number; maxSize: number }
} {
  const l2Meta = _l2GetMeta()
  return {
    l1: {
      size: _l1CacheKeys.length,
      maxSize: CACHE_CONFIG.L1_MAX_SIZE,
    },
    l2: {
      size: l2Meta.size,
      maxSize: CACHE_CONFIG.L2_MAX_SIZE,
    },
  }
}
