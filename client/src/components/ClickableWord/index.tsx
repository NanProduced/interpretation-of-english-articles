import { memo } from 'react'
import { Text } from '@tarojs/components'
import './index.scss'

interface ClickableWordProps {
  word: string
  isSaved?: boolean // 是否已加入生词本
  onClick: (word: string) => void
}

/**
 * 轻量可点击单词组件
 *
 * 渲染为一个透明的 Text，下划线样式暗示可点击。
 * 专用于"全文点词查词"——非标注的普通英文单词。
 */
const ClickableWord = memo(function ClickableWord({ word, isSaved, onClick }: ClickableWordProps) {
  return (
    <Text
      className={`clickable-word ${isSaved ? 'saved' : ''}`}
      onClick={(e) => {
        e.stopPropagation()
        onClick(word)
      }}
      role='button'
      aria-label={`${isSaved ? '已收藏生词: ' : '查词: '}${word}`}
    >
      {word}
    </Text>
  )
})

export default ClickableWord
