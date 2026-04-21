import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { memo, useState, useCallback } from 'react'
import type { DailyReaderFooterAnalysis as FooterAnalysisType } from '../../types/view/daily-reader.vm'
import './index.scss'

interface Props {
  footerAnalysis: FooterAnalysisType
  sourceUrl: string
  source: string
}

const DailyReaderFooterAnalysis = memo(function DailyReaderFooterAnalysis({
  footerAnalysis,
  sourceUrl,
  source,
}: Props) {
  const [analysisExpanded, setAnalysisExpanded] = useState(false)
  const toggleAnalysis = useCallback(() => setAnalysisExpanded((v) => !v), [])

  return (
    <View className='daily-footer'>
      <View className='daily-footer__divider'>
        <View className='daily-footer__divider-line' />
        <Text className='daily-footer__divider-label'>深度解析</Text>
        <View className='daily-footer__divider-line' />
      </View>

      <View className='daily-footer__section'>
        <Text className='daily-footer__section-icon'>📝</Text>
        <Text className='daily-footer__section-title'>摘要</Text>
        <Text className='daily-footer__summary'>{footerAnalysis.summary}</Text>
      </View>

      <View className='daily-footer__section'>
        <Text className='daily-footer__section-icon'>🎯</Text>
        <Text className='daily-footer__section-title'>主旨与意图</Text>
        <View className='daily-footer__thesis-block'>
          <Text className='daily-footer__thesis-label'>主旨</Text>
          <Text className='daily-footer__thesis-text'>{footerAnalysis.thesisAndIntent.thesis}</Text>
        </View>
        <View className='daily-footer__thesis-block'>
          <Text className='daily-footer__thesis-label'>作者意图</Text>
          <Text className='daily-footer__thesis-text'>{footerAnalysis.thesisAndIntent.authorIntent}</Text>
        </View>
      </View>

      {footerAnalysis.structure.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>🏗</Text>
          <Text className='daily-footer__section-title'>文章结构</Text>
          <View className='daily-footer__structure'>
            {footerAnalysis.structure.map((part, idx) => (
              <View key={idx} className='daily-footer__structure-item'>
                <View className='daily-footer__structure-marker'>
                  <Text className='daily-footer__structure-label'>{part.label}</Text>
                </View>
                <View className='daily-footer__structure-content'>
                  <Text className='daily-footer__structure-title'>{part.title}</Text>
                  <Text className='daily-footer__structure-summary'>{part.summary}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {footerAnalysis.keyExpressions.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>💡</Text>
          <Text className='daily-footer__section-title'>关键表达</Text>
          <View className='daily-footer__expressions'>
            {footerAnalysis.keyExpressions.map((expr, idx) => (
              <View key={idx} className='daily-footer__expr-card'>
                <Text className='daily-footer__expr-en'>{expr.expression}</Text>
                <Text className='daily-footer__expr-zh'>{expr.gloss}</Text>
                <Text className='daily-footer__expr-context'>"{expr.contextSentence}"</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {footerAnalysis.misreadingPoints.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>⚠️</Text>
          <Text className='daily-footer__section-title'>易误读点</Text>
          {footerAnalysis.misreadingPoints.map((point, idx) => (
            <View key={idx} className='daily-footer__misreading'>
              <Text className='daily-footer__misreading-point'>{point.point}</Text>
              <Text className='daily-footer__misreading-clarify'>{point.clarification}</Text>
            </View>
          ))}
        </View>
      )}

      <View className='daily-footer__section'>
        <Text className='daily-footer__section-icon'>📖</Text>
        <Text className='daily-footer__section-title'>全篇讲解</Text>
        <View
          className={`daily-footer__analysis ${analysisExpanded ? 'daily-footer__analysis--expanded' : ''}`}
          onClick={toggleAnalysis}
        >
          <Text className='daily-footer__analysis-text'>
            {footerAnalysis.fullArticleAnalysis}
          </Text>
        </View>
        {!analysisExpanded && footerAnalysis.fullArticleAnalysis.length > 200 && (
          <Text className='daily-footer__expand-btn' onClick={toggleAnalysis}>
            展开全文 ↓
          </Text>
        )}
      </View>

      {footerAnalysis.discussionQuestions.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>💬</Text>
          <Text className='daily-footer__section-title'>讨论问题</Text>
          {footerAnalysis.discussionQuestions.map((q, idx) => (
            <View key={idx} className='daily-footer__question'>
              <Text className='daily-footer__question-num'>{idx + 1}.</Text>
              <Text className='daily-footer__question-text'>{q}</Text>
            </View>
          ))}
        </View>
      )}

      <View className='daily-footer__source' onClick={() => {
        if (sourceUrl) {
          Taro.setClipboardData({ data: sourceUrl })
        }
      }}>
        <Text className='daily-footer__source-label'>原文来源</Text>
        <Text className='daily-footer__source-name'>{source}</Text>
        {sourceUrl && <Text className='daily-footer__source-link'> → 阅读原文</Text>}
      </View>
    </View>
  )
})

export default DailyReaderFooterAnalysis
