import { useState, useEffect } from 'react'
import { View, Text, Textarea } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { ROUTES } from '../../config/routes'
import { useConfigStore, UserPurpose } from '../../stores/config'
import { useArticleStore } from '../../stores/article'
import { useLayoutStore } from '../../stores/layout'
import { saveDraft, getDraft, clearDraft } from '../../services/storage'
import { ensureLoggedIn } from '../../services/auth'
import { track } from '../../services/analytics'
import { detectGenre, type GenreDetectionResult } from '../../services/api'
import LucideIcon from '../../components/LucideIcon'
import NavBar from '../../components/NavBar'
import BottomSheetSelect from '../../components/BottomSheetSelect'
import CenterModal from '../../components/CenterModal'
import { READING_CONFIG_MAP, getDisplayLabel, getApiParams, ReadingGoal, SERVER_GOAL_TO_UI_GOAL } from '../../config/purpose'
import './index.scss'

export default function InputPage() {
  const [content, setContent] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [clipboardContent, setClipboardContent] = useState('')
  const [showClipboardBubble, setShowClipboardBubble] = useState(false)
  const [showModeSheet, setShowModeSheet] = useState(false)
  
  const [isDetectingGenre, setIsDetectingGenre] = useState(false)
  const [showAcademicSuggestionModal, setShowAcademicSuggestionModal] = useState(false)
  const [pendingSubmissionConfig, setPendingSubmissionConfig] = useState<{
    purpose: ReadingGoal;
    level: string | null;
  } | null>(null)
  const [lastDetectionResult, setLastDetectionResult] = useState<GenreDetectionResult | null>(null)
  
  const { purpose, level } = useConfigStore()
  const { navBarHeight } = useLayoutStore()
  
  const [tempConfig, setTempConfig] = useState<{
    purpose: ReadingGoal;
    level: string | null;
  }>({
    purpose: purpose as ReadingGoal,
    level: level
  })

  useEffect(() => {
    if (!content) {
      setTempConfig({
        purpose: purpose as ReadingGoal,
        level: level
      })
    }
  }, [purpose, level, content])

  const analyze = useArticleStore((s) => s.analyze)
  const recoverActiveTask = useArticleStore((s) => s.recoverActiveTask)

  const wordsCount = content.trim().split(/\s+/).filter(Boolean).length

  const checkClipboard = async () => {
    try {
      const res = await Taro.getClipboardData()
      const text = res.data?.trim() || ''
      const isEnglish = /[a-zA-Z]{5,}/.test(text)
      if (text.length > 20 && isEnglish && text !== content) {
        setClipboardContent(text)
        setShowClipboardBubble(true)
        const bubbleTimer = setTimeout(() => setShowClipboardBubble(false), 8000)
        return () => clearTimeout(bubbleTimer)
      }
    } catch (e) { console.error("index.tsx:", e) }
  }

  useEffect(() => {
    const draft = getDraft()
    if (draft?.text) setContent(draft.text)
  }, [])

  Taro.useDidShow(() => {
    checkClipboard()
    recoverActiveTask().then(() => {
      const phase = useArticleStore.getState().phase
      if (phase === 'polling' || phase === 'loading') {
        Taro.navigateTo({ url: ROUTES.RESULT })
      }
    })
  })

  useEffect(() => {
    if (!content) return
    const timer = setTimeout(() => {
      const { reading_goal, reading_variant } = getApiParams(tempConfig.purpose, tempConfig.level)
      saveDraft({
        text: content,
        reading_goal: reading_goal,
        reading_variant: reading_variant,
        savedAt: Date.now(),
      })
    }, 500)
    return () => clearTimeout(timer)
  }, [content, tempConfig])

  const handleBack = () => {
    if (content.trim().length > 0) {
      Taro.showModal({
        title: '离开',
        content: '草稿已自动保存',
        confirmText: '离开',
        cancelText: '继续',
        success: (res) => { if (res.confirm) Taro.navigateBack() },
      })
    } else {
      Taro.navigateBack()
    }
  }

  const handleModeChange = () => {
    setShowModeSheet(true)
  }

  const handleModeSelect = (goal: ReadingGoal, level: string | null) => {
    setTempConfig({ purpose: goal, level })
  }

  const shouldSuggestAcademicMode = (
    detection: GenreDetectionResult,
    currentPurpose: ReadingGoal
  ): boolean => {
    if (detection.genre !== 'academic') return false
    if (currentPurpose === 'academic') return false
    if (detection.confidence < 0.6) return false
    if (detection.suggested_goal !== 'academic') return false
    
    return true
  }

  const doSubmit = (submitConfig: { purpose: ReadingGoal; level: string | null }) => {
    const { reading_goal, reading_variant } = getApiParams(submitConfig.purpose, submitConfig.level)
    
    const isUsingAcademicSuggestion = 
      submitConfig.purpose === 'academic' && 
      tempConfig.purpose !== 'academic'
    
    track('submit_article', { 
      wordCount: wordsCount, 
      reading_goal, 
      reading_variant,
      is_temporary_config: submitConfig.purpose !== purpose || submitConfig.level !== level,
      is_academic_suggestion_accepted: isUsingAcademicSuggestion,
      detection_genre: lastDetectionResult?.genre,
      detection_confidence: lastDetectionResult?.confidence,
    })
    
    clearDraft()
    useArticleStore.getState().reset()
    analyze({
      text: content,
      reading_goal: reading_goal,
      reading_variant,
      source_type: 'user_input',
      extended: false,
    })
    Taro.redirectTo({ url: ROUTES.RESULT })
  }

  const handleAcceptAcademicSuggestion = () => {
    setShowAcademicSuggestionModal(false)
    
    track('genre_suggestion_accepted', {
      from_genre: tempConfig.purpose,
      to_genre: 'academic',
      detection_confidence: lastDetectionResult?.confidence,
      word_count: wordsCount,
    })
    
    const academicConfig = {
      purpose: 'academic' as ReadingGoal,
      level: 'academic_general'
    }
    
    doSubmit(academicConfig)
  }

  const handleRejectAcademicSuggestion = () => {
    setShowAcademicSuggestionModal(false)
    
    track('genre_suggestion_rejected', {
      current_genre: tempConfig.purpose,
      suggested_genre: 'academic',
      detection_confidence: lastDetectionResult?.confidence,
      word_count: wordsCount,
    })
    
    if (pendingSubmissionConfig) {
      doSubmit(pendingSubmissionConfig)
    }
    setPendingSubmissionConfig(null)
  }

  const handleSubmit = async () => {
    if (wordsCount < 10) {
      Taro.showToast({ title: '最少输入10个单词', icon: 'none' })
      return
    }

    const loginRes = await ensureLoggedIn()
    if (!loginRes.success) return

    let shouldSkipDetection = false
    
    if (tempConfig.purpose === 'academic') {
      shouldSkipDetection = true
      track('genre_detection_skipped', {
        reason: 'already_academic_mode',
        word_count: wordsCount,
      })
    }
    
    if (wordsCount < 30) {
      shouldSkipDetection = true
      track('genre_detection_skipped', {
        reason: 'text_too_short',
        word_count: wordsCount,
      })
    }

    if (shouldSkipDetection) {
      doSubmit(tempConfig)
      return
    }

    setIsDetectingGenre(true)
    
    try {
      const detectionResponse = await detectGenre(content)
      const detection = detectionResponse.detection
      setLastDetectionResult(detection)
      
      track('genre_detection_completed', {
        genre: detection.genre,
        confidence: detection.confidence,
        suggested_goal: detection.suggested_goal,
        word_count: wordsCount,
        current_mode: tempConfig.purpose,
        signals: detection.signals.join('|'),
        latency_ms: detectionResponse.latency_ms,
      })
      
      if (shouldSuggestAcademicMode(detection, tempConfig.purpose)) {
        track('genre_suggestion_shown', {
          from_genre: tempConfig.purpose,
          suggested_genre: 'academic',
          detection_confidence: detection.confidence,
          word_count: wordsCount,
        })
        
        setPendingSubmissionConfig({ ...tempConfig })
        setShowAcademicSuggestionModal(true)
        setIsDetectingGenre(false)
        return
      }
      
      doSubmit(tempConfig)
      
    } catch (error) {
      console.error('Genre detection failed:', error)
      
      track('genre_detection_failed', {
        error: error instanceof Error ? error.message : 'unknown',
        word_count: wordsCount,
      })
      
      doSubmit(tempConfig)
    } finally {
      setIsDetectingGenre(false)
    }
  }

  return (
    <View className={`input-page ${isFocused ? 'is-focused' : ''}`}>
      <NavBar
        title='Claread透读'
        showBack
        onBack={handleBack}
        background='transparent'
      />
      <View className='nav-placeholder' style={{ height: navBarHeight + 'px' }} />

      <View className='canvas-area'>
        <View className='canvas-toolbar'>
          <View className='mode-chip-v2' onClick={handleModeChange}>
            <View className='dot' />
            <Text className='mode-label'>{getDisplayLabel(tempConfig.purpose, tempConfig.level)}</Text>
            <LucideIcon name='chevronDown' size={14} color='var(--text-sub)' />
          </View>
          
          <View className='toolbar-actions'>
            {content && (
              <View className='t-btn clear' onClick={() => setContent('')} role='button' aria-label='清空内容'>
                <LucideIcon name='eraser' size={18} color='var(--text-muted)' />
              </View>
            )}
          </View>
        </View>

        <View className='textarea-wrapper'>
          <Textarea
            className='content-textarea'
            placeholder=''
            placeholderClass='placeholder-style'
            maxlength={10000}
            value={content}
            onInput={(e) => setContent(e.detail.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            autoFocus
            cursorSpacing={100}
          />
          {!content && (
             <View className='empty-guide' onClick={() => setIsFocused(true)}>
               <Text className='guide-title'>输入英文篇章</Text>
               <Text className='guide-subtitle'>在此开始你的深度阅读之旅</Text>
             </View>
          )}

          {showClipboardBubble && !content && (
            <View className='paste-shortcut' onClick={() => {
              setContent(clipboardContent)
              setShowClipboardBubble(false)
              Taro.showToast({ title: '已注入剪贴板内容', icon: 'none' })
            }}>
              <LucideIcon name='clipboard' size={14} color='var(--text-muted)' />
              <Text>粘贴自剪贴板</Text>
            </View>
          )}
        </View>
      </View>

      <View className='bottom-bar safe-area-bottom'>
        <View className={`interpret-btn ${wordsCount >= 10 && !isDetectingGenre ? 'active' : ''}`} onClick={handleSubmit}>
          <View className='btn-content'>
            <Text className='btn-text'>
              {isDetectingGenre ? '检测文体中...' : '开始透读'}
            </Text>
            <View className='btn-divider' />
            <Text className='btn-stats'>
              {isDetectingGenre ? 'AI 分析' : `${wordsCount} words`}
            </Text>
          </View>
          <LucideIcon 
            name={isDetectingGenre ? 'loader2' : 'sparkles'} 
            size={18} 
            color={wordsCount >= 10 && !isDetectingGenre ? 'var(--color-white)' : 'var(--text-muted)'} 
          />
        </View>
      </View>

      <BottomSheetSelect
        visible={showModeSheet}
        currentGoal={tempConfig.purpose}
        currentLevel={tempConfig.level}
        onClose={() => setShowModeSheet(false)}
        onSelect={handleModeSelect}
      />

      <CenterModal
        visible={showAcademicSuggestionModal}
        title='检测到学术文献'
        onClose={() => {
          setShowAcademicSuggestionModal(false)
          setPendingSubmissionConfig(null)
        }}
      >
        <View className='academic-suggestion-content'>
          <View className='suggestion-icon'>
            <LucideIcon name='microscope' size={48} color='var(--color-ink)' />
          </View>
          
          <Text className='suggestion-title'>这看起来像是一篇学术文献</Text>
          
          <Text className='suggestion-desc'>
            我们检测到您输入的文本可能包含：
          </Text>
          
          {lastDetectionResult?.signals && lastDetectionResult.signals.length > 0 && (
            <View className='suggestion-signals'>
              {lastDetectionResult.signals.slice(0, 3).map((signal, index) => (
                <View key={index} className='signal-tag'>
                  <LucideIcon name='check' size={12} color='var(--color-ink)' />
                  <Text className='signal-text'>{signal}</Text>
                </View>
              ))}
            </View>
          )}
          
          <Text className='suggestion-note'>
            建议使用「学术文献」模式，以获得更精准的术语解析和专业翻译。
          </Text>
          
          <View className='suggestion-actions'>
            <View className='action-btn secondary' onClick={handleRejectAcademicSuggestion}>
              <Text className='action-text'>继续使用当前模式</Text>
            </View>
            <View className='action-btn primary' onClick={handleAcceptAcademicSuggestion}>
              <LucideIcon name='sparkles' size={16} color='#fff' />
              <Text className='action-text'>切换到学术模式</Text>
            </View>
          </View>
          
          <Text className='suggestion-disclaimer'>
            本次切换仅影响当前解析，不会修改您的默认设置
          </Text>
        </View>
      </CenterModal>
    </View>
  )
}
