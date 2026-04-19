/**
 * 本地数据迁移：修复旧 UUID 污染数据
 *
 * 修复内容：
 * 1. VocabEntry.recordId 中被错误写入云端 UUID 的条目
 * 2. 旧资产补 syncState
 * 3. 补齐 record_identity_map
 *
 * 迁移要求：幂等、可重复执行、单条坏数据不影响整体迁移
 */

import Taro from '@tarojs/taro'
import {
  getRecordIds,
  getRecord,
  updateRecord,
  getVocabulary,
  saveVocabEntry,
  removeVocabEntry,
  getFavorites,
  getRecordIdentityMap,
  saveRecordIdentity,
  resolveClientIdFromMap,
} from './storage'
import type { VocabEntry } from '../types/view/vocabulary.vm'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../types/view/favorites.vm'

const MIGRATION_VERSION_KEY = 'data_migration_version'
const CURRENT_MIGRATION_VERSION = 1

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isUUID(str: string): boolean {
  return UUID_REGEX.test(str)
}

export async function runMigrations(): Promise<void> {
  const currentVersion = Taro.getStorageSync<number>(MIGRATION_VERSION_KEY) || 0

  if (currentVersion < 1) {
    await migrationV1_fixIdPollution()
    Taro.setStorageSync(MIGRATION_VERSION_KEY, 1)
  }
}

async function migrationV1_fixIdPollution(): Promise<void> {
  console.log('[migration] v1: fix ID pollution + add syncState + build identity map')

  const recordIds = getRecordIds()
  const idMap = getRecordIdentityMap()

  for (const rid of recordIds) {
    const record = getRecord(rid)
    if (!record) continue

    const updates: Partial<AnalysisRecord> = {}

    if (!record.syncState) {
      updates.syncState = record.cloudId ? 'synced' : 'local_only'
    }

    if (record.cloudId && record.recordId) {
      if (!idMap[record.recordId] || idMap[record.recordId] !== record.cloudId) {
        saveRecordIdentity(record.recordId, record.cloudId)
      }
    }

    if (Object.keys(updates).length > 0) {
      updateRecord(rid, updates)
    }
  }

  const vocab = getVocabulary()
  for (const entry of vocab) {
    if (entry.tombstone) continue

    let needsFix = false
    const fixedEntry: VocabEntry = { ...entry }

    if (isUUID(entry.recordId)) {
      const cloudId = entry.recordId
      const localRecord = getRecord(cloudId)

      if (localRecord) {
        fixedEntry.recordId = localRecord.recordId
        fixedEntry.cloudRecordId = cloudId
        needsFix = true
      } else {
        const clientIdFromMap = resolveClientIdFromMap(cloudId)
        if (clientIdFromMap) {
          fixedEntry.recordId = clientIdFromMap
          fixedEntry.cloudRecordId = cloudId
          needsFix = true
        } else {
          for (const rid of recordIds) {
            const r = getRecord(rid)
            if (r && r.cloudId === cloudId) {
              fixedEntry.recordId = r.recordId
              fixedEntry.cloudRecordId = cloudId
              saveRecordIdentity(r.recordId, cloudId)
              needsFix = true
              break
            }
          }
        }
      }

      if (!needsFix) {
        fixedEntry.cloudRecordId = cloudId
        fixedEntry.recordId = ''
        needsFix = true
      }
    }

    if (!fixedEntry.syncState) {
      fixedEntry.syncState = 'local_only'
      needsFix = true
    }

    if (needsFix) {
      removeVocabEntry(entry.id)
      saveVocabEntry(fixedEntry)
    }
  }

  console.log('[migration] v1: complete')
}
