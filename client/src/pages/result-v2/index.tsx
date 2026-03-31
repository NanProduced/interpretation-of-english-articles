import { useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { RenderSceneModel, InlineMarkModel, SentenceTailEntryModel, PageMode } from '../../types/v2-render'
import { mockSceneData, PAGE_MODE_OPTIONS, articleMeta } from './mock-data'
import NavBar from '../../components/NavBar'
import SentenceRow from '../../components/SentenceRow'
import WordPopup from '../../components/WordPopup'
import BottomSheetDetail from '../../components/BottomSheetDetail'
import AnalysisCard from '../../components/AnalysisCard'
import LucideIcon from '../../components/LucideIcon'
import './index.scss'

export default function ResultV2() {
  const [sceneData] = useState<RenderSceneModel>(mockSceneData)
  const [pageMode, setPageMode] = useState<PageMode>('bilingual')
  const [wordPopup, setWordPopup] = useState<{
    visible: boolean
    mark: InlineMarkModel | null
    word: string
  }>({ visible: false, mark: null, word: '' })
  const [bottomSheet, setBottomSheet] = useState<{
    visible: boolean
    entry: SentenceTailEntryModel | null
  }>({ visible: false, entry: null })

  // 根据页面模式决定是否显示翻译
  const showTranslation = pageMode === 'bilingual' || pageMode === 'intensive'

  // 处理单词点击
  const handleWordClick = (mark: InlineMarkModel, word: string) => {
    setWordPopup({ visible: true, mark, word })
  }

  // 处理句尾入口点击
  const handleChipClick = (entry: SentenceTailEntryModel) => {
    setBottomSheet({ visible: true, entry })
  }

  // 关闭词级弹窗
  const handleCloseWordPopup = () => {
    setWordPopup({ visible: false, mark: null, word: '' })
  }

  // 关闭底部面板
  const handleCloseBottomSheet = () => {
    setBottomSheet({ visible: false, entry: null })
  }

  // 渲染段落和句子
  const renderParagraphs = () => {
    return sceneData.article.paragraphs.map((paragraph) => {
      return (
        <View key={paragraph.paragraphId} className='paragraph-block'>
          {paragraph.sentenceIds.map((sentenceId) => {
            const sentence = sceneData.article.sentences.find((s) => s.sentenceId === sentenceId)
            const translation = sceneData.translations.find((t) => t.sentenceId === sentenceId)

            if (!sentence) return null

            // 查找插入在该句子后的卡片
            const cardsAfterSentence = sceneData.cards.filter(
              (card) => card.anchor.afterSentenceId === sentenceId
            )

            return (
              <View key={sentenceId} className='sentence-wrapper'>
                <SentenceRow
                  sentenceId={sentenceId}
                  englishText={sentence.text}
                  translationZh={translation?.translationZh}
                  showTranslation={showTranslation}
                  inlineMarks={sceneData.inlineMarks}
                  tailEntries={sceneData.sentenceEntries}
                  onWordClick={handleWordClick}
                  onChipClick={handleChipClick}
                />
                {/* 卡片插入在该句子后面 */}
                {cardsAfterSentence.map((card) => (
                  <AnalysisCard key={card.id} card={card} />
                ))}
              </View>
            )
          })}
        </View>
      )
    })
  }

  return (
    <View className='result-v2-page'>
      <NavBar title='AI 英语解读' showBack showHome />

      {/* 模式切换 Tab */}
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

      {/* 文章内容 */}
      <ScrollView className='article-scroll' scrollY>
        <View className='article-container'>
          {/* 标题区 */}
          <View className='article-header'>
            <Text className='article-title'>{articleMeta.title}</Text>
            <View className='article-meta-row'>
              <Text className='article-source'>{articleMeta.source}</Text>
              <Text className='meta-divider'>·</Text>
              <Text className='article-level'>{articleMeta.level}</Text>
            </View>
          </View>

          {/* 段落内容 */}
          {renderParagraphs()}
        </View>

        {/* 底部留白 */}
        <View className='bottom-spacer' />
      </ScrollView>

      {/* 标注图例 */}
      {pageMode === 'intensive' && (
        <View className='annotation-legend'>
          <View className='legend-item'>
            <View className='legend-marker exam' />
            <Text>考试重点词</Text>
          </View>
          <View className='legend-item'>
            <View className='legend-marker phrase' />
            <Text>短语搭配</Text>
          </View>
          <View className='legend-item'>
            <View className='legend-marker grammar' />
            <Text>语法标记</Text>
          </View>
        </View>
      )}

      {/* 词级弹窗 */}
      <WordPopup
        visible={wordPopup.visible}
        mark={wordPopup.mark}
        word={wordPopup.word}
        onClose={handleCloseWordPopup}
      />

      {/* 底部详情面板 */}
      <BottomSheetDetail
        visible={bottomSheet.visible}
        entry={bottomSheet.entry}
        onClose={handleCloseBottomSheet}
      />
    </View>
  )
}
