import { Text } from '@tarojs/components'
import './index.scss'

interface ClickableWordProps {
  word: string
  onClick: (word: string) => void
}

/**
 * 轻量可点击单词组件
 *
 * 渲染为一个透明的 Text，下划线样式暗示可点击。
 * 专用于"全文点词查词"——非标注的普通英文单词。
 */
export default function ClickableWord({ word, onClick }: ClickableWordProps) {
  return (
    <Text
      className='clickable-word'
      onClick={(e) => {
        e.stopPropagation()
        onClick(word)
      }}
    >
      {word}
    </Text>
  )
}
