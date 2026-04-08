import { useState, useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import LucideIcon from '../LucideIcon'
import { useConfigStore } from '../../stores/config'
import './index.scss'

export type AnalysisCardType = 'vocab' | 'grammar' | 'sentence'

export interface AnalysisChunk {
  order: string
  label: string
  text: string
}

export interface AnalysisCardProps {
  type: AnalysisCardType
  title: string
  label?: string
  content: string
  phonetic?: string
  tags?: string[]
  initiallyExpanded?: boolean
}

const TYPE_CONFIG = {
  vocab: {
    icon: 'languages',
    colorClass: 'type-vocab',
    accentColor: 'var(--vocab-accent)',
    defaultLabel: '核心词汇',
  },
  grammar: {
    icon: 'network',
    colorClass: 'type-grammar',
    accentColor: 'var(--grammar-accent)',
    defaultLabel: '语法要点',
  },
  sentence: {
    icon: 'layout-template',
    colorClass: 'type-sentence',
    accentColor: 'var(--sentence-accent)',
    defaultLabel: '句式解析',
  },
}

/**
 * 解析 sentence_analysis 的 content
 * 格式：
 * 前半段为整句说明
 * 后半段为：- **1. 主语**：`The article`
 */
function parseSentenceAnalysis(content: string): { summary: string; chunks: AnalysisChunk[] } {
  const lines = content.split('\n')
  const summaryLines: string[] = []
  const chunks: AnalysisChunk[] = []

  // 匹配正则：- **1. 主语**：`...` 或 - **主语**：`...`
  // 支持有数字和没数字的情况
  const chunkRegex = /^-\s*\*\*(?:(\d+)\.\s*)?([^*]+)\*\*[：:]\s*[`'"](.+)[`'"]$/

  lines.forEach(line => {
    const trimmed = line.trim()
    if (!trimmed) return

    const match = trimmed.match(chunkRegex)
    if (match) {
      chunks.push({
        order: match[1] || '',
        label: match[2].trim(),
        text: match[3].trim(),
      })
    } else {
      // 只有在还没开始匹配到 chunks 时，才把行加入 summary
      if (chunks.length === 0) {
        summaryLines.push(trimmed)
      }
    }
  })

  return {
    summary: summaryLines.join('\n'),
    chunks: chunks.sort((a, b) => {
      if (!a.order || !b.order) return 0
      return parseInt(a.order) - parseInt(b.order)
    }),
  }
}

export default function AnalysisCard({
  type,
  title,
  label,
  content,
  phonetic,
  tags,
  initiallyExpanded,
}: AnalysisCardProps) {
  const globalDefaultExpanded = useConfigStore((s) => s.defaultCardExpanded)
  const [isExpanded, setIsExpanded] = useState(initiallyExpanded ?? globalDefaultExpanded)

  // 同步全局配置
  useEffect(() => {
    if (initiallyExpanded === undefined) {
      setIsExpanded(globalDefaultExpanded)
    }
  }, [globalDefaultExpanded, initiallyExpanded])

  const config = TYPE_CONFIG[type]

  // 如果是句式解析，进行结构化解析
  const structuredData = type === 'sentence' ? parseSentenceAnalysis(content) : null

  return (
    <View className={`analysis-card ${config.colorClass} ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <View className='card-header' onClick={() => setIsExpanded(!isExpanded)}>
        <View className='header-left'>
          <View className='icon-wrapper'>
            <LucideIcon name={config.icon} size={14} color={config.accentColor} />
          </View>
          <Text className='card-label'>{label || config.defaultLabel}</Text>
        </View>
        <View className='header-right'>
          <LucideIcon 
            name={isExpanded ? 'chevron-up' : 'chevron-down'} 
            size={16} 
            color='var(--text-sub)' 
          />
        </View>
      </View>

      <View className='card-body'>
        <View className='card-title-row'>
          <Text className='card-title'>{title}</Text>
          {phonetic && <Text className='card-phonetic'>/{phonetic}/</Text>}
          {tags && tags.length > 0 && (
            <View className='card-tags'>
              {tags.map((tag) => (
                <View key={tag} className='tag-badge'>{tag}</View>
              ))}
            </View>
          )}
        </View>
        
        {isExpanded && (
          <View className='card-content-wrapper'>
            {type === 'sentence' && structuredData && structuredData.chunks.length > 0 ? (
              <View className='structured-analysis'>
                {structuredData.summary && (
                  <Text className='analysis-summary'>{structuredData.summary}</Text>
                )}
                <View className='analysis-steps'>
                  {structuredData.chunks.map((chunk, idx) => (
                    <View key={idx} className='step-item'>
                      <View className='step-dot-line'>
                        <View className='step-dot'>{chunk.order || idx + 1}</View>
                        {idx < structuredData.chunks.length - 1 && <View className='step-line' />}
                      </View>
                      <View className='step-content'>
                        <Text className='step-label'>{chunk.label}</Text>
                        <Text className='step-text'>{chunk.text}</Text>
                      </View>
                    </View>
                  ))}
                </View>
              </View>
            ) : (
              <Text className='card-content'>{content}</Text>
            )}
          </View>
        )}
      </View>
    </View>
  )
}
