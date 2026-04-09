import { memo } from 'react'
import { Text } from '@tarojs/components'
import './index.scss'

interface ClickableWordProps {
  word: string
  isSaved?: boolean // 是否已加入生词本
  className?: string // 额外样式类，如 tone-grammar
  onClick: (word: string, event: any) => void
}

/**
 * 轻量可点击单词组件
 *
 * 渲染为一个透明的 Text，下划线样式暗示可点击。
 * 专用于"全文点词查词"——非标注的普通英文单词。
 */
const ClickableWord = memo(function ClickableWord({ word, isSaved, className, onClick }: ClickableWordProps) {
  return (
    <Text
      className={['clickable-word', className, isSaved ? 'saved' : ''].filter(Boolean).join(' ')}
      onClick={(e) => {
        e.stopPropagation()
        onClick(word, e)
      }}
    >
      {word}
    </Text>
  )
})

export default ClickableWord
