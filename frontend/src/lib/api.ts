import axios from 'axios';
import { CSRF_HEADER } from './auth-contract';
import { ensureCsrfToken } from './csrf';
import { useUserStore } from './store';

const api = axios.create({
  baseURL: '/api/proxy',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config) => {
  const method = config.method?.toUpperCase();
  if (method && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    config.headers.set(CSRF_HEADER, await ensureCsrfToken());
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        useUserStore.getState().clearUser();
        if (!window.location.pathname.includes('/login')) {
          window.location.assign('/login');
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
