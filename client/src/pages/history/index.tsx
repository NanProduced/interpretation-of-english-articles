import { useEffect, useState, useCallback, useRef } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { getRecordIds, getRecord, deleteRecord, getVocabulary } from '../../services/storage'
import { useAuthStore } from '../../stores/auth'
import { fetchCloudRecords, deleteCloudRecord } from '../../services/api/records.client'
import { fetchCloudFavorites } from '../../services/api/favorites.client'
import type { AnalysisRecord } from '../../types/view/analysis-record.vm'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import { track } from '../../services/analytics'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

/** 格式化日期 */
function formatDate(timestamp: number): string {
  const now = Date.now()
  const diff = now - timestamp
  const oneDay = 24 * 60 * 60 * 1000

  if (diff < oneDay) {
    const hours = new Date(timestamp).getHours()
    const minutes = new Date(timestamp).getMinutes()
    return `今天 ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  } else if (diff < 2 * oneDay) {
    return '昨天'
  } else {
    const date = new Date(timestamp)
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}月${day}日`
  }
}

/** 读取显示用的前 50 字 */
function getDisplayTitle(sourceText: string): string {
  const firstLine = sourceText.split('\n')[0]
  return firstLine.length > 50 ? `${firstLine.slice(0, 50)}...` : firstLine
}

type FilterTab = 'all' | 'favorites' | 'vocab'

interface HistoryPageProps {
  isSubView?: boolean
  /** 外部传入默认 tab（如从生词本入口进入） */
  defaultTab?: FilterTab
}

