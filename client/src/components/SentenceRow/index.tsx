import { useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import { InlineMarkModel, SentenceTailEntryModel, TextAnchorModel, MultiTextAnchorModel } from '../../types/v2-render'
import InlineMark from '../InlineMark'
import SentenceActionChip from '../SentenceActionChip'
import './index.scss'

interface SentenceRowProps {
  sentenceId: string
  englishText: string
  translationZh?: string
  showTranslation: boolean
  inlineMarks: InlineMarkModel[]
  tailEntries: SentenceTailEntryModel[]
  onWordClick?: (mark: InlineMarkModel, word: string) => void
  onChipClick?: (entry: SentenceTailEntryModel) => void
}

/**
 * 在文本中查找第 N 次出现的位置
 * @param text 文本
 * @param anchorText 锚点文本
 * @param occurrence 第几次出现（默认1）
 */
function findTextAnchorPosition(text: string, anchorText: string, occurrence: number = 1): number {
  let count = 0
  let pos = 0
  while (count < occurrence) {
    const idx = text.indexOf(anchorText, pos)
    if (idx === -1) return -1
    count++
    if (count === occurrence) return idx
    pos = idx + 1
  }
  return -1
}

/**
 * 渲染单段锚点的 InlineMark
 */
function renderSingleTextMark(
  mark: InlineMarkModel,
  text: string,
  startFrom: number,
  onWordClick?: (mark: InlineMarkModel, word: string) => void
): { element: JSX.Element | null; endPos: number } {
  const anchor = mark.anchor as TextAnchorModel
  const anchorText = anchor.anchorText
  const occurrence = anchor.occurrence || 1
  const idx = findTextAnchorPosition(text, anchorText, occurrence)

  if (idx === -1) {
    return { element: null, endPos: startFrom }
  }

  return {
    element: (
      <InlineMark
        key={mark.id}
        mark={mark}
        text={anchorText}
        onClick={onWordClick}
      />
    ),
    endPos: idx + anchorText.length,
  }
}

/**
 * 渲染多段锚点（分开高亮）
 * 每个 part 独立高亮，中间文本正常显示
 */
function renderMultiTextMark(
  mark: InlineMarkModel,
  text: string,
  startFrom: number,
  onWordClick?: (mark: InlineMarkModel, word: string) => void
): { elements: JSX.Element[]; endPos: number } {
  const anchor = mark.anchor as MultiTextAnchorModel
  const parts = anchor.parts

  const elements: JSX.Element[] = []
  let currentPos = startFrom

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    const partText = part.anchorText
    const partOccurrence = part.occurrence || 1

    // 查找当前 part 在文本中的位置（使用 occurrence）
    const partIdx = findTextAnchorPosition(text, partText, partOccurrence)

    if (partIdx === -1) {
      // 如果找不到，继续下一个 part
      continue
    }

    // 添加 part 之前的普通文本
    if (partIdx > currentPos) {
      elements.push(<Text key={`gap-${i}`}>{text.slice(currentPos, partIdx)}</Text>)
    }

    // 创建当前 part 的 InlineMark（独立高亮）
    const partMark: InlineMarkModel = {
      ...mark,
      id: `${mark.id}-part-${i}`,
      anchor: {
        kind: 'text',
        sentenceId: anchor.sentenceId,
        anchorText: partText,
        occurrence: part.occurrence,
      },
    }

    elements.push(
      <InlineMark
        key={`${mark.id}-part-${i}`}
        mark={partMark}
        text={partText}
        onClick={onWordClick}
      />
    )

    currentPos = partIdx + partText.length
  }

  return { elements, endPos: currentPos }
}

/**
 * 在文本中查找标记位置并渲染
 * 支持单段和多段锚点，各段分开高亮
 */
