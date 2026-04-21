import { View, Text, Image } from '@tarojs/components'
import { memo } from 'react'
import type { DailyReaderArticle } from '../../types/view/daily-reader.vm'
import './index.scss'

interface Props {
  article: DailyReaderArticle
}

const DIFFICULTY_LABELS: Record<string, string> = {
  A2: 'A2 入门',
  B1: 'B1 中级',
  B2: 'B2 中高',
  C1: 'C1 高级',
}

const DailyReaderHeader = memo(function DailyReaderHeader({ article }: Props) {
  const hasCover = !!article.coverImageUrl

  return (
    <View className='daily-header'>
      {hasCover && (
        <View className='daily-header__cover'>
          <Image
            className='daily-header__cover-img'
            src={article.coverImageUrl!}
            mode='aspectFill'
            lazyLoad
          />
          <View className='daily-header__cover-overlay' />
        </View>
      )}
      {!hasCover && (
        <View className={`daily-header__gradient daily-header__gradient--${article.coverTheme}`} />
      )}
      <View className='daily-header__content'>
        <View className='daily-header__meta'>
          <Text className='daily-header__source'>{article.source}</Text>
          <Text className='daily-header__dot'>·</Text>
          <Text className='daily-header__date'>{article.publishDate}</Text>
        </View>
        <Text className='daily-header__title'>{article.title}</Text>
        {article.subtitle && (
          <Text className='daily-header__subtitle'>{article.subtitle}</Text>
        )}
        <View className='daily-header__badges'>
          <View className='daily-header__badge daily-header__badge--difficulty'>
            <Text className='daily-header__badge-text'>
              {DIFFICULTY_LABELS[article.difficulty] || article.difficulty}
            </Text>
          </View>
          <View className='daily-header__badge daily-header__badge--time'>
            <Text className='daily-header__badge-text'>{article.readTimeMinutes} min</Text>
          </View>
          {article.tags.slice(0, 3).map((tag) => (
            <View key={tag} className='daily-header__badge daily-header__badge--tag'>
              <Text className='daily-header__badge-text'>{tag}</Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  )
})

export default DailyReaderHeader
