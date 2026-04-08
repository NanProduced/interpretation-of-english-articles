import { create } from 'zustand'

export type UserPurpose = 'exam' | 'academic' | 'daily';

interface ConfigState {
  purpose: UserPurpose;
  level: string | null;
  defaultCardExpanded: boolean;
  setPurpose: (purpose: UserPurpose) => void;
  setLevel: (level: string | null) => void;
  setDefaultCardExpanded: (expanded: boolean) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  purpose: 'daily',
  level: null,
  defaultCardExpanded: false,
  setPurpose: (purpose) => set({ purpose }),
  setLevel: (level) => set({ level }),
  setDefaultCardExpanded: (expanded) => set({ defaultCardExpanded: expanded }),
}))
