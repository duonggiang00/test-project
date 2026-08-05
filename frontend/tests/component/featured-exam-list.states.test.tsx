import { render, screen } from '@testing-library/react';

import FeaturedExamList from '@/components/features/student-home/FeaturedExamList';
import { useStudentExams } from '../../src/hooks/useStudentExams';


jest.mock('../../src/hooks/useStudentExams', () => ({
  useStudentExams: jest.fn(),
}));

const mockedUseStudentExams = jest.mocked(useStudentExams);
const emptyPagination = { items: [], total: 0, page: 1, size: 4, pages: 1 };

describe('FeaturedExamList non-happy paths', () => {
  test('renders an explicit loading state', () => {
    mockedUseStudentExams.mockReturnValue({
      exams: [],
      pagination: emptyPagination,
      isLoading: true,
      isError: undefined,
      mutate: jest.fn(),
    });

    render(<FeaturedExamList />);

    expect(screen.getByTestId('featured-exams-loading')).toBeVisible();
  });

  test('renders a monochrome error state', () => {
    mockedUseStudentExams.mockReturnValue({
      exams: [],
      pagination: emptyPagination,
      isLoading: false,
      isError: new Error('network'),
      mutate: jest.fn(),
    });

    render(<FeaturedExamList />);

    expect(screen.getByTestId('featured-exams-error')).toBeVisible();
    expect(screen.queryByTestId('featured-exams-loading')).not.toBeInTheDocument();
  });

  test('renders an explicit empty state', () => {
    mockedUseStudentExams.mockReturnValue({
      exams: [],
      pagination: emptyPagination,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });

    render(<FeaturedExamList />);

    expect(screen.getByTestId('featured-exams-empty')).toBeVisible();
  });
});
