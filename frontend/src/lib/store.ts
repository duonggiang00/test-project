import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { logBackendError } from './errors';

interface UserState {
  user: { id: string; email: string; role: string; full_name: string | null } | null;
  setUser: (user: UserState['user']) => void;
  clearUser: () => void;
  logout: () => Promise<boolean>;
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  clearUser: () => set({ user: null }),
  logout: async () => {
    if (typeof window === 'undefined') return false;
    try {
      const { csrfHeaders } = await import('./csrf');
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        headers: await csrfHeaders(),
      });
      if (!response.ok) {
        logBackendError('Logout failed', await response.json().catch(() => null));
        return false;
      }
      const { mutate } = await import('swr');
      await mutate('/auth/me', null, { revalidate: false });
      set({ user: null });
      return true;
    } catch (error) {
      logBackendError('Logout failed', error);
      return false;
    }
  },
}));

interface ExamState {
  examId: string | null;
  startTime: number | null;
  durationMinutes: number | null;
  answers: Record<string, string>; // questionId -> optionId
  setExamData: (id: string, duration: number) => void;
  setAnswer: (qId: string, optId: string) => void;
  clearExam: () => void;
}

export const useExamStore = create<ExamState>()(
  persist(
    (set) => ({
      examId: null,
      startTime: null,
      durationMinutes: null,
      answers: {},
      setExamData: (id, duration) => set({ examId: id, durationMinutes: duration, startTime: Date.now(), answers: {} }),
      setAnswer: (qId, optId) => set((state) => ({
        answers: { ...state.answers, [qId]: optId },
      })),
      clearExam: () => set({ examId: null, startTime: null, durationMinutes: null, answers: {} }),
    }),
    {
      name: 'exam-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
