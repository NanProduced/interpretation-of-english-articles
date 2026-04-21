/**
 * 生词本页面
 *
 * 展示用户收藏的单词列表，支持搜索、筛选和云端同步。
 * 点击单词弹出详情视图。
 */

import { View, Text, ScrollView, Input } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { ROUTES } from '../../config/routes'
import { useEffect, useState, useCallback, useRef, useMemo } from 'react'
import { useAuthStore } from '../../stores/auth'
import { getVocabulary, removeVocabEntry, updateVocabEntry } from '../../services/storage'
import { CloudSyncService } from '../../services/cloudSync.service'
import { fetchCloudVocabulary } from '../../services/api/vocabulary.client'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import { track } from '../../services/analytics'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import VocabDetailView from '../../components/VocabDetailView'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

interface VocabPageProps {
  isSubView?: boolean
}

type SortMode = 'time' | 'alpha'
type FilterStatus = 'all' | 'new' | 'learning' | 'mastered'

const FILTER_OPTIONS: { value: FilterStatus; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'new', label: '新词' },
  { value: 'learning', label: '学习中' },
  { value: 'mastered', label: '已掌握' },
]

import { formatDate } from '../../utils/formatDate'

function mergeVocabCloudWithLocal(cloudItems: VocabEntry[], localItems: VocabEntry[]): VocabEntry[] {
  const localByLemma = new Map<string, VocabEntry>()
  for (const item of localItems) {
    const key = (item.lemma || item.word).toLowerCase()
    localByLemma.set(key, item)
  }

  const result: VocabEntry[] = []
  const seenLemmas = new Set<string>()

  for (const cloud of cloudItems) {
    const key = (cloud.lemma || cloud.word).toLowerCase()
    seenLemmas.add(key)
    const local = localByLemma.get(key)

    if (!local) {
      result.push(cloud)
      continue
    }

    if (local.tombstone) continue
    if (local.pendingOp === 'delete') continue
    if (local.pendingOp === 'create' || local.pendingOp === 'update') {
      result.push(local)
      continue
    }
    if (local.syncState === 'local_only') {
      result.push(local)
      continue
    }

    result.push({ ...cloud, mastered: local.mastered !== cloud.mastered ? local.mastered : cloud.mastered })
  }

  for (const local of localItems) {
    if (local.tombstone) continue
    const key = (local.lemma || local.word).toLowerCase()
    if (seenLemmas.has(key)) continue
    if (local.pendingOp === 'delete') continue
    result.push(local)
  }

  return result
}

function getMasteryStatus(entry: VocabEntry): string {
  if (entry.mastered) return 'mastered'
  const age = Date.now() - entry.addedAt
  const oneDay = 24 * 60 * 60 * 1000
  if (age < 7 * oneDay) return 'new'
  return 'learning'
}

