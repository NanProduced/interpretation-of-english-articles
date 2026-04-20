import { View, Text } from '@tarojs/components'
import { useState, useEffect } from 'react'
import { fetchCreditLedger, LedgerEntry } from '../../services/api/credit.client'
import './index.scss'

const ENTRY_TYPE_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  analysis_deduct: { label: '分析扣减', color: '#e53935', icon: '🔴' },
  feedback_reward: { label: '反馈奖励', color: '#4caf50', icon: '🟢' },
  daily_grant: { label: '每日发放', color: '#4caf50', icon: '🟢' },
  bonus_grant: { label: '奖励到账', color: '#4caf50', icon: '🟢' },
  refund: { label: '积分退回', color: '#2196f3', icon: '🔵' },
  manual_adjust: { label: '管理员调整', color: '#999', icon: '⚪' },
}

function formatDateGroup(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diff = (today.getTime() - target.getTime()) / (1000 * 60 * 60 * 24)

  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff < 7) return `${Math.floor(diff)}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

interface GroupedEntries {
  dateLabel: string
  entries: LedgerEntry[]
}

function groupByDate(entries: LedgerEntry[]): GroupedEntries[] {
  const groups: GroupedEntries[] = []
  let currentLabel = ''
  let currentEntries: LedgerEntry[] = []

  for (const entry of entries) {
    const label = formatDateGroup(entry.createdAt)
    if (label !== currentLabel) {
      if (currentEntries.length > 0) {
        groups.push({ dateLabel: currentLabel, entries: currentEntries })
      }
      currentLabel = label
      currentEntries = []
    }
    currentEntries.push(entry)
  }
  if (currentEntries.length > 0) {
    groups.push({ dateLabel: currentLabel, entries: currentEntries })
  }
  return groups
}

export default function CreditDetailPage() {
  const [entries, setEntries] = useState<LedgerEntry[]>([])
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
      const res = await fetchCreditLedger({ cursor: cursor || undefined, limit: 20 })
      setEntries(prev => [...prev, ...res.items])
      setCursor(res.cursor)
      setHasMore(res.hasMore)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const groups = groupByDate(entries)

  return (
    <View className='credit-detail'>
      {groups.map(group => (
        <View key={group.dateLabel} className='credit-detail__group'>
          <View className='credit-detail__date-header'>
            <Text className='credit-detail__date-label'>{group.dateLabel}</Text>
          </View>
          {group.entries.map(entry => {
            const config = ENTRY_TYPE_CONFIG[entry.entryType] || { label: entry.entryType, color: '#999', icon: '⚪' }
            const isPositive = entry.points > 0
            return (
              <View key={entry.id} className='credit-detail__entry'>
                <View className='credit-detail__entry-left'>
                  <Text className='credit-detail__entry-icon'>{config.icon}</Text>
                  <View className='credit-detail__entry-info'>
                    <Text className='credit-detail__entry-label'>{config.label}</Text>
                    <Text className='credit-detail__entry-desc'>{entry.description}</Text>
                    {entry.articleTitle && (
                      <Text className='credit-detail__entry-article'>《{entry.articleTitle.slice(0, 30)}》</Text>
                    )}
                  </View>
                </View>
                <View className='credit-detail__entry-right'>
                  <Text className='credit-detail__entry-points' style={{ color: isPositive ? '#4caf50' : '#e53935' }}>
                    {isPositive ? '+' : ''}{entry.points}
                  </Text>
                  <Text className='credit-detail__entry-time'>{formatTime(entry.createdAt)}</Text>
                </View>
              </View>
            )
          })}
        </View>
      ))}

      {hasMore && (
        <View className='credit-detail__load-more' onClick={loadMore}>
          <Text className='credit-detail__load-more-text'>
            {loading ? '加载中...' : '加载更多'}
          </Text>
        </View>
      )}

      {entries.length === 0 && !loading && (
        <View className='credit-detail__empty'>
          <Text className='credit-detail__empty-text'>暂无积分记录</Text>
        </View>
      )}
    </View>
  )
}
