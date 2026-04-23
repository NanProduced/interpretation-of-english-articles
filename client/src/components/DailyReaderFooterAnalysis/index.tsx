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

const EMPTY_FOOTER: FooterAnalysisType = {
  summary: '',
  thesisAndIntent: { thesis: '', authorIntent: '' },
  structure: [],
  keyExpressions: [],
  misreadingPoints: [],
  fullArticleAnalysis: '',
  discussionQuestions: [],
}

function safeFooter(raw: FooterAnalysisType | null | undefined): FooterAnalysisType {
  if (!raw || typeof raw !== 'object') return EMPTY_FOOTER
  return {
    summary: raw.summary ?? '',
    thesisAndIntent: raw.thesisAndIntent
      ? { thesis: raw.thesisAndIntent.thesis ?? '', authorIntent: raw.thesisAndIntent.authorIntent ?? '' }
      : { thesis: '', authorIntent: '' },
    structure: Array.isArray(raw.structure) ? raw.structure : [],
    keyExpressions: Array.isArray(raw.keyExpressions) ? raw.keyExpressions : [],
    misreadingPoints: Array.isArray(raw.misreadingPoints) ? raw.misreadingPoints : [],
    fullArticleAnalysis: raw.fullArticleAnalysis ?? '',
    discussionQuestions: Array.isArray(raw.discussionQuestions) ? raw.discussionQuestions : [],
  }
}

const DailyReaderFooterAnalysis = memo(function DailyReaderFooterAnalysis({
  footerAnalysis,
  sourceUrl,
  source,
}: Props) {
  const fa = safeFooter(footerAnalysis)
  const hasContent = fa.summary || fa.thesisAndIntent.thesis || fa.fullArticleAnalysis

  const [analysisExpanded, setAnalysisExpanded] = useState(false)
  const toggleAnalysis = useCallback(() => setAnalysisExpanded((v) => !v), [])

  return (
    <View className='daily-footer'>
      <View className='daily-footer__divider'>
        <View className='daily-footer__divider-line' />
        <Text className='daily-footer__divider-label'>深度解析</Text>
        <View className='daily-footer__divider-line' />
      </View>

      {!hasContent && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__empty-text'>解析内容生成中，请稍后再来阅读</Text>
        </View>
      )}

      {fa.summary && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>📝</Text>
          <Text className='daily-footer__section-title'>摘要</Text>
          <Text className='daily-footer__summary'>{fa.summary}</Text>
        </View>
      )}

      {fa.thesisAndIntent.thesis && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>🎯</Text>
          <Text className='daily-footer__section-title'>主旨与意图</Text>
          {fa.thesisAndIntent.thesis && (
            <View className='daily-footer__thesis-block'>
              <Text className='daily-footer__thesis-label'>主旨</Text>
              <Text className='daily-footer__thesis-text'>{fa.thesisAndIntent.thesis}</Text>
            </View>
          )}
          {fa.thesisAndIntent.authorIntent && (
            <View className='daily-footer__thesis-block'>
              <Text className='daily-footer__thesis-label'>作者意图</Text>
              <Text className='daily-footer__thesis-text'>{fa.thesisAndIntent.authorIntent}</Text>
            </View>
          )}
        </View>
      )}

      {fa.structure.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>🏗</Text>
          <Text className='daily-footer__section-title'>文章结构</Text>
          <View className='daily-footer__structure'>
            {fa.structure.map((part, idx) => (
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

      {fa.keyExpressions.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>💡</Text>
          <Text className='daily-footer__section-title'>关键表达</Text>
          <View className='daily-footer__expressions'>
            {fa.keyExpressions.map((expr, idx) => (
              <View key={idx} className='daily-footer__expr-card'>
                <Text className='daily-footer__expr-en'>{expr.expression}</Text>
                <Text className='daily-footer__expr-zh'>{expr.gloss}</Text>
                <Text className='daily-footer__expr-context'>"{expr.contextSentence}"</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {fa.misreadingPoints.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>⚠️</Text>
          <Text className='daily-footer__section-title'>易误读点</Text>
          {fa.misreadingPoints.map((point, idx) => (
            <View key={idx} className='daily-footer__misreading'>
              <Text className='daily-footer__misreading-point'>{point.point}</Text>
              <Text className='daily-footer__misreading-clarify'>{point.clarification}</Text>
            </View>
          ))}
        </View>
      )}

      {fa.fullArticleAnalysis && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>📖</Text>
          <Text className='daily-footer__section-title'>全篇讲解</Text>
          <View
            className={`daily-footer__analysis ${analysisExpanded ? 'daily-footer__analysis--expanded' : ''}`}
            onClick={toggleAnalysis}
          >
            <Text className='daily-footer__analysis-text'>
              {fa.fullArticleAnalysis}
            </Text>
          </View>
          {!analysisExpanded && fa.fullArticleAnalysis.length > 200 && (
            <Text className='daily-footer__expand-btn' onClick={toggleAnalysis}>
              展开全文 ↓
            </Text>
          )}
        </View>
      )}

      {fa.discussionQuestions.length > 0 && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__section-icon'>💬</Text>
          <Text className='daily-footer__section-title'>讨论问题</Text>
          {fa.discussionQuestions.map((q, idx) => (
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
