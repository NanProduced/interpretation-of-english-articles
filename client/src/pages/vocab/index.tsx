/**
 * 生词本页面
 *
 * 展示用户收藏的单词列表，支持云端同步。
 * 点击单词可跳转回原文记录。
 */

import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useAuthStore } from '../../stores/auth'
import { getVocabulary, removeVocabEntry } from '../../services/storage'
import { fetchCloudVocabulary, deleteCloudVocabulary } from '../../services/api/vocabulary.client'
import type { VocabEntry } from '../../types/view/vocabulary.vm'
import { track } from '../../services/analytics'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

interface VocabPageProps {
  isSubView?: boolean
}

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
  } else if (diff < 7 * oneDay) {
    return `${Math.floor(diff / oneDay)}天前`
  } else {
    const date = new Date(timestamp)
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}月${day}日`
  }
}

export default function VocabPage({ isSubView = false }: VocabPageProps) {
  const [vocabList, setVocabList] = useState<VocabEntry[]>([])
  const [loading, setLoading] = useState(true)
  const { navBarHeight } = useLayoutStore()
  const loadVocabRef = useRef<() => Promise<void>>()

  /** 加载生词本：云端优先，失败降级本地 */
  const loadVocab = useCallback(async () => {
    setLoading(true)
    const { isLoggedIn } = useAuthStore.getState()

    if (isLoggedIn) {
      try {
        const result = await fetchCloudVocabulary(1, 100)
        setVocabList(result.items)
        track('view_vocab', { count: result.total, source: 'cloud' })
        setLoading(false)
        return
      } catch {
        // 云端读取失败，降级到本地
      }
    }

    // 本地兜底
    const local = getVocabulary()
    setVocabList(local)
    track('view_vocab', { count: local.length, source: 'local' })
    setLoading(false)
  }, [])

  useEffect(() => {
    loadVocabRef.current = loadVocab
  }, [loadVocab])

  // 启动时加载
  useEffect(() => {
    loadVocab()
  }, [loadVocab])

  // 下拉刷新
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

  /** 跳转回原文记录 */
  const goToResult = (recordId: string) => {
    if (recordId) {
      Taro.navigateTo({ url: `/pages/result/index?recordId=${recordId}&mode=replay` })
    }
  }

  /** 删除生词 */
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
          // 本地一定删
          removeVocabEntry(entry.id)
          // 云端也同步删除（失败静默忽略）
          const { isLoggedIn } = useAuthStore.getState()
          if (isLoggedIn) {
            deleteCloudVocabulary(entry.id).catch(() => {})
          }
          // 更新列表
          setVocabList((prev) => prev.filter((v) => v.id !== entry.id))
        }
      },
    })
  }

  const goToInput = () => {
    Taro.navigateTo({ url: '/pages/input/index' })
  }

  return (
    <View className={`vocab-page ${isSubView ? 'sub-view' : ''}`}>
      {!isSubView && <NavBar title='生词本' />}
      {!isSubView && <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />}

      <ScrollView scrollY className='list-area'>
        {loading && vocabList.length === 0 ? (
          <View className='loading-state'>
            <Text className='loading-text'>加载中...</Text>
          </View>
        ) : vocabList.length === 0 ? (
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
              className='vocab-card'
              onClick={() => entry.recordId && goToResult(entry.recordId)}
            >
              <View className='card-header'>
                <Text className='word-text'>{entry.word}</Text>
                {entry.partOfSpeech && (
                  <Text className='pos-tag'>{entry.partOfSpeech}</Text>
                )}
                {entry.mastered && (
                  <Text className='mastered-tag'>已掌握</Text>
                )}
                <View
                  className='delete-btn'
                  onClick={(e) => handleDelete(entry, e)}
                >
                  <Text className='delete-icon'>×</Text>
                </View>
              </View>
              <View className='card-footer'>
                <Text className='meaning-text'>{entry.meaning}</Text>
                <Text className='date-text'>{formatDate(entry.addedAt)}</Text>
              </View>
            </View>
          ))
        )}
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {!isSubView && <TabBar current='profile' />}
    </View>
  )
}
