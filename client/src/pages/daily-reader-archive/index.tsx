import { View, Text, Image } from '@tarojs/components'
import { useEffect, useCallback } from 'react'
import Taro from '@tarojs/taro'
import { useDailyReaderStore } from '../../stores/daily-reader'
import './index.scss'

const DIFFICULTY_LABELS: Record<string, string> = {
  A2: 'A2',
  B1: 'B1',
  B2: 'B2',
  C1: 'C1',
}

export default function DailyReaderArchivePage() {
  const {
    articleList,
    listHasMore,
    loading,
    fetchList,
  } = useDailyReaderStore()

  useEffect(() => {
    fetchList()
  }, [fetchList])

  const handleLoadMore = useCallback(() => {
    if (listHasMore && !loading) {
      const store = useDailyReaderStore.getState()
      fetchList(store.listCursor || undefined)
    }
  }, [fetchList, listHasMore, loading])

  const handleArticleClick = useCallback((id: string) => {
    Taro.navigateTo({ url: `/pages/daily-reader/index?id=${id}` })
  }, [])

  return (
    <View className='archive-page'>
      <View className='archive-page__header'>
        <Text className='archive-page__title'>往期精选</Text>
        <Text className='archive-page__count'>{articleList.length} 篇</Text>
      </View>

      {articleList.length === 0 && !loading && (
        <View className='archive-page__empty'>
          <Text className='archive-page__empty-text'>暂无往期文章</Text>
        </View>
      )}

      <View className='archive-page__list'>
        {articleList.map((item) => (
          <View
            key={item.id}
            className='archive-card'
            onClick={() => handleArticleClick(item.id)}
          >
            <View className='archive-card__left'>
              <Text className='archive-card__title'>{item.title}</Text>
              <View className='archive-card__meta'>
                <Text className='archive-card__source'>{item.source}</Text>
                <Text className='archive-card__dot'>·</Text>
                <Text className='archive-card__date'>{item.publishDate}</Text>
                <Text className='archive-card__dot'>·</Text>
                <Text className='archive-card__time'>{item.readTimeMinutes} min</Text>
              </View>
              <View className='archive-card__badges'>
                <View className='archive-card__badge'>
                  <Text className='archive-card__badge-text'>
                    {DIFFICULTY_LABELS[item.difficulty] || item.difficulty}
                  </Text>
                </View>
                {item.tags.slice(0, 2).map((tag) => (
                  <View key={tag} className='archive-card__badge archive-card__badge--tag'>
                    <Text className='archive-card__badge-text'>{tag}</Text>
                  </View>
                ))}
              </View>
            </View>
            {item.coverImageUrl && (
              <View className='archive-card__right'>
                <Image
                  className='archive-card__cover'
                  src={item.coverImageUrl}
                  mode='aspectFill'
                  lazyLoad
                />
              </View>
            )}
          </View>
        ))}
      </View>

      {listHasMore && (
        <View className='archive-page__load-more' onClick={handleLoadMore}>
          <Text className='archive-page__load-more-text'>
            {loading ? '加载中...' : '加载更多'}
          </Text>
        </View>
      )}
    </View>
  )
}
