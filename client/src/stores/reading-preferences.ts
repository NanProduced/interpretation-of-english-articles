import Taro from '@tarojs/taro'
import { create } from 'zustand'
import { useAuthStore } from './auth'
import { updateProfile } from '../services/api/client'

export type FontSize = 'small' | 'standard' | 'large' | 'xlarge'
export type Spacing = 'compact' | 'standard' | 'loose'
export type TranslationDisplay = 'hidden' | 'muted' | 'standard'
export type PaperTheme = 'paper' | 'white' | 'sage'
export type AnnotationIntensity = 'quiet' | 'standard' | 'clear'

export interface ReadingPreferences {
  font_size: FontSize
  line_height: Spacing
  paragraph_spacing: Spacing
  translation_display: TranslationDisplay
  paper_theme: PaperTheme
  annotation_intensity: AnnotationIntensity
  updated_at?: string
}

export const DEFAULT_READING_PREFERENCES: ReadingPreferences = {
  font_size: 'standard',
  line_height: 'standard',
  paragraph_spacing: 'standard',
  translation_display: 'muted',
  paper_theme: 'paper',
  annotation_intensity: 'standard',
}

const PREF_STORAGE_KEY = 'reading_preferences_local'

let _cloudSyncTimer: ReturnType<typeof setTimeout> | null = null

interface ReadingPreferencesState {
  preferences: ReadingPreferences

  updatePreferences: (updates: Partial<ReadingPreferences>) => void

  syncFromAuth: () => void
}

export const useReadingPreferencesStore = create<ReadingPreferencesState>((set, get) => {
  const saved = Taro.getStorageSync(PREF_STORAGE_KEY)
  const initialPreferences = saved ? { ...DEFAULT_READING_PREFERENCES, ...JSON.parse(saved) } : DEFAULT_READING_PREFERENCES

  return {
    preferences: initialPreferences,

    updatePreferences: (updates) => {
      const newPrefs = {
        ...get().preferences,
        ...updates,
        updated_at: new Date().toISOString(),
      }

      set({ preferences: newPrefs })
      Taro.setStorageSync(PREF_STORAGE_KEY, JSON.stringify(newPrefs))

      const authStore = useAuthStore.getState()
      if (authStore.isLoggedIn) {
        if (_cloudSyncTimer) clearTimeout(_cloudSyncTimer)
        _cloudSyncTimer = setTimeout(() => {
          const currentSettings = useAuthStore.getState().userInfo?.settings || {}
          const latestPrefs = get().preferences
          const newSettings = {
            ...currentSettings,
            reading_preferences: latestPrefs,
          }

          updateProfile({ settings: newSettings }).then(() => {
            useAuthStore.getState().updateUserInfo({ settings: newSettings })
          }).catch(err => {
            console.warn('[reading-preferences] Failed to sync preferences to cloud', err)
          })
        }, 500)
      }
    },

    syncFromAuth: () => {
      const authStore = useAuthStore.getState()
      const cloudPrefs = authStore.userInfo?.settings?.reading_preferences

      if (cloudPrefs) {
        const localPrefs = get().preferences
        const cloudTime = cloudPrefs.updated_at ? new Date(cloudPrefs.updated_at).getTime() : 0
        const localTime = localPrefs.updated_at ? new Date(localPrefs.updated_at).getTime() : 0

        if (cloudTime >= localTime) {
          const merged = { ...DEFAULT_READING_PREFERENCES, ...cloudPrefs }
          set({ preferences: merged })
          Taro.setStorageSync(PREF_STORAGE_KEY, JSON.stringify(merged))
        }
      }
    }
  }
})

useAuthStore.subscribe((state, prevState) => {
  if (state.userInfo?.settings?.reading_preferences !== prevState.userInfo?.settings?.reading_preferences) {
    useReadingPreferencesStore.getState().syncFromAuth()
  }
})
