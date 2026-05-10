import { DictionaryResult, AnyInlineMarkModel } from '../types/view/render-scene.vm'

export const mockDictionaryLoading = null

export const mockDictionaryEntry: DictionaryResult = {
  resultType: 'entry',
  query: 'resilience',
  entry: {
    id: 1,
    word: 'resilience',
    phonetic: 'rɪˈzɪliəns',
    meanings: [
      {
        partOfSpeech: 'n.',
        definitions: [
          { meaning: '恢复力，弹性；顺应力', example: 'The resilience of the economy.', exampleTranslation: '经济的恢复力。' },
          { meaning: '回弹，回弹力', example: 'Nylon is excellent in stretch and resilience.', exampleTranslation: '尼龙的弹性和回弹力极佳。' }
        ]
      }
    ],
    phrases: [],
    examples: [],
    tags: ['CET6', 'IELTS', 'TOEFL'],
    entryKind: 'entry'
  }
}

export const mockDisambiguationResult: DictionaryResult = {
  resultType: 'disambiguation',
  query: 'project',
  candidates: [
    { entryId: 1, label: 'project (名词)', partOfSpeech: 'n.', preview: '项目，工程', entryKind: 'entry' },
    { entryId: 2, label: 'project (动词)', partOfSpeech: 'v.', preview: '规划；投射', entryKind: 'entry' }
  ]
}

export const mockMarkVocab: AnyInlineMarkModel = {
  id: 'm1',
  lookupText: 'resilience',
  lookupKind: 'word',
  annotationType: 'vocab_highlight',
  renderType: 'background',
  visualTone: 'vocab',
  clickable: true,
  anchor: { kind: 'text', sentenceId: 's1', anchorText: 'resilience', occurrence: 1 }
}

export const mockMarkPhrase: AnyInlineMarkModel = {
  id: 'm2',
  lookupText: 'give up',
  lookupKind: 'phrase',
  annotationType: 'phrase_gloss',
  renderType: 'background',
  visualTone: 'phrase',
  clickable: true,
  anchor: { kind: 'text', sentenceId: 's2', anchorText: 'give up', occurrence: 1 },
  glossary: {
    zh: '放弃，投降',
    phraseType: 'phrasal_verb',
    gloss: 'cease making an effort'
  }
}

export const mockMarkContext: AnyInlineMarkModel = {
  id: 'm3',
  lookupText: 'address',
  lookupKind: 'word',
  annotationType: 'context_gloss',
  renderType: 'underline',
  visualTone: 'context',
  clickable: true,
  anchor: { kind: 'text', sentenceId: 's3', anchorText: 'address', occurrence: 1 },
  glossary: {
    zh: '设法解决，处理',
    gloss: '设法解决',
    reason: '在这个语境中，address 并非"地址"或"演讲"，而是作为动词表示"处理、解决"（问题或困难）。'
  }
}

export const mockSavedSourceRefsNewContext = [
  { sentenceId: 's_123', status: 'learning' }
]

export const mockSavedSourceRefsAlreadyHere = [
  { sentenceId: 's_current', status: 'learning' }
]

export const mockSavedSourceRefsMastered = [
  { sentenceId: 's_current', status: 'mastered' }
]

export const mockSavedSourceRefsMultiple = [
  { sentenceId: 's_123', status: 'learning' },
  { sentenceId: 's_current', status: 'learning' }
]
