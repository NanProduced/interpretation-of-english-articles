import { View, Text } from '@tarojs/components'
import { useState, useEffect, useMemo } from 'react'
import { fetchCreditLedger, LedgerEntry } from '../../services/api/credit.client'
import { useAuthStore } from '../../stores/auth'
import { useLayoutStore } from '../../stores/layout'
import NavBar from '../../components/NavBar'
import LucideIcon from '../../components/LucideIcon'
import './index.scss'

const TYPE_CONFIG: Record<string, { label: string; icon: string; iconColor: string }> = {
  analysis_deduct: { label: '分析扣减', icon: 'minusCircle', iconColor: 'var(--color-danger)' },
  feedback_reward: { label: '反馈奖励', icon: 'gift', iconColor: '#059669' },
  daily_grant: { label: '每日发放', icon: 'plusCircle', iconColor: '#059669' },
  bonus_grant: { label: '奖励到账', icon: 'sparkles', iconColor: '#D97706' },
  refund: { label: '积分退回', icon: 'refreshCw', iconColor: 'var(--color-info)' },
  manual_adjust: { label: '管理员调整', icon: 'settings', iconColor: 'var(--reader-subtle)' },
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
  isUniformType: boolean
}

function groupByDate(entries: LedgerEntry[]): GroupedEntries[] {
  const groups: GroupedEntries[] = []
  let currentLabel = ''
  let currentEntries: LedgerEntry[] = []

  for (const entry of entries) {
    const label = formatDateGroup(entry.createdAt)
    if (label !== currentLabel) {
      if (currentEntries.length > 0) {
        const types = new Set(currentEntries.map(e => e.entryType))
        groups.push({ dateLabel: currentLabel, entries: currentEntries, isUniformType: types.size === 1 })
      }
      currentLabel = label
      currentEntries = []
    }
    currentEntries.push(entry)
  }
  if (currentEntries.length > 0) {
    const types = new Set(currentEntries.map(e => e.entryType))
    groups.push({ dateLabel: currentLabel, entries: currentEntries, isUniformType: types.size === 1 })
  }
  return groups
}

export default function CreditDetailPage() {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const { navBarHeight } = useLayoutStore()

  useEffect(() => {
    if (isLoggedIn) loadMore()
  }, [isLoggedIn])

  const loadMore = async () => {
    if (loading) return
    setLoading(true)
    try {
      const res = await fetchCreditLedger({ cursor: cursor || undefined, limit: 20 })
      setEntries(prev => [...prev, ...res.items])
      setCursor(res.cursor)
      setHasMore(res.hasMore)
    } catch (e) {
      console.error("index.tsx:", e)
    } finally {
      setLoading(false)
    }
  }

  const summary = useMemo(() => {
    const totalDeducted = entries
      .filter(e => e.points < 0 && e.entryType === 'analysis_deduct')
      .reduce((sum, e) => sum + Math.abs(e.points), 0)
    const todayDeducted = entries
      .filter(e => {
        if (e.points >= 0 || e.entryType !== 'analysis_deduct') return false
        const diff = (Date.now() - new Date(e.createdAt).getTime()) / (1000 * 60 * 60 * 24)
        return diff < 1
      })
      .reduce((sum, e) => sum + Math.abs(e.points), 0)
    const lastBalance = entries.length > 0 ? entries[0].balanceAfter : null
    return { totalDeducted, todayDeducted, lastBalance }
  }, [entries])

  const groups = groupByDate(entries)

  const cleanDescription = (entry: LedgerEntry): string => {
    const prefix = `${TYPE_CONFIG[entry.entryType]?.label || entry.entryType}，`
    if (entry.description.startsWith(prefix)) {
      return entry.description.slice(prefix.length)
    }
    return entry.description
  }

  return (
    <View className='credit-detail'>
      <NavBar
        title='积分记录'
        showBack
        background='var(--reader-paper, #FAF9F6)'
        color='var(--text-primary, #111111)'
      />
      <View className='nav-spacer' style={{ height: navBarHeight + 'px' }} />
      <View className='credit-detail__summary'>
        <View className='credit-detail__summary-item'>
          <Text className='credit-detail__summary-label'>当前余额</Text>
          <Text className='credit-detail__summary-value'>{summary.lastBalance ?? '--'}</Text>
        </View>
        <View className='credit-detail__summary-divider' />
        <View className='credit-detail__summary-item'>
          <Text className='credit-detail__summary-label'>今日消耗</Text>
          <Text className={`credit-detail__summary-value ${summary.todayDeducted > 0 ? 'credit-detail__summary-value--danger' : ''}`}>
            -{summary.todayDeducted}
          </Text>
        </View>
      </View>

      {groups.length > 0 && (
        <View className='credit-detail__list'>
          {groups.map(group => (
            <View key={group.dateLabel} className='credit-detail__group'>
              <Text className='credit-detail__date-label'>{group.dateLabel}</Text>
              {group.entries.map(entry => {
                const config = TYPE_CONFIG[entry.entryType] || { label: entry.entryType, icon: 'circle', iconColor: 'var(--reader-subtle)' }
                const isPositive = entry.points > 0
                const desc = cleanDescription(entry)
                const showLabel = !group.isUniformType

                return (
                  <View key={entry.id} className='credit-detail__entry'>
                    <View className='credit-detail__entry-left'>
                      <View className='credit-detail__entry-icon-wrap'>
                        <LucideIcon name={config.icon as any} size={32} color={config.iconColor} strokeWidth={2} />
                      </View>
                      <View className='credit-detail__entry-info'>
                        {showLabel && (
                          <Text className='credit-detail__entry-label'>{config.label}</Text>
                        )}
                        <Text className='credit-detail__entry-desc'>{desc}</Text>
                        {entry.articleTitle && !desc.includes(entry.articleTitle.slice(0, 8)) && (
                          <Text className='credit-detail__entry-article'>《{entry.articleTitle.slice(0, 28)}》</Text>
                        )}
                      </View>
                    </View>
                    <View className='credit-detail__entry-right'>
                      <Text className={`credit-detail__entry-points ${isPositive ? 'credit-detail__entry-points--plus' : ''}`}>
                        {isPositive ? '+' : ''}{entry.points}
                      </Text>
                      <Text className='credit-detail__entry-time'>{formatTime(entry.createdAt)}</Text>
                    </View>
                  </View>
                )
              })}
            </View>
          ))}
        </View>
      )}

      {hasMore && (
        <View className='credit-detail__load-more' onClick={loadMore}>
          <Text className='credit-detail__load-more-text'>
            {loading ? '加载中...' : '加载更多'}
          </Text>
        </View>
      )}

      {entries.length === 0 && !loading && (
        <View className='credit-detail__empty'>
          <View className='credit-detail__empty-icon'>
            <LucideIcon name='ticket' size={56} color='var(--reader-subtle)' strokeWidth={1.2} />
          </View>
          <Text className='credit-detail__empty-title'>暂无积分记录</Text>
          <Text className='credit-detail__empty-desc'>阅读文章时会消耗积分，记录会显示在这里</Text>
        </View>
      )}
    </View>
  )
}
