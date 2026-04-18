/**
 * 用户资产状态管理
 *
 * 用于跨页面同步收藏状态、生词数量等需要实时更新的数据。
 * 解决 Taro 小程序页面栈中前页面组件不重新挂载导致的状态不同步问题。
 *
 * 设计思路：
 * 1. 页面初始化时从本地存储加载一次全量数据
 * 2. 当在其他页面修改数据时（如收藏、添加生词），同步更新此 store
 * 3. 订阅此 store 的页面会自动响应变化，实现增量更新
 */

import { create } from 'zustand'
import {
  getFavorites,
  getVocabulary,
  getRecordIds,
} from '../services/storage'
import type { VocabEntry } from '../types/view/vocabulary.vm'

interface AssetsState {
  favoriteRecordIds: Set<string>
  vocabCounts: Record<string, number>
  totalVocabCount: number
  totalArticleCount: number

  setFavorite: (recordId: string, isFavorite: boolean) => void
  addVocab: (entry: VocabEntry) => void
  removeVocab: (entryId: string, recordId?: string) => void
  addRecord: () => void
  removeRecord: (recordId: string) => void
  initialize: () => void
}

export const useAssetsStore = create<AssetsState>((set, get) => ({
  favoriteRecordIds: new Set(),
  vocabCounts: {},
  totalVocabCount: 0,
  totalArticleCount: 0,

  setFavorite: (recordId: string, isFavorite: boolean) => {
    set((state) => {
      const nextFavorites = new Set(state.favoriteRecordIds)
      if (isFavorite) {
        nextFavorites.add(recordId)
      } else {
        nextFavorites.delete(recordId)
      }
      return { favoriteRecordIds: nextFavorites }
    })
  },

  addVocab: (entry: VocabEntry) => {
    set((state) => {
      const recordId = entry.recordId
      const nextVocabCounts = { ...state.vocabCounts }
      if (recordId) {
        nextVocabCounts[recordId] = (nextVocabCounts[recordId] || 0) + 1
      }
      return {
        vocabCounts: nextVocabCounts,
        totalVocabCount: state.totalVocabCount + 1,
      }
    })
  },

  removeVocab: (entryId: string, recordId?: string) => {
    set((state) => {
      if (!recordId) {
        return { totalVocabCount: Math.max(0, state.totalVocabCount - 1) }
      }
      const nextVocabCounts = { ...state.vocabCounts }
      if (nextVocabCounts[recordId]) {
        nextVocabCounts[recordId] = Math.max(0, nextVocabCounts[recordId] - 1)
        if (nextVocabCounts[recordId] === 0) {
          delete nextVocabCounts[recordId]
        }
      }
      return {
        vocabCounts: nextVocabCounts,
        totalVocabCount: Math.max(0, state.totalVocabCount - 1),
      }
    })
  },

  addRecord: () => {
    set((state) => ({
      totalArticleCount: state.totalArticleCount + 1,
    }))
  },

  removeRecord: (recordId: string) => {
    set((state) => {
      const nextFavorites = new Set(state.favoriteRecordIds)
      nextFavorites.delete(recordId)

      const nextVocabCounts = { ...state.vocabCounts }
      const removedVocabCount = nextVocabCounts[recordId] || 0
      delete nextVocabCounts[recordId]

      return {
        favoriteRecordIds: nextFavorites,
        vocabCounts: nextVocabCounts,
        totalArticleCount: Math.max(0, state.totalArticleCount - 1),
        totalVocabCount: Math.max(0, state.totalVocabCount - removedVocabCount),
      }
    })
  },

  initialize: () => {
    const favorites = getFavorites()
    const vocab = getVocabulary()
    const recordIds = getRecordIds()

    const vocabCounts: Record<string, number> = {}
    vocab.forEach((v) => {
      if (v.recordId) {
        vocabCounts[v.recordId] = (vocabCounts[v.recordId] || 0) + 1
      }
    })

    set({
      favoriteRecordIds: new Set(favorites.map((f) => f.recordId)),
      vocabCounts,
      totalVocabCount: vocab.length,
      totalArticleCount: recordIds.length,
    })
  },
}))
