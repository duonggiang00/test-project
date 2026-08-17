import type { Exam } from './index';


describe('frontend API types', () => {
  test('accepts an explicit null creator for quarantined legacy exams', () => {
    const legacyExam: Exam = {
      id: 'legacy-exam',
      title: 'Legacy quarantined exam',
      description: null,
      duration_minutes: 30,
      is_published: false,
      topic_id: null,
      creator_id: null,
    };

    expect(legacyExam.creator_id).toBeNull();
  });
});
