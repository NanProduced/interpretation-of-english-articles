import { View, Text } from '@tarojs/components'
import { memo, useState } from 'react'
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
  const [activePanel, setActivePanel] = useState<'paper' | 'type' | 'rhythm' | 'translation' | 'annotation'>('type')

  if (!visible) return null

  const fontSizes: { value: FontSize; aSize: string }[] = [
    { value: 'small', aSize: '24rpx' },
    { value: 'standard', aSize: '30rpx' },
    { value: 'large', aSize: '34rpx' },
    { value: 'xlarge', aSize: '40rpx' }
  ]

  const spacings: { value: Spacing; mark: string }[] = [
    { value: 'compact', mark: 'Ⅰ' },
    { value: 'standard', mark: 'Ⅱ' },
    { value: 'loose', mark: 'Ⅲ' }
  ]

  const themes: { value: PaperTheme; label: string; color: string; tint: string }[] = [
    { value: 'paper', label: '纸张', color: '#F9F5EC', tint: '#B59C77' },
    { value: 'white', label: '纯白', color: '#FFFFFF', tint: '#C9CDD0' },
    { value: 'sage', label: '护眼', color: '#F0F4F0', tint: '#8EA9A0' }
  ]

  const intensities: { value: AnnotationIntensity; label: string; opacity: number; width: string }[] = [
    { value: 'quiet', label: '克制', opacity: 0.32, width: '54%' },
    { value: 'standard', label: '标准', opacity: 0.56, width: '72%' },
    { value: 'clear', label: '明显', opacity: 0.82, width: '92%' },
  ]

  const previewFontSize: Record<FontSize, string> = {
    small: '26rpx',
    standard: '30rpx',
    large: '34rpx',
    xlarge: '38rpx'
  }

  const previewLineHeight: Record<Spacing, string> = {
    compact: '42rpx',
    standard: '50rpx',
    loose: '58rpx'
  }

  const previewParagraphGap: Record<Spacing, string> = {
    compact: '8rpx',
    standard: '18rpx',
    loose: '30rpx'
  }

  const panelCopy = {
    paper: { title: '纸面', hint: '选择适合眼睛的底色' },
    type: { title: '字号', hint: '正文大小实时预览' },
    rhythm: { title: '节奏', hint: '调节正文呼吸感' },
    translation: { title: '译文', hint: '控制中文辅助的存在感' }
  }[activePanel === 'annotation' ? 'type' : activePanel]
  const effectivePanelCopy = activePanel === 'annotation'
    ? { title: '标注', hint: '调节解析标注的存在感' }
    : panelCopy

  const translationOpacity: Record<TranslationDisplay, number> = {
    hidden: 0,
    muted: 0.45,
    standard: 0.86
  }

  return (
    <View className='rs-overlay' onClick={onClose}>
      <View className='rs-sheet' onClick={(e) => e.stopPropagation()}>
        <View className='rs-handle' />

        <View className='rs-tray'>
          <View className='rs-dock'>
            <View
              className={`rs-dock-button ${activePanel === 'paper' ? 'rs-dock-button--active' : ''}`}
              onClick={() => setActivePanel('paper')}
            >
              <LucideIcon name='bookOpen' size={30} color={activePanel === 'paper' ? '#315E67' : '#201F1C'} strokeWidth={1.8} />
              <Text className='rs-dock-label'>纸面</Text>
            </View>
            <View
              className={`rs-dock-button ${activePanel === 'type' ? 'rs-dock-button--active' : ''}`}
              onClick={() => setActivePanel('type')}
            >
              <Text className='rs-dock-aa'>A</Text>
              <Text className='rs-dock-label'>字号</Text>
            </View>
            <View
              className={`rs-dock-button ${activePanel === 'rhythm' ? 'rs-dock-button--active' : ''}`}
              onClick={() => setActivePanel('rhythm')}
            >
              <View className='rs-lines-icon'>
                <View className='rs-lines-icon-line' />
                <View className='rs-lines-icon-line' />
                <View className='rs-lines-icon-line' />
              </View>
              <Text className='rs-dock-label'>节奏</Text>
            </View>
            <View
              className={`rs-dock-button ${activePanel === 'translation' ? 'rs-dock-button--active' : ''}`}
              onClick={() => setActivePanel('translation')}
            >
              <LucideIcon name='languages' size={31} color={activePanel === 'translation' ? '#315E67' : '#201F1C'} strokeWidth={1.7} />
              <Text className='rs-dock-label'>译文</Text>
            </View>
            <View
              className={`rs-dock-button ${activePanel === 'annotation' ? 'rs-dock-button--active' : ''}`}
              onClick={() => setActivePanel('annotation')}
            >
              <LucideIcon name='highlighter' size={30} color={activePanel === 'annotation' ? '#315E67' : '#201F1C'} strokeWidth={1.7} />
              <Text className='rs-dock-label'>标注</Text>
            </View>
          </View>

          <View className='rs-panel'>
            <View className='rs-panel-copy'>
              <Text className='rs-panel-title'>{effectivePanelCopy.title}</Text>
              <Text className='rs-panel-hint'>{effectivePanelCopy.hint}</Text>
            </View>

            {activePanel === 'paper' && (
              <View className='rs-theme-strip'>
                {themes.map(t => (
                  <View
                    key={t.value}
                    className={`rs-theme-option ${preferences.paper_theme === t.value ? 'rs-theme-option--active' : ''}`}
                    onClick={() => updatePreferences({ paper_theme: t.value })}
                    style={{ backgroundColor: t.color }}
                  >
                    <View className='rs-theme-glow' style={{ backgroundColor: t.tint }} />
                    <Text className='rs-theme-label'>{t.label}</Text>
                  </View>
                ))}
              </View>
            )}

            {activePanel === 'type' && (
              <View className='rs-type-panel'>
                <Text
                  className='rs-sample'
                  style={{
                    fontSize: previewFontSize[preferences.font_size],
                    lineHeight: previewLineHeight[preferences.line_height]
                  }}
                >
                  The quick brown fox jumps over the lazy dog.
                </Text>
                <View className='rs-font-strip'>
                  {fontSizes.map(f => (
                    <View
                      key={f.value}
                      className={`rs-font-btn ${preferences.font_size === f.value ? 'rs-font-btn--active' : ''}`}
                      onClick={() => updatePreferences({ font_size: f.value })}
                    >
                      <Text className='rs-font-a' style={{ fontSize: f.aSize }}>A</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {activePanel === 'rhythm' && (
              <View className='rs-rhythm-panel'>
                <View className='rs-rhythm-preview'>
                  <View className='rs-rhythm-paragraph'>
                    <Text
                      className='rs-rhythm-sample'
                      style={{
                        fontSize: previewFontSize[preferences.font_size],
                        lineHeight: previewLineHeight[preferences.line_height]
                      }}
                    >
                      Nature conservation is a critical arena for careful reading.
                    </Text>
                  </View>
                  <View className='rs-rhythm-paragraph' style={{ marginTop: previewParagraphGap[preferences.paragraph_spacing] }}>
                    <Text
                      className='rs-rhythm-sample'
                      style={{
                        fontSize: previewFontSize[preferences.font_size],
                        lineHeight: previewLineHeight[preferences.line_height]
                      }}
                    >
                      A quieter rhythm helps the page breathe.
                    </Text>
                  </View>
                </View>
                <View className='rs-control-row'>
                  <View className='rs-lines-icon rs-lines-icon--muted'>
                    <View className='rs-lines-icon-line' />
                    <View className='rs-lines-icon-line' />
                    <View className='rs-lines-icon-line' />
                  </View>
                  <View className='rs-step-track'>
                    {spacings.map(s => (
                      <View
                        key={s.value}
                        className={`rs-step ${preferences.line_height === s.value ? 'rs-step--active' : ''}`}
                        onClick={() => updatePreferences({ line_height: s.value })}
                      >
                        <Text>{s.mark}</Text>
                      </View>
                    ))}
                  </View>
                </View>
                <View className='rs-control-row'>
                  <View className='rs-paragraph-icon'>
                    <View className='rs-paragraph-line rs-paragraph-line--short' />
                    <View className='rs-paragraph-gap' />
                    <View className='rs-paragraph-line' />
                  </View>
                  <View className='rs-step-track'>
                    {spacings.map(s => (
                      <View
                        key={s.value}
                        className={`rs-step ${preferences.paragraph_spacing === s.value ? 'rs-step--active' : ''}`}
                        onClick={() => updatePreferences({ paragraph_spacing: s.value })}
                      >
                        <Text>{s.mark}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              </View>
            )}

            {activePanel === 'translation' && (
              <View className='rs-translation-panel'>
                <View className='rs-translation-preview'>
                  <Text className='rs-translation-en'>The quick brown fox jumps over the lazy dog.</Text>
                  <Text
                    className='rs-translation-zh'
                    style={{ opacity: translationOpacity[preferences.translation_display] }}
                  >
                    敏捷的棕色狐狸跳过了懒狗。
                  </Text>
                </View>
                <View className='rs-translation-options'>
                  {(['hidden', 'muted', 'standard'] as TranslationDisplay[]).map((t, i) => (
                    <View
                      key={t}
                      className={`rs-meter ${preferences.translation_display === t ? 'rs-meter--active' : ''}`}
                      onClick={() => updatePreferences({ translation_display: t })}
                    >
                      <View className='rs-meter-line' style={{ opacity: i === 0 ? 0.18 : i === 1 ? 0.48 : 0.92 }} />
                      <View className='rs-meter-line rs-meter-line--short' style={{ opacity: i === 0 ? 0.12 : i === 1 ? 0.36 : 0.72 }} />
                      <Text className='rs-meter-label'>{t === 'hidden' ? '隐藏' : t === 'muted' ? '淡显' : '标准'}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {activePanel === 'annotation' && (
              <View className='rs-annotation-panel'>
                <View className='rs-annotation-preview'>
                  <Text className='rs-annotation-line'>The sentence keeps its reading rhythm.</Text>
                  <View className='rs-annotation-mark-row'>
                    <View className='rs-annotation-mark rs-annotation-mark--vocab' style={{ opacity: intensities.find(i => i.value === preferences.annotation_intensity)?.opacity }} />
                    <View className='rs-annotation-mark rs-annotation-mark--phrase' style={{ opacity: intensities.find(i => i.value === preferences.annotation_intensity)?.opacity }} />
                    <View className='rs-annotation-underline' style={{ opacity: intensities.find(i => i.value === preferences.annotation_intensity)?.opacity }} />
                  </View>
                </View>
                <View className='rs-intensity-options'>
                  {intensities.map(item => (
                    <View
                      key={item.value}
                      className={`rs-intensity ${preferences.annotation_intensity === item.value ? 'rs-intensity--active' : ''}`}
                      onClick={() => updatePreferences({ annotation_intensity: item.value })}
                    >
                      <View className='rs-intensity-swatch'>
                        <View className='rs-intensity-fill' style={{ width: item.width, opacity: item.opacity }} />
                      </View>
                      <Text className='rs-intensity-label'>{item.label}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}
          </View>
        </View>
      </View>
    </View>
  )
})

export default ReadingSettingsSheet
