/**
 * Axios Client — BI AI Agent Data Analyst
 *
 * - Base URL lấy từ import.meta.env.VITE_API_BASE_URL (mặc định http://127.0.0.1:8000)
 * - Tự động inject header X-API-Key vào mọi request
 * - Interceptor xử lý lỗi tập trung (401, 413, 422, 500...)
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
  timeout: 120_000,               // 2 minutes — phù hợp với LLM + E2B
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
        400: 'Yêu cầu không hợp lệ. Vui lòng kiểm tra lại dữ liệu đầu vào.',
        401: 'Xác thực thất bại. Vui lòng kiểm tra API key.',
        403: 'Bạn không có quyền truy cập tài nguyên này.',
        404: 'Tài nguyên không tìm thấy.',
        413: 'File quá lớn. Kích thước tối đa là 100MB.',
        422: 'Dữ liệu không thể xử lý. Vui lòng kiểm tra định dạng file.',
        429: 'Quá nhiều yêu cầu. Vui lòng thử lại sau.',
        500: 'Lỗi máy chủ nội bộ. Vui lòng thử lại sau.',
        503: 'Dịch vụ tạm thời không khả dụng (LLM/E2B).',
      };

      const message =
        data?.detail ||
        statusMessages[status] ||
        `Lỗi máy chủ (${status})`;

      return Promise.reject(new Error(message));
    }

    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Kết nối bị timeout. Vui lòng thử lại.'));
    }

    if (!error.response) {
      return Promise.reject(new Error('Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng.'));
    }

    return Promise.reject(error);
  },
);

export default axiosClient;