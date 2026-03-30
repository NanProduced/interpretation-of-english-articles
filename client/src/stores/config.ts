import { create } from 'zustand'

export type UserPurpose = 'exam' | 'academic' | 'daily';

interface ConfigState {
  purpose: UserPurpose;
  level: string | null;
  setPurpose: (purpose: UserPurpose) => void;
  setLevel: (level: string | null) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  purpose: 'daily',
  level: null,
  setPurpose: (purpose) => set({ purpose }),
  setLevel: (level) => set({ level }),
}))
