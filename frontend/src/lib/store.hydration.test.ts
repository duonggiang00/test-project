import { useUserStore } from './store';


describe('user store session authority', () => {
  beforeEach(() => {
    window.localStorage.clear();
    useUserStore.setState({ user: null });
    document.cookie = 'csrf_token=csrf-secret; path=/';
    jest.restoreAllMocks();
  });

  afterEach(() => {
    Reflect.deleteProperty(global, 'fetch');
  });

  test('ignores stale persisted role data', () => {
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

    expect(useUserStore.getState().user).toBeNull();
    expect('persist' in useUserStore).toBe(false);
    expect(window.localStorage.getItem('token')).toBeNull();
  });

  test('keeps the hydrated user when server-side logout fails', async () => {
    const user = {
      id: 'user-1',
      email: 'teacher@example.com',
      role: 'teacher',
      full_name: 'Teacher',
    };
    useUserStore.setState({ user });
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
          error_code: 'LOGOUT_FAILED',
          details: {},
          request_id: null,
      }),
    } as Response);
    jest.spyOn(console, 'error').mockImplementation(() => undefined);

    await expect(useUserStore.getState().logout()).resolves.toBe(false);
    expect(useUserStore.getState().user).toEqual(user);
  });

  test('clears the hydrated user only after server-side logout succeeds', async () => {
    useUserStore.setState({
      user: {
        id: 'user-1',
        email: 'teacher@example.com',
        role: 'teacher',
        full_name: 'Teacher',
      },
    });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);

    await expect(useUserStore.getState().logout()).resolves.toBe(true);
    expect(useUserStore.getState().user).toBeNull();
  });
});
