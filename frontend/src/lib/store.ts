import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface UserState {
  user: { id: string; email: string; role: string; full_name: string } | null;
  setUser: (user: UserState['user']) => void;
  logout: () => Promise<void>;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      logout: async () => {
        set({ user: null });
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          await fetch('/api/auth/logout', { method: 'POST' }).catch(console.error);
        }
      },
    }),
    {
      name: 'user-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

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
