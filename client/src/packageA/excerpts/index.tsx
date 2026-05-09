import { useCallback, useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { ROUTES } from '../../config/routes'
import { ensureLoggedIn } from '../../services/auth'
import { useAuthStore } from '../../stores/auth'
import { fetchCloudFavoriteItems, FavoriteItemDto } from '../../services/api/favorites.client'
import { listUserAnnotations, UserAnnotationDto } from '../../services/api/user-annotations.client'
import NavBar from '../../components/NavBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

interface SentenceAsset {
  key: string
  recordId?: string | null
  cloudRecordId?: string | null
  sentenceId?: string
  sourceTitle: string
  text: string
  translation?: string
  note?: string
  color?: string
  isFavorited: boolean
  isHighlighted: boolean
  updatedAt: string
}

interface ArticleGroup {
  key: string
  title: string
  recordId?: string | null
  cloudRecordId?: string | null
  updatedAt: string
  items: SentenceAsset[]
}

function getPayloadString(payload: Record<string, unknown> | undefined, key: string): string | undefined {
  if (!payload) return undefined
  const value = payload[key]
  return typeof value === 'string' && value.trim() ? value : undefined
}

function getFavoriteSentenceKey(item: FavoriteItemDto): string {
  return item.target_key || `${item.analysis_record_id || 'record'}:${getPayloadString(item.payload_json, 'sentence_id') || item.id}`
}

function getAnnotationSentenceKey(item: UserAnnotationDto): string {
  return item.target_key || `${item.analysis_record_id || 'record'}:${item.sentence_id}`
}

function upsertAsset(map: Map<string, SentenceAsset>, key: string, patch: Partial<SentenceAsset> & Pick<SentenceAsset, 'sourceTitle' | 'text' | 'updatedAt'>) {
  const current = map.get(key)
  map.set(key, {
    key,
    recordId: patch.recordId ?? current?.recordId,
    cloudRecordId: patch.cloudRecordId ?? current?.cloudRecordId,
    sentenceId: patch.sentenceId ?? current?.sentenceId,
    sourceTitle: patch.sourceTitle || current?.sourceTitle || '未命名文章',
    text: patch.text || current?.text || '',
    translation: patch.translation ?? current?.translation,
    note: patch.note ?? current?.note,
    color: patch.color ?? current?.color,
    isFavorited: patch.isFavorited ?? current?.isFavorited ?? false,
    isHighlighted: patch.isHighlighted ?? current?.isHighlighted ?? false,
    updatedAt: new Date(patch.updatedAt).getTime() > new Date(current?.updatedAt || 0).getTime()
      ? patch.updatedAt
      : current?.updatedAt || patch.updatedAt,
  })
}

function buildSentenceAssets(favorites: FavoriteItemDto[], annotations: UserAnnotationDto[]): SentenceAsset[] {
  const map = new Map<string, SentenceAsset>()

  favorites.forEach(item => {
    if (item.target_type !== 'sentence') return
    const text = getPayloadString(item.payload_json, 'text')
    if (!text) return
    const key = getFavoriteSentenceKey(item)
    upsertAsset(map, key, {
      recordId: getPayloadString(item.payload_json, 'client_record_id') || item.analysis_record_id,
      cloudRecordId: item.analysis_record_id,
      sentenceId: getPayloadString(item.payload_json, 'sentence_id'),
      sourceTitle: getPayloadString(item.payload_json, 'article_title') || '未命名文章',
      text,
      translation: getPayloadString(item.payload_json, 'translation'),
      isFavorited: true,
      updatedAt: item.updated_at || item.created_at,
    })
  })

  annotations.forEach(item => {
    if (item.anchor_type !== 'sentence') return
    const key = getAnnotationSentenceKey(item)
    upsertAsset(map, key, {
      recordId: getPayloadString(item.payload_json, 'client_record_id') || item.analysis_record_id,
      cloudRecordId: item.analysis_record_id,
      sentenceId: item.sentence_id,
      sourceTitle: getPayloadString(item.payload_json, 'article_title') || '未命名文章',
      text: item.selected_text,
      translation: getPayloadString(item.payload_json, 'translation'),
      note: item.note || undefined,
      color: item.color,
      isHighlighted: true,
      updatedAt: item.updated_at || item.created_at,
    })
  })

  return Array.from(map.values())
    .filter(item => item.text)
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
}

function groupByArticle(items: SentenceAsset[]): ArticleGroup[] {
  const groups = new Map<string, ArticleGroup>()
  items.forEach(item => {
    const groupKey = item.cloudRecordId || item.recordId || item.sourceTitle
    const current = groups.get(groupKey)
    const nextUpdatedAt = new Date(item.updatedAt).getTime() > new Date(current?.updatedAt || 0).getTime()
      ? item.updatedAt
      : current?.updatedAt || item.updatedAt
    groups.set(groupKey, {
      key: groupKey,
      title: item.sourceTitle,
      recordId: item.recordId ?? current?.recordId,
      cloudRecordId: item.cloudRecordId ?? current?.cloudRecordId,
      updatedAt: nextUpdatedAt,
      items: [...(current?.items || []), item],
    })
  })
  return Array.from(groups.values())
    .map(group => ({
      ...group,
      items: group.items.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()),
    }))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
}

