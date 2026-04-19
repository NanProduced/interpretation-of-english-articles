/**
 * 生词本页面
 *
 * 展示用户收藏的单词列表，支持云端同步。
 * 点击单词可跳转回原文记录。
 */

import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useAuthStore } from '../../stores/auth'
import { getVocabulary, removeVocabEntry, getRecord, updateVocabEntry } from '../../services/storage'
import { fetchCloudVocabulary, deleteCloudVocabulary, updateCloudVocabulary } from '../../services/api/vocabulary.client'
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
  const [popupEntry, setPopupEntry] = useState<VocabEntry | null>(null)
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

  useDidShow(loadVocab)

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
  const goToResult = (recordId: string, e?: any) => {
    if (e) e.stopPropagation()
    if (!recordId) return
    Taro.navigateTo({ url: `/pages/result/index?recordId=${recordId}&mode=replay` })
    // 如果是从弹窗跳走，顺便关闭弹窗
    if (popupEntry) setPopupEntry(null)
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
          removeVocabEntry(entry.id)
          const { isLoggedIn } = useAuthStore.getState()
          if (isLoggedIn) {
            deleteCloudVocabulary(entry.id).catch((err) => {
               console.error('[Vocab] delete cloud failed', err)
            })
          }
          setVocabList((prev) => prev.filter((v) => v.id !== entry.id))
        }
      },
    })
  }

  /** 切换掌握状态 */
  const handleToggleMastery = (entry: VocabEntry) => {
    const newMastered = !entry.mastered
    const newStatus = newMastered ? 'mastered' : 'learning'
    
    // 更新本地
    updateVocabEntry(entry.id, { mastered: newMastered })
    
    // 更新列表和弹窗状态
    setVocabList(prev => prev.map(v => v.id === entry.id ? { ...v, mastered: newMastered } : v))
    if (popupEntry && popupEntry.id === entry.id) {
      setPopupEntry({ ...popupEntry, mastered: newMastered })
    }

    // 同步云端
    const { isLoggedIn } = useAuthStore.getState()
    if (isLoggedIn) {
      updateCloudVocabulary(entry.id, { mastery_status: newStatus }).catch(() => {})
    }
    
    Taro.showToast({ title: newMastered ? '已标记掌握' : '已取消掌握', icon: 'success' })
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
          vocabList.map((entry, index) => (
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
              <View className='card-body'>
                <View className='meaning-row'>
                  {entry.partOfSpeech && (
                    <Text className='pos-tag'>{entry.partOfSpeech}</Text>
                  )}
                  <Text className='meaning-text'>{entry.meaning}</Text>
                </View>
                {entry.sentence && (
                  <View className='context-box'>
                    <Text className='context-text'>"{entry.sentence}"</Text>
                  </View>
                )}
              </View>
              <View className='card-footer'>
                <Text className='date-text'>收藏于 {formatDate(entry.addedAt)}</Text>
                {entry.recordId && (
                  <View className='source-link' onClick={(e) => goToResult(entry.recordId, e)}>
                    <Text>查看原文</Text>
                    <LucideIcon name='chevronRight' size={14} color='currentColor' />
                  </View>
                )}
              </View>
            </View>
          ))
        )}
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {!isSubView && <TabBar current='profile' />}

      {/* 沉浸式单词详情页 */}
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