export default function VocabPage({ isSubView = false }: VocabPageProps) {
  const [vocabList, setVocabList] = useState<VocabEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [popupEntry, setPopupEntry] = useState<VocabEntry | null>(null)
  const { navBarHeight } = useLayoutStore()
  const loadVocabRef = useRef<() => Promise<void>>()

  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [sortMode, setSortMode] = useState<SortMode>('time')
  const [showFilterPanel, setShowFilterPanel] = useState(false)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadVocab = useCallback(async () => {
    setLoading(true)
    const { isLoggedIn } = useAuthStore.getState()

    if (isLoggedIn) {
      try {
        let allCloudItems: VocabEntry[] = []
        let page = 1
        const pageSize = 100
        let hasMore = true
        while (hasMore) {
          const result = await fetchCloudVocabulary(page, pageSize)
          allCloudItems = allCloudItems.concat(result.items)
          hasMore = allCloudItems.length < result.total
          page++
        }
        const localItems = getVocabulary()
        const merged = mergeVocabCloudWithLocal(allCloudItems, localItems)
        setVocabList(merged)
        track('view_vocab', { count: merged.length, source: 'cloud_merged' })
        setLoading(false)
        return
      } catch {
        // fallback to local
      }
    }

    const local = getVocabulary()
    setVocabList(local)
    track('view_vocab', { count: local.length, source: 'local' })
    setLoading(false)
  }, [])

  useEffect(() => {
    loadVocabRef.current = loadVocab
  }, [loadVocab])

  useEffect(() => {
    loadVocab()
  }, [loadVocab])

  useDidShow(loadVocab)

  useEffect(() => {
    if (isSubView) return
    const handler = () => {
      loadVocabRef.current?.()
      Taro.stopPullDownRefresh()
    }
    const page = Taro.getCurrentInstance().page
    if (!page) return
    ;(page as any).onPullDownRefresh(handler)
  }, [isSubView])

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, 300)
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    }
  }, [searchQuery])

  const filteredList = useMemo(() => {
    let list = vocabList

    if (debouncedQuery) {
      const q = debouncedQuery.toLowerCase()
      list = list.filter((v) => {
        if (v.lemma?.toLowerCase().startsWith(q)) return true
        if (v.word.toLowerCase().startsWith(q)) return true
        if (v.collectedForms?.some(f => f.toLowerCase().startsWith(q))) return true
        if (v.meaning?.toLowerCase().includes(q)) return true
        return false
      })
    }

    if (filterStatus !== 'all') {
      list = list.filter((v) => getMasteryStatus(v) === filterStatus)
    }

    if (sortMode === 'alpha') {
      list = [...list].sort((a, b) => (a.lemma || a.word).localeCompare(b.lemma || b.word))
    }

    return list
  }, [vocabList, debouncedQuery, filterStatus, sortMode])

  const goToResult = (recordId: string, sentenceId?: string, e?: any) => {
    if (e) e.stopPropagation()
    if (!recordId) return
    let url = `${ROUTES.RESULT}?recordId=${recordId}&mode=replay`
    if (sentenceId) url += `&sentenceId=${sentenceId}`
    Taro.navigateTo({ url })
    if (popupEntry) setPopupEntry(null)
  }

  const handleDelete = (entry: VocabEntry, e: any) => {
    e.stopPropagation()
    Taro.showModal({
      title: '删除生词',
      content: `确定要删除「${entry.word}」吗？`,
      confirmText: '删除',
      confirmColor: '#ef4444',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          removeVocabEntry(entry.id)
          CloudSyncService.syncDeleteVocab(entry.id, entry.lemma || entry.word)
          setVocabList((prev) => prev.filter((v) => v.id !== entry.id))
        }
      },
    })
  }

  const handleToggleMastery = (entry: VocabEntry) => {
    const newMastered = !entry.mastered
    const newStatus = newMastered ? 'mastered' : 'learning'

    updateVocabEntry(entry.id, { mastered: newMastered })

    setVocabList(prev => prev.map(v => v.id === entry.id ? { ...v, mastered: newMastered } : v))
    if (popupEntry && popupEntry.id === entry.id) {
      setPopupEntry({ ...popupEntry, mastered: newMastered })
    }

    CloudSyncService.syncVocabMastery(entry.id, newStatus, entry.lemma || entry.word)

    Taro.showToast({ title: newMastered ? '已标记掌握' : '已取消掌握', icon: 'success' })
  }

  const goToInput = () => {
    Taro.navigateTo({ url: ROUTES.INPUT })
  }

  const handleSearchInput = (e: any) => {
    setSearchQuery(e.detail.value || '')
  }

  const clearSearch = () => {
    setSearchQuery('')
    setDebouncedQuery('')
  }

  return (
    <View className={`vocab-page ${isSubView ? 'sub-view' : ''}`}>
      {!isSubView && <NavBar title='生词本' />}
      {!isSubView && <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />}

      <View className='search-bar'>
        <View className='search-input-wrap'>
          <LucideIcon name='search' size={16} color='var(--text-muted)' />
          <Input
            className='search-input'
            type='text'
            placeholder='搜索单词或释义'
            placeholderClass='search-placeholder'
            value={searchQuery}
            onInput={handleSearchInput}
            confirmType='search'
          />
          {searchQuery && (
            <View className='search-clear' onClick={clearSearch}>
              <LucideIcon name='x' size={14} color='var(--text-muted)' />
            </View>
          )}
        </View>
        <View
          className={`filter-btn ${showFilterPanel ? 'active' : ''}`}
          onClick={() => setShowFilterPanel(!showFilterPanel)}
        >
          <LucideIcon name='slidersHorizontal' size={18} color={showFilterPanel ? 'var(--color-ink)' : 'var(--text-sub)'} />
        </View>
      </View>

      {showFilterPanel && (
        <View className='filter-panel'>
          <View className='filter-row'>
            <Text className='filter-label'>状态</Text>
            <View className='filter-chips'>
              {FILTER_OPTIONS.map(opt => (
                <View
                  key={opt.value}
                  className={`filter-chip ${filterStatus === opt.value ? 'active' : ''}`}
                  onClick={() => setFilterStatus(opt.value)}
                >
                  <Text>{opt.label}</Text>
                </View>
              ))}
            </View>
          </View>
          <View className='filter-row'>
            <Text className='filter-label'>排序</Text>
            <View className='filter-chips'>
              <View
                className={`filter-chip ${sortMode === 'time' ? 'active' : ''}`}
                onClick={() => setSortMode('time')}
              >
                <Text>按时间</Text>
              </View>
              <View
                className={`filter-chip ${sortMode === 'alpha' ? 'active' : ''}`}
                onClick={() => setSortMode('alpha')}
              >
                <Text>按字母</Text>
              </View>
            </View>
          </View>
        </View>
      )}

      {debouncedQuery && (
        <View className='search-result-hint'>
          <Text className='search-result-text'>
            {filteredList.length > 0
              ? `找到 ${filteredList.length} 个结果`
              : '未找到匹配的生词'}
          </Text>
        </View>
      )}

      <ScrollView scrollY className='list-area'>
        {loading && vocabList.length === 0 ? (
          <View className='loading-state'>
            <Text className='loading-text'>加载中...</Text>
          </View>
        ) : filteredList.length === 0 ? (
          <View className='empty-state'>
            <Text className='empty-text'>{debouncedQuery ? '未找到匹配的生词' : '暂无生词'}</Text>
            {!debouncedQuery && (
              <View className='empty-action' onClick={goToInput}>
                <Text className='empty-sub'>去读一篇文章，记下不认识的词吧 →</Text>
              </View>
            )}
          </View>
        ) : (
          filteredList.map((entry, index) => {
            const sourceCount = entry.sourceRefs?.length || 0
            const primaryRef = entry.sourceRefs?.[0]

            return (
              <View
                key={entry.id}
                className='vocab-card'
                style={{
                  animation: `slideInUp 0.6s var(--ease-spring) both`,
                  animationDelay: `${index * 0.05}s`
                }}
                onClick={() => setPopupEntry(entry)}
              >
                <View className='card-header'>
                  <View className='word-group'>
                    <Text className='word-text'>{entry.word}</Text>
                    {entry.phonetic && (
                      <Text className='phonetic-text'>/{entry.phonetic}/</Text>
                    )}
                  </View>
                  <View className='card-header-right'>
                    {sourceCount > 1 && (
                      <Text className='source-count-badge'>{sourceCount} 篇</Text>
                    )}
                    {entry.mastered && (
                      <Text className='mastered-tag'>已掌握</Text>
                    )}
                    <View
                      className='delete-btn'
                      onClick={(e) => handleDelete(entry, e)}
                    >
                      <LucideIcon name='trash2' size={18} color='var(--text-muted)' />
                    </View>
                  </View>
                </View>
                <View className='card-body'>
                  <View className='meaning-row'>
                    {entry.partOfSpeech && (
                      <Text className='pos-tag'>{entry.partOfSpeech}</Text>
                    )}
                    <Text className='meaning-text'>{entry.meaning}</Text>
                  </View>
                  {(primaryRef?.sourceSentence || entry.sentence) && (
                    <View className='context-box'>
                      <Text className='context-text'>"{primaryRef?.sourceSentence || entry.sentence}"</Text>
                      {sourceCount > 1 && (
                        <Text className='more-context'>还有 {sourceCount - 1} 个语境</Text>
                      )}
                    </View>
                  )}
                </View>
                <View className='card-footer'>
                  <Text className='date-text'>收藏于 {formatDate(entry.addedAt)}</Text>
                  {primaryRef?.clientRecordId && (
                    <View className='source-link' onClick={(e) => goToResult(primaryRef.clientRecordId, primaryRef.sourceSentenceId, e)}>
                      <Text>查看原文</Text>
                      <LucideIcon name='chevronRight' size={14} color='currentColor' />
                    </View>
                  )}
                </View>
              </View>
            )
          })
        )}
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {!isSubView && <TabBar current='profile' />}

      <VocabDetailView
        visible={!!popupEntry}
        entry={popupEntry}
        onClose={() => setPopupEntry(null)}
        onGoToResult={goToResult}
        onToggleMastery={handleToggleMastery}
      />
    </View>
  )
}
