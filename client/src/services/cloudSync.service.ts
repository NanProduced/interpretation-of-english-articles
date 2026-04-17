import { useAuthStore } from '../stores/auth'
import type { AnalysisRecord } from '../types/view/analysis-record.vm'
import type { FavoriteRecord } from '../types/view/favorites.vm'
import type { VocabEntry } from '../types/view/vocabulary.vm'
import { getRecord } from './storage'
import { syncService } from './sync'

export const CloudSyncService = {
  async initialize(): Promise<void> {
    await syncService.initialize()
  },

  async syncRecord(record: AnalysisRecord): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueRecordSync(record)
  },

  async syncFavorite(
    cloudId: string | undefined,
    clientRecordId: string,
    action: 'add' | 'remove'
  ): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueFavoriteSync(cloudId, clientRecordId, action)
  },

  async syncVocab(entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueVocabSync(entry, 'add')
  },

  async updateVocab(
    vocabId: string,
    entry: VocabEntry,
    patch: {
      mastery_status?: 'new' | 'learning' | 'review' | 'mastered' | 'archived'
      short_meaning?: string
    }
  ): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueVocabSync(entry, 'update', vocabId, patch)
  },

  async deleteVocab(vocabId: string, entry: VocabEntry): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return
    syncService.enqueueVocabSync(entry, 'delete', vocabId)
  },

  async syncAllFavorites(localFavorites: FavoriteRecord[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    const records = localFavorites
      .map((favorite) => getRecord(favorite.recordId))
      .filter((record): record is AnalysisRecord => !!record)

    for (const record of records) {
      if (record.isFavorited) {
        syncService.enqueueFavoriteSync(record.cloudId, record.recordId, 'add')
      }
    }
  },

  async syncAllVocab(localVocab: VocabEntry[]): Promise<void> {
    if (!useAuthStore.getState().isLoggedIn) return

    for (const entry of localVocab) {
      syncService.enqueueVocabSync(entry, 'add')
    }
  },

  getQueueStats(): {
    pendingCount: number
    inProgressCount: number
    failedCount: number
    totalCount: number
  } {
    return syncService.getQueueStats()
  },

  triggerSync(): void {
    syncService.triggerSync()
  },

  compressQueue(): void {
    syncService.compressQueue()
  },

  isOnline(): boolean {
    return syncService.isOnline()
  },

  getConsumerStatus(): string {
    return syncService.getConsumerStatus()
  }
}