function renderTextWithMarks(
  text: string,
  marks: InlineMarkModel[],
  onWordClick?: (mark: InlineMarkModel, word: string) => void
) {
  if (marks.length === 0) {
    return <Text className='sentence-text'>{text}</Text>
  }

  // 分离单段和多段锚点
  const singleTextMarks = marks.filter((m) => m.anchor.kind === 'text') as InlineMarkModel[]
  const multiTextMarks = marks.filter((m) => m.anchor.kind === 'multi_text') as InlineMarkModel[]

  // 按出现位置排序单段锚点（使用 occurrence-aware 查找）
  const sortedSingleMarks = [...singleTextMarks].sort((a, b) => {
    const anchorA = a.anchor as TextAnchorModel
    const anchorB = b.anchor as TextAnchorModel
    const posA = findTextAnchorPosition(text, anchorA.anchorText, anchorA.occurrence || 1)
    const posB = findTextAnchorPosition(text, anchorB.anchorText, anchorB.occurrence || 1)
    return posA - posB
  })

  // 按第一个 part 的位置排序多段锚点
  const sortedMultiMarks = [...multiTextMarks].sort((a, b) => {
    const anchorA = a.anchor as MultiTextAnchorModel
    const anchorB = b.anchor as MultiTextAnchorModel
    const posA = findTextAnchorPosition(text, anchorA.parts[0]?.anchorText || '', anchorA.parts[0]?.occurrence || 1)
    const posB = findTextAnchorPosition(text, anchorB.parts[0]?.anchorText || '', anchorB.parts[0]?.occurrence || 1)
    return posA - posB
  })

  const resultElements: Array<JSX.Element | string> = []
  let lastEnd = 0

  // 合并处理：按位置顺序交错渲染单段和多段
  const allMarks = [
    ...sortedSingleMarks.map((m) => ({
      mark: m,
      kind: 'single' as const,
      position: findTextAnchorPosition(text, (m.anchor as TextAnchorModel).anchorText, (m.anchor as TextAnchorModel).occurrence || 1),
    })),
    ...sortedMultiMarks.map((m) => ({
      mark: m,
      kind: 'multi' as const,
      position: findTextAnchorPosition(text, (m.anchor as MultiTextAnchorModel).parts[0]?.anchorText || '', (m.anchor as MultiTextAnchorModel).parts[0]?.occurrence || 1),
    })),
  ]
    .filter((item) => item.position >= 0)
    .sort((a, b) => a.position - b.position)

  for (const item of allMarks) {
    if (item.position < lastEnd) continue

    // 添加当前位置之前的普通文本
    if (item.position > lastEnd) {
      resultElements.push(text.slice(lastEnd, item.position))
    }

    if (item.kind === 'single') {
      const { element, endPos } = renderSingleTextMark(item.mark, text, lastEnd, onWordClick)
      if (element) {
        resultElements.push(element)
        lastEnd = endPos
      }
    } else {
      const { elements, endPos } = renderMultiTextMark(item.mark, text, lastEnd, onWordClick)
      resultElements.push(...elements)
      lastEnd = endPos
    }
  }

  // 添加剩余文本
  if (lastEnd < text.length) {
    resultElements.push(text.slice(lastEnd))
  }

  return (
    <Text className='sentence-text'>
      {resultElements}
    </Text>
  )
}

export default function SentenceRow({
  sentenceId,
  englishText,
  translationZh,
  showTranslation,
  inlineMarks,
  tailEntries,
  onWordClick,
  onChipClick,
}: SentenceRowProps) {
  // 过滤出属于本句的标记
  const sentenceMarks = useMemo(() => {
    return inlineMarks.filter((mark) => {
      const anchor = mark.anchor
      if (anchor.kind === 'text') {
        return anchor.sentenceId === sentenceId
      }
      if (anchor.kind === 'multi_text') {
        return anchor.sentenceId === sentenceId
      }
      return false
    })
  }, [inlineMarks, sentenceId])

  // 过滤出属于本句的句尾入口
  const sentenceEntries = useMemo(() => {
    return tailEntries.filter((entry) => {
      return entry.anchor.sentenceId === sentenceId
    })
  }, [tailEntries, sentenceId])

  return (
    <View className='sentence-row'>
      {/* 英文行 */}
      <View className='english-line'>
        {renderTextWithMarks(englishText, sentenceMarks, onWordClick)}

        {/* 句尾入口 */}
        {sentenceEntries.length > 0 && (
          <View className='tail-entries'>
            {sentenceEntries.map((entry) => (
              <SentenceActionChip
                key={entry.id}
                entry={entry}
                onClick={onChipClick}
              />
            ))}
          </View>
        )}
      </View>

      {/* 中文翻译行 */}
      {showTranslation && translationZh && (
        <View className='translation-line'>
          <Text className='translation-text'>{translationZh}</Text>
        </View>
      )}
    </View>
  )
}
