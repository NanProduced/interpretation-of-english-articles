import { Text } from '@tarojs/components'
import { tokenizeText } from '../ParagraphBlock/utils'
import ClickableWord from '../ClickableWord'
import type { AnyInlineMarkModel } from '../../types/view/render-scene.vm'
import type { WordClickPayload } from '../ParagraphBlock'
import './index.scss'

interface GrammarInlineSpanProps {
  mark: AnyInlineMarkModel
  text: string
  selectedWord?: string | null
  vocabSet?: Set<string>
  vocabSavedMap?: Record<string, string>
  isActive?: boolean
  role?: string
  contextSentence?: string
  onWordClick?: (payload: WordClickPayload) => void
  getNextOccurrence: (word: string) => number
}

export default function GrammarInlineSpan({
  mark,
  text,
  selectedWord,
  vocabSet,
  vocabSavedMap,
  isActive,
  role,
  contextSentence,
  onWordClick,
  getNextOccurrence,
}: GrammarInlineSpanProps) {
  const toneClass = `tone-${mark.visualTone}`
  const tokens = tokenizeText(text)

  return (
    <Text className={`grammar-inline-span ${toneClass} ${isActive ? 'active' : ''}`}>
      {isActive && role && <Text className='grammar-role-label'>{role}</Text>}
      {tokens.map((token, idx) => {
        if (token.type === 'word') {
          const isSaved = vocabSet?.has(token.text.toLowerCase())
          const savedStatus = vocabSavedMap?.[token.text.toLowerCase()]
          const occ = getNextOccurrence(token.text)
          
          return (
            <ClickableWord
              key={`gw-${mark.id}-${idx}`}
              word={token.text}
              isSaved={isSaved}
              savedStatus={savedStatus}
              className={[toneClass, selectedWord === token.text ? 'active' : ''].filter(Boolean).join(' ')}
              onClick={(w, e) => onWordClick?.({ word: w, mark: null, event: e, contextSentence, occurrence: occ })}
            />
          )
        }
        return <Text key={`gp-${idx}`} className={toneClass}>{token.text}</Text>
      })}
    </Text>
  )
}
