/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import axios from 'axios';
import { useAuthStore } from './stores/auth';
import { useRouter } from 'vue-router';

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export const createApiClient = () => {
  const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  // Request interceptor: Add auth token to headers
  api.interceptors.request.use(
    (config) => {
      const authStore = useAuthStore();
      if (authStore.token) {
        config.headers.Authorization = `Token ${authStore.token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor: Handle auth errors
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401 || error.response?.status === 403) {
        const authStore = useAuthStore();
        authStore.logout();
        
        // Redirect to login if not already there
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
      return Promise.reject(error);
    }
  );

  return api;
};

// Export a singleton instance for convenience
export default createApiClient();
