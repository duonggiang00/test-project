import { useUserStore } from './store';


describe('user store hydration', () => {
  beforeEach(() => {
    window.localStorage.clear();
    useUserStore.setState({ user: null });
  });

  test('rehydrates the persisted user without persisting an access token', async () => {
    window.localStorage.setItem(
      'user-storage',
      JSON.stringify({
        state: {
          user: {
            id: 'user-1',
            email: 'teacher@example.com',
            role: 'teacher',
            full_name: 'Teacher',
          },
        },
        version: 0,
      }),
    );

    await useUserStore.persist.rehydrate();

    expect(useUserStore.getState().user).toEqual({
      id: 'user-1',
      email: 'teacher@example.com',
      role: 'teacher',
      full_name: 'Teacher',
    });
    expect(window.localStorage.getItem('token')).toBeNull();
  });
});
