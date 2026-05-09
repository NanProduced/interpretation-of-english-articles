import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { memo } from 'react'
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

function splitLectureParagraphs(text: string): string[] {
  const normalized = text.replace(/\r/g, '').trim()
  if (!normalized) return []

  const explicitParagraphs = normalized
    .split(/\n{2,}/)
    .map((p) => p.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)

  if (explicitParagraphs.length > 1) return explicitParagraphs
  if (normalized.length <= 260) return [normalized]

  const sentences = normalized
    .split(/(?<=[。！？.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
  const chunks: string[] = []
  let current = ''

  sentences.forEach((sentence) => {
    if (!current) {
      current = sentence
      return
    }
    if ((current + sentence).length > 220) {
      chunks.push(current)
      current = sentence
      return
    }
    current = `${current} ${sentence}`
  })

  if (current) chunks.push(current)
  return chunks.length ? chunks : [normalized]
}

const DailyReaderFooterAnalysis = memo(function DailyReaderFooterAnalysis({
  footerAnalysis,
  sourceUrl,
  source,
}: Props) {
  const fa = safeFooter(footerAnalysis)
  const lectureParagraphs = splitLectureParagraphs(fa.fullArticleAnalysis)
  const hasLead = fa.summary || fa.thesisAndIntent.thesis || fa.thesisAndIntent.authorIntent
  const hasContent = hasLead || fa.structure.length > 0 || lectureParagraphs.length > 0
    || fa.keyExpressions.length > 0 || fa.misreadingPoints.length > 0 || fa.discussionQuestions.length > 0

  return (
    <View className='daily-footer'>
      <View className='daily-footer__divider'>
        <View className='daily-footer__divider-line' />
        <Text className='daily-footer__divider-label'>精读笔记</Text>
        <View className='daily-footer__divider-line' />
      </View>

      {!hasContent && (
        <View className='daily-footer__empty'>
          <Text className='daily-footer__empty-text'>精读笔记正在生成中，稍后回来阅读吧。</Text>
        </View>
      )}

      {hasContent && (
        <View className='daily-footer__editorial'>
          {hasLead && (
            <View className='daily-footer__lead'>
              <Text className='daily-footer__kicker'>Editor's reading</Text>
              {fa.summary && <Text className='daily-footer__lead-summary'>{fa.summary}</Text>}
              {(fa.thesisAndIntent.thesis || fa.thesisAndIntent.authorIntent) && (
                <View className='daily-footer__lead-notes'>
                  {fa.thesisAndIntent.thesis && (
                    <View className='daily-footer__lead-note'>
                      <Text className='daily-footer__lead-note-label'>这篇真正想说什么</Text>
                      <Text className='daily-footer__lead-note-text'>{fa.thesisAndIntent.thesis}</Text>
                    </View>
                  )}
                  {fa.thesisAndIntent.authorIntent && (
                    <View className='daily-footer__lead-note'>
                      <Text className='daily-footer__lead-note-label'>作者为什么这样写</Text>
                      <Text className='daily-footer__lead-note-text'>{fa.thesisAndIntent.authorIntent}</Text>
                    </View>
                  )}
                </View>
              )}
            </View>
          )}

          {fa.structure.length > 0 && (
            <View className='daily-footer__block'>
              <View className='daily-footer__block-heading'>
                <Text className='daily-footer__block-title'>文章骨架</Text>
                <Text className='daily-footer__block-subtitle'>先看作者如何推进观点</Text>
              </View>
              <View className='daily-footer__structure'>
                {fa.structure.map((part, idx) => (
                  <View key={`${part.label}-${idx}`} className='daily-footer__structure-item'>
                    <View className='daily-footer__structure-index'>
                      <Text className='daily-footer__structure-index-text'>{idx + 1}</Text>
                    </View>
                    <View className='daily-footer__structure-copy'>
                      <Text className='daily-footer__structure-label'>{part.label}</Text>
                      <Text className='daily-footer__structure-title'>{part.title}</Text>
                      <Text className='daily-footer__structure-summary'>{part.summary}</Text>
                    </View>
                  </View>
                ))}
              </View>
            </View>
          )}

          {lectureParagraphs.length > 0 && (
            <View className='daily-footer__block daily-footer__block--lecture'>
              <View className='daily-footer__block-heading'>
                <Text className='daily-footer__block-title'>精读讲解</Text>
                <Text className='daily-footer__block-subtitle'>像老师带读一样，把文章讲透</Text>
              </View>
              <View className='daily-footer__lecture'>
                {lectureParagraphs.map((paragraph, idx) => (
                  <Text key={idx} className='daily-footer__lecture-paragraph'>{paragraph}</Text>
                ))}
              </View>
            </View>
          )}

          {fa.keyExpressions.length > 0 && (
            <View className='daily-footer__block'>
              <View className='daily-footer__block-heading'>
                <Text className='daily-footer__block-title'>值得带走的表达</Text>
                <Text className='daily-footer__block-subtitle'>从原文里摘出的可复用说法</Text>
              </View>
              <View className='daily-footer__expressions'>
                {fa.keyExpressions.map((expr, idx) => (
                  <View key={`${expr.expression}-${idx}`} className='daily-footer__expression'>
                    <Text className='daily-footer__expression-en'>{expr.expression}</Text>
                    <Text className='daily-footer__expression-zh'>{expr.gloss}</Text>
                    <Text className='daily-footer__expression-context'>"{expr.contextSentence}"</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {fa.misreadingPoints.length > 0 && (
            <View className='daily-footer__block'>
              <View className='daily-footer__block-heading'>
                <Text className='daily-footer__block-title'>别读偏了</Text>
                <Text className='daily-footer__block-subtitle'>容易误解的地方，先校准</Text>
              </View>
              <View className='daily-footer__misreadings'>
                {fa.misreadingPoints.map((point, idx) => (
                  <View key={`${point.point}-${idx}`} className='daily-footer__misreading'>
                    <Text className='daily-footer__misreading-label'>误区 {idx + 1}</Text>
                    <Text className='daily-footer__misreading-point'>{point.point}</Text>
                    <Text className='daily-footer__misreading-label daily-footer__misreading-label--answer'>正解</Text>
                    <Text className='daily-footer__misreading-clarify'>{point.clarification}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {fa.discussionQuestions.length > 0 && (
            <View className='daily-footer__block daily-footer__block--questions'>
              <View className='daily-footer__block-heading'>
                <Text className='daily-footer__block-title'>思考讨论</Text>
                <Text className='daily-footer__block-subtitle'>用英文把观点再说一遍</Text>
              </View>
              <View className='daily-footer__questions'>
                {fa.discussionQuestions.map((q, idx) => (
                  <View key={`${q}-${idx}`} className='daily-footer__question'>
                    <Text className='daily-footer__question-num'>{idx + 1}.</Text>
                    <Text className='daily-footer__question-text'>{q}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}
        </View>
      )}

      <View className='daily-footer__source' onClick={() => {
        if (sourceUrl) {
          Taro.setClipboardData({ data: sourceUrl })
          Taro.showToast({ title: '链接已复制', icon: 'none', duration: 1500 })
        }
      }}>
        <Text className='daily-footer__source-label'>原文来源</Text>
        <Text className='daily-footer__source-name'>{source}</Text>
        {sourceUrl && <Text className='daily-footer__source-link'>阅读原文</Text>}
      </View>
    </View>
  )
})

export default DailyReaderFooterAnalysis
