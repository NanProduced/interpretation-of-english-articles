import { create } from 'zustand'

export type UserPurpose = 'exam' | 'academic' | 'daily';

interface ConfigState {
  purpose: UserPurpose;
  setPurpose: (purpose: UserPurpose) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  purpose: 'daily',
  setPurpose: (purpose) => set({ purpose }),
}))
