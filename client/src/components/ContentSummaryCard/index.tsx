import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import type { ContentSummaryModel } from '../../types/view/render-scene.vm'
import './index.scss'

interface ContentSummaryCardProps {
  summary: ContentSummaryModel
}

export default function ContentSummaryCard({ summary }: ContentSummaryCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [detailExpanded, setDetailExpanded] = useState(false)

  const hasDetails =
    summary.researchQuestion ||
    summary.methodology ||
    (summary.keyFindings && summary.keyFindings.length > 0) ||
    (summary.limitations && summary.limitations.length > 0)

  const coreFindings = summary.keyFindings?.slice(0, 3) ?? []
  const hasFindings = coreFindings.length > 0

  return (
    <View className={`research-brief ${expanded ? 'is-expanded' : 'is-collapsed'}`}>
      <View className='brief-header' onClick={() => setExpanded(!expanded)}>
        <View className='brief-header-left'>
          <LucideIcon name='file-text' size={14} color='var(--reader-muted)' />
          <Text className='brief-label'>本文主旨</Text>
        </View>
        <View className={`brief-chevron ${expanded ? 'is-open' : ''}`}>
          <LucideIcon name='chevron-right' size={14} color='var(--reader-subtle)' />
        </View>
      </View>

      <View className={`brief-body ${expanded ? 'show' : 'hide'}`}>
        <View className='brief-overview'>
          <Text className='overview-text'>{summary.overview}</Text>
        </View>

        {hasFindings && (
          <View className='brief-findings'>
            <View className='findings-header'>
              <Text className='findings-label'>核心观点</Text>
              <Text className='findings-count'>{coreFindings.length}</Text>
            </View>
            <View className='findings-list'>
              {coreFindings.map((finding, idx) => (
                <View key={idx} className={`finding-item finding-item-${idx + 1}`}>
                  <Text className='finding-num'>{String(idx + 1).padStart(2, '0')}</Text>
                  <Text className='finding-text'>{finding}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {hasDetails && (
          <>
            <View className='brief-detail-toggle' onClick={(e) => {
              e.stopPropagation()
              setDetailExpanded(!detailExpanded)
            }}>
              <View className='toggle-left'>
                <Text className='toggle-text'>
                  {detailExpanded ? '收起结构' : '展开结构'}
                </Text>
              </View>
              <View className={`toggle-right ${detailExpanded ? 'is-open' : ''}`}>
                <LucideIcon name='chevron-down' size={13} color='var(--reader-subtle)' />
              </View>
            </View>

            {detailExpanded && (
              <View className='brief-detail-body'>
                {summary.researchQuestion && (
                  <View className='detail-section'>
                    <Text className='detail-key'>研究问题</Text>
                    <Text className='detail-value'>{summary.researchQuestion}</Text>
                  </View>
                )}
                {summary.methodology && (
                  <View className='detail-section'>
                    <Text className='detail-key'>研究方法</Text>
                    <Text className='detail-value'>{summary.methodology}</Text>
                  </View>
                )}
                {summary.limitations && summary.limitations.length > 0 && (
                  <View className='detail-section'>
                    <Text className='detail-key'>研究局限</Text>
                    <View className='detail-list'>
                      {summary.limitations.map((item, idx) => (
                        <Text key={idx} className='detail-list-item'>· {item}</Text>
                      ))}
                    </View>
                  </View>
                )}
              </View>
            )}
          </>
        )}
      </View>
    </View>
  )
}
