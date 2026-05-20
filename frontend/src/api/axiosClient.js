/**
 * Axios Client — BI AI Agent Data Analyst
 *
 * - Base URL from import.meta.env.VITE_API_BASE_URL (default http://127.0.0.1:8000)
 * - Automatically inject X-API-Key header into every request
 * - Centralized error handling interceptor (401, 413, 422, 500...)
 */

import axios from 'axios';

// ── Base URL ─────────────────────────────────────────────────────────
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_KEY = import.meta.env.VITE_BACKEND_SECRET_TOKEN || '';
console.log('VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
console.log('VITE_BACKEND_SECRET_TOKEN:', import.meta.env.VITE_BACKEND_SECRET_TOKEN);
// ── Instance ─────────────────────────────────────────────────────────
const axiosClient = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,               // 2 minutes — suitable for LLM + E2B
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor: inject API key ─────────────────────────────
axiosClient.interceptors.request.use(
  (config) => {
    if (API_KEY) {
      config.headers['X-API-Key'] = API_KEY;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor: normalize errors ──────────────────────────
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;

      // Map common status codes to user-friendly messages
      const statusMessages = {
        400: 'Invalid request. Please check your input data.',
        401: 'Authentication failed. Please check your API key.',
        403: 'You don\'t have permission to access this resource.',
        404: 'Resource not found.',
        413: 'File too large. Maximum size is 100MB.',
        422: 'Data cannot be processed. Please check file format.',
        429: 'Too many requests. Please try again later.',
        500: 'Internal server error. Please try again later.',
        503: 'Service temporarily unavailable (LLM/E2B).',
      };

      const message =
        data?.detail ||
        statusMessages[status] ||
        `Server error (${status})`;

      return Promise.reject(new Error(message));
    }

    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Connection timeout. Please try again.'));
    }

    if (!error.response) {
      return Promise.reject(new Error('Unable to connect to server. Please check your network connection.'));
    }

    return Promise.reject(error);
  },
);

export default axiosClient;