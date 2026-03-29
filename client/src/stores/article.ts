import { create } from 'zustand'
import { AnalysisResponse } from '../types/schema'

interface ArticleState {
  currentAnalysis: AnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  setAnalysis: (analysis: AnalysisResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useArticleStore = create<ArticleState>((set) => ({
  currentAnalysis: null,
  isLoading: false,
  error: null,
  setAnalysis: (analysis) => set({ currentAnalysis: analysis, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  reset: () => set({ currentAnalysis: null, isLoading: false, error: null }),
}))
