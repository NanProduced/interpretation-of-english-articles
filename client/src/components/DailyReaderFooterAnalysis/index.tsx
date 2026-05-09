import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { memo, useState, useCallback } from 'react'
import type { DailyReaderFooterAnalysis as FooterAnalysisType } from '../../types/view/daily-reader.vm'
import LucideIcon from '../LucideIcon'
import './index.scss'

const CollapsibleHeader = memo(({ icon, title, isOpen, onToggle, children }: {
  icon: string
  title: string
  isOpen: boolean
  onToggle: () => void
  children: React.ReactNode
}) => {
  return (
    <View className='daily-footer__collapsible'>
      <View className='daily-footer__collapsible-header' onClick={onToggle}>
        <LucideIcon name={icon as any} size={18} color='var(--dr-accent)' />
        <Text className='daily-footer__collapsible-title'>{title}</Text>
        <LucideIcon name={isOpen ? 'chevronUp' : 'chevronDown'} size={16} color='var(--dr-text-muted)' />
      </View>
      {isOpen && (
        <View className='daily-footer__collapsible-body'>
          {children}
        </View>
      )}
    </View>
  )
})

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

type SectionKey = 'overview' | 'deepread' | 'extended'

const DailyReaderFooterAnalysis = memo(function DailyReaderFooterAnalysis({
  footerAnalysis,
  sourceUrl,
  source,
}: Props) {
  const fa = safeFooter(footerAnalysis)
  const hasContent = fa.summary || fa.thesisAndIntent.thesis || fa.fullArticleAnalysis

  const [analysisExpanded, setAnalysisExpanded] = useState(false)
  const toggleAnalysis = useCallback(() => setAnalysisExpanded((v) => !v), [])

  const [expandedSections, setExpandedSections] = useState<Set<SectionKey>>(new Set(['overview']))
  const toggleSection = useCallback((key: SectionKey) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const hasDeepRead = fa.thesisAndIntent.thesis || fa.structure.length > 0 || fa.misreadingPoints.length > 0
  const hasExtended = fa.fullArticleAnalysis || fa.discussionQuestions.length > 0

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

      {hasContent && (
        <>
          <CollapsibleHeader icon='FileText' title='概览' isOpen={expandedSections.has('overview')} onToggle={() => toggleSection('overview')}>
            {fa.summary && (
              <View className='daily-footer__section'>
                <Text className='daily-footer__summary'>{fa.summary}</Text>
              </View>
            )}
            {fa.keyExpressions.length > 0 && (
              <View className='daily-footer__section'>
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
          </CollapsibleHeader>

          {hasDeepRead && (
            <CollapsibleHeader icon='Layers' title='精读分析' isOpen={expandedSections.has('deepread')} onToggle={() => toggleSection('deepread')}>
              {fa.thesisAndIntent.thesis && (
                <View className='daily-footer__section'>
                  {fa.thesisAndIntent.thesis && (
                    <View className='daily-footer__thesis-block'>
                      <Text className='daily-footer__thesis-label'>主旨</Text>
                      <Text className='daily-footer__thesis-text'>{fa.thesisAndIntent.thesis}</Text>
                    </View>
                  )}
                  {fa.thesisAndIntent.authorIntent && (
                    <View className='daily-footer__thesis-block daily-footer__thesis-block--intent'>
                      <Text className='daily-footer__thesis-label'>作者意图</Text>
                      <Text className='daily-footer__thesis-text'>{fa.thesisAndIntent.authorIntent}</Text>
                    </View>
                  )}
                </View>
              )}

              {fa.structure.length > 0 && (
                <View className='daily-footer__section'>
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

              {fa.misreadingPoints.length > 0 && (
                <View className='daily-footer__section'>
                  {fa.misreadingPoints.map((point, idx) => (
                    <View key={idx} className='daily-footer__misreading'>
                      <View className='daily-footer__misreading-header'>
                        <LucideIcon name='AlertTriangle' size={14} color='var(--dr-text-warning)' />
                        <Text className='daily-footer__misreading-point'>{point.point}</Text>
                      </View>
                      <Text className='daily-footer__misreading-clarify'>{point.clarification}</Text>
                    </View>
                  ))}
                </View>
              )}
            </CollapsibleHeader>
          )}

          {hasExtended && (
            <CollapsibleHeader icon='BookOpen' title='延伸阅读' isOpen={expandedSections.has('extended')} onToggle={() => toggleSection('extended')}>
              {fa.fullArticleAnalysis && (
                <View className='daily-footer__section'>
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
                  {fa.discussionQuestions.map((q, idx) => (
                    <View key={idx} className='daily-footer__question'>
                      <Text className='daily-footer__question-num'>{idx + 1}.</Text>
                      <Text className='daily-footer__question-text'>{q}</Text>
                    </View>
                  ))}
                </View>
              )}
            </CollapsibleHeader>
          )}
        </>
      )}

      <View className='daily-footer__source' onClick={() => {
        if (sourceUrl) {
          Taro.setClipboardData({ data: sourceUrl })
          Taro.showToast({ title: '链接已复制', icon: 'none', duration: 1500 })
        }
      }}>
        <LucideIcon name='ExternalLink' size={14} color='var(--dr-text-muted)' />
        <Text className='daily-footer__source-label'>原文来源</Text>
        <Text className='daily-footer__source-name'>{source}</Text>
        {sourceUrl && <Text className='daily-footer__source-link'> 阅读原文 →</Text>}
      </View>
    </View>
  )
})

export default DailyReaderFooterAnalysis
