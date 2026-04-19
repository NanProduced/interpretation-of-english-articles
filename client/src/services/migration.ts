/**
 * 本地数据迁移
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
import type { VocabEntry, SourceRef } from '../types/view/vocabulary.vm'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../types/view/favorites.vm'

const MIGRATION_VERSION_KEY = 'data_migration_version'
const CURRENT_MIGRATION_VERSION = 2

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

  if (currentVersion < 2) {
    await migrationV2_migrateVocabToSourceRefs()
    Taro.setStorageSync(MIGRATION_VERSION_KEY, 2)
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

  console.log('[migration] v1: complete')
}

/**
 * V2: 将旧 VocabEntry 的 recordId/cloudRecordId/sentence/context
 * 迁移到新的 sourceRefs 结构。
 *
 * 旧结构：
 *   { recordId, cloudRecordId, sentence, context, ... }
 * 新结构：
 *   { sourceRefs: [{ clientRecordId, cloudRecordId, sourceSentence, sourceContext }], ... }
 */
async function migrationV2_migrateVocabToSourceRefs(): Promise<void> {
  console.log('[migration] v2: migrate vocab recordId/cloudRecordId to sourceRefs')

  const vocab = getVocabulary()
  const recordIds = getRecordIds()

  for (const entry of vocab) {
    if (entry.tombstone) continue
    if (entry.sourceRefs && entry.sourceRefs.length > 0) continue

    const oldRecordId = (entry as any).recordId as string | undefined
    const oldCloudRecordId = (entry as any).cloudRecordId as string | undefined

    let clientRecordId = oldRecordId || ''
    let cloudRecordId = oldCloudRecordId

    if (oldRecordId && isUUID(oldRecordId)) {
      const localRecord = getRecord(oldRecordId)
      if (localRecord) {
        clientRecordId = localRecord.recordId
        cloudRecordId = oldRecordId
      } else {
        const clientIdFromMap = resolveClientIdFromMap(oldRecordId)
        if (clientIdFromMap) {
          clientRecordId = clientIdFromMap
          cloudRecordId = oldRecordId
        } else {
          for (const rid of recordIds) {
            const r = getRecord(rid)
            if (r && r.cloudId === oldRecordId) {
              clientRecordId = r.recordId
              cloudRecordId = oldRecordId
              saveRecordIdentity(r.recordId, oldRecordId)
              break
            }
          }
        }
      }
    }

    const sourceRef: SourceRef = {
      clientRecordId,
      cloudRecordId: cloudRecordId || undefined,
      sourceSentence: entry.sentence || undefined,
      sourceContext: entry.context || undefined,
      collectedAt: entry.addedAt ? new Date(entry.addedAt).toISOString() : undefined,
    }

    const migrated: VocabEntry = {
      ...entry,
      sourceRefs: [sourceRef],
      collectedForms: entry.word ? [entry.word] : [],
    }
    delete (migrated as any).recordId
    delete (migrated as any).cloudRecordId

    if (!migrated.syncState) {
      migrated.syncState = 'local_only'
    }

    removeVocabEntry(entry.id)
    saveVocabEntry(migrated)
  }

  console.log('[migration] v2: complete')
}
