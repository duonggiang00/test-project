import { useExamStore } from './store';

describe('useExamStore', () => {
  beforeEach(() => {
    // Reset Zustand store state and localStorage between tests
    useExamStore.setState({ examId: null, startTime: null, durationMinutes: null, answers: {} });
    localStorage.clear();
  });

  it('should initialize exam data', () => {
    useExamStore.getState().setExamData('exam-123', 60);
    const state = useExamStore.getState();
    
    expect(state.examId).toBe('exam-123');
    expect(state.durationMinutes).toBe(60);
    expect(state.answers).toEqual({});
    expect(state.startTime).toBeDefined();
  });

  it('should set answers correctly', () => {
    useExamStore.getState().setExamData('exam-123', 60);
    useExamStore.getState().setAnswer('q1', 'opt1');
    
    const state = useExamStore.getState();
    expect(state.answers).toEqual({ q1: 'opt1' });
  });

  it('should clear exam data', () => {
    useExamStore.getState().setExamData('exam-123', 60);
    useExamStore.getState().clearExam();
    
    const state = useExamStore.getState();
    expect(state.examId).toBeNull();
    expect(state.answers).toEqual({});
  });
});
