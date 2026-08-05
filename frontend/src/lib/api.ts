import axios from 'axios';
import { useUserStore } from './store';

const api = axios.create({
  baseURL: '/api/proxy',
  headers: {
    'Content-Type': 'application/json',
  },
});

// We don't need a request interceptor anymore because the 
// HttpOnly cookie is automatically sent to the Next.js /api/proxy route.

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        // Clear zustand user state and token, then redirect
        useUserStore.getState().logout().then(() => {
          // Prevent redirect loop if already on login
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        });
      }
    }
    return Promise.reject(error);
  }
);

export default api;