export default function ExcerptsPage() {
  const { navBarHeight } = useLayoutStore()
  const isLoggedIn = useAuthStore(state => state.isLoggedIn)
  const [favorites, setFavorites] = useState<FavoriteItemDto[]>([])
  const [annotations, setAnnotations] = useState<UserAnnotationDto[]>([])
  const [loading, setLoading] = useState(true)

  const loadExcerpts = useCallback(async () => {
    setLoading(true)
    const result = isLoggedIn ? { success: true } : await ensureLoggedIn()
    if (!result.success) {
      setLoading(false)
      return
    }
    try {
      const [favoriteResult, annotationResult] = await Promise.all([
        fetchCloudFavoriteItems(),
        listUserAnnotations(),
      ])
      setFavorites(favoriteResult.items)
      setAnnotations(annotationResult)
    } catch (err) {
      console.warn('Failed to load excerpts', err)
      Taro.showToast({ title: '摘录加载失败', icon: 'none' })
    } finally {
      setLoading(false)
    }
  }, [isLoggedIn])

  useDidShow(loadExcerpts)

  const groups = useMemo(() => groupByArticle(buildSentenceAssets(favorites, annotations)), [favorites, annotations])
  const totalCount = useMemo(() => groups.reduce((sum, group) => sum + group.items.length, 0), [groups])

  const goToRecord = (item: SentenceAsset) => {
    const targetId = item.recordId || item.cloudRecordId
    if (!targetId) {
      Taro.showToast({ title: '来源记录不可用', icon: 'none' })
      return
    }
    Taro.navigateTo({ url: `${ROUTES.RESULT}?recordId=${encodeURIComponent(targetId)}&mode=replay` })
  }

  return (
    <View className='excerpts-page'>
      <NavBar title='我的摘录' showBack />
      <View className='nav-spacer' style={{ height: navBarHeight + 'px' }} />
      <ScrollView scrollY className='excerpts-scroll'>
        <View className='excerpts-header'>
          <Text className='excerpts-title'>我的摘录</Text>
          <Text className='excerpts-subtitle'>{totalCount > 0 ? `${groups.length} 篇文章，${totalCount} 条句子资产` : '收藏、高亮和笔记会按文章归档。'}</Text>
        </View>

        {loading ? (
          <View className='excerpts-empty'>
            <Text>同步中...</Text>
          </View>
        ) : groups.length === 0 ? (
          <View className='excerpts-empty'>
            <LucideIcon name='bookOpen' size={54} color='var(--text-muted)' />
            <Text className='empty-title'>还没有摘录</Text>
            <Text className='empty-copy'>在解析页长按句子，可以收藏、高亮或写笔记。</Text>
          </View>
        ) : (
          <View className='article-group-list'>
            {groups.map(group => (
              <View key={group.key} className='article-group'>
                <View className='article-group-head'>
                  <Text className='article-group-title' numberOfLines={2}>{group.title}</Text>
                  <Text className='article-group-count'>{group.items.length} 条</Text>
                </View>
                <View className='sentence-asset-list'>
                  {group.items.map(item => (
                    <View key={item.key} className='sentence-asset' onClick={() => goToRecord(item)}>
                      <View className='asset-status-row'>
                        {item.isFavorited && (
                          <View className='asset-chip'>
                            <LucideIcon name='bookmark' size={18} color='currentColor' />
                            <Text>收藏</Text>
                          </View>
                        )}
                        {item.isHighlighted && (
                          <View className='asset-chip asset-chip--highlight'>
                            <LucideIcon name='highlighter' size={18} color='currentColor' />
                            <Text>高亮</Text>
                          </View>
                        )}
                        {item.note && (
                          <View className='asset-chip asset-chip--note'>
                            <LucideIcon name='penLine' size={18} color='currentColor' />
                            <Text>笔记</Text>
                          </View>
                        )}
                        {item.sentenceId && <Text className='asset-sentence-id'>{item.sentenceId}</Text>}
                      </View>
                      <Text className='asset-text'>{item.text}</Text>
                      {item.translation && <Text className='asset-translation'>{item.translation}</Text>}
                      {item.note && (
                        <View className='asset-note'>
                          <Text>{item.note}</Text>
                        </View>
                      )}
                    </View>
                  ))}
                </View>
              </View>
            ))}
          </View>
        )}
        <View className='bottom-spacer' />
      </ScrollView>
    </View>
  )
}
