import { View, Text } from '@tarojs/components'
import { useState, useEffect } from 'react'
import { fetchFeedbackList, FeedbackListItem, deleteFeedback } from '../../services/api/feedback.client'
import Taro from '@tarojs/taro'
import './my-feedback.scss'

const SCOPE_LABELS: Record<string, string> = {
  analysis_result: '结果反馈',
  annotation: '标注反馈',
  dictionary: '词典反馈',
  app: '功能反馈',
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: '待处理', color: 'var(--color-pending)' },
  adopted: { label: '已采纳', color: 'var(--color-success)' },
  resolved: { label: '已解决', color: 'var(--color-info)' },
  dismissed: { label: '已关闭', color: 'var(--text-muted)' },
}

export default function MyFeedbackPage() {
  const [items, setItems] = useState<FeedbackListItem[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadMore()
  }, [])

  const loadMore = async () => {
    if (loading) return
    setLoading(true)
    try {
      const res = await fetchFeedbackList({ cursor: cursor || undefined, limit: 20 })
      setItems(prev => [...prev, ...res.items])
      setCursor(res.cursor)
      setHasMore(res.hasMore)
    } catch {
      Taro.showToast({ title: '加载失败', icon: 'error', duration: 1500 })
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteFeedback(id)
      setItems(prev => prev.filter(item => item.id !== id))
      Taro.showToast({ title: '已删除', icon: 'success', duration: 1500 })
    } catch {
      Taro.showToast({ title: '删除失败', icon: 'error', duration: 1500 })
    }
  }

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}月${d.getDate()}日`
  }

  return (
    <View className='my-feedback'>
      {items.length === 0 && !loading && (
        <View className='my-feedback__empty'>
          <Text className='my-feedback__empty-text'>暂无反馈记录</Text>
        </View>
      )}

      {items.map(item => {
        const statusInfo = STATUS_LABELS[item.status] || STATUS_LABELS.pending
        return (
          <View key={item.id} className='my-feedback__item'>
            <View className='my-feedback__item-header'>
              <Text className='my-feedback__item-scope'>
                {SCOPE_LABELS[item.feedbackScope] || item.feedbackScope}
              </Text>
              <Text className='my-feedback__item-date'>{formatDate(item.createdAt)}</Text>
            </View>
            {item.content && (
              <Text className='my-feedback__item-content'>{item.content}</Text>
            )}
            <View className='my-feedback__item-footer'>
              <Text className='my-feedback__item-status' style={{ color: statusInfo.color }}>
                {statusInfo.label}
              </Text>
              {item.rewardPoints > 0 && (
                <Text className='my-feedback__item-reward'>+{item.rewardPoints} 积分</Text>
              )}
              {item.status === 'pending' && (
                <Text
                  className='my-feedback__item-delete'
                  onClick={() => handleDelete(item.id)}
                >
                  删除
                </Text>
              )}
            </View>
          </View>
        )
      })}

      {hasMore && (
        <View className='my-feedback__load-more' onClick={loadMore}>
          <Text className='my-feedback__load-more-text'>
            {loading ? '加载中...' : '加载更多'}
          </Text>
        </View>
      )}
    </View>
  )
}
