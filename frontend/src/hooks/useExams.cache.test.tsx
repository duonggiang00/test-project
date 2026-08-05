import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { SWRConfig } from 'swr';

import { fetcher } from './useFetch';
import { useExams } from './useExams';


jest.mock('./useFetch', () => ({
  fetcher: jest.fn(),
}));

const mockedFetcher = jest.mocked(fetcher);

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
}

describe('useExams cache coordination', () => {
  test('mutates cached server state without a page reload', async () => {
    mockedFetcher.mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      size: 50,
      pages: 0,
    });
    const { result } = renderHook(() => useExams(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.mutate(
        {
          items: [
            {
              id: 'exam-1',
              title: 'Cached exam',
              description: null,
              duration_minutes: 30,
              is_published: true,
              topic_id: null,
              creator_id: 'teacher-1',
              created_at: '2026-08-05T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          size: 50,
          pages: 1,
        },
        { revalidate: false },
      );
    });

    expect(result.current.exams).toHaveLength(1);
    expect(result.current.exams[0].title).toBe('Cached exam');
    expect(mockedFetcher).toHaveBeenCalledTimes(1);
  });
});
