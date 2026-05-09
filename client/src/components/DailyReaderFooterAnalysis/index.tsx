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

type SectionKey = 'overview' | 'deepread' | 'reading-guide' | 'discussion'

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
  const hasReadingGuide = fa.fullArticleAnalysis
  const hasDiscussion = fa.discussionQuestions.length > 0

  return (
    <View className='daily-footer'>
      <View className='daily-footer__divider'>
        <View className='daily-footer__divider-line' />
        <Text className='daily-footer__divider-label'>深度解析</Text>
        <View className='daily-footer__divider-line' />
      </View>

      {!hasContent && (
        <View className='daily-footer__section'>
          <Text className='daily-footer__empty-text'>深度解析正在生成中，稍后回来阅读吧～</Text>
        </View>
      )}

      {hasContent && (
        <>
          {/* 概览：始终展开 */}
          <View className='daily-footer__section'>
            {fa.summary && (
              <View className='daily-footer__card daily-footer__card--subtle'>
                <Text className='daily-footer__summary'>{fa.summary}</Text>
              </View>
            )}
            {fa.keyExpressions.length > 0 && (
              <View className='daily-footer__expressions'>
                {fa.keyExpressions.map((expr, idx) => (
                  <View key={idx} className='daily-footer__expr-card'>
                    <Text className='daily-footer__expr-en'>{expr.expression}</Text>
                    <Text className='daily-footer__expr-zh'>{expr.gloss}</Text>
                    <Text className='daily-footer__expr-context'>"{expr.contextSentence}"</Text>
                  </View>
                ))}
              </View>
            )}
          </View>

          {/* 精读分析：默认折叠 */}
          {hasDeepRead && (
            <CollapsibleHeader icon='Layers' title='精读分析' isOpen={expandedSections.has('deepread')} onToggle={() => toggleSection('deepread')}>
              {fa.thesisAndIntent.thesis && (
                <View className='daily-footer__section'>
                  <View className='daily-footer__card'>
                    <View className='daily-footer__card-header'>
                      <View className='daily-footer__card-dot' />
                      <Text className='daily-footer__card-label'>主旨</Text>
                    </View>
                    <Text className='daily-footer__thesis-text'>{fa.thesisAndIntent.thesis}</Text>
                  </View>
                  {fa.thesisAndIntent.authorIntent && (
                    <View className='daily-footer__card daily-footer__card--warm'>
                      <View className='daily-footer__card-header'>
                        <View className='daily-footer__card-dot' />
                        <Text className='daily-footer__card-label'>作者意图</Text>
                      </View>
                      <Text className='daily-footer__thesis-text'>{fa.thesisAndIntent.authorIntent}</Text>
                    </View>
                  )}
                </View>
              )}

              {fa.structure.length > 0 && (
                <View className='daily-footer__section'>
                  <View className='daily-footer__structure'>
                    {fa.structure.map((part, idx) => {
                      const isShortLabel = part.label.length <= 8
                      return (
                        <View
                          key={idx}
                          className={`daily-footer__structure-item ${isShortLabel ? 'daily-footer__structure-item--short' : 'daily-footer__structure-item--long'}`}
                        >
                          {isShortLabel ? (
                            <>
                              <View className='daily-footer__structure-marker'>
                                <Text className='daily-footer__structure-label'>{part.label}</Text>
                              </View>
                              <View className='daily-footer__structure-content'>
                                <Text className='daily-footer__structure-title'>{part.title}</Text>
                                <Text className='daily-footer__structure-summary'>{part.summary}</Text>
                              </View>
                            </>
                          ) : (
                            <View className='daily-footer__structure-content daily-footer__structure-content--full'>
                              <Text className='daily-footer__label-inline'>{part.label}</Text>
                              <Text className='daily-footer__structure-title'>{part.title}</Text>
                              <Text className='daily-footer__structure-summary'>{part.summary}</Text>
                            </View>
                          )}
                        </View>
                      )
                    })}
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

          {/* 文章导读：默认折叠 */}
          {hasReadingGuide && (
            <CollapsibleHeader icon='BookOpen' title='文章导读' isOpen={expandedSections.has('reading-guide')} onToggle={() => toggleSection('reading-guide')}>
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
                    阅读全文
                  </Text>
                )}
              </View>
            </CollapsibleHeader>
          )}

          {/* 思考讨论：默认折叠 */}
          {hasDiscussion && (
            <CollapsibleHeader icon='MessageCircle' title='思考讨论' isOpen={expandedSections.has('discussion')} onToggle={() => toggleSection('discussion')}>
              <View className='daily-footer__section'>
                {fa.discussionQuestions.map((q, idx) => (
                  <View key={idx} className='daily-footer__question'>
                    <Text className='daily-footer__question-num'>{idx + 1}.</Text>
                    <Text className='daily-footer__question-text'>{q}</Text>
                  </View>
                ))}
              </View>
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