export default function HistoryPage({ isSubView = false, defaultTab }: HistoryPageProps) {
  const [records, setRecords] = useState<AnalysisRecord[]>([])
  const [vocabList, setVocabList] = useState<VocabEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<FilterTab>(defaultTab || 'all')
  const { navBarHeight } = useLayoutStore()

  const filteredRecords = activeTab === 'favorites'
    ? records.filter((r) => r.isFavorited)
    : records

  const loadRecords = useCallback(async () => {
    setLoading(true)
    const { isLoggedIn } = useAuthStore.getState()

    if (isLoggedIn) {
      try {
        const [recordResult, favResult] = await Promise.all([
          fetchCloudRecords(),
          fetchCloudFavorites(),
        ])
        const favIds = new Set(favResult.items.map((f) => f.recordId))
        const merged: AnalysisRecord[] = recordResult.items.map((r) => ({
          ...r,
          isFavorited: favIds.has(r.recordId),
        }))
        setRecords(merged)
        track('view_history', { count: merged.length, source: 'cloud' })
        setLoading(false)
        return
      } catch {
        // 云端读取失败，降级到本地
      }
    }

    // 本地兜底
    const ids = getRecordIds()
    const loaded: AnalysisRecord[] = []
    for (const id of ids) {
      const record = getRecord(id)
      if (record) loaded.push(record)
    }
    setRecords(loaded)
    track('view_history', { count: loaded.length, source: 'local' })
    setLoading(false)
  }, [])

  // 加载生词本
  const loadVocab = useCallback(() => {
    const all = getVocabulary()
    setVocabList(all)
  }, [])

  useEffect(() => {
    loadRecords()
    loadVocab()
    // 读取 URL 参数，支持从外部跳转时指定 tab
    const pages = Taro.getCurrentPages()
    const current = pages[pages.length - 1]
    const params = (current as any).options || {}
    if (params.vtab && ['all', 'favorites', 'vocab'].includes(params.vtab)) {
      setActiveTab(params.vtab as FilterTab)
    }
  }, [loadRecords, loadVocab])

  // 下拉刷新（仅在非子视图模式下处理）
  const loadRecordsRef = useRef(loadRecords)
  useEffect(() => { loadRecordsRef.current = loadRecords }, [loadRecords])

  useEffect(() => {
    if (isSubView) return
    const handler = () => {
      loadRecordsRef.current()
      Taro.stopPullDownRefresh()
    }
    const page = Taro.getCurrentInstance().page
    if (!page) return
    ;(page as any).onPullDownRefresh(handler)
  }, [loadRecords, isSubView])

  const handleDelete = (recordId: string, e: any) => {
    e.stopPropagation()
    Taro.showModal({
      title: '删除记录',
      content: '确定要删除这条解读记录吗？',
      confirmText: '删除',
      confirmColor: '#ef4444',
      success: (res) => {
        if (res.confirm) {
          // 本地一定删
          deleteRecord(recordId)
          // 云端也同步删除（失败静默忽略）
          const { isLoggedIn } = useAuthStore.getState()
          if (isLoggedIn) {
            deleteCloudRecord(recordId).catch(() => {})
          }
          loadRecords()
        }
      },
    })
  }

  const goToResult = (recordId: string) => {
    Taro.navigateTo({ url: `/pages/result/index?recordId=${recordId}&mode=replay` })
  }

  const goToInput = () => {
    Taro.navigateTo({ url: '/pages/input/index' })
  }

  const handleVocabClick = (entry: VocabEntry) => {
    if (entry.recordId) {
      goToResult(entry.recordId)
    }
  }

  return (
    <View className={`history-page ${isSubView ? 'sub-view' : ''}`}>
      {!isSubView && <NavBar title='历史解读' />}
      {!isSubView && <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />}

      <View className='filter-tabs'>
        <View
          className={`filter-tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          <Text className='filter-tab-label'>全部</Text>
        </View>
        <View
          className={`filter-tab ${activeTab === 'favorites' ? 'active' : ''}`}
          onClick={() => setActiveTab('favorites')}
        >
          <Text className='filter-tab-label'>已收藏</Text>
        </View>
        <View
          className={`filter-tab ${activeTab === 'vocab' ? 'active' : ''}`}
          onClick={() => setActiveTab('vocab')}
        >
          <Text className='filter-tab-label'>生词本</Text>
        </View>
      </View>

      <ScrollView
        scrollY
        className='list-area'
      >
        {activeTab === 'vocab' ? (
          // 生词本 tab
          loading && vocabList.length === 0 ? null : vocabList.length === 0 ? (
            <View className='empty-state'>
              <Text className='empty-text'>暂无生词</Text>
              <View className='empty-action' onClick={goToInput}>
                <Text className='empty-sub'>去读一篇文章，记下不认识的词吧 →</Text>
              </View>
            </View>
          ) : (
            vocabList.map((entry) => (
              <View
                key={entry.id}
                className='history-card'
                onClick={() => handleVocabClick(entry)}
              >
                <View className='card-header'>
                  <Text className='item-title'>{entry.word}</Text>
                  <Text className='config-tag' style={{ fontSize: '22rpx' }}>
                    {entry.partOfSpeech}
                  </Text>
                </View>
                <View className='card-footer'>
                  <Text className='date-text' style={{ flex: 1 }}>{entry.meaning}</Text>
                </View>
              </View>
            ))
          )
        ) : (
          // 全部 / 已收藏 tab
          loading && records.length === 0 ? null : filteredRecords.length === 0 ? (
            <View className='empty-state'>
              <Text className='empty-text'>
                {activeTab === 'favorites' ? '暂无收藏记录' : '暂无解读记录'}
              </Text>
              {activeTab === 'all' && (
                <View className='empty-action' onClick={goToInput}>
                  <Text className='empty-sub'>去粘贴一篇文章试试吧 →</Text>
                </View>
              )}
            </View>
          ) : (
            filteredRecords.map((record) => (
              <View
                key={record.recordId}
                className='history-card'
                onClick={() => goToResult(record.recordId)}
              >
                <View className='card-header'>
                  <Text className='item-title'>{getDisplayTitle(record.sourceText)}</Text>
                  <View className='delete-btn' onClick={(e) => handleDelete(record.recordId, e)}>
                    <Text className='delete-icon'>×</Text>
                  </View>
                </View>
                <View className='card-footer'>
                  <Text className='date-text'>{formatDate(record.createdAt)}</Text>
                  <View className='tag-row'>
                    {record.isFavorited && (
                      <View className='fav-tag'>
                        <Text>★ 已收藏</Text>
                      </View>
                    )}
                    <Text className='config-tag'>
                      {record.requestPayload.reading_variant.toUpperCase()}
                    </Text>
                  </View>
                </View>
              </View>
            ))
          )
        )}
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {!isSubView && <TabBar current='history' />}
    </View>
  )
}
