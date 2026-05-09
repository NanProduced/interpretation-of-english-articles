import { View, Text } from '@tarojs/components'
import { memo } from 'react'
import { 
  useReadingPreferencesStore, 
  FontSize, 
  Spacing, 
  TranslationDisplay, 
  PaperTheme, 
  AnnotationIntensity 
} from '../../stores/reading-preferences'
import LucideIcon from '../LucideIcon'
import './index.scss'

interface Props {
  visible: boolean
  onClose: () => void
}

const ReadingSettingsSheet = memo(function ReadingSettingsSheet({ visible, onClose }: Props) {
  const { preferences, updatePreferences } = useReadingPreferencesStore()

  if (!visible) return null

  const fontSizes: { value: FontSize; label: string }[] = [
    { value: 'small', label: '小' },
    { value: 'standard', label: '标准' },
    { value: 'large', label: '大' },
    { value: 'xlarge', label: '特大' }
  ]

  const spacings: { value: Spacing; label: string }[] = [
    { value: 'compact', label: '紧凑' },
    { value: 'standard', label: '标准' },
    { value: 'loose', label: '宽松' }
  ]

  const translations: { value: TranslationDisplay; label: string }[] = [
    { value: 'hidden', label: '隐藏' },
    { value: 'muted', label: '淡显' },
    { value: 'standard', label: '标准' }
  ]

  const themes: { value: PaperTheme; label: string; color: string }[] = [
    { value: 'paper', label: '纸张', color: '#F9F5EC' },
    { value: 'white', label: '纯白', color: '#FFFFFF' },
    { value: 'sage', label: '护眼', color: '#F0F4F0' }
  ]

  const intensities: { value: AnnotationIntensity; label: string }[] = [
    { value: 'quiet', label: '克制' },
    { value: 'standard', label: '标准' },
    { value: 'clear', label: '明显' }
  ]

  return (
    <View className='rs-overlay' onClick={onClose}>
      <View className='rs-sheet' onClick={(e) => e.stopPropagation()}>
        <View className='rs-handle' />
        <View className='rs-header'>
          <Text className='rs-title'>阅读设置</Text>
          <View className='rs-close' onClick={onClose}>
            <LucideIcon name='x' size={20} color='var(--text-muted)' />
          </View>
        </View>

        <View className='rs-scroll-area'>
          {/* 背景色 */}
          <View className='rs-section'>
            <Text className='rs-section-label'>背景</Text>
            <View className='rs-theme-group'>
              {themes.map(t => (
                <View 
                  key={t.value} 
                  className={`rs-theme-item ${preferences.paper_theme === t.value ? 'rs-theme-item--active' : ''}`}
                  onClick={() => updatePreferences({ paper_theme: t.value })}
                >
                  <View className='rs-theme-circle' style={{ backgroundColor: t.color }}>
                    {preferences.paper_theme === t.value && (
                      <LucideIcon name='check' size={16} color={t.value === 'paper' ? '#8C7A5E' : '#999'} />
                    )}
                  </View>
                  <Text className='rs-theme-label'>{t.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 字号 */}
          <View className='rs-section'>
            <Text className='rs-section-label'>字号</Text>
            <View className='rs-segment-group'>
              {fontSizes.map(f => (
                <View 
                  key={f.value}
                  className={`rs-segment-item ${preferences.font_size === f.value ? 'rs-segment-item--active' : ''}`}
                  onClick={() => updatePreferences({ font_size: f.value })}
                >
                  <Text className={`rs-font-icon rs-font-icon--${f.value}`}>A</Text>
                  <Text className='rs-segment-text'>{f.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 行距 & 段距 */}
          <View className='rs-row-sections'>
            <View className='rs-section rs-section--half'>
              <Text className='rs-section-label'>行距</Text>
              <View className='rs-segment-group rs-segment-group--small'>
                {spacings.map(s => (
                  <View 
                    key={s.value}
                    className={`rs-segment-item ${preferences.line_height === s.value ? 'rs-segment-item--active' : ''}`}
                    onClick={() => updatePreferences({ line_height: s.value })}
                  >
                    <Text className='rs-segment-text'>{s.label}</Text>
                  </View>
                ))}
              </View>
            </View>

            <View className='rs-section rs-section--half'>
              <Text className='rs-section-label'>段距</Text>
              <View className='rs-segment-group rs-segment-group--small'>
                {spacings.map(s => (
                  <View 
                    key={s.value}
                    className={`rs-segment-item ${preferences.paragraph_spacing === s.value ? 'rs-segment-item--active' : ''}`}
                    onClick={() => updatePreferences({ paragraph_spacing: s.value })}
                  >
                    <Text className='rs-segment-text'>{s.label}</Text>
                  </View>
                ))}
              </View>
            </View>
          </View>

          {/* 译文显示 */}
          <View className='rs-section'>
            <Text className='rs-section-label'>译文</Text>
            <View className='rs-segment-group'>
              {translations.map(t => (
                <View 
                  key={t.value}
                  className={`rs-segment-item ${preferences.translation_display === t.value ? 'rs-segment-item--active' : ''}`}
                  onClick={() => updatePreferences({ translation_display: t.value })}
                >
                  <Text className='rs-segment-text'>{t.label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 标注强度 */}
          <View className='rs-section'>
            <Text className='rs-section-label'>标注强度</Text>
            <View className='rs-segment-group'>
              {intensities.map(i => (
                <View 
                  key={i.value}
                  className={`rs-segment-item ${preferences.annotation_intensity === i.value ? 'rs-segment-item--active' : ''}`}
                  onClick={() => updatePreferences({ annotation_intensity: i.value })}
                >
                  <Text className='rs-segment-text'>{i.label}</Text>
                </View>
              ))}
            </View>
          </View>
        </View>
      </View>
    </View>
  )
})

export default ReadingSettingsSheet
