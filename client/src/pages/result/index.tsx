import { useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import { RenderSceneModel, InlineMarkModel, SentenceEntryModel, PageMode } from '../../types/render-scene'
import { ALL_SCENARIOS, PAGE_MODE_OPTIONS, articleMeta } from './mock-data'
import NavBar from '../../components/NavBar'
import ParagraphBlock from '../../components/ParagraphBlock'
import WordPopup from '../../components/WordPopup'
import BottomSheetDetail from '../../components/BottomSheetDetail'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

export default function ResultV2() {
  const { navBarHeight } = useLayoutStore()
  const [scenarioName, setScenarioName] = useState<keyof typeof ALL_SCENARIOS>('全功能演示')
  const [pageMode, setPageMode] = useState<PageMode>('bilingual')
  const [showDebug, setShowDebug] = useState(false)
  const [wordPopup, setWordPopup] = useState<{
    visible: boolean
    mode: 'mini' | 'full'
    mark: InlineMarkModel | null
    word: string
    x: number
    y: number
  }>({ visible: false, mode: 'mini', mark: null, word: '', x: 0, y: 0 })
  const [activeMarkId, setActiveMarkId] = useState<string | null>(null)
  const [bottomSheet, setBottomSheet] = useState<{
    visible: boolean
    entry: SentenceEntryModel | null
  }>({ visible: false, entry: null })

  const sceneData: RenderSceneModel = ALL_SCENARIOS[scenarioName]

  const showTranslation = pageMode === 'bilingual' || pageMode === 'intensive'

  const handleWordClick = (mark: InlineMarkModel, word: string, e?: any) => {
    // If it has AI glossary, go straight to full sheet. Otherwise, show mini tooltip.
    const isAIAnnotated = !!mark.glossary
    const initialMode = isAIAnnotated ? 'full' : 'mini'
    
    setActiveMarkId(mark.id)

    let clientX = 0
    let clientY = 0
    
    // Safely extract coordinates from Taro touch/click event
    if (e) {
      if (e.changedTouches && e.changedTouches[0]) {
        clientX = e.changedTouches[0].clientX
        clientY = e.changedTouches[0].clientY
      } else if (e.detail && e.detail.x !== undefined) {
        clientX = e.detail.x
        clientY = e.detail.y
      }
    }

    setWordPopup({ visible: true, mode: initialMode, mark, word, x: clientX, y: clientY })
  }

  const handleClosePopup = () => {
    setWordPopup({ ...wordPopup, visible: false })
    setActiveMarkId(null)
  }

  const handleChipClick = (entry: SentenceEntryModel) => {
    setBottomSheet({ visible: true, entry })
  }

  const renderParagraphs = () => {
    return sceneData.article.paragraphs.map((paragraph) => {
      // Find all sentences for this paragraph
      const sentences = paragraph.sentenceIds
        .map(id => sceneData.article.sentences.find(s => s.sentenceId === id))
        .filter((s): s is NonNullable<typeof s> => !!s)

      return (
        <ParagraphBlock
          key={paragraph.paragraphId}
          sentences={sentences}
          translations={sceneData.translations}
          showTranslation={showTranslation}
          inlineMarks={sceneData.inlineMarks}
          activeMarkId={activeMarkId}
          tailEntries={sceneData.sentenceEntries}
          pageMode={pageMode}
          onWordClick={handleWordClick}
          onChipClick={handleChipClick}
        />
      )
    })
  }

  return (
    <View className='result-page'>
      <NavBar title='AI 英语解读' showBack showHome />
      <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />

      <View className='mode-tabs-container'>
        <View className='mode-tabs'>
          {PAGE_MODE_OPTIONS.map((mode) => (
            <View
              key={mode.value}
              className={`mode-tab ${pageMode === mode.value ? 'active' : ''}`}
              onClick={() => setPageMode(mode.value as PageMode)}
            >
              <Text className='mode-tab-label'>{mode.label}</Text>
            </View>
          ))}
        </View>
      </View>

      <ScrollView className='article-scroll' scrollY>
        <View className='article-container'>
          {sceneData.warnings.length > 0 && (
            <View className='warnings-container'>
              {sceneData.warnings.map((w, idx) => (
                <View key={idx} className={`warning-item ${w.level}`}>
                  <LucideIcon name='alert-circle' size={14} color='inherit' />
                  <Text className='warning-msg'>{w.message}</Text>
                </View>
              ))}
            </View>
          )}

          <View className='article-header'>
            <Text className='article-title'>{articleMeta.title}</Text>
            <View className='article-meta-row'>
              <View className='source-tag'>{articleMeta.source}</View>
              <View className='level-tag'>{articleMeta.level}</View>
            </View>
          </View>

          {renderParagraphs()}
        </View>

        <View className='bottom-spacer' />
      </ScrollView>

      {/* Global Bottom Action Bar */}
      <View className='global-action-bar safe-area-bottom'>
        <View className='action-bar-inner'>
          <View className='secondary-action'>
            <LucideIcon name='star' size={20} color='var(--text-sub)' />
            <Text>收藏全文</Text>
          </View>
          <View className='primary-action'>
            <LucideIcon name='refresh-cw' size={18} color='#fff' />
            <Text>重新分析</Text>
          </View>
        </View>
      </View>

      <View className={`debug-fab ${showDebug ? 'expanded' : ''}`} onClick={() => !showDebug && setShowDebug(true)}>
        {!showDebug ? (
          <LucideIcon name='settings' size={18} color='#999' />
        ) : (
          <View className='debug-menu'>
            <View className='debug-header'>
              <Text>场景切换</Text>
              <View onClick={(e) => { e.stopPropagation(); setShowDebug(false); }}>
                <LucideIcon name='x' size={16} color='#999' />
              </View>
            </View>
            <View className='scenario-list'>
              {Object.keys(ALL_SCENARIOS).map((name) => (
                <View
                  key={name}
                  className={`scenario-option ${scenarioName === name ? 'active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setScenarioName(name as any);
                    setShowDebug(false);
                  }}
                >
                  <Text>{name}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </View>

      <WordPopup
        visible={wordPopup.visible}
        mode={wordPopup.mode}
        mark={wordPopup.mark}
        word={wordPopup.word}
        x={wordPopup.x}
        y={wordPopup.y}
        onClose={handleClosePopup}
        onExpand={() => setWordPopup({ ...wordPopup, mode: 'full' })}
      />

      <BottomSheetDetail
        visible={bottomSheet.visible}
        entry={bottomSheet.entry}
        onClose={() => setBottomSheet({ ...bottomSheet, visible: false })}
      />
    </View>
  )
}
